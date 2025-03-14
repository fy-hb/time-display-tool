{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    systems.url = "github:nix-systems/x86_64-linux";
    flake-utils.url = "github:numtide/flake-utils";
    flake-utils.inputs.systems.follows = "systems";
  };
  outputs = { self, nixpkgs, flake-utils, systems }:
    flake-utils.lib.eachDefaultSystem (system:
      let pkgs = nixpkgs.legacyPackages.${system}; in
      {
        packages = {
          default = pkgs.python312Packages.buildPythonApplication rec {
            pname = "time-display-tool";
            version = "0.1.0";
            pyproject = true;
            src = ./.;
            propagatedBuildInputs = with pkgs.python312Packages; [
              ntplib tkinter
            ];
            build-system = with pkgs.python312Packages; [
              setuptools
            ];
            postInstall = ''
              install -Dm755 main.py $out/bin/${pname}
              rm $out/bin/main.py
            '';
          };
        };
      }
    );
}
