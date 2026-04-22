// GENERATED FILE
#pragma once

#include <modules/register_module_types.h>
#include <core/string/print_string.h>

namespace godot
{
template <typename... Args>
void print_error(Args... p_args) {
	Variant variants[sizeof...(p_args)] = { p_args... };
	print_error(stringify_variants(Span(variants)));
}
}

#ifdef GODOT_MODULE
#define FORWARD_DECLARE_GODOT(X) X;
#else
#define FORWARD_DECLARE_GODOT(X) namespace godot { X; }
#endif


#ifndef GODOT_MODULE
// This is in core/string/string_name.h in Godot
#define SNAME(m_arg) ([]() -> const StringName & { static StringName sname = StringName(m_arg, true); return sname; })()
#endif

