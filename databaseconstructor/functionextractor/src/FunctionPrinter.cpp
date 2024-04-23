#pragma once
#include <clang/ASTMatchers/ASTMatchFinder.h>
#include <clang/Lex/Lexer.h>
#include <clang/Tooling/Tooling.h>

#include <nlohmann/json.hpp>
#include <nlohmann/json_fwd.hpp>
#include <iostream>

#include "FunctionPrinter.hpp"

using namespace clang;
using namespace ast_matchers;

namespace printer {

std::string getFunctionAsText(const Decl *F,
                              const SourceManager &SM, const LangOptions &lp) {
  auto SR = CharSourceRange::getTokenRange(F->getSourceRange());
  return Lexer::getSourceText(SR, SM, lp).str();
}

FunctionPrinter::FunctionPrinter(){}

void FunctionPrinter::run(const clang::ast_matchers::MatchFinder::MatchResult &Result) {
    nlohmann::json J;
    if (const auto *F = Result.Nodes.getNodeAs<clang::FunctionDecl>("function")) {
        std::vector<std::string> ParameterTypes;
        if (F->param_size() == 0)
            ParameterTypes.push_back("void");
        const auto &SM = *Result.SourceManager;
        auto *FEntry = SM.getFileEntryForID(
            SM.getDecomposedLoc(F->getLocation()).first);
        // J["original_file"] = FEntry->getName(); // may crash
        J["function"] = getFunctionAsText(F, *Result.SourceManager, Result.Context->getLangOpts());
        std::transform(F->param_begin(), F->param_end(),
                        std::back_inserter(ParameterTypes),
                        [](const auto &Param) -> std::string {
                            return Param->getType().getAsString();
                        });
        J["parameter_types"] = ParameterTypes;
        J["return_type"] = F->getReturnType().getAsString();
        J["function_name"] = F->getName();
	    std::cout << J << '\n';
    }
    if (const auto *F = Result.Nodes.getNodeAs<clang::TypedefDecl>("typedef")) {
        const auto &SM = *Result.SourceManager;
        J["typedef"] = getFunctionAsText(F, *Result.SourceManager, Result.Context->getLangOpts());
	    std::cout << J << '\n';
    }
    if (const auto *F = Result.Nodes.getNodeAs<clang::VarDecl>("globalDecl")) {
        const auto &SM = *Result.SourceManager;
        J["global"] = getFunctionAsText(F, *Result.SourceManager, Result.Context->getLangOpts());
	    std::cout << J << '\n';
    }
}

} // namespace printer
