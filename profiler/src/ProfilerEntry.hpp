#pragma once

#include <clang/ASTMatchers/ASTMatchers.h>
#include <clang/Tooling/Transformer/RewriteRule.h>
#include <clang/Tooling/Transformer/Stencil.h>

#include <clang/AST/Decl.h>
#include <clang/ASTMatchers/ASTMatchFinder.h>
#include <clang/Basic/TargetOptions.h>
#include <clang/Tooling/CommonOptionsParser.h>
#include <clang/Tooling/Tooling.h>
#include <clang/Tooling/Transformer/MatchConsumer.h>

#include "RuleActionCallback.hpp"
#include "TagExpression.hpp"
#include "GlobalMacro.hpp"

namespace profiler {

enum class ToolMode {
    Expression,
    Statement,
    All
};
  
class ProfilerEntry {
  public:
    ProfilerEntry(std::map<std::string, clang::tooling::Replacements> &FileToReplacements, ToolMode mode);
    ProfilerEntry(const ProfilerEntry &) = delete;
    ProfilerEntry(ProfilerEntry &&) = delete;

    void registerMatchers(clang::ast_matchers::MatchFinder &Finder);


  private:
    std::map<std::string, clang::tooling::Replacements> &FileToReplacements;
    std::vector<ruleactioncallback::RuleActionCallback> Callbacks;
    std::map<std::string, int> FileToNumberValueTrackers;
};
} // namespace profiler