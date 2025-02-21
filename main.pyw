import datetime
from dataclasses import dataclass
from threading import Thread, Lock
from typing import List, Union, Optional
import logging
import tkinter as tk
from tkinter.ttk import Separator, Style

import ntplib
import darian_datetime as mdatetime

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Settings
WINDOW_TITLE = '时间显示工具（火星版）'
BG_COLOR = '#AA0000'
FG_COLOR = '#FFEF66'
FONT_NAME = 'LXGW Wenkai'
NTP_SERVER = 'ntp.ntsc.ac.cn'
UPDATE_INTERVAL_MS = 20
TIME_SYNC_INTERVAL = 300  # 进行同步的时间间隔（秒
WINDOW_SCALE = 3.0       # 窗口缩放
FONT_EXTRA_SCALE = 1.0  # 对字体进行额外的缩放 如果字体大小炸了可以更改一下


@dataclass
class TimeZoneConfig:
    name: str
    timezone: Union[datetime.timezone, mdatetime.Mtimezone]


class TimeConfigs:
    @classmethod
    def get_default_config(cls) -> List[TimeZoneConfig]:
        return [
            TimeZoneConfig('北 京 时', datetime.timezone(datetime.timedelta(hours=8))),  # noqa: E501
            TimeZoneConfig('协调火星时', mdatetime.Mtimezone(mdatetime.Mtimedelta(0))),  # noqa: E501
        ]


class TimeSync:
    """处理时间同步"""

    def __init__(self):
        self.offset: float = 0.0
        self.last_sync: float = 0.0
        self._lock = Lock()
        self._syncing = False

    def needs_sync(self, current_time: float) -> bool:
        return (current_time - self.last_sync > TIME_SYNC_INTERVAL
                and not self._syncing)

    def sync(self, current_time: float) -> None:
        def _sync_thread():
            with self._lock:
                self._syncing = True
                logger.info(f'Starting time synchronization at {current_time}')

                try:
                    response = ntplib.NTPClient().request(NTP_SERVER)
                    self.offset = response.offset
                    self.last_sync = current_time

                    if response.leap != 0:
                        logger.warning(
                            f'Leap second event possible within 24 hours, leap={response.leap}'  # noqa: E501
                        )

                    logger.info(f'Sync completed at {self.last_sync:.2f}, offset={self.offset}')  # noqa: E501

                except ntplib.NTPException:
                    logger.error('Time synchronization failed')

                finally:
                    self._syncing = False

        # 新建一个线程，防止主线程卡死
        Thread(target=_sync_thread, daemon=True).start()


class TimeDisplay(tk.Frame):
    """用于显示单个时间的子块"""

    def __init__(
        self,
        parent: tk.Widget,
        config: TimeZoneConfig,
        scale: float = 1.0,
        font_extra_scale: float = 1.0
    ):
        super().__init__(parent, bg=BG_COLOR, width=int(270*scale), height=int(120*scale))  # noqa: E501

        self.time_var = tk.StringVar()
        self.date_var = tk.StringVar()
        self.config = config
        self.scale = scale
        self.font_extra_scale = font_extra_scale

        self.pack(side='left', pady=int(self.scale*10), ipadx=int(self.scale*30))  # noqa: E501
        self.pack_propagate(False)

        # 日期以及名称
        header_frame = tk.Frame(
            self,
            bg=BG_COLOR,
            width=int(self.scale*270),
            height=int(self.scale*30)
        )
        header_frame.pack()
        header_frame.pack_propagate(False)

        tk.Label(
            header_frame,
            textvariable=self.date_var,
            font=(FONT_NAME, int(self.scale*self.font_extra_scale*7)),
            fg=FG_COLOR,
            bg=BG_COLOR,
            padx=int(self.scale*3)
        ).pack(side='left')

        tk.Label(
            header_frame,
            text=self.config.name,
            font=(FONT_NAME, int(self.scale*self.font_extra_scale*7)),
            fg=FG_COLOR,
            bg=BG_COLOR,
            padx=int(self.scale*3)
        ).pack(side='right')

        # 时间
        tk.Label(
            self,
            textvariable=self.time_var,
            font=(FONT_NAME, int(self.scale*self.font_extra_scale*20)),
            fg=FG_COLOR,
            bg=BG_COLOR,
            pady=0,
            padx=int(self.scale*3)
        ).pack()

    def update_time(self, utc_time: datetime.datetime, mars_time: mdatetime.Mdatetime) -> None:  # noqa: E501
        """更新界面上显示的时间"""
        if isinstance(self.config.timezone, datetime.timezone):
            local_time = utc_time.astimezone(self.config.timezone)
            self.time_var.set(local_time.strftime('%H:%M:%S'))
            self.date_var.set(local_time.strftime('%Y-%m-%d'))
        elif isinstance(self.config.timezone, mdatetime.Mtimezone):
            local_time = mars_time.astimezone(self.config.timezone)
            self.time_var.set(local_time.strftime('%H:%M:%S'))
            self.date_var.set(local_time.strftime('%Y-%m-%d'))
        else:
            raise TypeError(f'Unsupported timezone type: {type(self.config.timezone)}')  # noqa: E501


