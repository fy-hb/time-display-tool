"""
Concrete Darian Martian date/time and related type,
convert Gregorian calendar and the Darian Martian calendar to each other.

Mostly adapted from Python's datetime library.

Regarding conversion accuracy: The conversion results are not significantly
different from NASA's MARS24 application.

The syntax is similar to datetime library, but with some subtle differences:
1. Each element of Martian date/time was preceded by the letter "M", which
   stands for "Mars".
2. Each method or function related to ISO is not available in Martian date/time
   class, for there is no ISO standard for Martian date/time. Use other methods
   such as strftime instead.
3. All the words "day" are replaced by "sol", such as:
   >>> from darian_datetime import *
   >>> from datetime import *
   >>> print(Mdate(219,13,27).sol)  # [1]
   '27'
   >>> print(Mtimedelta(1,2,3,4,5,6))
   '1 sol, 6:05:02.004003(Martian)'
   But you can still input the word "day":
   >>> print(Mdate(219,13,27).day)  # equal to [1]
   '27'
4. All the words "utc" are replaced by "mtc", but different to 3., "utc" can't
   be used, examples omitted.
5. You can use the function "E2M"(which means "Earth to Mars") to convert a
   timedelta or datetime class to a Mtimedelta or Mdatetime class, such as:
   >>> e = datetime(2021,4,29,5,25,35,132504,timezone(timedelta(0)))
   >>> print(E2M(e))
   '0219-03-24 22:52:59.725889+00:00(Martian)'
6. Function "M2E"(which means "Mars to Earth") can be used in a similar way.
7. You can easily compare or do operations on timedelta, Mtimedelta, datetime
   and Mdatetime classes without having to use "M2E" or "E2M" function. Have a
   try! Examples:
   >>> e = datetime(2021,4,29,13,25,35,132504,timezone(timedelta(hours=8)))
   >>> m = Mdatetime(218,22,18,9,24,59,13291,Mtimezone(Mtimedelta(hours=-5)))
   >>> print(e-m)
   '149 days, 8:22:09.066854'
   >>> print(m-e)
   '-146 sols, 15:31:59.287402(Martian)'
   >>> print(m>e)
   'False'

NOTE: Leap seconds are unpredictable, so this library's calculations are
slightly off, and the further away the time is from the present, the greater
the off is.

* See http://ops-alaska.com/time/gangale_mst/darian.htm for Darian Martian
calendar's rules.
* See http://ops-alaska.com/time/gangale_converter/7_clock.htm for online
Darian clock.

"""

__all__ = ("Mdate", "Mdatetime", "Mtime", "Mtimedelta", "Mtimezone", "Mtzinfo",
           "MMINYEAR", "MMAXYEAR", "E2M", "M2E")

import datetime
import math as _math
import time as _time


def _cmp(x, y):
    return 0 if x == y else 1 if x > y else -1


MMINYEAR = 0
MMAXYEAR = 9999
_MAXORDINAL = 6685945  # Mdate.max.toordinal()

# NOTE: Different to the datetime library, the code here calls
# Sagittarius(1st month) 1 of year 0 sol number 1, for I want to add year 0,
# about AD 1609/1610, when Johannes Kepler published his first two laws of
# planetary motion and Galileo Galilei observed the phases of Mars, to the
# range.


def _is_leap(y):
    "y(year) -> True if leap year, else False."
    # I'm sorry I couldn't program it more succinctly.
    if y <= 2000:  # in the calendar's rule, y must be 0 or more.
        if y % 1000 == 0:
            return True
        elif y % 100 == 0:
            return False
        elif y % 10 == 0:
            return True
        elif y % 2 == 1:
            return True
        return False
    elif y <= 4800:
        if y % 150 == 0:
            return False
        elif y % 10 == 0:
            return True
        elif y % 2 == 1:
            return True
        return False
    elif y <= 6800:
        # Actually, these time exceed the year 9999 AD,
        # which is not supported by datetime lib.
        if y % 200 == 0:
            return False
        elif y % 10 == 0:
            return True
        elif y % 2 == 1:
            return True
        return False
    elif y <= 8400:
        if y % 300 == 0:
            return False
        elif y % 10 == 0:
            return True
        elif y % 2 == 1:
            return True
        return False
    else:  # in the calendar's rule, y must be 10000 or less.
        if y % 600 == 0:
            return False
        elif y % 10 == 0:
            return True
        elif y % 2 == 1:
            return True
        return False


def _sols_before_year(y):
    "y(year) -> number of sols before January 1st of year."
    x = y-1
    if y <= 2000:
        return y*669 - x//2 + x//10 - x//100 + x//1000
    elif y <= 4800:
        return y*669 - x//2 + x//10 - x//150 - 5
    elif y <= 6800:
        return y*669 - x//2 + x//10 - x//200 - 13
    elif y <= 8400:
        return y*669 - x//2 + x//10 - x//300 - 25
    return y*669 - x//2 + x//10 - x//600 - 39


def _sols_in_month(y, m):
    "y(year), m(month) -> number of sols in that month in that year."
    assert 1 <= m <= 24, 'month must be in 1..24'
    if m == 6 or m == 12 or m == 18:
        return 27
    elif m == 24 and not _is_leap(y):
        return 27
    return 28


def _sols_before_month(month):
    """month -> number of sols in year preceding first sol of month.

    Different to datetime library, Leap day is in Vrishika(24th month),
    so we can forget it."""
    assert 1 <= month <= 24, 'month must be in 1..24'
    return (month-1)*28-(month-1)//6


def _ymd2ord(year, month, sol):
    "year, month, sol -> ordinal, considering 01-Sag-0000 as sol 1."
    assert 1 <= month <= 24, 'month must be in 1..24'
    dim = _sols_in_month(year, month)
    assert 1 <= sol <= dim, ('sol must be in 1..%d' % dim)
    return (_sols_before_year(year) + _sols_before_month(month) + sol)


