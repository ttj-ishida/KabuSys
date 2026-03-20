Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

現行バージョン: 0.1.0

Unreleased
----------

- なし

0.1.0 - 2026-03-20
------------------

初回公開リリース。日本株自動売買システムのコアライブラリを実装しました。主な追加点、設計方針、既知の動作について以下にまとめます。

Added
- パッケージ基盤
  - kabusys パッケージ初版を追加。バージョンは 0.1.0。
- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機構を実装。
  - プロジェクトルートの検出は __file__ を基点に親ディレクトリから .git または pyproject.toml を探索する方式を採用（CWD に依存しない）。
  - 高度な .env パーサーを実装（コメント行、export プレフィックス、シングル/ダブルクォート対応、バックスラッシュエスケープ処理）。
  - .env と .env.local の優先読み込み（OS 環境変数の保護機能付き）と自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を導入。
  - Settings クラスで主要な設定値をプロパティとして提供（J-Quants トークン、kabu API、Slack トークン・チャンネル、DB パス、環境・ログレベル判定ユーティリティ等）。
  - KABUSYS_ENV / LOG_LEVEL の値チェックを追加（許容値以外は ValueError を送出）。
- データ取得 / 保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。日足、財務データ、マーケットカレンダーの取得関数（ページネーション対応）を提供。
  - レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を追加。
  - HTTP リトライロジック（指数バックオフ、最大試行回数、HTTP 408/429/5xx を考慮）を実装。429 時は Retry-After ヘッダを優先。
  - 401 受信時はリフレッシュトークンから自動で ID トークンを再取得して 1 回リトライする機能を追加。モジュールレベルの ID トークンキャッシュを導入してページネーション間で共有。
  - fetch_* 系関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を実装。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT による冪等保存をサポート。
  - データ変換ユーティリティ（_to_float, _to_int）を実装し、不正データや空値に安全に対処。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集モジュールを実装。デフォルトで Yahoo Finance Business の RSS を参照する設定を用意。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化、フラグメント削除）と記事 ID（正規化 URL の SHA-256 の先頭 32 文字）による冪等性を導入。
  - defusedxml を使った XML パースによる安全性強化、受信サイズ制限（MAX_RESPONSE_BYTES=10MB）、SSRF 対策（HTTP/HTTPS スキーム限定）などのセキュリティ対策を実装。
  - テキスト前処理、バルク挿入チャンク化、トランザクションでの DB 書き込みなどの効率化を実装。
- リサーチ / ファクター（kabusys.research）
  - 研究用途のファクター計算モジュールを実装。
  - calc_momentum, calc_volatility, calc_value を提供（prices_daily / raw_financials を参照）。
  - calc_forward_returns（将来リターン計算、複数ホライズン対応）、calc_ic（Spearman ランク相関に基づく IC 計算）、factor_summary（基本統計量計算）、rank（同順位は平均ランク）を実装。
  - 外部ライブラリに依存せず、DuckDB を中心に SQL と標準ライブラリで完結する設計。
- 戦略（kabusys.strategy）
  - feature_engineering.build_features：研究で計算した raw factors をマージ・ユニバースフィルタ適用・Z スコア正規化（_NORM_COLS）・±3 クリップし、features テーブルへ日付単位で置換（トランザクション）する処理を実装。
  - signal_generator.generate_signals：features と ai_scores を統合して final_score を算出し、BUY / SELL シグナルを生成して signals テーブルへ日付単位で置換する処理を実装。Bear レジーム抑制、BUY/SELL 優先ポリシー、重み補正/再スケーリングなどをサポート。
  - エグジット判定ロジック（ストップロス、スコア低下）を実装（トレーリングストップや時間決済は未実装で注記あり）。
- DB / トランザクション取り扱い
  - features / signals などテーブルへの書き込みは「日付単位の置換」を基本とし、BEGIN/COMMIT/ROLLBACK を用いた原子性を確保。ROLLBACK 失敗時の警告ログを出力。

Changed
- 設計上の決定と方針を明文化
  - ルックアヘッドバイアス防止方針を全体で採用（target_date 時点のデータのみ参照する設計）。
  - 本番発注 API（execution 層）への直接依存は持たないモジュール分離を徹底（strategy/research/data 層の分離）。
  - DuckDB を中心としたデータ設計（raw_* / prices_daily / features / ai_scores / signals / positions 等を前提）で実装。

Fixed
- .env パーサーの改善
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント判別などの細かいケースに対応し、より堅牢な .env 解析を実現。
- データ保存の堅牢化
  - raw_* テーブルへの保存時に主キー欠損行をスキップしてログ出力する処理を追加。
  - save_* 関数で ON CONFLICT による更新を適切に行うことで冪等性を保証。
- HTTP / API 呼び出しの堅牢化
  - ネットワークエラーや HTTP エラーに対する再試行ロジック、429 の Retry-After 尊重、401 時のトークンリフレッシュを実装し、運用上の失敗を減らす。

Security
- XML/パース関連
  - defusedxml を用いた RSS パースで XML Bomb 等の攻撃を軽減。
- ネットワーク関連
  - ニュース収集で最大受信バイト数を制限しメモリ DoS を防止。
  - URL 正規化でスキーム検査を行い HTTP/HTTPS 以外を拒否して SSRF リスクを低減。
- 認証
  - ID トークンの安全なキャッシュと自動リフレッシュを実装し、認証失敗時のリトライを管理。

Deprecated
- なし

Removed
- なし

Notes / Known limitations
- positions テーブルに peak_price / entry_date 等がないため、トレーリングストップや時間決済のロジックは未実装。将来実装予定。
- calc_forward_returns のホライズンは最大 252 営業日までの制約あり（不正な値は ValueError）。
- generate_signals で不正な weights が与えられた場合は無効値をスキップしデフォルトにフォールバックまたは再スケールされる。詳細は関数ドキュメント参照。
- 一部の集計は DuckDB のウィンドウ関数や LEAD/LAG に依存するため、データの整合性（連続した営業日レコード等）に注意。

開発者向けメモ
- 自動 .env ロードを無効化したいテストや CI 環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 接続は各関数に明示的に渡す設計です。接続管理（接続の生成/クローズ）は呼び出し側で行ってください。

以上。