#pragma once

#include "RuleActionCallback.hpp"

namespace process {

class RenameGlobal {
  public:
    RenameGlobal(std::map<std::string, clang::tooling::Replacements> &FileToReplacements);
    RenameGlobal(const RenameGlobal &) = delete;
    RenameGlobal(RenameGlobal &&) = delete;

    void registerMatchers(clang::ast_matchers::MatchFinder &Finder);


  private:
    std::map<std::string, clang::tooling::Replacements> &FileToReplacements;
    std::vector<ruleactioncallback::RuleActionCallback> ruleCallbacks;
    std::map<std::string, int> FileToNumberValueTrackers;
};

} // namespace process