def _ord2ymd(n):
    "ordinal -> (year, month, sol), considering 01-Sag-0000 as sol 1."
    year = int(n//668.59)  # estimate the year number
    if n <= _sols_before_year(year):  # the estimate is too large
        year -= 1
    elif n > _sols_before_year(year+1):  # the estimate is too small
        year += 1
    n -= _sols_before_year(year)
    month = n//28 + 1
    if n <= _sols_before_month(month):  # the estimate is too large
        month -= 1
    # the estimate is too small
    elif month < 24 and n > _sols_before_month(month+1):
        month += 1
    n -= _sols_before_month(month)
    return year, month, n


def _format_time(hh, mm, ss, us, timespec='auto'):
    specs = {
        'hours': '{:02d}',
        'minutes': '{:02d}:{:02d}',
        'seconds': '{:02d}:{:02d}:{:02d}',
        'milliseconds': '{:02d}:{:02d}:{:02d}.{:03d}',
        'microseconds': '{:02d}:{:02d}:{:02d}.{:06d}'
    }

    if timespec == 'auto':
        # Skip trailing microseconds when us==0.
        timespec = 'microseconds' if us else 'seconds'
    elif timespec == 'milliseconds':
        us //= 1000
    try:
        fmt = specs[timespec]
    except KeyError:
        raise ValueError('Unknown timespec value')
    else:
        return fmt.format(hh, mm, ss, us)


def _format_offset(off):
    s = ''
    if off is not None:
        if off.sols < 0:
            sign = "-"
            off = -off
        else:
            sign = "+"
        hh, mm = divmod(off, Mtimedelta(hours=1))
        mm, ss = divmod(mm, Mtimedelta(minutes=1))
        s += "%s%02d:%02d" % (sign, hh, mm)
        if ss or ss.microseconds:
            s += ":%02d" % ss.seconds

            if ss.microseconds:
                s += '.%06d' % ss.microseconds
    return s


_MONTHNAMES = [None,
               "Sag", "Dha", "Cap", "Mak", "Aqu", "Kum",
               "Pis", "Min", "Ari", "Mes", "Tau", "Ris",
               "Gem", "Mit", "Can", "Kar", "Leo", "Sim",
               "Vir", "Kan", "Lib", "Tul", "Sco", "Vri"]
_SOLNAMES = ["Lu", "Ma", "Me", "Jo", "Ve", "Sa", "So"]


def _wrap_strftime(obj, format, timetuple):
    # timetuple : (year, month, sol,
    #              hour, minute, second(float),
    #              weeksol, yearsol, isdst(1 for True,
    #                                      0 for False,
    #                                      -1 for Unknown))

    MONTHNAMES = _MONTHNAMES
    SOLNAMES = _SOLNAMES
    MONTHNAMES_FULL = [None,
                       "Sagittarius", "Dhanus",  "Capricornus", "Makara",
                       "Aquarius",    "Kumbha",  "Pisces",      "Mina",
                       "Aries",       "Mesha",   "Taurus",      "Rishabha",
                       "Gemini",      "Mithuna", "Cancer",      "Karka",
                       "Leo",         "Simha",   "Virgo",       "Kanya",
                       "Libra",       "Tula",    "Scorpius",    "Vrishika"]
    SOLNAMES_FULL = ["Lunae", "Martis", "Mercurii",
                     "Jovis", "Veneris", "Saturni", "Solis"]
    s = ''
    escape = False
    for ch in format:
        if escape:
            escape = False
            if ch == 'A':
                s += SOLNAMES_FULL[timetuple[6]]
            elif ch == 'a':
                s += SOLNAMES[timetuple[6]]
            elif ch == 'B':
                s += MONTHNAMES_FULL[timetuple[1]]
            elif ch == 'b':
                s += MONTHNAMES[timetuple[1]]
            elif ch == 'C':
                # TODO: '%C' is not supported for I don't know
                # what it's stand for.
                pass
            elif ch == 'c':
                s += '{0} {1} {2: >2d} {3:0>2d}:{4:0>2d}:{5:0>2d} {6: >4d}'.format(
                    SOLNAMES[timetuple[6]],
                    MONTHNAMES[timetuple[1]],
                    timetuple[2],
                    timetuple[3],
                    timetuple[4],
                    int(timetuple[5]),
                    timetuple[0])
            elif ch == 'D':
                s += '{0:0>2d}/{1:0>2d}/{2:0>2d}'.format(
                    timetuple[1],
                    timetuple[2],
                    timetuple[0] % 100)
            elif ch == 'd':
                s += '{:0>2d}'.format(timetuple[2])
            elif ch == 'e':
                s += '{: >2d}'.format(timetuple[2])
            elif ch == 'F':
                s += '{0:0>4d}-{1:0>2d}-{2:0>2d}'.format(
                    timetuple[0],
                    timetuple[1],
                    timetuple[2])
            elif ch == 'f':
                s += '{:0>6d}'.format(int((timetuple[5] % 1)*100000))
            elif ch == 'G':
                s += '{:0>4d}'.format(timetuple[0])
            elif ch == 'g':
                s += '{:0>2d}'.format(timetuple[0] % 100)
            elif ch == 'H':
                s += '{:0>2d}'.format(timetuple[3])
            elif ch == 'h':
                s += MONTHNAMES[timetuple[1]]
            elif ch == 'I':
                s += '{:0>2d}'.format(timetuple[3])
            elif ch == 'j':
                s += '{:0>3d}'.format(
                    _sols_before_month(timetuple[1]) + timetuple[2])
            elif ch == 'M':
                s += '{:0>2d}'.format(timetuple[4])
            elif ch == 'm':
                s += '{:0>2d}'.format(timetuple[1])
            elif ch == 'n':
                s += '\n'
            elif ch == 'p':
                if timetuple[3] <= 11:
                    s += 'AM'
                else:
                    s += 'PM'
            elif ch == 'R':
                s += '{0:0>2d}:{1:0>2d}'.format(timetuple[3], timetuple[4])
            elif ch == 'r':
                s += '{0:0>2d}:{1:0>2d}:{2:0>2d}'.format(
                    timetuple[3],
                    timetuple[4],
                    int(timetuple[5]))
            elif ch == 'S':
                s += '{:0>2d}'.format(int(timetuple[5]))
            elif ch == 'T':
                s += '{0:0>2d}:{1:0>2d}:{2:0>2d}'.format(
                    timetuple[3],
                    timetuple[4],
                    int(timetuple[5]))
            elif ch == 't':
                # TODO: '%t' is not supported for I don't know
                # what it's stand for.
                pass
            elif ch == 'U':
                s += '{:0>2d}'.format((timetuple[1]-1)*4+(timetuple[2]-1)//7+1)
            elif ch == 'u':
                # TODO: '%u' is not supported for I don't know
                # what it's stand for.
                pass
            elif ch == 'V':
                # TODO: '%V' is not supported for I don't know
                # what it's stand for.
                pass
            elif ch == 'W':
                if timetuple[1] == 1 and timetuple[2] == 1:
                    s += '96'
                else:
                    s += '{:0>2d}'.format((timetuple[1]-1)
                                          * 4+(timetuple[2]+5)//7)
                pass
            elif ch == 'w':
                s += str((timetuple[6]+1) % 7)
            elif ch == 'X':
                s += '{0:0>2d}:{1:0>2d}:{2:0>2d}'.format(
                    timetuple[3],
                    timetuple[4],
                    int(timetuple[5]))
            elif ch == 'x':
                s += '{0:0>2d}/{1:0>2d}/{2:0>2d}'.format(
                    timetuple[1],
                    timetuple[2],
                    timetuple[0] % 100)
            elif ch == 'Y':
                s += '{:0>4d}'.format(timetuple[0])
            elif ch == 'y':
                s += '{:0>2d}'.format(timetuple[0] % 100)
            elif ch == 'Z':
                if hasattr(obj, "tzname"):
                    s += obj.tzname()
            elif ch == 'z':
                if hasattr(obj, "mtcoffset"):
                    offset = obj.mtcoffset()
                    if offset is not None:
                        sign = '+'
                        if offset.sols < 0:
                            offset = -offset
                            sign = '-'
                        h, rest = divmod(offset, Mtimedelta(hours=1))
                        m, rest = divmod(rest, Mtimedelta(minutes=1))
                        sec = rest.seconds
                        u = offset.microseconds
                        if u:
                            s += '%c%02d%02d%02d.%06d' % (
                                sign, h, m, sec, u)
                        elif sec:
                            s += '%c%02d%02d%02d' % (sign, h, m, sec)
                        else:
                            s += '%c%02d%02d' % (sign, h, m)
            elif ch == '%':
                s += '%'
            else:
                raise ValueError('Invalid format string "%%%c"' % ch)
        else:
            if ch == '%':
                escape = True
            else:
                s += ch
    return s


# Just raise TypeError if the arg isn't None or a string.
def _check_tzname(name):
    if name is not None and not isinstance(name, str):
        raise TypeError("tzinfo.tzname() must return None or string, "
                        "not '%s'" % type(name))


# name is the offset-producing method, "mtcoffset" or "dst".
# offset is what it returned.
# If offset isn't None or timedelta, raises TypeError.
# If offset is None, returns None.
# Else offset is checked for being in range.
# If it is, its integer value is returned.  Else ValueError is raised.
def _check_mtc_offset(name, offset):
    assert name in ("mtcoffset", "dst")
    if offset is None:
        return
    if not isinstance(offset, Mtimedelta):
        raise TypeError("tzinfo.%s() must return None "
                        "or timedelta, not '%s'" % (name, type(offset)))
    if not -Mtimedelta(1) < offset < Mtimedelta(1):
        raise ValueError("%s()=%s, must be strictly between "
                         "-timedelta(hours=24) and timedelta(hours=24)" %
                         (name, offset))


def _check_int_field(value):
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        raise TypeError('integer argument expected, got float')
    try:
        value = value.__index__()
    except AttributeError:
        pass
    else:
        if not isinstance(value, int):
            raise TypeError('__index__ returned non-int (type %s)' %
                            type(value).__name__)
        return value
    orig = value
    try:
        value = value.__int__()
    except AttributeError:
        pass
    else:
        if not isinstance(value, int):
            raise TypeError('__int__ returned non-int (type %s)' %
                            type(value).__name__)
        import warnings
        warnings.warn("an integer is required (got type %s)" %
                      type(orig).__name__,
                      DeprecationWarning,
                      stacklevel=2)
        return value
    raise TypeError('an integer is required (got type %s)' %
                    type(value).__name__)


def _check_date_fields(year, month, sol):
    year = _check_int_field(year)
    month = _check_int_field(month)
    sol = _check_int_field(sol)
    if not MMINYEAR <= year <= MMAXYEAR:
        raise ValueError('year must be in %d..%d' % (MMINYEAR, MMAXYEAR), year)
    if not 1 <= month <= 24:
        raise ValueError('month must be in 1..24', month)
    dim = _sols_in_month(year, month)
    if not 1 <= sol <= dim:
        raise ValueError('sol must be in 1..%d' % dim, sol)
    return year, month, sol


def _check_time_fields(hour, minute, second, microsecond, fold):
    hour = _check_int_field(hour)
    minute = _check_int_field(minute)
    second = _check_int_field(second)
    microsecond = _check_int_field(microsecond)
    if not 0 <= hour <= 23:
        raise ValueError('hour must be in 0..23', hour)
    if not 0 <= minute <= 59:
        raise ValueError('minute must be in 0..59', minute)
    if not 0 <= second <= 59:
        raise ValueError('second must be in 0..59', second)
    if not 0 <= microsecond <= 999999:
        raise ValueError('microsecond must be in 0..999999', microsecond)
    if fold not in (0, 1):
        raise ValueError('fold must be either 0 or 1', fold)
    return hour, minute, second, microsecond, fold


def _check_tzinfo_arg(tz):
    if tz is not None and not isinstance(tz, Mtzinfo):
        raise TypeError(
            "tzinfo argument must be None or of a Mtzinfo subclass")


def _cmperror(x, y):
    raise TypeError("can't compare '%s' to '%s'" % (
                    type(x).__name__, type(y).__name__))


def _divide_and_round(a, b):
    """divide a by b and round result to the nearest integer

    When the ratio is exactly half-way between two integers,
    the even integer is returned.
    """
    # Based on the reference implementation for divmod_near
    # in Objects/longobject.c.
    q, r = divmod(a, b)
    # round up if either r / b > 0.5, or r / b == 0.5 and q is odd.
    # The expression r / b > 0.5 is equivalent to 2 * r > b if b is
    # positive, 2 * r < b if b negative.
    r *= 2
    greater_than_half = r > b if b > 0 else r < b
    if greater_than_half or r == b and q % 2 == 1:
        q += 1

    return q

# convert Gregorian calendar and the Darian Martian calendar to each other.


_1SOL = 88775.244147  # unit: terrestrial second
_M2EC = _1SOL/86400  # 1sol / 1day
_E2MC = 86400/_1SOL  # 1day / 1sol

# NOTE: This value can change over time, but is unpredictable, so update it
# frequently. Now UTC is 37 seconds behind TAI at 2022/2/15 from 2017/1/1.
_TAIMUTC = 37


def _Mfromtimestamp(t):
    ord_f = (t + _TAIMUTC) / _1SOL + 128257.2954262
    ord, t = divmod(ord_f, 1)
    t *= 24
    h, t = divmod(t, 1)
    t *= 60
    min, t = divmod(t, 1)
    t *= 60
    y, m, d = _ord2ymd(int(ord))
    return y, m, d, int(h), int(min), round(t, 6)  # MTC based


def M2E(obj):
    if isinstance(obj, Mtimedelta):
        obj = obj*_M2EC
        return datetime.timedelta(obj.sols, obj.seconds, obj.microseconds)
    elif isinstance(obj, Mdatetime):
        if obj.tzinfo is None:
            raise ValueError('Time zone must be specified.')
        ts = obj.timestamp()
        return datetime.datetime.fromtimestamp(ts).astimezone()
    else:
        raise TypeError('Cannot transform %s to a terrestrial type' % type(
            obj).__name__)


def E2M(obj):
    if isinstance(obj, datetime.timedelta):
        obj = obj*_E2MC
        return Mtimedelta(obj.days, obj.seconds, obj.microseconds)
    elif isinstance(obj, datetime.datetime):
        if obj.tzinfo is None:
            # Local time is used for conversion by default.
            obj = obj.astimezone()
        ts = obj.timestamp()
        return Mdatetime.fromtimestamp(ts)
    raise TypeError('Cannot transform %s to a Martian type' % type(
        obj).__name__)


class Mtimedelta:
    """Represent the difference between two Mdatetime objects.

    Supported operators:

    - add, subtract timedelta
    - unary plus, minus, abs
    - compare to timedelta
    - multiply, divide by int

    In addition, datetime supports subtraction of two datetime objects
    returning a timedelta, and addition or subtraction of a datetime
    and a timedelta giving a datetime.

    Representation: (sols, seconds, microseconds).  Why?  Because I
    felt like it.
    """
    __slots__ = '_sols', '_seconds', '_microseconds', '_hashcode'

    def __new__(cls, sols=0, seconds=0, microseconds=0,
                milliseconds=0, minutes=0, hours=0, weeks=0):
        # Doing this efficiently and accurately in C is going to be difficult
        # and error-prone, due to ubiquitous overflow possibilities, and that
        # C double doesn't have enough bits of precision to represent
        # microseconds over 10K years faithfully.  The code here tries to make
        # explicit where go-fast assumptions can be relied on, in order to
        # guide the C implementation; it's way more convoluted than speed-
        # ignoring auto-overflow-to-long idiomatic Python could be.

        # XXX Check that all inputs are ints or floats.

        # Final values, all integer.
        # s and us fit in 32-bit signed ints; d isn't bounded.
        d = s = us = 0

        # Normalize everything to sols, seconds, microseconds.
        sols += weeks*7
        seconds += minutes*60 + hours*3600
        microseconds += milliseconds*1000

        # Get rid of all fractions, and normalize s and us.
        # Take a deep breath <wink>.
        if isinstance(sols, float):
            solfrac, sols = _math.modf(sols)
            solsecondsfrac, solsecondswhole = _math.modf(solfrac * (24.*3600.))
            assert solsecondswhole == int(solsecondswhole)  # can't overflow
            s = int(solsecondswhole)
            assert sols == int(sols)
            d = int(sols)
        else:
            solsecondsfrac = 0.0
            d = sols
        assert isinstance(solsecondsfrac, float)
        assert abs(solsecondsfrac) <= 1.0
        assert isinstance(d, int)
        assert abs(s) <= 24 * 3600
        # sols isn't referenced again before redefinition

        if isinstance(seconds, float):
            secondsfrac, seconds = _math.modf(seconds)
            assert seconds == int(seconds)
            seconds = int(seconds)
            secondsfrac += solsecondsfrac
            assert abs(secondsfrac) <= 2.0
        else:
            secondsfrac = solsecondsfrac
        # solsecondsfrac isn't referenced again
        assert isinstance(secondsfrac, float)
        assert abs(secondsfrac) <= 2.0

        assert isinstance(seconds, int)
        sols, seconds = divmod(seconds, 24*3600)
        d += sols
        s += int(seconds)    # can't overflow
        assert isinstance(s, int)
        assert abs(s) <= 2 * 24 * 3600
        # seconds isn't referenced again before redefinition

        usdouble = secondsfrac * 1e6
        assert abs(usdouble) < 2.1e6    # exact value not critical
        # secondsfrac isn't referenced again

        if isinstance(microseconds, float):
            microseconds = round(microseconds + usdouble)
            seconds, microseconds = divmod(microseconds, 1000000)
            sols, seconds = divmod(seconds, 24*3600)
            d += sols
            s += seconds
        else:
            microseconds = int(microseconds)
            seconds, microseconds = divmod(microseconds, 1000000)
            sols, seconds = divmod(seconds, 24*3600)
            d += sols
            s += seconds
            microseconds = round(microseconds + usdouble)
        assert isinstance(s, int)
        assert isinstance(microseconds, int)
        assert abs(s) <= 3 * 24 * 3600
        assert abs(microseconds) < 3.1e6

        # Just a little bit of carrying possible for microseconds and seconds.
        seconds, us = divmod(microseconds, 1000000)
        s += seconds
        sols, s = divmod(s, 24*3600)
        d += sols

        assert isinstance(d, int)
        assert isinstance(s, int) and 0 <= s < 24*3600
        assert isinstance(us, int) and 0 <= us < 1000000

        if abs(d) > 999999999:
            raise OverflowError("timedelta # of sols is too large: %d" % d)

        self = object.__new__(cls)
        self._sols = d
        self._seconds = s
        self._microseconds = us
        self._hashcode = -1
        return self

    def __repr__(self):
        args = []
        if self._sols:
            args.append("sols=%d" % self._sols)
        if self._seconds:
            args.append("seconds=%d" % self._seconds)
        if self._microseconds:
            args.append("microseconds=%d" % self._microseconds)
        if not args:
            args.append('0')
        return "%s.%s(%s)" % (self.__class__.__module__,
                              self.__class__.__qualname__,
                              ', '.join(args))

    def __str__(self):
        mm, ss = divmod(self._seconds, 60)
        hh, mm = divmod(mm, 60)
        s = "%d:%02d:%02d" % (hh, mm, ss)
        if self._sols:
            def plural(n):
                return n, abs(n) != 1 and "s" or ""
            s = ("%d sol%s, " % plural(self._sols)) + s
        if self._microseconds:
            s = s + ".%06d" % self._microseconds
        return s + "(Martian)"

    def total_seconds(self):
        """Total seconds in the duration."""
        return ((self.sols * 86400 + self.seconds) * 10**6 +
                self.microseconds) / 10**6

    # Read-only field accessors
    @property
    def sols(self):
        """sols"""
        return self._sols

    days = sols

    @property
    def seconds(self):
        """seconds"""
        return self._seconds

    @property
    def microseconds(self):
        """microseconds"""
        return self._microseconds

    def __add__(self, other):
        if isinstance(other, Mtimedelta):
            # for CPython compatibility, we cannot use
            # our __class__ here, but need a real timedelta
            return Mtimedelta(self._sols + other._sols,
                              self._seconds + other._seconds,
                              self._microseconds + other._microseconds)
        elif isinstance(other, datetime.timedelta):
            return self+E2M(other)
        elif isinstance(other, datetime.datetime):
            return other+M2E(self)
        return NotImplemented

    def __radd__(self, other):
        if isinstance(other, Mtimedelta):
            return other+self
        elif isinstance(other, datetime.timedelta):
            return other+M2E(self)
        elif isinstance(other, datetime.datetime):
            return other+M2E(self)
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, Mtimedelta):
            # for CPython compatibility, we cannot use
            # our __class__ here, but need a real timedelta
            return Mtimedelta(self._sols - other._sols,
                              self._seconds - other._seconds,
                              self._microseconds - other._microseconds)
        elif isinstance(other, datetime.timedelta):
            return self-E2M(other)
        return NotImplemented

    def __rsub__(self, other):
        if isinstance(other, Mtimedelta):
            return -self + other
        elif isinstance(other, datetime.timedelta):
            return -M2E(self) + other
        elif isinstance(other, datetime.datetime):
            return other-M2E(self)
        return NotImplemented

    def __neg__(self):
        # for CPython compatibility, we cannot use
        # our __class__ here, but need a real timedelta
        return Mtimedelta(-self._sols,
                          -self._seconds,
                          -self._microseconds)

    def __pos__(self):
        return self

    def __abs__(self):
        if self._sols < 0:
            return -self
        else:
            return self

    def __mul__(self, other):
        if isinstance(other, int):
            # for CPython compatibility, we cannot use
            # our __class__ here, but need a real timedelta
            return Mtimedelta(self._sols * other,
                              self._seconds * other,
                              self._microseconds * other)
        if isinstance(other, float):
            usec = self._to_microseconds()
            a, b = other.as_integer_ratio()
            return Mtimedelta(0, 0, _divide_and_round(usec * a, b))
        return NotImplemented

    __rmul__ = __mul__

    def _to_microseconds(self):
        return ((self._sols * (24*3600) + self._seconds) * 1000000 +
                self._microseconds)

    def __floordiv__(self, other):
        if isinstance(other, Mtimedelta):
            return self._to_microseconds() // other._to_microseconds()
        elif isinstance(other, datetime.timedelta):
            return self._to_microseconds() // E2M(other)._to_microseconds()
        elif isinstance(other, int):
            return Mtimedelta(0, 0, self._to_microseconds() // other)
        return NotImplemented

    def __rfloordiv__(self, other):
        if isinstance(other, datetime.timedelta):
            return other // M2E(self)
        return NotImplemented

    def __truediv__(self, other):
        if isinstance(other, Mtimedelta):
            return self._to_microseconds() / other._to_microseconds()
        elif isinstance(other, int):
            return Mtimedelta(0, 0,
                              _divide_and_round(self._to_microseconds(), other))
        elif isinstance(other, float):
            a, b = other.as_integer_ratio()
            return Mtimedelta(0, 0, _divide_and_round(
                b * self._to_microseconds(), a))
        elif isinstance(other, datetime.timedelta):
            return self._to_microseconds() / E2M(other)._to_microseconds()
        return NotImplemented

    def __rtruediv__(self, other):
        if isinstance(other, datetime.timedelta):
            return other / M2E(self)
        return NotImplemented

    def __mod__(self, other):
        if isinstance(other, Mtimedelta):
            r = self._to_microseconds() % other._to_microseconds()
            return Mtimedelta(0, 0, r)
        elif isinstance(other, datetime.timedelta):
            r = self._to_microseconds() % E2M(other)._to_microseconds()
            return Mtimedelta(0, 0, r)
        return NotImplemented

    def __rmod__(self, other):
        if isinstance(other, datetime.timedelta):
            return other % M2E(self)
        return NotImplemented

    def __divmod__(self, other):
        if isinstance(other, Mtimedelta):
            q, r = divmod(self._to_microseconds(),
                          other._to_microseconds())
            return q, Mtimedelta(0, 0, r)
        elif isinstance(other, datetime.timedelta):
            q, r = divmod(self._to_microseconds(),
                          E2M(other)._to_microseconds())
            return q, Mtimedelta(0, 0, r)
        return NotImplemented

    def __rdivmod__(self, other):
        if isinstance(other, datetime.timedelta):
            return divmod(other, M2E(self))
        return NotImplemented

    # Comparisons of timedelta objects with other.
    def __eq__(self, other):
        if isinstance(other, Mtimedelta):
            return self._cmp(other) == 0
        elif isinstance(other, datetime.timedelta):
            return False
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, (Mtimedelta, datetime.timedelta)):
            return self._cmp(other) <= 0
        else:
            return NotImplemented

    def __lt__(self, other):
        if isinstance(other, (Mtimedelta, datetime.timedelta)):
            return self._cmp(other) < 0
        else:
            return NotImplemented

    def __ge__(self, other):
        if isinstance(other, (Mtimedelta, datetime.timedelta)):
            return self._cmp(other) >= 0
        else:
            return NotImplemented

    def __gt__(self, other):
        if isinstance(other, (Mtimedelta, datetime.timedelta)):
            return self._cmp(other) > 0
        else:
            return NotImplemented

    def _cmp(self, other):
        if isinstance(other, Mtimedelta):
            return _cmp(self._getstate(), other._getstate())
        elif isinstance(other, datetime.timedelta):
            return _cmp(self._getstate(), E2M(other)._getstate())
        else:
            raise

    def __hash__(self):
        if self._hashcode == -1:
            self._hashcode = hash(self._getstate())
        return self._hashcode

    def __bool__(self):
        return (self._sols != 0 or
                self._seconds != 0 or
                self._microseconds != 0)

    # Pickle support.

    def _getstate(self):
        return (self._sols, self._seconds, self._microseconds)

    def __reduce__(self):
        return (self.__class__, self._getstate())


Mtimedelta.min = Mtimedelta(-999999999)
Mtimedelta.max = Mtimedelta(sols=999999999, hours=23, minutes=59, seconds=59,
                            microseconds=999999)
Mtimedelta.resolution = Mtimedelta(microseconds=1)


class Mdate:
    """Concrete Mdate type.

    NOTE: Only Martian time element(including Mdate, Mdatetima and Mdeltatime)
    can participate in the calculations for timezone reasons.

    Constructors:

    __new__()
    fromtimestamp()
    tosol()
    fromordinal()

    Operators:

    __repr__, __str__
    __eq__, __le__, __lt__, __ge__, __gt__, __hash__
    __add__, __radd__, __sub__ (add/radd only with Mtimedelta arg)

    Methods:

    timetuple()
    toordinal()
    weeksol()
    strftime()

    Properties (readonly):
    year, month, sol
    """
    __slots__ = '_year', '_month', '_sol', '_hashcode'

    def __new__(cls, year, month=None, sol=None):
        """Constructor.

        Arguments:

        year, month, sol (required, base 1)
        """
        if (month is None and
            isinstance(year, (bytes, str)) and len(year) == 4 and
                1 <= ord(year[2:3]) <= 24):
            # Pickle support
            if isinstance(year, str):
                try:
                    year = year.encode('latin1')
                except UnicodeEncodeError:
                    # More informative error message.
                    raise ValueError(
                        "Failed to encode latin1 string when unpickling "
                        "a date object. "
                        "pickle.load(data, encoding='latin1') is assumed.")
            self = object.__new__(cls)
            self.__setstate(year)
            self._hashcode = -1
            return self
        year, month, sol = _check_date_fields(year, month, sol)
        self = object.__new__(cls)
        self._year = year
        self._month = month
        self._sol = sol
        self._hashcode = -1
        return self

    # Additional constructors

    @classmethod
    def fromtimestamp(cls, t):
        "Construct a date from a POSIX timestamp."
        y, m, d, hh, mm, ss = _Mfromtimestamp(t)
        return cls(y, m, d)

    @classmethod
    def tosol(cls):
        "Construct a date from time.time()."
        t = _time.time()
        return cls.fromtimestamp(t)

    today = tosol

    @classmethod
    def fromordinal(cls, n):
        """Construct a date from a proleptic Darian ordinal.

        Sagittarius 1 of year 0 is sol 0.  Only the year, month and sol are
        non-zero in the result.
        """
        y, m, d = _ord2ymd(n)
        return cls(y, m, d)

    # Conversions to string

    def __repr__(self):
        """Convert to formal string, for repr().

        >>> dt = Mdatetime(250, 1, 1)
        >>> repr(dt)
        'darian_datetime.Mdatetime(250, 1, 1, 0, 0)'

        >>> dt = Mdatetime(250, 1, 1, tzinfo=Mtimezone.mtc)
        >>> repr(dt)
        'darian_datetime.Mdatetime(250, 1, 1, 0, 0, tzinfo=Mdatetime.Mtimezone.mtc)'
        """
        return "%s.%s(%d, %d, %d)" % (self.__class__.__module__,
                                      self.__class__.__qualname__,
                                      self._year,
                                      self._month,
                                      self._sol)

    def strftime(self, fmt):
        "Format using strftime()."
        return _wrap_strftime(self, fmt, self.timetuple())

    def __format__(self, fmt):
        if not isinstance(fmt, str):
            raise TypeError("must be str, not %s" % type(fmt).__name__)
        if len(fmt) != 0:
            return self.strftime(fmt)
        return str(self)

    def __str__(self):
        return "%04d-%02d-%02d(Martian)" % (self._year, self._month, self._sol)

    # Read-only field accessors
    @property
    def year(self):
        """year (0-9999)"""
        return self._year

    @property
    def month(self):
        """month (1-24)"""
        return self._month

    @property
    def sol(self):
        """sol (1-28)"""
        return self._sol

    day = sol
    # Standard conversions, __eq__, __le__, __lt__, __ge__, __gt__,
    # __hash__ (and helpers)

    def timetuple(self):
        return (self._year, self._month, self._sol,
                0, 0, 0, self.weeksol(), None)

    def toordinal(self):
        """Return proleptic Gregorian ordinal for the year, month and sol.

        Sagittarius 1 of year 0 is sol 1.  Only the year, month and sol values
        contribute to the result.
        """
        return _ymd2ord(self._year, self._month, self._sol)

    def replace(self, year=None, month=None, sol=None):
        """Return a new date with new values for the specified fields."""
        if year is None:
            year = self._year
        if month is None:
            month = self._month
        if sol is None:
            sol = self._sol
        return type(self)(year, month, sol)

    # Comparisons of date objects with other.

    def __eq__(self, other):
        if isinstance(other, Mdate):
            return self._cmp(other) == 0
        elif isinstance(other, datetime.date):
            return False
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, Mdate):
            return self._cmp(other) <= 0
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, Mdate):
            return self._cmp(other) < 0
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, Mdate):
            return self._cmp(other) >= 0
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, Mdate):
            return self._cmp(other) > 0
        return NotImplemented

    def _cmp(self, other):
        assert isinstance(other, Mdate)
        y, m, d = self._year, self._month, self._sol
        y2, m2, d2 = other._year, other._month, other._sol
        return _cmp((y, m, d), (y2, m2, d2))

    def __hash__(self):
        "Hash."
        if self._hashcode == -1:
            self._hashcode = hash(self._getstate())
        return self._hashcode

    # Computations

    def __add__(self, other):
        "Add a Mdate to a Mtimedelta."
        if isinstance(other, Mtimedelta):
            o = self.toordinal() + other.sols
            if 0 < o <= _MAXORDINAL:
                return type(self).fromordinal(o)
            raise OverflowError("result out of range")
        return NotImplemented

    __radd__ = __add__

    def __sub__(self, other):
        """Subtract two dates, or a Mdate and a Mtimedelta."""
        if isinstance(other, Mtimedelta):
            return self + Mtimedelta(-other.sols)
        if isinstance(other, Mdate):
            sols1 = self.toordinal()
            sols2 = other.toordinal()
            return Mtimedelta(sols1 - sols2)
        return NotImplemented

    def weeksol(self):
        "Return sol of the week, where Lunae == 0 ... Solis == 6."
        return (self.sol+5) % 7

    weekday = weeksol

    # Pickle support.

    def _getstate(self):
        yhi, ylo = divmod(self._year, 256)
        return bytes([yhi, ylo, self._month, self._sol]),

    def __setstate(self, string):
        yhi, ylo, self._month, self._sol = string
        self._year = yhi * 256 + ylo

    def __reduce__(self):
        return (self.__class__, self._getstate())


