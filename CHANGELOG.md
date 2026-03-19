CHANGELOG
=========

すべての重要な変更点をこのファイルで記録します。
フォーマットは Keep a Changelog に準拠します。

[Unreleased]
------------

なし

[0.1.0] - 2026-03-19
-------------------

初回リリース。以下の主要機能・設計方針を実装しました。

Added
- パッケージ初期化
  - kabusys パッケージ作成。バージョンを __version__ = "0.1.0" として公開。
  - __all__ に data, strategy, execution, monitoring を公開対象として設定。

- 設定 / 環境変数管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする仕組みを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env の行パースを実装（export プレフィックス、クォート、インラインコメント対応、エスケープ対応）。
  - 環境変数保護（OS 環境変数を protected として .env.local での上書きを防ぐ）。
  - Settings クラスを実装し、J-Quants / kabu API / Slack / データベースパス / システム環境（env, log_level）等のアクセスをプロパティで提供。必須変数未設定時は ValueError を送出。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制限（120 req/min）対応の固定間隔レートリミッタを実装。
  - 再試行（指数バックオフ、最大3回）と 408/429/5xx の取り扱い。429 の場合は Retry-After を尊重。
  - 401 受信時にリフレッシュトークンで id_token を自動更新して 1 回リトライする処理を実装。
  - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
  - DuckDB への保存用関数 save_daily_quotes / save_financial_statements / save_market_calendar を実装。PK 欠損行のスキップ、ON CONFLICT を使った冪等保存を行う。
  - 入力変換ユーティリティ _to_float / _to_int を実装（堅牢なパースルール）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集と raw_news への冪等保存処理を実装するためのユーティリティを追加。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）を実装。
  - 受信サイズ上限（MAX_RESPONSE_BYTES）や defusedxml による XML パース保護、HTTP スキームチェック等を備えた安全設計。
  - 記事ID を正規化 URL の SHA-256 先頭による一意キーで生成する方針を採用。

- 研究用モジュール（kabusys.research）
  - factor_research モジュールでファクター計算を実装:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離）を計算。
    - calc_volatility: 20 日 ATR、atr_pct、avg_turnover、volume_ratio を計算。
    - calc_value: raw_financials と当日の株価から PER / ROE を計算。
  - feature_exploration モジュールで探索用ユーティリティを実装:
    - calc_forward_returns: 複数ホライズンの将来リターンを一括取得。
    - calc_ic: ファクター値と将来リターン間の Spearman IC（ランク相関）を実装。
    - rank / factor_summary: ランク変換、基本統計量（count/mean/std/min/max/median）を計算。
  - 研究側では外部依存を避け、DuckDB の prices_daily / raw_financials のみを参照する設計。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research で算出した生ファクターを結合・正規化して features テーブルへ保存する build_features() を実装。
  - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を実装。
  - Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）と ±3 のクリッピングを適用。
  - 日付単位での置換（DELETE + INSERT トランザクション）により冪等性と原子性を保証。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算、重み付け合算で final_score を算出する generate_signals() を実装。
  - デフォルト重み・閾値を定義し、ユーザ入力 weights を検証・正規化（負値や非数値を無視、合計が 1.0 に再スケール）。
  - Bear レジーム判定（AI の regime_score 平均が負かつサンプル数閾値以上）により BUY を抑制。
  - SELL（エグジット）判定実装（ストップロス -8%、スコア低下）。保有ポジションの価格欠損時は判定をスキップする安全措置。
  - BUY/SELL を signals テーブルに日付単位で置換して保存（トランザクション + バルク挿入）。

- パッケージ API エクスポート
  - kabusys.strategy.__init__ で build_features / generate_signals を公開。
  - kabusys.research/__init__ で主要な研究用関数を再公開（calc_momentum 等、zscore_normalize を含む）。

Changed
- 初回リリースのため該当なし。

Fixed
- 各種保存処理で PK 欠損行をスキップし、ログ警告を出すことで不正データによる例外を回避するようにした。
- JSON デコード失敗やネットワークエラー時のエラーメッセージを明確化し、リトライロジックで堅牢性を向上。

Security
- news_collector: defusedxml による安全な XML パース、受信サイズ制限、トラッキングパラメータ除去、HTTP スキーム検証等により RSS に起因する攻撃リスク（XML Bomb / SSRF / メモリ DoS）を低減。
- jquants_client: レート制限遵守・再試行ロジック・401 時の安全なトークンリフレッシュ実装により API 利用の信頼性を向上。

Notes / Breaking changes / 使用上の注意
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings のプロパティで必須扱い。未設定時は ValueError。
- デフォルト DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- 自動 .env ロード:
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動で読み込みます。テスト等で無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB テーブル期待:
  - 本モジュール群は内部で以下のテーブルを参照/更新します（作成スクリプトは別途用意する前提）:
    - prices_daily, raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals, raw_news
- 冪等性と原子性:
  - features / signals / raw_* 保存処理は日付単位の DELETE + INSERT（トランザクション）や ON CONFLICT による upsert を用いて冪等性を保証する設計。
- ルックアヘッドバイアス対策:
  - 特徴量・シグナル生成は target_date 時点で利用可能なデータのみを参照するよう設計されています（prices の latest-before-target の参照等）。
- 未実装 / 今後の拡張候補:
  - factor_research の一部（PBR・配当利回り等）は未実装。
  - generate_signals 内のトレーリングストップや時間決済（保有 60 営業日超）など一部エグジット条件は未実装（コメントで明記）。
  - execution モジュールはまだ実装なし（発注 API 連携は将来の作業）。

以上。追加の注記やバージョン/リリース情報を反映する場合は本ファイルを更新してください。