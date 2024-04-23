#pragma once

#include <clang/ASTMatchers/ASTMatchFinder.h>
#include <clang/Tooling/Core/Replacement.h>
#include <clang/Tooling/Transformer/RewriteRule.h>

#include "FunctionProcess.hpp"

process::FunctionProcess::FunctionProcess(
    std::map<std::string, clang::tooling::Replacements> &FileToReplacements)
    : FileToReplacements{FileToReplacements} {
      ruleCallbacks.emplace_back(ruleactioncallback::RuleActionCallback{
          process::processCallRule(), FileToReplacements, FileToNumberValueTrackers});
      ruleCallbacks.emplace_back(ruleactioncallback::RuleActionCallback{
          process::processExternRule(), FileToReplacements, FileToNumberValueTrackers});
    }

void process::FunctionProcess::registerMatchers(clang::ast_matchers::MatchFinder &Finder) {
    for (auto &Callback : ruleCallbacks){
      Callback.registerMatchers(Finder);
    }
}

