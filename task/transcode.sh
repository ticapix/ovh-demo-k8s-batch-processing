#!/bin/sh

set -eux

if [ $# -ne 3 ]; then
    echo "wrong argument. usage $0 <input_bucket> <file_path> <output_bucket>"
    exit 1
fi

input_bucket=$1
input_filepath=$2
output_bucket=$3

# Does the input file exist ?
if ! swift stat "$input_bucket" "$input_filepath"; then
    echo "Input file $input_bucket $input_filepath doesn't exist"
    exit 1
fi

output_filepath="${input_filepath%.*}.webm"

# Does the output file exist ?
if swift stat "$output_bucket" "$output_filepath"; then
    echo "Output file $output_bucket $output_filepath already exists"
    exit 0
fi

# Is the input file available localy ?
if ! ls "input.mp4"; then
    # transcode file on the fly to
    # - avoid IO access
    # - reduce disk space (reduce FPS and resolution)
    # - speed up seeks later
    swift download "$input_bucket" "$input_filepath" --output - | ffmpeg -i - -c:v libx265 -an -sn -x265-params crf=25 -preset ultrafast -r 30 -vf scale=320:-2 -y input.mp4
    input_filepath=input.mp4
fi

#docker run -v $(pwd):$(pwd) -w $(pwd) jrottenberg/ffmpeg:4.1-scratch -i "$input_filepath" -c:v libx265 -c:a copy -x265-params crf=25 -y output.mp4

# get file metadata
ffprobe -v quiet -hide_banner -loglevel fatal -show_streams -print_format json -i "$input_filepath" > data.json

parts=12
part_duration=1 # sec

# take duration of the first video stream
duration=`cat data.json | jq -r '[.streams[] | select(.codec_type == "video")][0] | .duration'`

if [ `echo '('$duration')>('$parts'*'$part_duration')' | bc -l` -ne 0 ]; then
    # generate $parts of $part_duration second
    rm files.txt || true
    for i in $(seq 1 $parts); do
        echo "file 'output-$i.mp4'" >> files.txt
        start_time=`echo 'x=('$duration')/'$parts'*('$i'-1); if(x<1){"0"}; x' | bc -l`
        ffmpeg -i "$input_filepath" -an -sn -ss $start_time -t $part_duration -r 30 -vf scale=320:-2 -y output-$i.mp4
    done
else
    echo "file '$input_filepath'" > files.txt
fi
# concatenate the parts
ffmpeg -f concat -i files.txt -c:v libvpx-vp9 -crf 30 -b:v 0 -y output.webm

# upload result
swift upload "$output_bucket" --object-name "$output_filepath" output.webm
