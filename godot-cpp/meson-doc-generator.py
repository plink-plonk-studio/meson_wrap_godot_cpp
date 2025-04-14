#!/usr/bin/env python3

import doc_source_generator
import sys

# arg1: target, arg2: directory
doc_source_generator.generate_doc_source_from_directory('doc_source.cpp', '../doc_classes')

