(function ($) {
	var resultURI = window.location.href.replace(/\/processing\?/, '/result?'),
	    testURI = window.location.href.replace(/\/processing\?/, '/completed?') + '&output_json=1',
	    poller = function() {
		    $.ajax({
		    	url: testURI,
		    	dataType: 'json',
		    	success: function(data, textStatus) {
			    	if (textStatus!=='success') {
			    		return;
			    	}
			    	if (data['completed']===true ||
			    		data['completed']===100 ||
			    		data['completed']==='ERROR') {
			    		window.location.href = resultURI;
			    	} else if (data['completed']===false) {
			    		// nothing to do
			    	} else {
			    		// update progress
			    		$('#progress').html(data['progress_message']);
			    	}
					window.setTimeout(poller, 5000);
			    },
			    error: function() {
					window.setTimeout(poller, 5000);
			    },
			    timeout: 15000
		    });
	};
	poller();
})(jq);