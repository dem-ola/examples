<?php
/*
* Template Name: Landing Template
* Template Post Type: post
*/
?>

<?php
/**
 * Template part for displaying posts
 *
 * @link https://developer.wordpress.org/themes/basics/template-hierarchy/
 *
 * @package Within_International
 */
?>

<script async=false>
	// First we get the viewport height and we multiple it by 1% to get a value for a vh unit
	// we take max of vert and hor in case user reloads in landscape - we don't want landscape height
	let vert = window.innerHeight * 0.01;
	let hor = window.innerWidth * 0.01;
	let vh = Math.max(vert, hor); 
	let hh = Math.min(vert, hor); 
	// Then we set the value in the --vh custom property to the root of the document
	document.documentElement.style.setProperty('--vh', `${vh}px`);
	document.documentElement.style.setProperty('--hh', `${hh}px`);	

</script>

<?php
	$menu_icon = pods_field('within_settings', false, 'menu_icon')["guid"];
	$company_name_image = pods_field('within_settings', false, 'company_name_image')["guid"];
	$company_logo = pods_field('within_settings', false, 'company_logo')["guid"];
	$console_collapse_button  = pods_field('console_button', false, 'collapse_button')['guid'];
	$console_expand_button = pods_field('console_button', false, 'expand_button')['guid'];
	$default_cbc = pods_field('within_settings', false, 'default_console_background_colour');
	$default_ctc = pods_field('within_settings', false, 'default_console_text_colour');
    $default_noncbc = pods_field('within_settings', false, 'default_non_console_background_colour');
    $console_opacity = pods_field('within_settings', false, 'console_opacity');
	$general_contact_email = pods_field('within_settings', false, 'general_contact_email');
	$up_arrow = pods_field('within_settings', false, 'up_arrow')["guid"];
	$home_website = pods_field('within_settings', false, 'home_website');
	$pro_bono_text = pods_field('within_settings', false, 'pro_bono_text');
	$pro_bono_link = pods_field('within_settings', false, 'pro_bono_link');
	$pro_bono_text_display = pods_field('within_settings', false, 'pro_bono_text_display');
	$careers_email = pods_field('within_settings', false, 'general_careers_email');
	$privacy_policy_link = pods_field('within_settings', false, 'privacy_policy_link');
	$privacy_policy_text = pods_field('within_settings', false, 'privacy_policy_text');
	$go_back_text = pods_field('within_settings', false, 'go_back_text');
	$slide_back_arrow = pods_field('within_settings', false, 'slide_back_arrow')['guid'];
	$slide_forward_arrow = pods_field('within_settings', false, 'slide_forward_arrow')['guid'];
	$previous_project_text = pods_field('within_settings', false, 'previous_project_text');
	$next_project_text = pods_field('within_settings', false, 'next_project_text');
	$default_projects_page_title = pods_field('within_settings', false, 'default_projects_page_title');
	$landing_page_default_poster = pods_field('within_settings', false, "landing_page_default_poster")['guid'];
	$landing_page_tablet_portrait_poster = pods_field('within_settings', false, "landing_page_tablet_portrait_poster")['guid'];
	$landing_page_tablet_landscape_poster = pods_field('within_settings', false, "landing_page_tablet_landscape_poster")['guid'];
	$landing_page_mobile_poster = pods_field('within_settings', false, "landing_page_mobile_poster")['guid'];

	$id_name = get_field('id_name');
	$show_console = get_field('show_console');
	$collapse_console = get_field('collapse_console_on_load');
	$show_mute_button = get_field('show_video_mute_button');
	$post_video = get_field('post_video');
	$mobile_video = get_field('mobile_video');
	$mobile_image = get_field('mobile_image');
	$tablet_portrait_video = get_field('tablet_video_portrait');
	$tablet_landscape_video = get_field('tablet_video_landscape');
	$post_vimeo_link = get_field('post_vimeo_link');
	$mobile_vimeo_link = get_field('mobile_vimeo_link');
	$tablet_portrait_vimeo_link = get_field('tablet_portrait_vimeo_link');
	$tablet_landscape_vimeo_link = get_field('tablet_landscape_vimeo_link');
	$hide_mobile_console = get_field('hide_mobile_console');
	$show_contact_email = get_field('show_contact_email');
	$noncbc = get_field('non_console_background_colour');
	$cbc = get_field('console_background_colour');
	$ctc = get_field('console_text_colour');
	$page_title = get_field('page_title');
	$navigation_bar_title = get_field('navigation_bar_title');

	$vimeo_suffix = "?autoplay=1&loop=1&background=1";

	if ($cbc == "") { $cbc = $default_cbc; } 
	$cbc = hex2rgba($cbc, $console_opacity);
	if ($noncbc == "") { $noncbc = $default_noncbc; }  
	if ($ctc == "") { $ctc = $default_ctc; } 

	// prepare for template - vimeo or video
	// means one kind of media delivery should be selected
	// and not mix and match vimeos and videos from server
	$vimeo = false;
	$video = false;
	$image = false;
	$image_thumb = false;
	if ( $post_vimeo_link || $tablet_portrait_vimeo_link || $tablet_landscape_vimeo_link || $mobile_vimeo_link) {
		$vimeo = true;
	} else if ($post_video || $mobile_video || $tablet_portrait_video || $tablet_landscape_video) {        
		$video = true;
	}

	if ($mobile_image) {
		$image = $mobile_image;
	}
	if ( has_post_thumbnail() ) {
		$image_thumb = get_the_post_thumbnail_url();
	}

