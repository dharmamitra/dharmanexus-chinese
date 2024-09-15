import pandas as pd 
import os 


def fix_tsv(path):
    # Read the TSV file
    df = pd.read_csv(path, sep='\t')
    long_lines_count = 0 
    # Initialize an empty list to store the new rows
    new_rows = []

    # Iterate through each row in the DataFrame
    for index, row in df.iterrows():
        original = row['original']
        segmentnr = row['segmentnr']

        # Check if the length of 'original' is greater than 30 characters
        if len(original) > 150:

            long_lines_count += 1
            # Break down 'original' into chunks of 10 characters each            
            chunks = []
            if "，" in original:                
                new_chunks = original.split("，")                
                if len(new_chunks) > len(chunks):
                    chunks = new_chunks
            if "、" in original:
                new_chunks = original.split("、")
                if len(new_chunks) > len(chunks):
                    chunks = new_chunks
            if "　" in original:
                new_chunks = original.split("　")
                if len(new_chunks) > len(chunks):
                    chunks = new_chunks
            else:
                chunks = [original[i:i+20] for i in range(0, len(original), 20)]
            
            # Create new rows for each chunk
            for i, chunk in enumerate(chunks):                
                subchunks = [chunk]
                if len(chunk) >150:
                    print(f"Found long line: {chunk}")
                    subchunks = [chunk[i:i+30] for i in range(0, len(chunk), 30)]
                for j, subchunk in enumerate(subchunks):
                    new_segmentnr = f"{segmentnr}_{i+j}"
                    new_row = row.copy()
                    new_row['original'] = subchunk
                    new_row['segmentnr'] = new_segmentnr
                    new_row['stemmed'] = " ".join(subchunk.split())
                    new_rows.append(new_row)
        else:
            new_rows.append(row)

    # Create a new DataFrame from the new rows
    new_df = pd.DataFrame(new_rows)
    
    # Save the modified DataFrame to a new TSV file
    new_df.to_csv(path.replace('.tsv', '_fixed.tsv'), sep='\t', index=False)
    return long_lines_count

total_lines = 0
for file in os.listdir('.'):
    if file.endswith('.tsv') and 'fixed' not in file:
        total_lines += fix_tsv(file)

print(f"Fixed {total_lines} long lines in TSV files.")