_date_class = Mdate  # so functions w/ args named "date" can get at the class

Mdate.min = Mdate(0, 1, 1)
Mdate.max = Mdate(9999, 24, 28)
Mdate.resolution = Mtimedelta(sols=1)


class Mtzinfo:
    """Abstract base class for Martian time zone info classes.

    Subclasses must override the name(), mtcoffset() and dst() methods.
    """
    __slots__ = ()

    def tzname(self, dt):
        "Mdatetime -> string name of time zone."
        raise NotImplementedError("Mtzinfo subclass must override tzname()")

    def mtcoffset(self, dt):
        "Mdatetime -> Mtimedelta, positive for east of MTC, negative for west of MTC"
        raise NotImplementedError("Mtzinfo subclass must override mtcoffset()")

    def dst(self, dt):
        """Mdatetime -> DST offset as timedelta, positive for east of MTC.

        Return 0 if DST not in effect.  mtcoffset() must include the DST
        offset.
        """
        raise NotImplementedError("Mtzinfo subclass must override dst()")

    def frommtc(self, dt):
        "Mdatetime in MTC -> Mdatetime in local time."

        if not isinstance(dt, Mdatetime):
            raise TypeError("frommtc() requires a datetime argument")
        if dt.tzinfo is not self:
            raise ValueError("dt.tzinfo is not self")

        dtoff = dt.mtcoffset()
        if dtoff is None:
            raise ValueError("frommtc() requires a non-None mtcoffset() "
                             "result")

        # See the long comment block at the end of this file for an
        # explanation of this algorithm.
        dtdst = dt.dst()
        if dtdst is None:
            raise ValueError("frommtc() requires a non-None dst() result")
        delta = dtoff - dtdst
        if delta:
            dt += delta
            dtdst = dt.dst()
            if dtdst is None:
                raise ValueError("frommtc(): dt.dst gave inconsistent "
                                 "results; cannot convert")
        return dt + dtdst

    # Pickle support.

    def __reduce__(self):
        getinitargs = getattr(self, "__getinitargs__", None)
        if getinitargs:
            args = getinitargs()
        else:
            args = ()
        getstate = getattr(self, "__getstate__", None)
        if getstate:
            state = getstate()
        else:
            state = getattr(self, "__dict__", None) or None
        if state is None:
            return (self.__class__, args)
        else:
            return (self.__class__, args, state)


