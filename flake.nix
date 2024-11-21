{
  description = "A very basic flake";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-24.05";
  };

  outputs = { self, nixpkgs }: let
    pkgs = import nixpkgs {
      system = "x86_64-linux";
      config.allowUnfree = true;
    };
    python-env = pkgs.python3.withPackages (p:
      with p; [
        mininet-python
        python-lsp-server
        matplotlib
      ]);
  in {
    devShells.x86_64-linux.default = pkgs.mkShell {
      buildInputs = with pkgs; [
        mininet
        iperf
        inetutils
        libcgroup
        python-env
      ];
    };
  };
}
