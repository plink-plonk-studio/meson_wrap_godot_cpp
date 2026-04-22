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
#define FORWARD_DECLARE_GODOT(X) X;
