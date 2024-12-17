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
        cmake
        cargo
        curlHTTP3
        openssl
        openvswitch
        mininet
        iperf
        inetutils
        python-env
        (texlive.combine {
          inherit (texlive) scheme-basic wrapfig etoolbox xcolor
            enumitem supertabular titlesec multirow parskip
            biblatex fontawesome fontawesome5
          ;
        })
      ];
    };
  };
}
