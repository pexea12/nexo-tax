{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  packages = with pkgs; [
    gnumake
    patchelf
    python314
    uv
  ];

  env.UV_PYTHON_PREFERENCE = "only-system";

  # Shared libraries for uv-installed native binaries (ruff, ty).
  env.LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
    pkgs.stdenv.cc.cc.lib
    pkgs.zlib
  ];

  shellHook =
    let
      ld = "${pkgs.stdenv.cc.libc}/lib/ld-linux-x86-64.so.2";
    in ''
      # Patch uv-installed native binaries so they find the NixOS dynamic linker.
      _patch_venv_bins() {
        if [ -d .venv/bin ]; then
          for bin in .venv/bin/*; do
            [ -f "$bin" ] || continue
            [ -x "$bin" ] || continue
            interp=$(patchelf --print-interpreter "$bin" 2>/dev/null) || continue
            if [ "$interp" = "/lib64/ld-linux-x86-64.so.2" ]; then
              patchelf --set-interpreter "${ld}" "$bin"
            fi
          done
        fi
      }
      _patch_venv_bins
    '';
}
