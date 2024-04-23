#pragma once

#include <clang/ASTMatchers/ASTMatchFinder.h>
#include <clang/Tooling/Core/Replacement.h>
#include <clang/Tooling/Transformer/RewriteRule.h>

#include "ProfilerEntry.hpp"

using namespace tagexpression;
using namespace globalmacro;

namespace profiler {

ProfilerEntry::ProfilerEntry(
    std::map<std::string, clang::tooling::Replacements> &FileToReplacements, ToolMode mode)
    : FileToReplacements{FileToReplacements} {
    switch (mode)
    {
    case ToolMode::Expression:
        Callbacks.emplace_back(ruleactioncallback::RuleActionCallback{
          TagExpressionRule(), FileToReplacements, FileToNumberValueTrackers});
        break;
    case ToolMode::Statement:
        Callbacks.emplace_back(ruleactioncallback::RuleActionCallback{
          TagStatementRule(), FileToReplacements, FileToNumberValueTrackers});
        break;
    case ToolMode::All:
        Callbacks.emplace_back(ruleactioncallback::RuleActionCallback{
          TagExpressionRule(), FileToReplacements, FileToNumberValueTrackers});
        Callbacks.emplace_back(ruleactioncallback::RuleActionCallback{
          TagStatementRule(), FileToReplacements, FileToNumberValueTrackers});
        break;
    default:
        break;
    }
    Callbacks.emplace_back(ruleactioncallback::RuleActionCallback{
          AddGlobalMacroRule(), FileToReplacements, FileToNumberValueTrackers});

}

void ProfilerEntry::registerMatchers(clang::ast_matchers::MatchFinder &Finder) {
    for (auto &Callback : Callbacks)
        Callback.registerMatchers(Finder);
}

} //namespace profiler