?>

<!-- first item: place here to retain menu and logo focus -->
<div id="page-<?php echo $id_name; ?>" class = "page-wrap" style="background-color:<?php echo $noncbc ?>">
	<div id="<?php echo $id_name; ?>-visuals" class="visuals-wrap">

		<?php if ( $vimeo || $video ) { ?>
			<?php if ( $show_mute_button ) { ?>
				<button id="<?php echo $id_name; ?>-unmute-button" class="unmute-button">UNMUTE</button>
			<?php } ?>
			<img id="landing-poster-image" src="">
			<div class='embed-container'>
				<iframe id="<?php echo $id_name; ?>-vimeo" class='post-vimeo' src="<?php echo $post_vimeo_link ?>" frameborder="0" allow="autoplay; fullscreen" allowfullscreen="allowfullscreen" mozallowfullscreen="mozallowfullscreen" msallowfullscreen="msallowfullscreen" oallowfullscreen="oallowfullscreen" webkitallowfullscreen="webkitallowfullscreen"></iframe>
			</div>
			<video id="<?php echo $id_name; ?>-video" class="post-video mobile-video" autoplay playsinline muted loop>
				<source src=" <?php echo $video ?>" type="video/mp4">
				Your browser does not support the video tag.
			</video> 
		<?php } else if ( $image || $image_thumb) { ?>
			<div><img id="<?php echo $id_name; ?>-image" class="post-image" src="<?php echo $image ?>"/></div>
		<?php } else { echo the_content(); } ?>
	</div>

	<script>
		// get media source - could be vimeo or server hosted video	
		var device;	
		var vim = document.querySelector("#<?php echo $id_name; ?>-vimeo");
		var vid = document.querySelector("#<?php echo $id_name; ?>-video");
		var landingPosterImage = document.querySelector("#landing-poster-image");
		var img = document.querySelector("#<?php echo $id_name; ?>-image");
		if (vim || vid) {
			let id = "<?php echo $id_name; ?>";
			let poster = "<?php echo $landing_page_default_poster ?>";	
			let tp_poster = "<?php echo $landing_page_tablet_portrait_poster ?>";
			let tl_poster = "<?php echo $landing_page_tablet_landscape_poster ?>";
			let mb_poster = "<?php echo $landing_page_mobile_poster ?>";
			let vimSuffix = "<?php echo $vimeo_suffix; ?>";
			let mobVim = "<?php echo $mobile_vimeo_link; ?>";
			let mobVimLink = "<?php echo $mobile_vimeo_link.$vimeo_suffix; ?>";
			let mobVid = "<?php echo $mobile_video; ?>";
			let postVim = "<?php echo $post_vimeo_link; ?>";
			let postVimLink = "<?php echo $post_vimeo_link.$vimeo_suffix; ?>";
			let postVid = "<?php echo $post_video; ?>";
			let tabPort = "<?php echo $tablet_portrait_vimeo_link; ?>"
			let tabPortLink = "<?php echo $tablet_portrait_vimeo_link.$vimeo_suffix; ?>"
			let tabLand = "<?php echo $tablet_landscape_vimeo_link; ?>"
			let tabLandLink = "<?php echo $tablet_landscape_vimeo_link.$vimeo_suffix; ?>"

			if (id == 'landing') {
				// change poster if mobile
				if (isMobile() && isPhone() && isPortrait()) {
					poster = "<?php echo $landing_page_mobile_poster ?>";
				} else if (isMobile() && !isPhone() && !isPortrait()) {
					poster = "<?php echo $landing_page_default_poster ?>";
				} else if (isMobile() && !isPhone() && isPortrait()) {
					poster = "<?php echo $landing_page_tablet_portrait_poster ?>";
				} else if (isMobile() && !isPhone() && !isPortrait()) {
					poster = "<?php echo $landing_page_tablet_landscape_poster ?>";
				}
			}

				device = getMediaSource(id, poster, landingPosterImage, vim, vid, 
							mobVim, mobVimLink, mobVid, 
							postVim, postVimLink, postVid, 
							tabPort, tabPortLink, tabLand, tabLandLink) 

			if (id == 'landing') {
				if (device == 'desktop') {
					let vidLand = document.querySelector("#landing-video");
					vidLand.addEventListener("canplay", function() {
						vidLand.play();
						setTimeout(function() { // so poster meshes with first frame
							landingPosterImage.style.opacity = '0'
							landingPosterImage.style.transition = 'opacity 0s';         
						}, 0);
					});

				} else if (device == 'mobile') {
					let vimLand = document.querySelector("#landing-vimeo");
					var player = new Vimeo.Player(vimLand);
					player.on('play', () => {
						setTimeout(function() { // so poster meshes with first frame
							landingPosterImage.style.opacity = '0'
							landingPosterImage.style.transition = 'opacity 0s';         
						}, 500);
					});
				}
			}

		} else if (img) {
			if (isMobile() && isPhone() && isPortrait() && "<?php echo $mobile_image; ?>"){
				img.src = "<?php echo $mobile_image; ?>";
			} else {
				img.src = "<?php echo $image_thumb; ?>";
			}
		}
	</script>
