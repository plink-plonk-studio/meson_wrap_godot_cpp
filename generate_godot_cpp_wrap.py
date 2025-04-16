#!/usr/bin/env python3

import subprocess
import os
import json
import urllib.request
import shutil
import glob
import re

def get_latest_tagged_version(repo_owner, repo_name)->str:
   
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

def download_repo(repo_url, version, output_dir)->bool:
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    command = ["git", "clone", "--depth", "1", "--branch", version, repo_url, output_dir]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"Downloaded {repo_url.split('/')[-1]} version {version} to {output_dir}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error downloading {repo_url}: {e.stderr}")
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



all_godot_include_files_no_third_party = []
load_all_godot_headers = {}

def find_mapping(godot_cpp_header):
    header_filename = os.path.basename(godot_cpp_header)

    search_string = header_filename.removesuffix('.hpp').removesuffix('.inc')
    search_string_no_underscore = search_string.replace('_', '')
    search_strings = [
        f"\nclass {search_string} :",
        f"\nclass {search_string} " + '{',
        f"\nclass [[nodiscard]] {search_string} " + '{',
        f"\nstruct {search_string} " + '{',
        f"\nstruct [[nodiscard]] {search_string} " + '{',

        f"\nclass {search_string_no_underscore} :",
        f"\nclass {search_string_no_underscore} " + '{',
        f"\nclass [[nodiscard]] {search_string_no_underscore} " + '{',
        f"\nstruct {search_string_no_underscore} " + '{',
        f"\nstruct [[nodiscard]] {search_string_no_underscore} " + '{'
    ]
            
    for filename in all_godot_include_files_no_third_party:
        # print(f"checking {filename} for {search_string}")
        lowercase_file = load_all_godot_headers[filename]
        for s in search_strings:
            if s in lowercase_file: 
                return ( godot_cpp_header, filename )
        
        if re.search(f'typedef\s.*\s{search_string};', lowercase_file) or re.search(f'typedef\s.*\s{search_string_no_underscore};', lowercase_file):
            return ( godot_cpp_header, filename )
    
    all_godot_headers_lookup = { os.path.basename(x) : x for x in all_godot_include_files_no_third_party }

    if (search_string + '.h') in all_godot_headers_lookup:
        return ( godot_cpp_header, all_godot_headers_lookup[(search_string + '.h')] )
    return ( godot_cpp_header, None )


def generate_module_adaptor(godot_dir, godot_cpp_dir):
    all_godot_cpp_include_files = []
    for x in glob.glob(f'{godot_cpp_dir}/**/*.hpp', recursive=True) + glob.glob(f'{godot_cpp_dir}/**/*.h', recursive=True) + glob.glob(f'{godot_cpp_dir}/**/*.inc', recursive=True):
        if '/test/' in x or '/gdextension/' in x or '/version.hpp' in x:
            continue
        all_godot_cpp_include_files.append(x) 


    for x in glob.glob(f'{godot_dir}/**/*.hpp', recursive=True) + glob.glob(f'{godot_dir}/**/*.h', recursive=True):
        if '/thirdparty/' in x or '/mono/' in x or '/drivers/' in x:
            continue
        all_godot_include_files_no_third_party.append(x)

    # load in ALL the data 1m40 -> 1m13
    print("Loading all the godot headers...")
    for filename in all_godot_include_files_no_third_party:
        # print(f"checking {filename} for {search_string}")
        with open(filename, 'rb') as file:
            lowercase_file = str(file.read().decode("utf-8","ignore")).lower()
            load_all_godot_headers[filename] = lowercase_file
            
    print("Searching for mappings...")

    # we need to try and match them
    #mappings = []
    #with ThreadPool(processes = 10) as pool:
     #   mappings += pool.map(find_mapping, all_godot_cpp_include_files, chunksize=100)
            
    mappings = []
    for godot_cpp_header in all_godot_cpp_include_files:
        mappings.append(find_mapping(godot_cpp_header))



    unmatched = [ x[0] for x in  filter( lambda x: x[1] == None, mappings ) ] 

    godot_cpp_to_godot_mapping = dict(filter( lambda x: x[1] != None, mappings ))
    

    print('Unmatched:')
    print('\n'.join(unmatched))


    print(f"Total godot_cpp headers: {len(all_godot_cpp_include_files)}, found {len(godot_cpp_to_godot_mapping)} matching.")

    for godot_cpp_path, godot_path in godot_cpp_to_godot_mapping.items():
        output_path = godot_cpp_path.replace(f'{godot_cpp_dir}/gen/include/', '').replace(f'{godot_cpp_dir}/include/','')
        output_path = 'godot-cpp/godot_cpp_module_adaptor/' + output_path
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        header_code = f"// GENERATED FILE\n\n#include <{godot_path.replace(godot_dir + '/','')}>\n"
       
        with open(output_path, "w") as output:
            output.write(header_code)
            output.close()

    unmatched.append('gdextension_interface.h')

    for unmatches_godot_cpp_path in unmatched:
        output_path = unmatches_godot_cpp_path.replace(f'{godot_cpp_dir}/gen/include/', '').replace(f'{godot_cpp_dir}/include/','')
        output_path = 'godot-cpp/godot_cpp_module_adaptor/' + output_path
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        header_code = "// GENERATED EMPTY FILE\n"

        if os.path.basename(output_path) == 'godot.hpp':
            header_code = """// GENERATED FILE

#include <modules/register_module_types.h>

namespace godot
{
}
"""
        with open(output_path, "w") as output:
            output.write(header_code)
            output.close()


if __name__ == "__main__":
    godot_cpp_repo_directory = ".tmp_godot_cpp"
    godot_repo_directory = ".tmp_godot"

    latest_tag = get_latest_tagged_version("godotengine", "godot-cpp")

    if latest_tag:
        print(f"Latest tagged version: {latest_tag}")
        if download_repo("https://github.com/godotengine/godot-cpp", latest_tag, godot_cpp_repo_directory):
            generate_meson_build_file(latest_tag, godot_cpp_repo_directory)

            godot_version = latest_tag.removeprefix('godot-')

            print(f'Downloading godot {godot_version}')
            if download_repo("https://github.com/godotengine/godot", godot_version, godot_repo_directory):
                
                generate_module_adaptor(godot_repo_directory, godot_cpp_repo_directory)
                
                shutil.rmtree(godot_repo_directory)
            else:
                print("Failed to download Godot.")

            shutil.rmtree(godot_cpp_repo_directory)
        else:
            print("Failed to download Godot-CPP.")
    else:
        print("No tags found for the repository.")