_tzinfo_class = Mtzinfo


class Mtime:
    """Martian time with time zone.

    Constructors:

    __new__()

    Operators:

    __repr__, __str__
    __eq__, __le__, __lt__, __ge__, __gt__, __hash__

    Methods:

    strftime()
    mtcoffset()
    tzname()
    dst()

    Properties (readonly):
    hour, minute, second, microsecond, tzinfo, fold
    """
    __slots__ = '_hour', '_minute', '_second', '_microsecond', '_tzinfo', '_hashcode', '_fold'

    def __new__(cls, hour=0, minute=0, second=0, microsecond=0, tzinfo=None, *, fold=0):
        """Constructor.

        Arguments:

        hour, minute (required)
        second, microsecond (default to zero)
        tzinfo (default to None)
        fold (keyword only, default to zero)
        """
        if (isinstance(hour, (bytes, str)) and len(hour) == 6 and
                ord(hour[0:1]) & 0x7F < 24):
            # Pickle support
            if isinstance(hour, str):
                try:
                    hour = hour.encode('latin1')
                except UnicodeEncodeError:
                    # More informative error message.
                    raise ValueError(
                        "Failed to encode latin1 string when unpickling "
                        "a time object. "
                        "pickle.load(data, encoding='latin1') is assumed.")
            self = object.__new__(cls)
            self.__setstate(hour, minute or None)
            self._hashcode = -1
            return self
        hour, minute, second, microsecond, fold = _check_time_fields(
            hour, minute, second, microsecond, fold)
        _check_tzinfo_arg(tzinfo)
        self = object.__new__(cls)
        self._hour = hour
        self._minute = minute
        self._second = second
        self._microsecond = microsecond
        self._tzinfo = tzinfo
        self._hashcode = -1
        self._fold = fold
        return self

    # Read-only field accessors
    @property
    def hour(self):
        """hour (0-23)"""
        return self._hour

    @property
    def minute(self):
        """minute (0-59)"""
        return self._minute

    @property
    def second(self):
        """second (0-59)"""
        return self._second

    @property
    def microsecond(self):
        """microsecond (0-999999)"""
        return self._microsecond

    @property
    def tzinfo(self):
        """Mtimezone info object"""
        return self._tzinfo

    @property
    def fold(self):
        return self._fold

    # Standard conversions, __hash__ (and helpers)

    # Comparisons of time objects with other.

    def __eq__(self, other):
        if isinstance(other, Mtime):
            return self._cmp(other, allow_mixed=True) == 0
        else:
            return NotImplemented

    def __le__(self, other):
        if isinstance(other, Mtime):
            return self._cmp(other) <= 0
        else:
            return NotImplemented

    def __lt__(self, other):
        if isinstance(other, Mtime):
            return self._cmp(other) < 0
        else:
            return NotImplemented

    def __ge__(self, other):
        if isinstance(other, Mtime):
            return self._cmp(other) >= 0
        else:
            return NotImplemented

    def __gt__(self, other):
        if isinstance(other, Mtime):
            return self._cmp(other) > 0
        else:
            return NotImplemented

    def _cmp(self, other, allow_mixed=False):
        assert isinstance(other, Mtime)
        mytz = self._tzinfo
        ottz = other._tzinfo
        myoff = otoff = None

        if mytz is ottz:
            base_compare = True
        else:
            myoff = self.mtcoffset()
            otoff = other.mtcoffset()
            base_compare = myoff == otoff

        if base_compare:
            return _cmp((self._hour, self._minute, self._second,
                         self._microsecond),
                        (other._hour, other._minute, other._second,
                         other._microsecond))
        if myoff is None or otoff is None:
            if allow_mixed:
                return 2  # arbitrary non-zero value
            else:
                raise TypeError("cannot compare naive and aware times")
        myhhmm = self._hour * 60 + self._minute - myoff//Mtimedelta(minutes=1)
        othhmm = other._hour * 60 + other._minute - \
            otoff//Mtimedelta(minutes=1)
        return _cmp((myhhmm, self._second, self._microsecond),
                    (othhmm, other._second, other._microsecond))

    def __hash__(self):
        """Hash."""
        if self._hashcode == -1:
            if self.fold:
                t = self.replace(fold=0)
            else:
                t = self
            tzoff = t.mtcoffset()
            if not tzoff:  # zero or None
                self._hashcode = hash(t._getstate()[0])
            else:
                h, m = divmod(Mtimedelta(hours=self.hour, minutes=self.minute) - tzoff,
                              Mtimedelta(hours=1))
                assert not m % Mtimedelta(minutes=1), "whole minute"
                m //= Mtimedelta(minutes=1)
                if 0 <= h < 24:
                    self._hashcode = hash(
                        Mtime(h, m, self.second, self.microsecond))
                else:
                    self._hashcode = hash(
                        (h, m, self.second, self.microsecond))
        return self._hashcode

    # Conversion to string

    def _tzstr(self):
        """Return formatted timezone offset (+xx:xx) or an empty string."""
        off = self.mtcoffset()
        return _format_offset(off)

    def __repr__(self):
        """Convert to formal string, for repr()."""
        if self._microsecond != 0:
            s = ", %d, %d" % (self._second, self._microsecond)
        elif self._second != 0:
            s = ", %d" % self._second
        else:
            s = ""
        s = "%s.%s(%d, %d%s)" % (self.__class__.__module__,
                                 self.__class__.__qualname__,
                                 self._hour, self._minute, s)
        if self._tzinfo is not None:
            assert s[-1:] == ")"
            s = s[:-1] + ", tzinfo=%r" % self._tzinfo + ")"
        if self._fold:
            assert s[-1:] == ")"
            s = s[:-1] + ", fold=1)"
        return s

    def __str__(self):
        """Return the time formatted according to ISO-like format.

        The full format is 'HH:MM:SS.mmmmmm+zz:zz'. By default, the fractional
        part is omitted if self.microsecond == 0.
        """
        s = _format_time(self._hour, self._minute, self._second,
                         self._microsecond, 'auto')
        tz = self._tzstr()
        if tz:
            s += tz
        return s+'(Martian)'

    def strftime(self, fmt):
        """Format using strftime().  The date part of the timestamp passed
        to underlying strftime should not be used.
        """
        timetuple = (0, 1, 1,
                     self._hour, self._minute,
                     self._second+self._microsecond/100000,
                     0, 1, -1)
        return _wrap_strftime(self, fmt, timetuple)

    def __format__(self, fmt):
        if not isinstance(fmt, str):
            raise TypeError("must be str, not %s" % type(fmt).__name__)
        if len(fmt) != 0:
            return self.strftime(fmt)
        return str(self)

    # Timezone functions

    def mtcoffset(self):
        """Return the timezone offset as timedelta, positive east of MTC
         (negative west of MTC)."""
        if self._tzinfo is None:
            return None
        offset = self._tzinfo.mtcoffset(None)
        _check_mtc_offset("mtcoffset", offset)
        return offset

    def tzname(self):
        """Return the timezone name.

        Note that the name is 100% informational -- there's no requirement that
        it mean anything in particular. For example, "Airy-0", "MTC", "-500",
        "-5:00", "115°E", "Curiosity", "Zhurong" are all valid replies.
        """
        if self._tzinfo is None:
            return None
        name = self._tzinfo.tzname(None)
        _check_tzname(name)
        return name

    def dst(self):
        """Return 0 if DST is not in effect, or the DST offset (as timedelta
        positive eastward) if DST is in effect.

        This is purely informational; the DST offset has already been added to
        the MTC offset returned by mtcoffset() if applicable, so there's no
        need to consult dst() unless you're interested in displaying the DST
        info.
        """
        if self._tzinfo is None:
            return None
        offset = self._tzinfo.dst(None)
        _check_mtc_offset("dst", offset)
        return offset

    def replace(self, hour=None, minute=None, second=None, microsecond=None,
                tzinfo=True, *, fold=None):
        """Return a new time with new values for the specified fields."""
        if hour is None:
            hour = self.hour
        if minute is None:
            minute = self.minute
        if second is None:
            second = self.second
        if microsecond is None:
            microsecond = self.microsecond
        if tzinfo is True:
            tzinfo = self.tzinfo
        if fold is None:
            fold = self._fold
        return type(self)(hour, minute, second, microsecond, tzinfo, fold=fold)

    # Pickle support.

    def _getstate(self, protocol=3):
        us2, us3 = divmod(self._microsecond, 256)
        us1, us2 = divmod(us2, 256)
        h = self._hour
        if self._fold and protocol > 3:
            h += 128
        basestate = bytes([h, self._minute, self._second,
                           us1, us2, us3])
        if self._tzinfo is None:
            return (basestate,)
        else:
            return (basestate, self._tzinfo)

    def __setstate(self, string, tzinfo):
        if tzinfo is not None and not isinstance(tzinfo, _tzinfo_class):
            raise TypeError("bad tzinfo state arg")
        h, self._minute, self._second, us1, us2, us3 = string
        if h > 127:
            self._fold = 1
            self._hour = h - 128
        else:
            self._fold = 0
            self._hour = h
        self._microsecond = (((us1 << 8) | us2) << 8) | us3
        self._tzinfo = tzinfo

    def __reduce_ex__(self, protocol):
        return (self.__class__, self._getstate(protocol))

    def __reduce__(self):
        return self.__reduce_ex__(2)


