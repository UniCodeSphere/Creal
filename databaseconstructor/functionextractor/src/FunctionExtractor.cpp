#pragma once

#include <clang/ASTMatchers/ASTMatchFinder.h>
#include <clang/Tooling/Core/Replacement.h>
#include <clang/Tooling/Transformer/RewriteRule.h>

#include "FunctionExtractor.hpp"

namespace extractor {

auto functionMatcher = functionDecl(
    isExpansionInMainFile(),
    isDefinition(),
    anyOf(
      returns(isInteger()), 
      returns(isAnyCharacter()), 
      returns(pointsTo(isInteger())), 
      returns(pointsTo(isAnyCharacter()))
    ),
    anyOf(
      unless(hasDescendant(parmVarDecl(unless(anyOf(
        hasType(isInteger()),
        hasType(isAnyCharacter()), 
        hasType(pointsTo(isInteger())),
        hasType(pointsTo(isAnyCharacter()))
        ))))),
      unless(hasDescendant(parmVarDecl()))
    ),
    unless(hasDescendant(declRefExpr(to(varDecl(unless(anyOf(hasLocalStorage(), hasType(isInteger())))))))),
    unless(hasDescendant(invocation()))
    ).bind("function");

auto typedefMatcher = typedefDecl(
    isExpansionInMainFile(),
    anyOf(
        hasType(isInteger()),
        hasType(isAnyCharacter()), 
        hasType(realFloatingPointType()),
        hasType(pointsTo(isInteger())),
        hasType(pointsTo(isAnyCharacter())),
        hasType(pointsTo(realFloatingPointType()))
    )
).bind("typedef");

auto globalDeclMatcher = varDecl(
    isExpansionInMainFile(),
    hasGlobalStorage(),
    anyOf(
        hasType(isInteger()),
        hasType(isAnyCharacter()), 
        hasType(realFloatingPointType()),
        hasType(pointsTo(isInteger())),
        hasType(pointsTo(isAnyCharacter())),
        hasType(pointsTo(realFloatingPointType()))
    )
).bind("globalDecl");

} //namespace extractor


extractor::FunctionExtractor::FunctionExtractor(
    std::map<std::string, clang::tooling::Replacements> &FileToReplacements)
    : FileToReplacements{FileToReplacements} {}

void extractor::FunctionExtractor::registerMatchers(clang::ast_matchers::MatchFinder &Finder) {
    Finder.addMatcher(functionMatcher, &Printer);
    Finder.addMatcher(typedefMatcher, &Printer);
    Finder.addMatcher(globalDeclMatcher, &Printer);
}
