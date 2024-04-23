#pragma once

#include "ProfilerEntry.hpp"

namespace tagexpression {

extern std::map<int, std::string> Tags; // <id, type>

struct clang::transformer::RewriteRule TagExpressionRule();
struct clang::transformer::RewriteRule TagStatementRule();

}