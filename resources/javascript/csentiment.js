function stopRKey(evt) { 
  var evt = (evt) ? evt : ((event) ? event : null); 
  var node = (evt.target) ? evt.target : ((evt.srcElement) ? evt.srcElement : null); 
  if ((evt.keyCode == 13) && (node.type=="text"))  {return false;} 
} 

document.onkeypress = stopRKey;

var maximum_annotations = 0;
var user_progress = 0;
var annotation_data = [];
var current_item;
var current_item_sentiment = 0.0;
var current_item_relevance = 0.0;
var idk_value = 50;
var current_item_all_sentiments = [];
var current_item_all_relevances = [];
var current_item_all_sentiments_count = 0.0;
var current_item_all_relevances_count = 0.0;
var current_item_span = [];

function showValue(newValue) {
	current_item_sentiment = newValue;
	current_item_all_sentiments.push(parseFloat(current_item_sentiment));
	n = current_item_all_sentiments.length;
	sent_mean = current_item_all_sentiments.reduce((a,b) => a+b)/n;
	sent_std = Math.sqrt(current_item_all_sentiments.map(x => Math.pow(x-sent_mean,2)).reduce((a,b) => a+b)/n);
	current_item_all_sentiments.pop();
	$("#sentimentmeancell").html("<strong>Mean:</strong>   " + sent_mean.toFixed(4) + "");
	$("#sentimentstdcell").html("<strong>STD:</strong>   " + sent_std.toFixed(4) + "");
}

function setRelevance(newRelevance) {
	current_item_relevance = newRelevance;
	current_item_all_relevances.push(parseFloat(current_item_relevance));
	n2 = current_item_all_relevances.length;
	rel_mean = current_item_all_relevances.reduce((a2,b2) => a2+b2)/n2;
	rel_std = Math.sqrt(current_item_all_relevances.map(x2 => Math.pow(x2-rel_mean,2)).reduce((a2,b2) => a2+b2)/n2);
	current_item_all_relevances.pop();
	$("#relevancemeancell").html("<strong>Mean:</strong>   " + rel_mean.toFixed(4) + "");
	$("#relevancestdcell").html("<strong>STD:</strong>   " + rel_std.toFixed(4) + "");
}

function reseteverything() {
	$("#sentimentrange").val("0");
	$("#relevancerange").val("0");
	current_item_sentiment = 0;
	current_item_relevance = 0;
	current_item_all_sentiments = [];
	current_item_all_relevances = [];
	current_item_all_sentiments_count = 0.0;
	current_item_all_relevances_count = 0.0;
	current_item_span = [];
	$('#remove_spans').hide();
	$('#submitannotation').attr("disabled", false);
	$('#submitnoidea').attr("disabled", false);
}

function escapeRegExp(input) {
	return input.toString().replace(/[\/\\^$*+?.\(\)|[\]{}\-\$,]/g, '\\$&');
}

function skip_token(s, pattern, token, sub){
	gex = "";
	for (i=0; i < pattern.length; i++){
		gex = gex + escapeRegExp(pattern[i]) + "\\s*" + token + "?\\s*";
	}
	return s.replace(new RegExp("("+ gex.substring(0, gex.length - 23) + ")", "g"), sub);
}

function remove_highlight(field){
	var textarea = $('#'+field);
	enew = textarea.html().replace(/(<mark>|<\/mark>)/igm, "");    
	textarea.html(enew);
}

function highlight(text,field){
	var textarea = $('#'+field);
	var enew = '';
	if (text != '') {
		enew = textarea.html();
		token = "(<mark>|<\/mark>)";
		sub = "<mark>$1</mark>";
		newtext = skip_token(enew,text,token,sub);
		newtext= newtext.replace(/<\/mark>(\s*)<mark>/g,"$1");
		textarea.html(newtext); 
	}
}

