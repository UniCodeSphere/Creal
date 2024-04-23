#pragma once

#include <clang/ASTMatchers/ASTMatchers.h>
#include <clang/Tooling/Transformer/RewriteRule.h>
#include <clang/Tooling/Transformer/Stencil.h>

#include <clang/AST/Decl.h>
#include <clang/ASTMatchers/ASTMatchFinder.h>
#include <clang/Basic/TargetOptions.h>
#include <clang/Tooling/CommonOptionsParser.h>
#include <clang/Tooling/Tooling.h>
#include <clang/Tooling/Transformer/MatchConsumer.h>

#include "FunctionPrinter.hpp"

namespace extractor {
  
class FunctionExtractor {
  public:
    FunctionExtractor(std::map<std::string, clang::tooling::Replacements> &FileToReplacements);
    FunctionExtractor(const FunctionExtractor &) = delete;
    FunctionExtractor(FunctionExtractor &&) = delete;

    void registerMatchers(clang::ast_matchers::MatchFinder &Finder);


  private:
    std::map<std::string, clang::tooling::Replacements> &FileToReplacements;
    std::map<std::string, int> FileToNumberValueTrackers;
    printer::FunctionPrinter Printer;
};
} // namespace extractor