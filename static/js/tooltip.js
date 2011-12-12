$(document).ready(function() {
  $('.toolTip').hover(
    function() {
    this.tip = $(this).attr('data-tooltip');
    $(this).append(
     '<div class="toolTipWrapper">'
        + this.tip
      +'</div>'
    );
    this.width = $(this).width();
    $(this).find('.toolTipWrapper').css({left:this.width-22})
    $('.toolTipWrapper').fadeIn(300);
  },
    function() {
      $('.toolTipWrapper').fadeOut(100);
      $(this).children().remove();
        this.title = this.tip;
      }
  );
});