</div>

<?php if ( $show_console ) { ?>
	<?php if ( $collapse_console ) { ?>
		<div id="<?php echo $id_name; ?>-console" class="console-wrap console-collapse-load" style="background-color:<?php echo $cbc ?>">
	<?php } else { ?>
		<div id="<?php echo $id_name; ?>-console" class="console-wrap"  style="background-color:<?php echo $cbc ?>">
	<?php } ?>

	<div class="console-col console-mobile"  style="color:<?php echo $ctc ?>">
	<div class="console-mobile-title"><?php echo $page_title ?> </div>
        <div class="console-mobile-secondary"></div>
		<div class="console-mobile-text"><?php echo get_field('console_mobile_text'); ?></div>
		<div class="console-mobile-supplementary-a"></div>
		<div class="console-mobile-supplementary-b"></div>
		<?php if ($show_contact_email) { ?>
			<div>
				<a class="contact-email" href="mailto:<?php echo $general_contact_email ?>">
				<?php echo $general_contact_email ?> </a> 
			</div>
		<?php } ?>
	</div>
	<div class="console-col console-col-left" style="color:<?php echo $ctc ?>">
		<div class="page-title"> <?php echo $page_title ?> </div>
		<div class="page-title-large"><?php echo get_field('console_text_left'); ?></div>
	</div>
	<div class="console-col console-col-middle baskerville-large"  style="color:<?php echo $ctc ?>">
		<?php echo get_field('console_text_middle'); ?>	
	</div>
	<div class="console-col console-col-right"  style="color:<?php echo $ctc ?>">
		<?php echo get_field('console_text_right'); ?>
		<?php if ($show_contact_email) { ?>
			<div>
				<a class="contact-email" href="mailto:<?php echo $general_contact_email ?>">
				<?php echo $general_contact_email ?> </a> 
			</div>
		<?php } ?>
	</div>	
</div>
<?php } ?>

<script>
	mobileObjects['page-landing'] = {
		'mobile video' :  "<?php echo $mobile_video; ?>",
		'post video': "<?php echo $post_video; ?>",
		'mobile image': "<?php echo $mobile_image; ?>",
		'post image': "<?php echo get_the_post_thumbnail_url(); ?>",
		'tablet portrait video': "<?php echo $tablet_portrait_video; ?>",
		'tablet landscape video': "<?php echo $tablet_landscape_video; ?>",
		'post vimeo': "<?php echo $post_vimeo_link.$vimeo_suffix; ?>",
		'mobile vimeo': "<?php echo $mobile_vimeo_link.$vimeo_suffix; ?>",
		'tablet portrait vimeo': "<?php echo $tablet_portrait_vimeo_link.$vimeo_suffix; ?>",
		'tablet landscape vimeo': "<?php echo $tablet_landscape_vimeo_link.$vimeo_suffix; ?>",
	}
</script>
