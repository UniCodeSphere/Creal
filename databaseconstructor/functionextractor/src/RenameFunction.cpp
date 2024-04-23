#pragma once
#include <algorithm>
#include "RenameFunction.hpp"

namespace process {

class ProcessRenameFunctionAction : public MatchComputation<std::string> {
public:
    ProcessRenameFunctionAction() = default;
    llvm::Error eval(const ast_matchers::MatchFinder::MatchResult &mResult,
                     std::string *Result) const override {
        const FunctionDecl *FD = mResult.Nodes.getNodeAs<clang::FunctionDecl>("function");
        std::string func_name = FD->getNameAsString();
        std::string new_func_name = "realsmith_" + extractor_utils::generate_random_string(5);
        // Result->append("realsmith_"+generate_random_string(5));
        std::string func_str = getFunctionAsText(FD, *mResult.SourceManager, mResult.Context->getLangOpts());
        size_t index = func_str.find(func_name);
        func_str.replace(index, func_name.length(), new_func_name);
        Result->append(func_str);
        return llvm::Error::success();
    }

    std::string toString() const override { return "{}"; }
    static std::string getFunctionAsText(const FunctionDecl *F,
                              const SourceManager &SM, const LangOptions &lp) {
        auto SR = CharSourceRange::getTokenRange(F->getSourceRange());
        return Lexer::getSourceText(SR, SM, lp).str();
    }
};


struct clang::transformer::RewriteRule processRenameFunctionRule() {
    auto functionMatcher = functionDecl(
    isExpansionInMainFile(),
    isDefinition()
    ).bind("function");
    
    return makeRule(functionMatcher, {
        changeTo(node("function"), std::make_unique<ProcessRenameFunctionAction>())
    });
}
}

process::RenameFunction::RenameFunction(
    std::map<std::string, clang::tooling::Replacements> &FileToReplacements)
    : FileToReplacements{FileToReplacements} {
      ruleCallbacks.emplace_back(ruleactioncallback::RuleActionCallback{
          process::processRenameFunctionRule(), FileToReplacements, FileToNumberValueTrackers});
    }

void process::RenameFunction::registerMatchers(clang::ast_matchers::MatchFinder &Finder) {
    for (auto &Callback : ruleCallbacks){
      Callback.registerMatchers(Finder);
    }
}