class DragWindow(tk.Tk):
    """
    可拖拽窗口类

    部分参考了：
    https://github.com/arcticfox1919/tkinter-tabview/blob/master/dragwindow.py
    """

    def __init__(
        self,
        topmost: bool = True,
        alpha: float = 0.4,
        bg: str = "gray",
        width: Optional[int] = None,
        height: Optional[int] = None
    ):
        super().__init__()

        self.root_x = self.root_y = self.abs_x = self.abs_y = 0
        self.width = width
        self.height = height
        self.on_move = False

        self.configure(bg=bg)
        self.overrideredirect(True)
        self.wm_attributes("-alpha", alpha)
        self.wm_attributes("-topmost", topmost)

        self.bind('<B1-Motion>', self._on_move)
        self.bind('<ButtonPress-1>', self._on_tap)
        self.bind('<ButtonRelease-1>', self._on_tap_end)

    def set_display_position(self, offset_x: int, offset_y: int) -> None:
        """设置窗口位置"""
        self.geometry(f"+{offset_x}+{offset_y}")

    def set_window_size(self, width: int, height: int) -> None:
        """设置窗口大小"""
        self.width = width
        self.height = height
        self.geometry(f"{width}x{height}")

    def _on_tap(self, event: tk.Event) -> None:
        """处理开始拖动事件"""
        self.on_move = True
        self.root_x, self.root_y = event.x_root, event.y_root
        self.abs_x, self.abs_y = self.winfo_x(), self.winfo_y()

    def _on_move(self, event: tk.Event) -> None:
        """处理拖动过程事件"""
        if self.on_move:
            offset_x = event.x_root - self.root_x
            offset_y = event.y_root - self.root_y

            if self.width and self.height:
                geo_str = f"{self.width}x{self.height}+{self.abs_x + offset_x}+{self.abs_y + offset_y}"  # noqa: E501
            else:
                geo_str = f"+{self.abs_x + offset_x}+{self.abs_y + offset_y}"

            self.geometry(geo_str)

    def _on_tap_end(self, event: tk.Event) -> None:
        """处理松开按键（结束拖动）事件"""
        self.on_move = False
        self.root_x, self.root_y = event.x_root, event.y_root
        self.abs_x, self.abs_y = self.winfo_x(), self.winfo_y()


class TimeDisplayApp:
    """
    时间显示工具类

    Usage:
    ----------

    >>> app = TimeDisplayApp()
    >>> app.run()
    """

    def __init__(self):
        self.window = DragWindow(alpha=1, bg=BG_COLOR)
        self.time_sync = TimeSync()
        self.displays: List[TimeDisplay] = []

        configs = TimeConfigs.get_default_config()

        self.window.title(WINDOW_TITLE)
        self.window.set_window_size(
            int(330 * len(configs) * WINDOW_SCALE),
            int(110 * WINDOW_SCALE)
        )
        self.window.set_display_position(100, 100)
        style = Style()
        style.configure('sep_line_1.TSeparator', background=FG_COLOR)

        # 右键退出
        self.window.bind('<ButtonPress-3>', self._on_exit)

        # 按照顺序放置每个子块
        for i, config in enumerate(configs):
            if i > 0:
                Separator(
                    self.window,
                    orient='vertical',
                    style='sep_line_1.TSeparator'
                ).pack(fill='y', side='left')

            self.displays.append(TimeDisplay(self.window, config, WINDOW_SCALE, FONT_EXTRA_SCALE))  # noqa: E501

    def _update_displays(self) -> None:
        """同步并更新时间"""
        current_time = datetime.datetime.now().timestamp() + self.time_sync.offset  # noqa: E501

        # 同步时间
        if self.time_sync.needs_sync(current_time):
            self.time_sync.sync(current_time)

        # 更新时间
        utc_time = datetime.datetime.fromtimestamp(
            current_time, datetime.UTC
        ).replace(
            tzinfo=datetime.timezone.utc
        )
        mars_time = mdatetime.E2M(utc_time)

        # 更新显示
        for display in self.displays:
            display.update_time(utc_time, mars_time)

        self.window.after(UPDATE_INTERVAL_MS, self._update_displays)

    def _on_exit(self, event: tk.Event) -> None:
        """退出"""
        logger.info('Application closing')
        self.window.destroy()

    def run(self) -> None:
        """开始运行"""
        self._update_displays()
        self.window.mainloop()


if __name__ == '__main__':
    app = TimeDisplayApp()
    app.run()
