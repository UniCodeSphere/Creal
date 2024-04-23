#pragma once

#include "Utils.hpp"

namespace extractor_utils{

std::string generate_random_string(int length) {
    static const char charset[] = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    static const int charset_size = sizeof(charset) - 1;
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(0, charset_size - 1);
    std::string result(length, ' ');
    for (int i = 0; i < length; ++i) {
        result[i] = charset[dis(gen)];
    }
    return result;
}
}