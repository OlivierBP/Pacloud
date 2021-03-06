#!/bin/bash

function convert() {
	local CATEGORY=$(echo $1 | awk -F"/" '{print $(NF-1)}')
	local NAME=$(echo $1 | awk -F"/" '{print $NF}')
	local versions=()
	local deps=()

	for file in "$1"/*.ebuild; do
		version=$(echo $file | grep -o "$NAME-.*") # Get the version part of the filename
		versions[${#versions[*]}]="${version:${#NAME}+1:-7}" # Remove "name-.ebuild"
		source $file 2>/dev/null # ebuilds are bash files, to read the variables we can just evaluate the file
		#list=$(echo "$RDEPEND" |
		#	sed 's/\t//' | # Remove tabs at the beginning of the lines
		#	printf %s "$(cat)" | # Remove empty lines and ending newline to avoid empty element at the end
		#	jq -Rs 'split("\n")') # Put in a json list
		RDEPEND="$(echo "$RDEPEND" | sed 's/\[.*\]//' | sed 's/\t*//' | sed 's/\n//' | printf %s "$(cat)")"
		list="["
		usedep=0 # levels for the optional dependencies that are sometimes written on multiple lines
		dep=""
		[[ "$RDEPEND" == "" ]] || { # Checking that the dependencies are not null
			while read depline; do
				[[ "$depline" =~ "?" || "$depline" =~ "||" ]] && ((usedep += $(echo $depline | tr -dc '?|' | sed 's/||/|/' | wc -c))) # usedep incremented by the number of ? or || (characters opening braces)
				[[ "$depline" =~ ")" ]] && ((usedep -= $(echo $depline | tr -dc ')' | wc -c))) # usedep decremented by the number of )
				#[[ "$depline" =~ "?" || "$depline" =~ "||" ]] && ((usedep++)); echo $usedep
				#[[ "$depline" =~ ")" ]] && ((usedep--)) && echo $usedep
				[[ "$dep" == "" ]] && dep="$depline" || dep="${dep} $depline"
				[[ "$dep" == "" || $usedep > 0 ]] || { list="$list \""$dep"\"," && dep=""; }
			done <<< "$RDEPEND"
			list="${list::-1}"
		}
		list="$list]"
		deps[${#deps[*]}]="$list" # Append to deps
	done

	METADATA="{
		\"name\": \"$CATEGORY/$NAME\",
		\"description\": \""$(echo $DESCRIPTION | sed 's/\"/\\"/g')"\",
		\"versions\": ["
	for (( i=0; i<${#versions[@]}; i++ )); do
		METADATA="$METADATA {
			\"number\": \"${versions[$i]}\",
			\"dependencies\": ${deps[$i]}
		},"
	done

	METADATA="${METADATA::-1}
		]
	}"
	echo "$METADATA"
}

DBDIR=$PWD
metadata="["
cd $1
for dir in $(ls -d */); do
	cd $dir
	metadata="$metadata $(convert $PWD),"
	cd ..
done
metadata="${metadata::-1}]"
cd $DBDIR
echo "$metadata" > "$(echo $1 | awk -F"/" '{print $NF}')".json
