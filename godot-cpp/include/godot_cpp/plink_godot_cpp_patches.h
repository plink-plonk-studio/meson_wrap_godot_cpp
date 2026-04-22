#pragma once

#define FORWARD_DECLARE_GODOT(X) namespace godot { X; }

// This is in core/string/string_name.h in Godot, but not in Godot-CPP
#define SNAME(m_arg) ([]() -> const StringName & { static StringName sname = StringName(m_arg, true); return sname; })()
