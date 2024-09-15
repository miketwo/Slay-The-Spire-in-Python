import argparse
import os
import subprocess
import sys


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Condense a Git repository into a single text file, respecting .gitignore.")
    parser.add_argument('repo_path', help='Path to the Git repository')
    parser.add_argument('output_file', help='Output file name')
    parser.add_argument('-e', '--exclude', action='append', default=[], help='Additional files or folders to exclude')
    args = parser.parse_args()

    repo_path = args.repo_path
    output_file = args.output_file
    exclude_list = args.exclude

    # Change to the repository directory
    os.chdir(repo_path)

    # Check if the directory is a Git repository
    if not os.path.exists(os.path.join(repo_path, '.git')):
        print("The specified directory is not a Git repository.")
        sys.exit(1)

    # Get the list of files tracked by git
    result = subprocess.run(['git', 'ls-files'], stdout=subprocess.PIPE, text=True)
    files = result.stdout.strip().split('\n')

    # Apply additional exclusions
    def is_excluded(file_path):
        for pattern in exclude_list:
            if os.path.commonpath([file_path, pattern]) == pattern or pattern in file_path:
                return True
        return False

    files = [f for f in files if not is_excluded(f)]

    # Initialize token counts
    per_file_token_counts = {}
    total_tokens = 0

    # Use tiktoken to tokenize content
    try:
        import tiktoken
        encoding = tiktoken.get_encoding('cl100k_base')
    except ImportError:
        print("The 'tiktoken' library is not installed. Install it with 'pip install tiktoken'.")
        sys.exit(1)

    # Open the output file
    with open(output_file, 'w', encoding='utf-8') as outfile:
        # Iterate over each file
        for file in files:
            # Try to read the content of the file
            try:
                with open(file, 'r', encoding='utf-8') as infile:
                    content = infile.read()
                    # Tokenize content to get token count
                    tokens = encoding.encode(content)
                    num_tokens = len(tokens)
                    total_tokens += num_tokens
                    per_file_token_counts[file] = num_tokens

                    # Print file processing details
                    print(f"Processing file: {file} - Tokens: {num_tokens}")

                    # Include the filename as a separator
                    outfile.write(f"\n\n# File: {file}\n\n")
                    outfile.write(content)
            except (UnicodeDecodeError, IsADirectoryError, PermissionError) as e:
                print(f"Skipping file {file}: {e}")

    # Print total token count
    print(f"\nThe total number of tokens in the output file is: {total_tokens}")

    # Print files contributing most to token count
    print("\nFiles contributing most to the token count:")
    sorted_files = sorted(per_file_token_counts.items(), key=lambda item: item[1], reverse=True)
    for file, tokens in sorted_files:
        print(f"{file}: {tokens} tokens")

if __name__ == "__main__":
    main()
