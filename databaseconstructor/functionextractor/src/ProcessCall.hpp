#pragma once

#include "RuleActionCallback.hpp"
#include "FunctionProcess.hpp"

namespace process {

    struct clang::transformer::RewriteRule processCallRule();
    struct clang::transformer::RewriteRule processExternRule();

} // namespace process