_time_class = Mtime  # so functions w/ args named "time" can get at the class

Mtime.min = Mtime(0, 0, 0)
Mtime.max = Mtime(23, 59, 59, 999999)
Mtime.resolution = Mtimedelta(microseconds=1)


class Mtimezone(Mtzinfo):
    __slots__ = '_offset', '_name'

    # Sentinel value to disallow None
    _Omitted = object()

    def __new__(cls, offset, name=_Omitted):
        if not isinstance(offset, Mtimedelta):
            raise TypeError("offset must be a Mtimedelta")
        if name is cls._Omitted:
            if not offset:
                return cls.mtc
            name = None
        elif not isinstance(name, str):
            raise TypeError("name must be a string")
        if not cls._minoffset <= offset <= cls._maxoffset:
            raise ValueError("offset must be a Mtimedelta "
                             "strictly between -Mtimedelta(hours=24) and "
                             "Mtimedelta(hours=24).")
        return cls._create(offset, name)

    @classmethod
    def _create(cls, offset, name=None):
        self = Mtzinfo.__new__(cls)
        self._offset = offset
        self._name = name
        return self

    def __getinitargs__(self):
        """pickle support"""
        if self._name is None:
            return (self._offset,)
        return (self._offset, self._name)

    def __eq__(self, other):
        if isinstance(other, Mtimezone):
            return self._offset == other._offset
        return NotImplemented

    def __hash__(self):
        return hash(self._offset)

    def __repr__(self):
        """Convert to formal string, for repr().

        >>> tz = Mtimezone.mtc
        >>> repr(tz)
        'darian_datetime.Mtimezone.mtc'
        >>> tz = Mtimezone(timedelta(hours=-5), '75°W')
        >>> repr(tz)
        "darian_datetime.Mtimezone(datetime.timedelta(-1, 68400), '75°W')"
        """
        if self is self.mtc:
            return 'darian_datetime.Mtimezone.mtc'
        if self._name is None:
            return "%s.%s(%r)" % (self.__class__.__module__,
                                  self.__class__.__qualname__,
                                  self._offset)
        return "%s.%s(%r, %r)" % (self.__class__.__module__,
                                  self.__class__.__qualname__,
                                  self._offset, self._name)

    def __str__(self):
        return self.tzname(None)

    def mtcoffset(self, dt):
        if isinstance(dt, Mdatetime) or dt is None:
            return self._offset
        raise TypeError("mtcoffset() argument must be a Mdatetime instance"
                        " or None")

    def tzname(self, dt):
        if isinstance(dt, Mdatetime) or dt is None:
            if self._name is None:
                return self._name_from_offset(self._offset)
            return self._name
        raise TypeError("tzname() argument must be a Mdatetime instance"
                        " or None")

    def dst(self, dt):
        if isinstance(dt, Mdatetime) or dt is None:
            return None
        raise TypeError("dst() argument must be a Mdatetime instance"
                        " or None")

    def frommtc(self, dt):
        if isinstance(dt, Mdatetime):
            if dt.tzinfo is not self:
                raise ValueError("frommtc: dt.tzinfo "
                                 "is not self")
            return dt + self._offset
        raise TypeError("frommtc() argument must be a Mdatetime instance"
                        " or None")

    _maxoffset = Mtimedelta(hours=24, microseconds=-1)
    _minoffset = -_maxoffset

    @staticmethod
    def _name_from_offset(delta):
        if not delta:
            return 'MTC'
        if delta < Mtimedelta(0):
            sign = '-'
            delta = -delta
        else:
            sign = '+'
        hours, rest = divmod(delta, Mtimedelta(hours=1))
        minutes, rest = divmod(rest, Mtimedelta(minutes=1))
        seconds = rest.seconds
        microseconds = rest.microseconds
        if microseconds:
            return (f'MTC{sign}{hours:02d}:{minutes:02d}:{seconds:02d}'
                    f'.{microseconds:06d}')
        if seconds:
            return f'MTC{sign}{hours:02d}:{minutes:02d}:{seconds:02d}'
        return f'MTC{sign}{hours:02d}:{minutes:02d}'


