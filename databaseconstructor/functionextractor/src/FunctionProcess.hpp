#pragma once

#include "RuleActionCallback.hpp"
#include "ProcessCall.hpp"
#include "RenameFunction.hpp"

namespace process {
  
class FunctionProcess {
  public:
    FunctionProcess(std::map<std::string, clang::tooling::Replacements> &FileToReplacements);
    FunctionProcess(const FunctionProcess &) = delete;
    FunctionProcess(FunctionProcess &&) = delete;

    void registerMatchers(clang::ast_matchers::MatchFinder &Finder);


  private:
    std::map<std::string, clang::tooling::Replacements> &FileToReplacements;
    std::vector<ruleactioncallback::RuleActionCallback> ruleCallbacks;
    std::map<std::string, int> FileToNumberValueTrackers;
};

} // namespace process