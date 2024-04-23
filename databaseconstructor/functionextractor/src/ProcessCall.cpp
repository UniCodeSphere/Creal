#pragma once
#include "ProcessCall.hpp"

namespace process {

std::string getTypeValue(std::string typeStr) {
    std::string value = "";
    /* char * */
    if (typeStr.find("char*") != -1 || typeStr.find("char *") != -1) {
        value.append("\"0\"");
        return value;
    }
    /*ignore types*/
    if (
        typeStr.find("struct") != -1 || 
        typeStr.find("union") != -1 ||
        std::count(typeStr.begin(), typeStr.end(), '*') > 0 ||
        std::count(typeStr.begin(), typeStr.end(), '[') > 0
        ) {
        return value;
    }
    /*integer*/
    if (
        typeStr.find("int") != -1 ||
        typeStr.find("long") != -1 ||
        typeStr.find("signed") != -1
        ) {
        value.append("1");
    }
    /*char*/
    else if (
        typeStr.find("char") != -1 ||
        typeStr.find("long") != -1 ||
        typeStr.find("signed") != -1
        ) {
        value.append("\'a\'");
    }
    return value;
    
}

class ProcessCallAction : public MatchComputation<std::string> {
public:
    ProcessCallAction() = default;
    llvm::Error eval(const ast_matchers::MatchFinder::MatchResult &mResult,
                     std::string *Result) const override {
        const Expr *expr = mResult.Nodes.getNodeAs<clang::Expr>("call");
        std::string typeStr = expr->getType().getDesugaredType(*mResult.Context).getAsString();
        std::string replaceStr = getTypeValue(typeStr);
        if (replaceStr == "") {
            replaceStr = getExprAsText(expr, *mResult.SourceManager, mResult.Context->getLangOpts());
        }
        Result->append("(" + replaceStr + ")");
        return llvm::Error::success();
    }
    std::string toString() const override { return "{}"; }
    static std::string getExprAsText(const Expr *E, const SourceManager &SM, const LangOptions &lp) {
        auto SR = CharSourceRange::getTokenRange(E->getSourceRange());
        return Lexer::getSourceText(SR, SM, lp).str();
    }
};


struct clang::transformer::RewriteRule processCallRule() {
    auto callMatcher = functionDecl(
        isExpansionInMainFile(),
        isDefinition(),
        forEachDescendant(
            invocation(unless(hasAncestor(invocation()))).bind("call")
        )
    );
    
    return makeRule(callMatcher, {
        /*we don't use changeTo but two inserts is becase using changeTo will change locations of ast and thus causing some offset
        */
            changeTo(node("call"), std::make_unique<ProcessCallAction>()),
        });
}

/* Remove extern function declarations */
struct clang::transformer::RewriteRule processExternRule() {
    auto functionDeclMatcher = functionDecl(
        isExpansionInMainFile(),
        isDefinition(),
        forEachDescendant(
            functionDecl().bind("functionDecl")
        )
    );
    
    return makeRule(functionDeclMatcher, {
        /*we don't use changeTo but two inserts is becase using changeTo will change locations of ast and thus causing some offset
        */
            changeTo(node("functionDecl"), cat("")),
        });
}


}
