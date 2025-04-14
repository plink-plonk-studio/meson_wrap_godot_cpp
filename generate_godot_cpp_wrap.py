#!/usr/bin/env python3

import subprocess
import os
import json
import urllib.request
import shutil
import glob

def get_latest_tagged_version(repo_owner, repo_name):
   
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/git/matching-refs/tags"

    try:        
        with urllib.request.urlopen(url) as response:
            data = response.read()
            tags = json.loads(data.decode('utf-8'))
            if tags:
                return tags[-1]['ref'].replace('refs/tags/', '')
            else:
                return None
    except Exception as e:
        print(f"Error fetching tags: {e}")
        return None

def download_godot_cpp(version, output_dir):
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir) # TODO: warn?

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    repo_url = "https://github.com/godotengine/godot-cpp"
    command = ["git", "clone", "--depth", "1", "--branch", version, repo_url, output_dir]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"Downloaded Godot-CPP version {version} to {output_dir}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error downloading Godot-CPP: {e.stderr}")
        return False


def generate_meson_build_file(godot_version, godot_cpp_folder):


    shutil.copyfile(os.path.join('godot-cpp', 'meson-bindings-generator.py'), os.path.join(godot_cpp_folder, 'meson-bindings-generator.py'))
   
    try:
        command = ["python3", "meson-bindings-generator.py", "gdextension/extension_api.json", ".", "single"]
        subprocess.run(command, check=True, capture_output=True, text=True, cwd=godot_cpp_repo_directory)
        print(f"Generated bindings")
    except subprocess.CalledProcessError as e:
        print(f"Failed to generate bindings: {e.stderr}")
        return

    generated_sources = [ f"  '{x.replace(godot_cpp_repo_directory, '.')}'" for x in glob.glob(os.path.join(godot_cpp_repo_directory, 'gen', 'src', '**','*.cpp'), recursive=True) ]
    generated_sources.sort()
    generated_sources = ',\n'.join(generated_sources)
    
    core_sources = [ f"  '{x.replace(godot_cpp_repo_directory, '.')}'" for x in glob.glob(os.path.join(godot_cpp_repo_directory, 'src', '**', '*.cpp'), recursive=True) ]
    core_sources.sort()
    core_sources = ',\n'.join(core_sources)

    version_value = godot_version.split('-')[1]

    meson_content = f"""# GENERATED FILE - DO NOT EDIT

project(
  'godot-cpp',
  'cpp',
  version: '{version_value}',
  default_options: ['cpp_std=c++17', 'cpp_eh=none'],
)

cpp_compiler = meson.get_compiler('cpp')
godot_precision = get_option('precision')

# Disable warning: https://github.com/mesonbuild/meson/issues/13978
warnings_to_suppress = ['-U_LIBCPP_ENABLE_ASSERTIONS']
foreach p : warnings_to_suppress
  if cpp_compiler.has_argument(p)
    add_project_arguments(p, language: 'cpp')
  endif
endforeach

godot_cpp_compiler_defines = [
  '-DDEBUG_ENABLED',
  '-DDEBUG_METHODS_ENABLED',
  '-DGDEXTENSION',
  '-DHOT_RELOAD_ENABLED',
  '-DMACOS_ENABLED',
  '-DTHREADS_ENABLED',
  '-DUNIX_ENABLED',
]
foreach p : godot_cpp_compiler_defines
  if cpp_compiler.has_argument(p)
    add_project_arguments(p, language: 'cpp')
  endif
endforeach

fs = import('fs')

# We need to check if code is already generated. It doesn't matter what you
# check - include directory or some generated file, as long as you can detect
# whether to run meson-bindings-generator or not
if not fs.exists('gen/include/')
  message(f'Generating Godot classes by api.json. precison: @godot_precision@')
  run_command(
    './meson-bindings-generator.py',
    'gdextension/extension_api.json',
    '.',
    godot_precision,
    check: true,
  )
endif

includes = include_directories(
  'include/',
  'gdextension/',
  'gen/include/',
)

generated_sources = [
{generated_sources},
]

core_sources = [
{core_sources},
]

godot_cpp_lib = static_library(
  'godot-cpp',
  core_sources + generated_sources,
  include_directories: includes,
  pic: true,
  gnu_symbol_visibility: 'hidden',
)

godot_cpp_dep = declare_dependency(include_directories: includes, link_with: godot_cpp_lib)"""

    with open(os.path.join('godot-cpp', 'meson.build'), "w") as f:
        f.write(meson_content)

    print(f"Generated meson.build")

if __name__ == "__main__":
    godot_cpp_repo_directory = ".tmp_godot_cpp"

    latest_tag = get_latest_tagged_version("godotengine", "godot-cpp")

    if latest_tag:
        print(f"Latest tagged version: {latest_tag}")
        if download_godot_cpp(latest_tag, godot_cpp_repo_directory):
            generate_meson_build_file(latest_tag, godot_cpp_repo_directory)
            shutil.rmtree(godot_cpp_repo_directory)
        else:
            print("Failed to download Godot-CPP.")
    else:
        print("No tags found for the repository.")
