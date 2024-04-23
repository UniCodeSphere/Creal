#pragma once
#include <algorithm>
#include "RenameGlobal.hpp"

namespace process {

/* Rename global variable declaration */
struct clang::transformer::RewriteRule processRenameGlobalRule() {
    auto globalDeclMatcher = varDecl(
        isExpansionInMainFile(),
        hasGlobalStorage(),
        hasAncestor(translationUnitDecl(
            hasDescendant(
                functionDecl(
                    isExpansionInMainFile(),
                    isDefinition()
                ).bind("function")
            )
        ))
    ).bind("globalDecl");
    
    return makeRule(globalDeclMatcher, {
        insertAfter(name("globalDecl"), cat("_", name("function"))),
    });
}

/* Rename global variable reference */
struct clang::transformer::RewriteRule processRenameGlobalRefRule() {
    auto globalDefRefMatcher = declRefExpr(
        isExpansionInMainFile(),
        to(varDecl(
            hasGlobalStorage()
        )),
        hasAncestor(functionDecl(
                    isExpansionInMainFile(),
                    isDefinition()
                ).bind("function")
            )
    ).bind("globalDeclRef");
    
    return makeRule(globalDefRefMatcher, {
        insertAfter(node("globalDeclRef"), cat("_", name("function"))),
    });
}

} // namespace process

process::RenameGlobal::RenameGlobal(
    std::map<std::string, clang::tooling::Replacements> &FileToReplacements)
    : FileToReplacements{FileToReplacements} {
        ruleCallbacks.emplace_back(ruleactioncallback::RuleActionCallback{
            process::processRenameGlobalRule(), FileToReplacements, FileToNumberValueTrackers});
        ruleCallbacks.emplace_back(ruleactioncallback::RuleActionCallback{
            process::processRenameGlobalRefRule(), FileToReplacements, FileToNumberValueTrackers});
    }

void process::RenameGlobal::registerMatchers(clang::ast_matchers::MatchFinder &Finder) {
    for (auto &Callback : ruleCallbacks){
      Callback.registerMatchers(Finder);
    }
}
