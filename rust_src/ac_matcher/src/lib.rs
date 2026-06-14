use aho_corasick::{AhoCorasick, MatchKind};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::collections::HashMap;

// ---------------------------------------------------------------------------
// AcMatch: a single match result from the AC automaton
// ---------------------------------------------------------------------------

/// A single match result containing the matched pattern and its position.
#[pyclass]
#[derive(Clone, Debug)]
struct AcMatch {
    /// The matched pattern string.
    #[pyo3(get)]
    pattern: String,
    /// The byte offset of the start of the match.
    #[pyo3(get)]
    start: usize,
    /// The byte offset of the end of the match.
    #[pyo3(get)]
    end: usize,
    /// The original text that was matched (slice of the input).
    #[pyo3(get)]
    original: String,
}

#[pymethods]
impl AcMatch {
    #[new]
    fn new(pattern: String, start: usize, end: usize, original: String) -> Self {
        AcMatch {
            pattern,
            start,
            end,
            original,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "AcMatch(pattern={:?}, start={}, end={}, original={:?})",
            self.pattern, self.start, self.end, self.original
        )
    }

    fn __str__(&self) -> String {
        self.__repr__()
    }
}

// ---------------------------------------------------------------------------
// AcMatcher: the Aho-Corasick automaton
// ---------------------------------------------------------------------------

/// Aho-Corasick automaton for high-performance multi-pattern matching.
///
/// Uses `LeftmostLongest` match semantics to always return the longest
/// matching pattern when multiple patterns overlap at the same position.
#[pyclass]
struct AcMatcher {
    ac: AhoCorasick,
    patterns: Vec<String>,
}

#[pymethods]
impl AcMatcher {
    /// Build a new automaton from a list of pattern strings.
    #[new]
    fn new(patterns: Vec<String>) -> PyResult<Self> {
        if patterns.is_empty() {
            return Err(PyValueError::new_err(
                "at least one pattern is required to build the automaton",
            ));
        }

        let ac = AhoCorasick::builder()
            .match_kind(MatchKind::LeftmostLongest)
            .build(&patterns)
            .map_err(|e| {
                PyValueError::new_err(format!("failed to build AC automaton: {}", e))
            })?;

        Ok(AcMatcher { ac, patterns })
    }

    /// Return the number of patterns loaded in the automaton.
    fn __len__(&self) -> usize {
        self.patterns.len()
    }

    /// Find all non-overlapping matches in `text`.
    ///
    /// Returns a list of `AcMatch` objects sorted by their start position.
    /// When multiple patterns match at the same position, the longest match
    /// is returned (`LeftmostLongest` semantics).
    fn find_all(&self, text: &str) -> Vec<AcMatch> {
        let mut results = Vec::new();
        for m in self.ac.find_iter(text) {
            let pid = m.pattern().as_usize();
            let original = &text[m.start()..m.end()];
            results.push(AcMatch {
                pattern: self.patterns[pid].clone(),
                start: m.start(),
                end: m.end(),
                original: original.to_string(),
            });
        }
        results
    }

    /// Replace all matched patterns in `text` using the replacement map.
    ///
    /// Each matched pattern is replaced with the corresponding value from
    /// `replacements` (keyed by the original pattern string). If a pattern
    /// is not present in `replacements`, its original text is kept unchanged.
    fn replace_all(&self, text: &str, replacements: HashMap<String, String>) -> String {
        let matches = self.find_all(text);
        if matches.is_empty() {
            return text.to_string();
        }

        let mut result = String::with_capacity(text.len());
        let mut last_end = 0;

        for m in &matches {
            // Append any text between the previous match and this one.
            if last_end < m.start {
                result.push_str(&text[last_end..m.start]);
            }
            // Append the replacement string, or the original text if no
            // replacement is provided for this pattern.
            let replacement = replacements
                .get(&m.pattern)
                .map(|s| s.as_str())
                .unwrap_or(&text[m.start..m.end]);
            result.push_str(replacement);
            last_end = m.end;
        }

        // Append any trailing text after the last match.
        if last_end < text.len() {
            result.push_str(&text[last_end..]);
        }

        result
    }
}

// ---------------------------------------------------------------------------
// Free functions
// ---------------------------------------------------------------------------

/// Build an Aho-Corasick automaton from a list of patterns.
///
/// This is a convenience function equivalent to ``AcMatcher(patterns)``.
#[pyfunction]
fn build_ac(patterns: Vec<String>) -> PyResult<AcMatcher> {
    AcMatcher::new(patterns)
}

