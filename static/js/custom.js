/* =====================================
All JavaScript fuctions Start
======================================*/
(function ($) {
	
    'use strict';
/*--------------------------------------------------------------------------------------------
	document.ready ALL FUNCTION START
---------------------------------------------------------------------------------------------*/	


// popovers initialization - on hover
	// Image Popover = jquery.prettyPhoto.js ================= // 	
	function image_popover(){	
		jQuery("[data-toggle=popover]").each(function() {
			jQuery(this).popover({
				html: true,
				content: function() {
				var id = jQuery(this).attr('id')
				return jQuery('#popover-content-' + id).html();
				}
			});
		});
	}       
// Bootstrap Slider function by  = bootstrap-slider.min.js   
    function Bootstrap_Slider(){
        jQuery('#ex1').slider({
            formatter: function(value) {
                return 'Current value: ' + value;
            }
        });  
        jQuery('#ex2').slider({
            formatter: function(value) {
                return 'Current value: ' + value;
            }
        });     
        
        jQuery('#ex3').slider({
            formatter: function(value) {
                return 'Current value: ' + value;
            }
        });           
        
        
    }

	//  On off button	
	jQuery('.sf-toogle-btn').on('click', function(e){
		jQuery(this).parent('.header-widget').toggleClass('active');
		jQuery(this).parent().siblings(".header-widget").removeClass('active');
		e.preventDefault();
	});		
    
 	//  On off button	
	jQuery('.admin-area-heading').on('click', function(e){
		jQuery('.admin-area-mid').toggleClass('active-plan');
		e.preventDefault();
	});		
    
    
       
    

 // > LIGHTBOX Gallery Popup function	by = lc_lightbox.lite.js =========================== //      
 	function lightbox_popup(){
        lc_lightbox('.elem', {
            wrap_class: 'lcl_fade_oc',
            gallery : true,	
            thumb_attr: 'data-lcl-thumb', 
            
            skin: 'minimal',
            radius: 0,
            padding	: 0,
            border_w: 0,
        });
	}			 
 
 // > Nav submenu show hide on mobile by = custom.js
	function mobile_nav(){
		jQuery(".sub-menu").parent('li').addClass('has-child');
		jQuery("<div class='fa fa-angle-right submenu-toogle'></div>").insertAfter(".has-child > a");

		jQuery('.has-child a+.submenu-toogle').on('click',function(ev) {

			jQuery(this).parent().siblings(".has-child ").children(".sub-menu").slideUp(500, function(){
				jQuery(this).parent().removeClass('nav-active');
			});

			jQuery(this).next(jQuery('.sub-menu')).slideToggle(500, function(){
				jQuery(this).parent().toggleClass('nav-active');
			});

			ev.stopPropagation();
		});
	
	}
	

	 
	// Mobile side drawer function by = custom.js
	function mobile_side_drawer(){
		jQuery('#mobile-side-drawer').on('click', function () { 
			jQuery('.mobile-sider-drawer-menu').toggleClass('active');
		});
	}
/*--------------------------------------------------------------------------------------------
	document.ready ALL FUNCTION START
---------------------------------------------------------------------------------------------*/
	jQuery(document).ready(function() {
		// Image Popover = jquery.prettyPhoto.js ================= // 	
		image_popover(),
        // Bootstrap Slider function by  = bootstrap-slider.min.js   
        Bootstrap_Slider(),
		 // > LIGHTBOX Gallery Popup function	by = lc_lightbox.lite.js =========================== //      
		lightbox_popup(),
		// > Nav submenu on off function by = custome.js ===================//
		mobile_nav(),
		// Mobile side drawer function by = custom.js
		mobile_side_drawer()

	}); 	
	
/*===========================
	Window Resize ALL FUNCTION START
===========================*/

	jQuery(window).on('resize', function () {


	});jQuery(window).resize();
	
	
})(window.jQuery);