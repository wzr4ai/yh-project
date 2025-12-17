<script>
  import { getRole, getToken, isTokenValid } from './common/auth.js'

  const LOGIN_PAGE = '/pages/auth/login'
  const CLERK_HOME = '/pages/pricing/overview'
  const OWNER_HOME = '/pages/dashboard/index'

  function normalizePath(url) {
    if (!url) return ''
    const path = String(url).split('?')[0]
    return path.startsWith('/') ? path : `/${path}`
  }

  function shouldForceLogin() {
    const token = getToken()
    return !token || !isTokenValid(token)
  }

  function isClerkOnlyMode() {
    return getRole() !== 'owner'
  }

  function isAllowedForClerk(path) {
    return path === LOGIN_PAGE || path === CLERK_HOME
  }

  function guardAndRedirect(targetUrl) {
    const path = normalizePath(targetUrl)
    if (shouldForceLogin() && path !== LOGIN_PAGE) {
      uni.reLaunch({ url: LOGIN_PAGE })
      return false
    }
    if (isClerkOnlyMode() && !isAllowedForClerk(path)) {
      uni.reLaunch({ url: CLERK_HOME })
      return false
    }
    return true
  }

	export default {
		onLaunch: function() {
			console.log('App Launch')
      ;['navigateTo', 'redirectTo', 'reLaunch', 'switchTab'].forEach((method) => {
        uni.addInterceptor(method, {
          invoke(args) {
            if (args && args.url) {
              return guardAndRedirect(args.url) ? args : false
            }
            return args
          }
        })
      })
		},
		onShow: function() {
			console.log('App Show')
      const pages = getCurrentPages() || []
      const current = pages.length ? pages[pages.length - 1] : null
      const path = current && current.route ? `/${current.route}` : ''
      if (shouldForceLogin() && path && path !== LOGIN_PAGE) {
        uni.reLaunch({ url: LOGIN_PAGE })
        return
      }
      if (!shouldForceLogin() && isClerkOnlyMode() && path && !isAllowedForClerk(path)) {
        uni.reLaunch({ url: CLERK_HOME })
        return
      }
      if (!shouldForceLogin() && getRole() === 'owner' && path === CLERK_HOME) {
        uni.reLaunch({ url: OWNER_HOME })
      }
		},
		onHide: function() {
			console.log('App Hide')
		}
	}
</script>

<style>
	/*每个页面公共css */
</style>