// ---------------------------------------------------------------------------
// PyO3 module registration
// ---------------------------------------------------------------------------

#[pymodule]
fn ac_matcher(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<AcMatch>()?;
    m.add_class::<AcMatcher>()?;
    m.add_function(wrap_pyfunction!(build_ac, m)?)?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_single_pattern() {
        let matcher = AcMatcher::new(vec!["hello".to_string()]).unwrap();
        let matches = matcher.find_all("say hello world");
        assert_eq!(matches.len(), 1);
        assert_eq!(matches[0].pattern, "hello");
        assert_eq!(matches[0].start, 4);
        assert_eq!(matches[0].end, 9);
        assert_eq!(matches[0].original, "hello");
    }

    #[test]
    fn test_multiple_patterns() {
        let matcher = AcMatcher::new(vec![
            "he".to_string(),
            "hello".to_string(),
            "world".to_string(),
        ])
        .unwrap();
        let matches = matcher.find_all("hello world");
        assert_eq!(matches.len(), 2);
        // "hello" is longer than "he" at position 0, so it wins.
        assert_eq!(matches[0].pattern, "hello");
        assert_eq!(matches[1].pattern, "world");
    }

    #[test]
    fn test_leftmost_longest_semantics() {
        let matcher = AcMatcher::new(vec![
            "a".to_string(),
            "ab".to_string(),
            "abc".to_string(),
            "bc".to_string(),
        ])
        .unwrap();
        let matches = matcher.find_all("abcd");
        assert_eq!(matches.len(), 1);
        // "abc" is the longest match starting at position 0.
        assert_eq!(matches[0].pattern, "abc");
        assert_eq!(matches[0].start, 0);
        assert_eq!(matches[0].end, 3);
    }

    #[test]
    fn test_no_matches() {
        let matcher = AcMatcher::new(vec!["foo".to_string()]).unwrap();
        let matches = matcher.find_all("bar");
        assert!(matches.is_empty());
    }

    #[test]
    fn test_overlapping_patterns() {
        let matcher = AcMatcher::new(vec![
            "ana".to_string(),
            "an".to_string(),
            "na".to_string(),
        ])
        .unwrap();
        let matches = matcher.find_all("banana");
        // "banana": b(0) a(1) n(2) a(3) n(4) a(5)
        // LeftmostLongest at 1: "ana" (len 3) wins over "an" (len 2).
        // After 1..4 consumed, automaton resumes at position 4.
        // "na" matches at 4..6 (non-overlapping with 1..4).
        assert_eq!(matches.len(), 2);
        assert_eq!(matches[0].pattern, "ana");
        assert_eq!(matches[1].pattern, "na");
    }

    #[test]
    fn test_empty_patterns() {
        let result = AcMatcher::new(vec![]);
        assert!(result.is_err());
    }

    #[test]
    fn test_replace_all_basic() {
        let matcher = AcMatcher::new(vec![
            "hello".to_string(),
            "world".to_string(),
        ])
        .unwrap();
        let replacements = [
            ("hello".to_string(), "hi".to_string()),
            ("world".to_string(), "earth".to_string()),
        ]
        .into_iter()
        .collect();
        let result = matcher.replace_all("hello world", replacements);
        assert_eq!(result, "hi earth");
    }

    #[test]
    fn test_replace_all_no_replacement() {
        let matcher = AcMatcher::new(vec!["hello".to_string()]).unwrap();
        let replacements = HashMap::new();
        let result = matcher.replace_all("say hello", replacements);
        // No replacement provided, original text kept.
        assert_eq!(result, "say hello");
    }

    #[test]
    fn test_replace_all_no_matches() {
        let matcher = AcMatcher::new(vec!["foo".to_string()]).unwrap();
        let replacements = HashMap::new();
        let result = matcher.replace_all("bar", replacements);
        assert_eq!(result, "bar");
    }

    #[test]
    fn test_build_ac_function() {
        let matcher = build_ac(vec!["test".to_string()]).unwrap();
        let matches = matcher.find_all("this is a test");
        assert_eq!(matches.len(), 1);
        assert_eq!(matches[0].pattern, "test");
    }

    #[test]
    fn test_pattern_count() {
        let matcher = AcMatcher::new(vec![
            "a".to_string(),
            "b".to_string(),
            "c".to_string(),
        ])
        .unwrap();
        assert_eq!(matcher.patterns.len(), 3);
    }
}
