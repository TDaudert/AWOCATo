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
var current_item_annotation = 0;
var class1_value = 0;
var class2_value = 0;
var idk_value = 0;

function reseteverything() {
	current_item_annotation = 0;
}

function displaynewdataset(finished=false) {
	if (finished == true) {
		$("#endscreen").html("<b><font color='#FF3333'>Thank you, you have completed the annotation!</font></b>");
		$('#submitannotation').attr("disabled", true);
		$('#submit_irrelevant').attr("disabled", true);
		$('#submit_noidea').attr("disabled", true);
		$('.step1').hide();
		$('.step2').show();
	} else {
		if (annotation_data.length > 0) {
			//new Tweet	
			current_item = annotation_data.shift()
			$("#datadisplay").html(current_item["text"]);
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
		'value1' : current_item_annotation,
		'value2' : 0
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
	        	if ("annotation_classes" in data){
	        		$('#submitannotation1').val(data["annotation_classes"][0]["class_name"]);
	        		$('#submitannotation2').val(data["annotation_classes"][1]["class_name"]);
	        		$("#submitannotation1").css("background-color", data["annotation_classes"][0]["button_color_bg"]);
	        		$("#submitannotation2").css("background-color", data["annotation_classes"][1]["button_color_bg"]);
	        		$("#submitannotation1").css("border-bottom-color", data["annotation_classes"][0]["button_color_border"]);
	        		$("#submitannotation2").css("border-bottom-color", data["annotation_classes"][1]["button_color_border"]);
	        		$("#submitannotation1").css("border-right-color", data["annotation_classes"][0]["button_color_border"]);
	        		$("#submitannotation2").css("border-right-color", data["annotation_classes"][1]["button_color_border"]);
	        		class1_value = data["annotation_classes"][0]["annotation_value"]
	        		class2_value = data["annotation_classes"][1]["annotation_value"]
	        	} else {
	        		alert("An error loading your class data occured.");
	        	}
	        }
			displaynewdataset();
		} else {
			displaynewdataset(true);
		}
    });
    return false;
}

$( document ).ready(function() {
$('.step2').hide();
ajaxdata(true);

	$("#submitnoidea").click(function() {
		current_item_annotation = idk_value;
		ajaxupdate();
	});	

	$("#submitannotation1").click(function() {
		current_item_annotation = class1_value;
		ajaxupdate();
	});
	
	$("#submitannotation2").click(function() {
		current_item_annotation = class2_value;
		ajaxupdate();
	});

});