#pragma once

#include "RuleActionCallback.hpp"

namespace process {

class RenameFunction {
  public:
    RenameFunction(std::map<std::string, clang::tooling::Replacements> &FileToReplacements);
    RenameFunction(const RenameFunction &) = delete;
    RenameFunction(RenameFunction &&) = delete;

    void registerMatchers(clang::ast_matchers::MatchFinder &Finder);


  private:
    std::map<std::string, clang::tooling::Replacements> &FileToReplacements;
    std::vector<ruleactioncallback::RuleActionCallback> ruleCallbacks;
    std::map<std::string, int> FileToNumberValueTrackers;
};

} // namespace process