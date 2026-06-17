use std::env;
use std::fs;
use std::path::{Path, PathBuf};

fn main() {
    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").expect("CARGO_MANIFEST_DIR set"));
    let protocol_dir = manifest_dir.join("src").join("protocol");

    let mut missing = Vec::new();

    for entry in fs::read_dir(&protocol_dir).expect("read protocol directory") {
        let path = entry.expect("protocol entry").path();
        if path.extension().and_then(|ext| ext.to_str()) != Some("rs") {
            continue;
        }

        println!("cargo:rerun-if-changed={}", path.display());
        check_protocol_file(&path, &mut missing);
    }

    if !missing.is_empty() {
        panic!(
            "protocol Serialize/Deserialize types must declare #[serde(rename_all = \"snake_case\")]:\n{}",
            missing.join("\n")
        );
    }
}

fn check_protocol_file(path: &Path, missing: &mut Vec<String>) {
    let source = fs::read_to_string(path).unwrap_or_else(|err| panic!("read {}: {err}", path.display()));
    let lines: Vec<&str> = source.lines().collect();

    for (index, line) in lines.iter().enumerate() {
        let trimmed = line.trim();
        if !trimmed.starts_with("#[derive")
            || !trimmed.contains("Serialize")
            || !trimmed.contains("Deserialize")
        {
            continue;
        }

        let mut attr_block = String::from(trimmed);
        let mut cursor = index + 1;

        while let Some(next_line) = lines.get(cursor) {
            let next = next_line.trim();
            if next.is_empty()
                || next.starts_with("///")
                || next.starts_with("//")
                || next.starts_with("#[")
            {
                attr_block.push('\n');
                attr_block.push_str(next);
                cursor += 1;
                continue;
            }
            break;
        }

        let Some(item_line) = lines.get(cursor).map(|line| line.trim()) else {
            continue;
        };

        let is_protocol_type = item_line.starts_with("pub struct ")
            || item_line.starts_with("struct ")
            || item_line.starts_with("pub enum ")
            || item_line.starts_with("enum ");

        if is_protocol_type && !attr_block.contains("rename_all") {
            missing.push(format!(
                "{}:{} {}",
                path.display(),
                index + 1,
                item_line
            ));
        }
    }
}
