# Screen patterns

## Edit form

Use a meaningful title, persistent field labels, concise help and field-specific
errors. Keep submitted values when validation fails. Put the main commit after
the inputs or in the native MainButton; explain any disabled state. Unsaved-change
handling belongs to the app's navigation and supported close-confirmation API.
Don't trap users in the app after a failed save.

## Catalog and detail

Use a readable title, current price/currency, relevant availability and a bounded
list. Filter/search states should explain whether there are no records or no
matching records. Detail screens expose one main next action and quiet navigation.
Do not make a hover-only action essential on touch devices. Server IDs and quoted
prices are application data, never authorization supplied by the browser.

## Checkout

Show the exact item, quantity, amount/currency and consequences before committing.
Keep Cancel neutral. Native invoice closure updates the UI; entitlement comes
from the authenticated backend's durable payment state. Display pending, failed,
canceled and fulfilled states separately. Provide Check status for an uncertain
outcome instead of repeatedly creating an order.

## Settings and permission

Use a checkbox/switch for a real boolean preference and a labeled radio/select
for peer choices. A visual switch must have the right native semantic control or
an implemented ARIA switch pattern. Don't conflate a stored preference with OS
permission. Explain contact/location/write-access requests at the point of need
and keep denial recoverable. Respect reduced motion and don't require haptics.

## Offline and empty states

An empty state should offer the first useful action. An offline state retains
already loaded data when safe and marks it stale. Reads may be retryable; a timed
out mutation needs reconciliation before another commit. Avoid discarding the
user's form merely because a connection failed. Recovery copy should identify
what is saved and what the user can do next.
