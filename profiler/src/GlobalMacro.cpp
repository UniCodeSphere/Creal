#pragma once

#include "TagExpression.hpp"
#include "GlobalMacro.hpp"

using namespace std;

namespace globalmacro {

std::map<string, string> TypeToFormat = {
    {"char", "PRId8"}, {"unsignedchar", "PRIu8"},
    {"short", "PRId16"}, {"unsignedshort", "PRIu16"},
    {"shortint", "PRId16"}, {"unsignedshortint", "PRIu16"},
    {"int", "PRId32"}, {"unsignedint", "PRIu32"},
    {"int8_t", "PRId8"}, {"uint8_t", "PRIu8"},
    {"int16_t", "PRId16"}, {"uint16_t", "PRIu16"},
    {"int32_t", "PRId32"}, {"uint32_t", "PRIu32"},
    {"int64_t", "PRId64"}, {"uint64_t", "PRIu64"},
};

class AddGlobalMacro : public MatchComputation<std::string> {
  public:
    AddGlobalMacro() = default;
    llvm::Error eval(const ast_matchers::MatchFinder::MatchResult &,
                     std::string *Result) const override {
        Result->append("#include<stdint.h>\n");
        Result->append("#include<inttypes.h>\n");
        /*Add macros for TagExpression*/
        for (auto tag = tagexpression::Tags.begin(); tag != tagexpression::Tags.end(); ++tag) {
            auto tag_id = tag->first;
            auto tag_type = tag->second;
            if (tag_id == 0) {
                continue;
            }
            std:string tag_id_str = std::to_string(tag_id);
            Result->append(
                "#define Tag" + tag_id_str + "(x) (x)\n"
            );
        }
        return llvm::Error::success();
    }

    std::string toString() const override {
        return "AddGlobalMacroError\n";
    }
};

struct clang::transformer::RewriteRule AddGlobalMacroRule() {
    return makeRule(functionDecl(
        isExpansionInMainFile(),
        isMain()
        ).bind("main"),
        insertAfter(ruleactioncallback::startOfFile("main"), 
        std::make_unique<AddGlobalMacro>()));
}


} //namespace globalmacro