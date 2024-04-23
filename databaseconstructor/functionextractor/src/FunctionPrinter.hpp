#pragma once
#include <clang/ASTMatchers/ASTMatchFinder.h>

using namespace clang;
using namespace ast_matchers;

namespace printer {
  
class FunctionPrinter : public clang::ast_matchers::MatchFinder::MatchCallback  {
  public:
    FunctionPrinter();
    FunctionPrinter(const FunctionPrinter &) = delete;
    FunctionPrinter(FunctionPrinter &&) = delete;
    void
    run(const clang::ast_matchers::MatchFinder::MatchResult &Result) override;
};

std::string getFunctionAsText(const Decl *F, const SourceManager &SM, const LangOptions &lp);
} // namespace printer