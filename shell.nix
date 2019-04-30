{ pkgs ? import <nixpkgs> { } }:
let
    python = pkgs.python37.override {
        packageOverrides = self: super: {
            imagemagick7Big = pkgs.imagemagick7Big.overrideAttrs (oldAttrs: rec {
                buildInputs = oldAttrs.buildInputs ++ [ pkgs.liblqr1 ];
            });
        };
    };
    python-pkgs = python.withPackages (ps: [
        ps.Wand ps.telethon
    ]);
in pkgs.mkShell {
    name = "super-crunch-bot-shell";
    buildInputs = [ python-pkgs pkgs.openssl_1_0_2 ];
}