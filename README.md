# Godot CPP Meson Wrapper

## Usage

Download the [godot-cpp.wrap](https://github.com/plink-plonk-studio/meson_wrap_godot_cpp/releases/latest/download/godot-cpp.wrap) for the release version you would like to use, and put it in your `subprojects` folder.

## Generate a new release

```bash
./genererate_godot_cpp_wrap.py
git add .
git commit -m "Updated version"
git push
git tag -a $INSERT_GODOT_VERSION_FROM_ABOVE -m "Some useful comment"
git push origin $INSERT_GODOT_VERSION_FROM_ABOVE
```