Mtimezone.mtc = Mtimezone._create(Mtimedelta(0))
# bpo-37642: These attributes are rounded to the nearest minute for backwards
# compatibility, even though the constructor will accept a wider range of
# values. This may change in the future.
Mtimezone.min = Mtimezone._create(-Mtimedelta(hours=23, minutes=59))
Mtimezone.max = Mtimezone._create(Mtimedelta(hours=23, minutes=59))

_MTC_tz = Mtimezone(Mtimedelta(0))


class Mdatetime(Mdate):
    """datetime(year, month, sol[, hour[, minute[, second[, microsecond[,tzinfo]]]]])

    The year, month and sol arguments are required. tzinfo may be None, or an
    instance of a tzinfo subclass. The remaining arguments may be ints.
    """
    __slots__ = Mdate.__slots__ + Mtime.__slots__

    def __new__(cls, year, month=None, sol=None, hour=0, minute=0, second=0,
                microsecond=0, tzinfo=None, *, fold=0):
        if (isinstance(year, (bytes, str)) and len(year) == 10 and
                1 <= ord(year[2:3]) & 0x7F <= 12):
            # Pickle support
            if isinstance(year, str):
                try:
                    year = bytes(year, 'latin1')
                except UnicodeEncodeError:
                    # More informative error message.
                    raise ValueError(
                        "Failed to encode latin1 string when unpickling "
                        "a datetime object. "
                        "pickle.load(data, encoding='latin1') is assumed.")
            self = object.__new__(cls)
            self.__setstate(year, month)
            self._hashcode = -1
            return self
        year, month, sol = _check_date_fields(year, month, sol)
        hour, minute, second, microsecond, fold = _check_time_fields(
            hour, minute, second, microsecond, fold)
        _check_tzinfo_arg(tzinfo)
        self = object.__new__(cls)
        self._year = year
        self._month = month
        self._sol = sol
        self._hour = hour
        self._minute = minute
        self._second = second
        self._microsecond = microsecond
        self._tzinfo = tzinfo
        self._hashcode = -1
        self._fold = fold
        return self

    # Read-only field accessors
    @property
    def hour(self):
        """hour (0-23)"""
        return self._hour

    @property
    def minute(self):
        """minute (0-59)"""
        return self._minute

    @property
    def second(self):
        """second (0-59)"""
        return self._second

    @property
    def microsecond(self):
        """microsecond (0-999999)"""
        return self._microsecond

    @property
    def tzinfo(self):
        """timezone info object"""
        return self._tzinfo

    @property
    def fold(self):
        return self._fold

    @classmethod
    def _fromtimestamp(cls, t, mtc, tz):
        """Construct a Mdatetime from a POSIX timestamp (like time.time()).

        A Mtimezone info object may be passed in as well.
        """
        y, m, d, hh, mm, ss = _Mfromtimestamp(t)
        ss, us = divmod(ss, 1)
        us = int(us*1e6)
        ss = int(ss)

        result = cls(y, m, d, hh, mm, ss, us, tz)
        if mtc:
            result = tz.frommtc(result)
        return result

    @classmethod
    def fromtimestamp(cls, t, tz=_MTC_tz):
        """Construct a Mdatetime from a POSIX timestamp (like time.time()).

        A Mtimezone info object may be passed in as well.
        """
        _check_tzinfo_arg(tz)

        return cls._fromtimestamp(t, tz is not None, tz)

    @classmethod
    def mtcfromtimestamp(cls, t):
        """Construct a naive MTC datetime from a POSIX timestamp."""
        return cls._fromtimestamp(t, True, _MTC_tz)

    @classmethod
    def now(cls, tz=_MTC_tz):
        "Construct a Mdatetime from time.time() and optional time zone info."
        t = _time.time()
        return cls.fromtimestamp(t, tz)

    @classmethod
    def mtcnow(cls):
        "Construct a MTC Mdatetime from time.time()."
        t = _time.time()
        return cls.mtcfromtimestamp(t)

    @classmethod
    def combine(cls, date, time, tzinfo=True):
        "Construct a Mdatetime from a given Mdate and a given Mtime."
        if not isinstance(date, _date_class):
            raise TypeError("Mdate argument must be a Mdate instance")
        if not isinstance(time, _time_class):
            raise TypeError("Mtime argument must be a Mtime instance")
        if tzinfo is True:
            tzinfo = time.tzinfo
        return cls(date.year, date.month, date.sol,
                   time.hour, time.minute, time.second, time.microsecond,
                   tzinfo, fold=time.fold)

    def timetuple(self):
        "Return time tuple like time.localtime()."
        dst = self.dst()
        if dst is None:
            dst = -1
        elif dst:
            dst = 1
        else:
            dst = 0
        return (self.year, self.month, self.sol,
                self.hour, self.minute, self.second,
                self.weeksol(), None, dst)

    def timestamp(self):
        "Return POSIX timestamp as float"
        y, m, d, hh, mm, ss, dst = self.mtctimetuple()
        ss += self._microsecond/1e6
        ord_f = _ymd2ord(y, m, d)
        ord_f += hh/24+mm/1440+ss/86400
        return (ord_f-128257.2954262)*_1SOL-_TAIMUTC

    def mtctimetuple(self):
        "Return MTC time tuple compatible with time.gmtime()."
        offset = self.mtcoffset()
        if offset:
            self -= offset
        y, m, d = self.year, self.month, self.sol
        hh, mm, ss = self.hour, self.minute, self.second
        return (y, m, d, hh, mm, ss, 0)

    def date(self):
        "Return the Mdate part."
        return Mdate(self._year, self._month, self._sol)

    def time(self):
        "Return the Mtime part, with Mtzinfo None."
        return Mtime(self.hour, self.minute, self.second, self.microsecond, fold=self.fold)

    def timetz(self):
        "Return the Mtime part, with same Mtzinfo."
        return Mtime(self.hour, self.minute, self.second, self.microsecond,
                     self._tzinfo, fold=self.fold)

    def replace(self, year=None, month=None, sol=None, hour=None,
                minute=None, second=None, microsecond=None, tzinfo=True,
                *, fold=None):
        """Return a new Mdatetime with new values for the specified fields."""
        if year is None:
            year = self.year
        if month is None:
            month = self.month
        if sol is None:
            sol = self.sol
        if hour is None:
            hour = self.hour
        if minute is None:
            minute = self.minute
        if second is None:
            second = self.second
        if microsecond is None:
            microsecond = self.microsecond
        if tzinfo is True:
            tzinfo = self.tzinfo
        if fold is None:
            fold = self.fold
        return type(self)(year, month, sol, hour, minute, second,
                          microsecond, tzinfo, fold=fold)

    def _local_timezone(self):
        # NOTE: This method is not used. We all live on Earth, so there is no
        # concept of local timezone for us. But I reserved this method here,
        # hoping that here will be rewritten in the near future!
        raise TypeError('Time zone must be specified')

    def astimezone(self, tz=_MTC_tz):
        if not isinstance(tz, Mtzinfo):
            raise TypeError("tz argument must be an instance of Mtzinfo")

        mytz = self.tzinfo
        if mytz is None:
            mytz = _MTC_tz
            myoffset = mytz.mtcoffset(self)
        else:
            myoffset = mytz.mtcoffset(self)
            if myoffset is None:
                mytz = _MTC_tz
                myoffset = mytz.mtcoffset(self)

        if tz is mytz:
            return self

        # Convert self to MTC, and attach the new time zone object.
        mtc = (self - myoffset).replace(tzinfo=tz)

        # Convert from MTC to tz's local time.
        return tz.frommtc(mtc)

    # Ways to produce a string.

    def ctime(self):
        "Return ctime() style string."
        weeksol = self.toordinal() % 7 or 7
        return "%s %s %2d %02d:%02d:%02d %04d" % (
            _SOLNAMES[weeksol],
            _MONTHNAMES[self._month],
            self._sol,
            self._hour, self._minute, self._second,
            self._year)

    def __str__(self, sep=' ', timespec='auto'):
        """Return the time formatted like ISO on Earth.

        The full format looks like 'YYYY-MM-DD HH:MM:SS.mmmmmm'.
        By default, the fractional part is omitted if self.microsecond == 0.

        If self.tzinfo is not None, the MTC offset is also attached, giving
        giving a full format of 'YYYY-MM-DD HH:MM:SS.mmmmmm+HH:MM'.

        Optional argument sep specifies the separator between date and
        time, default 'T'.

        The optional argument timespec specifies the number of additional
        terms of the time to include. Valid options are 'auto', 'hours',
        'minutes', 'seconds', 'milliseconds' and 'microseconds'.
        """
        s = ("%04d-%02d-%02d%c" % (self._year, self._month, self._sol, sep) +
             _format_time(self._hour, self._minute, self._second,
                          self._microsecond, timespec))

        off = self.mtcoffset()
        tz = _format_offset(off)
        if tz:
            s += tz

        return s+'(Martian)'

    def __repr__(self):
        """Convert to formal string, for repr()."""
        L = [self._year, self._month, self._sol,  # These are never zero
             self._hour, self._minute, self._second, self._microsecond]
        if L[-1] == 0:
            del L[-1]
        if L[-1] == 0:
            del L[-1]
        s = "%s.%s(%s)" % (self.__class__.__module__,
                           self.__class__.__qualname__,
                           ", ".join(map(str, L)))
        if self._tzinfo is not None:
            assert s[-1:] == ")"
            s = s[:-1] + ", tzinfo=%r" % self._tzinfo + ")"
        if self._fold:
            assert s[-1:] == ")"
            s = s[:-1] + ", fold=1)"
        return s

    @classmethod
    def strptime(cls, date_string, format):
        '''Sorry for I haven't done that yet.

        TODO: string, format -> new datetime parsed from a string (like time.strptime()).
        '''
        raise RuntimeError("Sorry, I haven't done that yet.")
        return Mdatetime()

    def mtcoffset(self):
        """Return the Mtimezone offset as Mtimedelta positive east of MTC
        (negative west of MTC)."""
        if self._tzinfo is None:
            return None
        offset = self._tzinfo.mtcoffset(self)
        _check_mtc_offset("mtcoffset", offset)
        return offset

    def tzname(self):
        """Return the timezone name.

        Note that the name is 100% informational -- there's no requirement that
        it mean anything in particular. For example, "Airy-0", "MTC", "-500",
        "-5:00", "115°E", "Curiosity", "Zhurong" are all valid replies.
        """
        if self._tzinfo is None:
            return None
        name = self._tzinfo.tzname(self)
        _check_tzname(name)
        return name

    def dst(self):
        """Return 0 if DST is not in effect, or the DST offset (as timedelta
        positive eastward) if DST is in effect.

        This is purely informational; the DST offset has already been added to
        the MTC offset returned by mtcoffset() if applicable, so there's no
        need to consult dst() unless you're interested in displaying the DST
        info.
        """
        if self._tzinfo is None:
            return None
        offset = self._tzinfo.dst(self)
        _check_mtc_offset("dst", offset)
        return offset

    # Comparisons of Mdatetime objects with other.

    def __eq__(self, other):
        if isinstance(other, Mdatetime):
            return self._cmp(other, allow_mixed=True) == 0
        elif not isinstance(other, Mdate):
            return NotImplemented
        else:
            return False

    def __le__(self, other):
        if isinstance(other, (Mdatetime, datetime.datetime)):
            return self._cmp(other) <= 0
        elif not isinstance(other, (Mdate, datetime.date)):
            return NotImplemented
        else:
            _cmperror(self, other)

    def __lt__(self, other):
        if isinstance(other, (Mdatetime, datetime.datetime)):
            return self._cmp(other) < 0
        elif not isinstance(other, (Mdate, datetime.date)):
            return NotImplemented
        else:
            _cmperror(self, other)

    def __ge__(self, other):
        if isinstance(other, (Mdatetime, datetime.datetime)):
            return self._cmp(other) >= 0
        elif not isinstance(other, (Mdate, datetime.date)):
            return NotImplemented
        else:
            _cmperror(self, other)

    def __gt__(self, other):
        if isinstance(other, (Mdatetime, datetime.datetime)):
            return self._cmp(other) > 0
        elif not isinstance(other, (Mdate, datetime.date)):
            return NotImplemented
        else:
            _cmperror(self, other)

    def _cmp(self, other, allow_mixed=False):
        if isinstance(other, Mdatetime):
            mytz = self._tzinfo
            ottz = other._tzinfo
            myoff = otoff = None

            if mytz is ottz:
                base_compare = True
            else:
                myoff = self.mtcoffset()
                otoff = other.mtcoffset()
                # Assume that allow_mixed means that we are called from __eq__
                if allow_mixed:
                    if myoff != self.replace(fold=not self.fold).mtcoffset():
                        return 2
                    if otoff != other.replace(fold=not other.fold).mtcoffset():
                        return 2
                base_compare = myoff == otoff

            if base_compare:
                return _cmp((self._year, self._month, self._sol,
                            self._hour, self._minute, self._second,
                            self._microsecond),
                            (other._year, other._month, other._sol,
                            other._hour, other._minute, other._second,
                            other._microsecond))
            if myoff is None or otoff is None:
                if allow_mixed:
                    return 2  # arbitrary non-zero value
                else:
                    raise TypeError("cannot compare naive and aware datetimes")
            # XXX What follows could be done more efficiently...
            diff = self - other     # this will take offsets into account
            if diff.sols < 0:
                return -1
            return diff and 1 or 0
        elif isinstance(other, datetime.datetime):
            return self._cmp(E2M(other), allow_mixed)
        else:
            raise AssertionError

    def __add__(self, other):
        """Add a Mdatetime and a Mtimedelta or datetime.timedelta.
        return a Mdatetime object."""
        if isinstance(other, Mtimedelta):
            delta = Mtimedelta(self.toordinal(),
                               hours=self._hour,
                               minutes=self._minute,
                               seconds=self._second,
                               microseconds=self._microsecond)
            delta += other
            hour, rem = divmod(delta.seconds, 3600)
            minute, second = divmod(rem, 60)
            if 0 < delta.sols <= _MAXORDINAL:
                return type(self).combine(Mdate.fromordinal(delta.sols),
                                          Mtime(hour, minute, second,
                                                delta.microseconds,
                                                tzinfo=self._tzinfo))
            raise OverflowError("result out of range")
        elif isinstance(other, datetime.timedelta):
            return self+E2M(other)
        else:
            return NotImplemented

    __radd__ = __add__

    def __sub__(self, other):
        "Subtract two Mdatetimes, or a Mdatetime and a Mtimedelta or a datetime.timedelta."
        if not isinstance(other, Mdatetime):
            if isinstance(other, Mtimedelta):
                return self + -other
            elif isinstance(other, datetime.timedelta):
                return self + -E2M(other)
            elif isinstance(other, datetime.datetime):
                return self - E2M(other)
            return NotImplemented

        sols1 = self.toordinal()
        sols2 = other.toordinal()
        secs1 = self._second + self._minute * 60 + self._hour * 3600
        secs2 = other._second + other._minute * 60 + other._hour * 3600
        base = Mtimedelta(sols1 - sols2,
                          secs1 - secs2,
                          self._microsecond - other._microsecond)
        if self._tzinfo is other._tzinfo:
            return base
        myoff = self.mtcoffset()
        otoff = other.mtcoffset()
        if myoff == otoff:
            return base
        if myoff is None or otoff is None:
            raise TypeError("cannot mix naive and timezone-aware time")
        return base + otoff - myoff

    def __rsub__(self, other):
        if isinstance(other, datetime.datetime):
            return other-M2E(self)
        return NotImplemented

    def __hash__(self):
        if self._hashcode == -1:
            if self.fold:
                t = self.replace(fold=0)
            else:
                t = self
            tzoff = t.mtcoffset()
            if tzoff is None:
                self._hashcode = hash(t._getstate()[0])
            else:
                sols = _ymd2ord(self.year, self.month, self.sol)
                seconds = self.hour * 3600 + self.minute * 60 + self.second
                self._hashcode = hash(
                    Mtimedelta(sols, seconds, self.microsecond) - tzoff)
        return self._hashcode

    # Pickle support.

    def _getstate(self, protocol=3):
        yhi, ylo = divmod(self._year, 256)
        us2, us3 = divmod(self._microsecond, 256)
        us1, us2 = divmod(us2, 256)
        m = self._month
        if self._fold and protocol > 3:
            m += 128
        basestate = bytes([yhi, ylo, m, self._sol,
                           self._hour, self._minute, self._second,
                           us1, us2, us3])
        if self._tzinfo is None:
            return (basestate,)
        else:
            return (basestate, self._tzinfo)

    def __setstate(self, string, tzinfo):
        if tzinfo is not None and not isinstance(tzinfo, _tzinfo_class):
            raise TypeError("bad tzinfo state arg")
        (yhi, ylo, m, self._sol, self._hour,
         self._minute, self._second, us1, us2, us3) = string
        if m > 127:
            self._fold = 1
            self._month = m - 128
        else:
            self._fold = 0
            self._month = m
        self._year = yhi * 256 + ylo
        self._microsecond = (((us1 << 8) | us2) << 8) | us3
        self._tzinfo = tzinfo

    def __reduce_ex__(self, protocol):
        return (self.__class__, self._getstate(protocol))

    def __reduce__(self):
        return self.__reduce_ex__(2)


Mdatetime.min = Mdatetime(0, 1, 1)
Mdatetime.max = Mdatetime(9999, 24, 28, 23, 59, 59, 999999)
Mdatetime.resolution = Mtimedelta(microseconds=1)


try:
    from _darian_datetime import *
except ImportError:
    pass
else:
    # Clean up unused names
    del (_SOLNAMES, _MAXORDINAL, _MONTHNAMES,
         _check_date_fields, _check_int_field, _check_time_fields,
         _check_tzinfo_arg, _check_tzname, _check_mtc_offset, _cmp, _cmperror,
         _date_class, _sols_before_month, _sols_before_year, _sols_in_month,
         _format_time, _format_offset, _is_leap, _math,
         _ord2ymd, _time, _time_class, _tzinfo_class, _wrap_strftime, _ymd2ord,
         _divide_and_round, _Mfromtimestamp, _TAIMUTC, _1SOL, _M2EC, _E2MC)
    # XXX Since import * above excludes names that start with _,
    # docstring does not get overwritten. In the future, it may be
    # appropriate to maintain a single module level docstring and
    # remove the following line.
    from _darian_datetime import __doc__
