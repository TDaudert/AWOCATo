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
var current_item_sentiment = 0;
var current_item_relevance = 0;
var current_item_span = [];
var idk_value = 0;

function showValue(newValue) {
	current_item_sentiment = newValue;
}

function setRelevance(newRelevance) {
	current_item_relevance = newRelevance;
	$('.step3').show();
}

function reseteverything() {
	$('.step3').hide();
	$("#sentimentrange").val("0");
	$("#relevancerange").val("0");
	$('#remove_spans').hide();
	current_item_sentiment = 0;
	current_item_relevance = 0;
	current_item_span = [];
	$('#submitannotation').attr("disabled", false);
	$('#submitnoidea').attr("disabled", false);
}

function displaynewdataset(finished=false) {
	if (finished == true) {
		$("#endscreen").html("<b><font color='#FF3333'>Thank you, you have completed the annotation!</font></b>");
		$('#submitannotation').attr("disabled", true);
		$('#submit_irrelevant').attr("disabled", true);
		$('#submit_noidea').attr("disabled", true);
		$('.step1').hide();
		$('.step2').hide();
		$('.step3').hide();
		$('.step4').show();
	} else {
		if (annotation_data.length > 0) {
			//new Tweet	
			current_item = annotation_data.shift()
			$("#datadisplay").html(current_item["text"]);
			$("#entitydisplay").html("Annotation for: <font size=\"5px\"><strong>" + current_item["entity"] + "</strong></font>");
			$("#progressfield").html("Annotation: " + user_progress + " of " + maximum_annotations);
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

	$.post("annotation",JSON.stringify(JSONannotation),
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

function escapeRegExp(input) {
	return input.toString().replace(/[\/\\^$*+?.\(\)|[\]{}\-\$,]/g, '\\$&');
}

function skip_token(s, pattern, token, sub){
	gex = ""
	for (i=0; i < pattern.length; i++){
		gex = gex + escapeRegExp(pattern[i]) + "\\s*" + token + "?\\s*";
	}
	return s.replace(new RegExp("("+ gex.substring(0, gex.length - 23) + ")", "g"), sub);
}

function highlight(text,field){
	var textarea = $('#'+field);
	var enew = '';
	if (text != '') {
		enew = textarea.html();
		token = "(<mark>|<\/mark>)"
		sub = "<mark>$1</mark>"
		newtext = skip_token(enew,text,token,sub);
		newtext= newtext.replace(/<\/mark>(\s*)<mark>/g,"$1");
		textarea.html(newtext); 
	}
}

function remove_highlight(field){
	var textarea = $('#'+field);
	enew = textarea.html().replace(/(<mark>|<\/mark>)/igm, "");    
	textarea.html(enew);
}

$( document ).ready(function() {
$('.step3').hide();
$('.step4').hide();
$('#remove_spans').hide();
ajaxdata(true);

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


	$("#submitnoidea").click(function() {
		current_item_sentiment = idk_value;
		current_item_relevance = idk_value;
		$("#submitnoidea").prop('disabled', true);
		ajaxupdate();
	});	
	
	$("#submitannotation").click(function() {
		if ((current_item_relevance > 0) && (current_item_span.length == 0)){
			if (confirm("Please don't forget to mark spans. Do you still want to submit?")) {
				ajaxupdate();
			}	
		} else{
			$("#submitannotation").prop('disabled', true);
			ajaxupdate();
		}
	});

	$("#remove_spans").click(function() {
		current_item_span = [];
		remove_highlight("datadisplay");
		$('#remove_spans').hide();
	});

});