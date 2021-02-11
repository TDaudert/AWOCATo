$( document ).ready(function() {
	$("body").on("contextmenu",function(e){
		return false;
	});
	$('body').bind('cut copy paste', function (e) {
		e.preventDefault();
	});
	$('body').bind('cut copy paste', function (e) {
		e.preventDefault();
	});

	function copyToClipboard() {
		var aux = document.createElement("input");
		aux.setAttribute("value", "Print screens are no permitted.");
		document.body.appendChild(aux);
		aux.select();
		document.execCommand("copy");
		document.body.removeChild(aux);
		alert("Print screens are not permitted.");
	}

	$(window).keyup(function(e){
		if(e.keyCode == 44){
			copyToClipboard();
		}
	}); 

	$(window).focus(function() {
		$("body").show();
	}).blur(function() {
		$("body").hide();
	});
});