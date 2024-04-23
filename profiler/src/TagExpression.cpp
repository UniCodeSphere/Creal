#pragma once

#include "TagExpression.hpp"

namespace tagexpression {

std::map<int, std::string> Tags{{0, ""}};

std::list<std::tuple<int64_t, std::string>> StmtVars;

class TagExpressionAction : public MatchComputation<std::string> {
public:
    TagExpressionAction() = default;
    llvm::Error eval(const ast_matchers::MatchFinder::MatchResult &mResult,
                     std::string *Result) const override {
        // get declaration of expr
        const VarDecl *decl = mResult.Nodes.getNodeAs<clang::VarDecl>("decl");
        std::string var_storage = "1"; //local
        if (decl->hasGlobalStorage()) {
            var_storage = "0";//global
        }

        const Expr *expr = mResult.Nodes.getNodeAs<clang::Expr>("expr");
        std::string typeStr = expr->getType().getAsString();
        if (typeStr.find("struct") != -1 || typeStr.find("union") != -1) {
            return llvm::Error::success();
        }

        std::string exprStr = getExprAsText(expr, *mResult.SourceManager, mResult.Context->getLangOpts());
        
        // if this is a statement tag
        const Stmt *stmt = mResult.Nodes.getNodeAs<clang::Stmt>("stmt");
        std::string stmt_curr = "0";
        if (stmt) {
            int64_t stmt_id = stmt->getID(*mResult.Context);
            stmt_curr = std::to_string(stmt_id);
        }

        std::string tag_style = "e";

        //debug
        std::string scope_current = var_storage;
        const Stmt *scopeCurrent = mResult.Nodes.getNodeAs<clang::Stmt>("scope_curr");
        if (scopeCurrent) {
            scope_current = std::to_string(scopeCurrent->getID(*mResult.Context));
        }
        std::string scope_parent = scope_current;
        const Stmt *scopeParent = mResult.Nodes.getNodeAs<clang::Stmt>("scope_parent");
        if (scopeParent) {
            scope_parent = std::to_string(scopeParent->getID(*mResult.Context));
        }

        // generate tag
        int tag_id = Tags.rbegin()->first;
        tag_id++;
        std::string tagStr = "Tag" + std::to_string(tag_id) + 
                             "("  + "/*" + typeStr + ":" + scope_current + ":" + scope_parent + ":" + stmt_curr + ":" + tag_style + "*/";
        Result->append(tagStr);
        // for statemtent tag, append more
        // if (stmt) {
        //     Result->append(exprStr + ")/*s*/;\n");
        // }

        //replace const keyword in typeStr
        size_t pos_const = typeStr.find("const");
        if (pos_const != std::string::npos) {
            typeStr.replace(pos_const, std::strlen("const"), "");
        }
        Tags.insert({tag_id, typeStr});
        return llvm::Error::success();
    }
    std::string toString() const override { return "{}"; }
    static std::string getExprAsText(const Expr *E, const SourceManager &SM, const LangOptions &lp) {
        auto SR = CharSourceRange::getTokenRange(E->getSourceRange());
        return Lexer::getSourceText(SR, SM, lp).str();
    }
};


class TagStatementAction : public MatchComputation<std::string> {
public:
    TagStatementAction() = default;
    llvm::Error eval(const ast_matchers::MatchFinder::MatchResult &mResult,
                     std::string *Result) const override {
        const Stmt *stmt = mResult.Nodes.getNodeAs<clang::Stmt>("stmt");
        std::string stmt_curr = "0";
        if (stmt) {
            int64_t stmt_id = stmt->getID(*mResult.Context);
            stmt_curr = std::to_string(stmt_id);
        }

        Result->append(stmt_curr);
        
        return llvm::Error::success();
    }
    std::string toString() const override { return "{}"; }
};

auto scopeMatcher = anyOf(
                        hasAncestor(
                            stmt(hasParent(compoundStmt(
                                anyOf(
                                    hasAncestor(stmt(hasParent(compoundStmt().bind("scope_parent")))),
                                    hasParent(functionDecl())
                                )
                            ).bind("scope_curr")))
                        ),
                        hasAncestor(functionDecl(hasDescendant(compoundStmt().bind("scope_curr")))), // function args
                        hasAncestor(translationUnitDecl()) // global vars
                    );

auto matcher = expr(
    expr().bind("expr"),
    anyOf(
        declRefExpr(
            hasDeclaration(decl(scopeMatcher).bind("decl")),
            unless(hasAncestor(memberExpr()))
        ), 
        unaryOperator(hasOperatorName("*"), hasDescendant(declRefExpr(hasDeclaration(decl(scopeMatcher).bind("decl"))))),
        arraySubscriptExpr(
            hasBase(hasDescendant(declRefExpr(hasDeclaration(decl(scopeMatcher).bind("decl"))).bind("arrbase"))),
            unless(hasDescendant(declRefExpr(unless(equalsBoundNode("arrbase"))))),
            unless(hasAncestor(memberExpr()))
        ),
        memberExpr((hasDescendant(declRefExpr(hasDeclaration(decl(scopeMatcher).bind("decl"))))))
    ),
    isExpansionInMainFile(),
    hasType(isInteger()),
    hasAncestor(compoundStmt()),
    unless(hasAncestor(functionDecl(isMain()))),
    // unless(hasParent(memberExpr())), // hack to avoid member expressions
    unless(hasAncestor(binaryOperator(isAssignmentOperator(),
                                        hasLHS(ignoringParenImpCasts(equalsBoundNode("expr")))))),
    unless(hasAncestor(unaryOperator(hasOperatorName("&")))),
    unless(hasAncestor(
        unaryOperator(hasAnyOperatorName("++", "--")))),
    unless(hasDescendant(unaryOperator(hasAnyOperatorName("++", "--")))),
    hasAncestor(stmt(hasParent(compoundStmt())).bind("stmt"))
);

auto statementMatcher = expr(
    expr().bind("expr"),
    // declRefExpr(), //anyOf(declRefExpr(), integerLiteral(), characterLiteral(), floatLiteral()),
    anyOf(
        declRefExpr(hasDeclaration(decl().bind("decl"))), 
        unaryOperator(hasOperatorName("*"), hasDescendant(declRefExpr(hasDeclaration(decl().bind("decl"))))),
        arraySubscriptExpr(
            hasBase(hasDescendant(declRefExpr(hasDeclaration(decl().bind("decl"))).bind("arrbase")))
        )
    ),
    isExpansionInMainFile(),
    anyOf(
        hasType(asString("int")), hasType(asString("const int")),
        hasType(asString("unsigned int")), hasType(asString("const unsigned int")),
        hasType(asString("long")), hasType(asString("const long")),
        hasType(asString("char")), hasType(asString("const char")),
        hasType(asString("int8_t")), hasType(asString("const int8_t")),
        hasType(asString("uint8_t")), hasType(asString("const uint8_t")),
        hasType(asString("int16_t")), hasType(asString("const int16_t")),
        hasType(asString("uint16_t")), hasType(asString("const uint16_t")),
        hasType(asString("int32_t")), hasType(asString("const int32_t")),
        hasType(asString("uint32_t")), hasType(asString("const uint32_t")),
        hasType(asString("int64_t")), hasType(asString("const int64_t")),
        hasType(asString("uint64_t")), hasType(asString("const uint64_t"))
    ),
    hasAncestor(compoundStmt()),
    unless(hasAncestor(functionDecl(isMain()))),
    unless(hasParent(memberExpr())), // hack to avoid member expressions
    unless(hasAncestor(binaryOperator(isAssignmentOperator(),
                                        hasLHS(ignoringParenImpCasts(equalsBoundNode("expr")))))),
    unless(hasAncestor(unaryOperator(hasOperatorName("&")))),
    unless(hasAncestor(
        unaryOperator(hasAnyOperatorName("++", "--")))),
    unless(hasDescendant(unaryOperator(hasAnyOperatorName("++", "--")))),
    hasAncestor(stmt(hasParent(compoundStmt(
        anyOf(
            hasParent(stmt(hasParent(compoundStmt().bind("scope1")))),
            hasParent(functionDecl())
        )
    ).bind("scope0"))).bind("stmt")),
    unless(hasAncestor(forStmt(hasLoopInit(hasDescendant(declRefExpr(hasDeclaration(equalsBoundNode("decl")))))))), // int i; for(i=0;i<1;i++)
    unless(hasAncestor(forStmt(hasLoopInit(hasDescendant(varDecl((equalsBoundNode("decl")))))))) // for(int i=0;i<1;i++)
);


struct clang::transformer::RewriteRule TagExpressionRule() {
    return makeRule(matcher, {
        insertBefore(node("expr"), std::make_unique<TagExpressionAction>()),
        insertAfter(node("expr"), cat(")")),
        insertBefore(statement("stmt"), cat("/*bef_stmt:", std::make_unique<TagStatementAction>(), "*/\n")),
        insertAfter(statement("stmt"), cat("\n/*aft_stmt:", std::make_unique<TagStatementAction>(), "*/"))
    });
}

struct clang::transformer::RewriteRule TagStatementRule() {
    return makeRule(statementMatcher, {
        insertBefore(node("stmt"), std::make_unique<TagExpressionAction>()),
        insertAfter(node("stmt"), cat(")"))
    });
}
    
} //namespace tag_expression