function displaynewdataset(finished=false) {
	if (finished == true) {
		$("#endscreen").html("<b><font color='#FF3333'>Thank you, you have completed the consolidation!</font></b>");
		$('#submitannotation').attr("disabled", true);
		$('#submit_noidea').attr("disabled", true);
		$('.step1').hide();
		$('.step2').show();
	} else {
		if (annotation_data.length > 0) {
			current_item = annotation_data.shift()
			annotations = current_item["annotations"];
			$("#datadisplay").html(current_item["text"]);
			$("#sentimentrange").val(annotations["sentiment_mean"]);
			$("#relevancerange").val(annotations["relevance_mean"]);
			current_item_sentiment = annotations["sentiment_mean"];
			current_item_relevance = annotations["relevance_mean"];
			$("#entitydisplay").html("Consolidation for: <font size=\"5px\"><strong>" + current_item["entity"] + "</strong></font>");
			$("#progressfield").html("Consolidation: " + user_progress + " of " + maximum_annotations);
			header_string = "<table width='650px'><tr><td></td><td colspan='2' bgcolor='#1984c3'>Sentiment</td><td colspan='2' bgcolor='#1984c3'>Relvance</td></tr>";
			stat_string = "<tr><td></td><td><div id='sentimentmeancell'><strong>Mean:</strong>   " + annotations["sentiment_mean"] +" </div></td><td id='sentimentstdcell'><strong>STD:</strong>   " + annotations["sentiment_standard_deviation"] + "</td><td id='relevancemeancell'><strong>Mean:</strong>   " + annotations["relevance_mean"] +" </td><td id='relevancestdcell'><strong>STD:</strong>   " + annotations["relevance_standard_deviation"] + "</td></tr>";
			annotations_string = "";
			for (key in annotations["annotations_sentiment"]){
				current_item_all_sentiments.push(parseFloat(annotations["annotations_sentiment"][key]));
				current_item_all_sentiments_count = current_item_all_sentiments_count + parseFloat(annotations["annotations_sentiment"][key]);
				if (((Math.abs(annotations["annotations_sentiment"][key]) + annotations["sentiment_standard_deviation"]) < Math.abs(annotations["sentiment_mean"])) || ((Math.abs(annotations["annotations_sentiment"][key]) - annotations["sentiment_standard_deviation"]) > Math.abs(annotations["sentiment_mean"])) || (Math.sign(annotations["annotations_sentiment"][key]) == 1 && annotations["majority_polarity"] != "pos") || (Math.sign(annotations["annotations_sentiment"][key]) == 0 && annotations["majority_polarity"] != "neu") || (Math.sign(annotations["annotations_sentiment"][key]) == -1 && annotations["majority_polarity"] != "neg")){
					sentiment_string = "<strong><font color='red'>" + annotations["annotations_sentiment"][key] + "</font></strong>";
				} else {
					sentiment_string = annotations["annotations_sentiment"][key];
				}
				if (key in annotations["annotations_relevance"]){
					current_item_all_relevances.push(parseFloat(annotations["annotations_relevance"][key]));
					current_item_all_relevances_count = current_item_all_relevances_count + parseFloat(annotations["annotations_relevance"][key]);
					if (((Math.abs(annotations["annotations_relevance"][key]) + annotations["relevance_standard_deviation"]) < Math.abs(annotations["relevance_mean"])) || ((Math.abs(annotations["annotations_relevance"][key]) - annotations["relevance_standard_deviation"]) > Math.abs(annotations["relevance_mean"]))){
						relevance_string = "<strong><font color='red'>" + annotations["annotations_relevance"][key] + "</font></strong>";
					} else {
						relevance_string = annotations["annotations_relevance"][key];
					}
					annotations_string += "<tr><td bgcolor='#1984c3'>Annotator " + key + ":</td><td colspan='2'>" + sentiment_string +"</td><td colspan='2'>" + relevance_string + "</td></tr>";
				} else {
					annotations_string += "<tr><td bgcolor='#1984c3'>Annotator " + key + ":</td><td colspan='2'>" + sentiment_string +"</td><td colspan='2'></td></tr>";
				}
			}
			statistic_string = header_string + annotations_string + stat_string + "</table>"
			$("#statdisplay").html(statistic_string);
		} else {
			//request more data		
			ajaxdata();
		}
	}
}

function ajaxupdate() {
	var JSONannotation  = {
		'_id': current_item["_id"],
		'value1' : current_item_sentiment,
		'value2' : current_item_relevance,
		'spans': current_item_span
	};

	$.post("consolidation",JSON.stringify(JSONannotation),
	function(data, status){
		if (status == 'success') {
			user_progress++;
			reseteverything();
			displaynewdataset();
		} else {
			alert("An error occured - please try again");
		}
	});
	return false;
}

function ajaxdata(val=false) {
    $.post("data",JSON.stringify(val),
    function(data, status){
    	if (data != "finished"){
	        annotation_data = data["content"];
	        if (val == true){
	        	user_progress = data["progress"];
	        	maximum_annotations = data["maximum_annotations"];
	        	idk_value = data["idontknow_value"];
	        }
			displaynewdataset();
		} else {
			displaynewdataset(true);
		}
    });
    return false;
}



$( document ).ready(function() {
	ajaxdata(true);
	$('.step2').hide();
	$('#remove_spans').hide();
	$("#datadisplay").click(function() {
		t = '';
		if (window.getSelection) {
			t = window.getSelection();
		} else if (document.getSelection) {
			t = document.getSelection();
		} else if (document.selection) {
			t = document.selection.createRange().text;
		}
		if (t == ''){
			alert("Please select a span.");
		} else {
			current_item_span.push({"text_span": t.toString()});
			highlight(t.toString(),"datadisplay");
			$('#remove_spans').show();
		}
	});

	$("#remove_spans").click(function() {
		current_item_span = [];
		remove_highlight("datadisplay");
		$('#remove_spans').hide();
	});

	$("#submitnoidea").click(function() {
		current_item_sentiment = idk_value;
		current_item_relevance = idk_value;
		$("#submitnoidea").prop('disabled', true);
		ajaxupdate();
	});	
	
	$("#submitannotation").click(function() {
		$("#submitannotation").prop('disabled', true);
		ajaxupdate();
	});
});