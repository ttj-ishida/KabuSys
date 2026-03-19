# CHANGELOG

すべての重要な変更点は Keep a Changelog の形式に従って記載しています。  
このリポジトリはバージョン 0.1.0 として初期リリース相当の実装が含まれています。

全般的な方針・注意
- 本リリースは内部設計ドキュメント（StrategyModel.md / DataPlatform.md 等）の仕様に基づく実装を含みます。  
- 多くの処理は DuckDB のテーブル（例: `prices_daily`, `raw_prices`, `raw_financials`, `features`, `ai_scores`, `signals`, `positions`, `market_calendar` など）を前提にしており、本パッケージ自体は発注 API へ直接アクセスしない設計です（execution 層とは分離）。
- デフォルト設定や必須環境変数:
  - 必須: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`
  - データベースパス: `DUCKDB_PATH`（デフォルト `data/kabusys.duckdb`）, `SQLITE_PATH`（監視用、デフォルト `data/monitoring.db`）
  - 環境: `KABUSYS_ENV`（`development`, `paper_trading`, `live` のいずれか）
  - ログレベル: `LOG_LEVEL`（`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`）
  - 自動 .env ロードを無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- セキュリティ・堅牢化に配慮した実装（例: XML パーシングに defusedxml、HTTP レスポンスサイズ上限、SSRF 回避のための URL スキーム検査など）が導入されています。

Unreleased
- （なし）

0.1.0 - 2026-03-19
- Added
  - パッケージ初期化
    - `kabusys.__init__` を追加し、バージョンを `0.1.0` に設定。公開モジュールとして `data`, `strategy`, `execution`, `monitoring` を宣言。
  - 環境設定管理
    - `kabusys.config` を追加。
      - プロジェクトルート検出（`.git` または `pyproject.toml` を探索）により、作業ディレクトリに依存しない `.env` 自動ロード機能を実装。
      - `.env` パーサ（シングル/ダブルクォート、バックスラッシュエスケープ、`export KEY=val` 形式、インラインコメント処理など）を備えた堅牢な `_parse_env_line` 実装。
      - 読み込み優先順位: OS 環境変数 > `.env.local` > `.env`。OS 環境変数の保護（protected set）をサポート。
      - 必須キー取得時に未設定なら `ValueError` を投げる `_require`、および `Settings` クラスによるプロパティアクセス (`jquants_refresh_token`, `kabu_api_password`, `kabu_api_base_url`, `slack_bot_token`, `slack_channel_id`, `duckdb_path`, `sqlite_path`, `env`, `log_level`, `is_live`, `is_paper`, `is_dev`) を実装。`env` / `log_level` は入力検証あり。
  - データ収集 / 保存（J-Quants）
    - `kabusys.data.jquants_client` を追加。
      - J-Quants API へのリクエスト実装（ページネーション対応）。
      - 固定間隔のレートリミッタ（120 req/min）を `_RateLimiter` で実装。
      - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を考慮）、および 401 の場合の自動トークンリフレッシュ（1 回のみ）を実装。
      - `get_id_token`（リフレッシュトークン→IDトークン取得）、データ取得関数 `fetch_daily_quotes`, `fetch_financial_statements`, `fetch_market_calendar` を提供。
      - DuckDB への保存ユーティリティ `save_daily_quotes`, `save_financial_statements`, `save_market_calendar` を実装。PK 欠損行のスキップや `ON CONFLICT DO UPDATE` による冪等保存をサポート。
      - 型変換ユーティリティ `_to_float`, `_to_int` を追加し、入力データの不正値を安全に扱う。
  - ニュース収集
    - `kabusys.data.news_collector` を追加。
      - RSS フィード収集（デフォルトに Yahoo Finance RSS）。
      - URL 正規化（トラッキングパラメータ削除、クエリソート、断片削除等）と記事 ID を SHA-256 ベースで生成して冪等性を担保。
      - defusedxml による安全な XML パース、受信サイズ上限（10MB）、チャンク単位のバルク挿入制御等の堅牢化施策を実装。
  - 研究用モジュール（research）
    - `kabusys.research.factor_research` を追加し、以下の定量ファクター計算を実装:
      - Momentum: `calc_momentum`（mom_1m, mom_3m, mom_6m, ma200_dev）、200日移動平均判定（データ不足時に None）。
      - Volatility/Liquidity: `calc_volatility`（20日 ATR、atr_pct、avg_turnover、volume_ratio）、NULL 管理を厳密に行う。
      - Value: `calc_value`（最新財務データ取得と PER/ROE 計算、EPS が 0/欠損時は PER を None）。
    - `kabusys.research.feature_exploration` を追加:
      - `calc_forward_returns`（指定ホライズンの将来リターンを一括取得、ホライズン検証あり）。
      - `calc_ic`（スピアマンのランク相関 / Information Coefficient を計算、有効レコード 3 未満は None を返す）。
      - `factor_summary`（count/mean/std/min/max/median）と `rank`（同順位は平均ランク、丸めにより ties の判定安定化）。
    - `kabusys.research.__init__` で主要関数をエクスポート。
  - 戦略モジュール（strategy）
    - `kabusys.strategy.feature_engineering` を追加:
      - 研究環境で算出した生ファクターを受け取り、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
      - 正規化（`zscore_normalize` の使用）、Z スコアの ±3 クリップ、`features` テーブルへの日付単位の置換（トランザクション + バルク挿入）で冪等性を保持する `build_features` を実装。
    - `kabusys.strategy.signal_generator` を追加:
      - 正規化済みの `features` と `ai_scores` を統合し、コンポーネントスコア（momentum / value / volatility / liquidity / news）を算出。
      - 統合重み（デフォルト: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）と閾値（デフォルト BUY=0.60）に基づく `generate_signals` を実装。ユーザ指定の weights は妥当性チェックとリスケールを行う。
      - Sigmoid/平均補完ロジック、AI レジームスコアの集計による Bear 判定（サンプル数閾値あり）、Bear 時の BUY 抑制を実装。
      - エグジット条件（ストップロス -8%、スコア低下）に基づく SELL シグナル生成（`_generate_sell_signals`）。保有銘柄の価格欠損や未登録要素の扱いに注意深いログ・挙動を追加。
      - `signals` テーブルへの日付単位の置換（トランザクション + バルク挿入）で冪等性を保証。
  - パッケージ公開 API
    - `kabusys.strategy.__init__` で `build_features`, `generate_signals` を公開。

- Changed
  - （初期リリースのため「変更」は特になし）

- Fixed
  - （初期リリースのため「修正」は特になし）

- Security
  - RSS XML パースに defusedxml を使用して XML Bomb 等を軽減。
  - ニュース収集での URL 正規化・トラッキングパラメータ除去、受信上限バイト数、HTTP スキームチェック等を導入し SSRF / DoS 対策を考慮。
  - J-Quants クライアントはトークンの自動リフレッシュ、リトライ、RateLimit を組み合わせて安定性と認証周りの安全性を向上。

Notes / 今後の実装予定（既に設計に含まれているが未実装の機能）
- signal_generator 内の一部エグジット条件（トレーリングストップ、保有日数ベースの時間決済）は positions テーブルに `peak_price` / `entry_date` 等が必要であり、現バージョンでは未実装（コメントで記載）。
- data/news_collector の RSS フィード収集ループ・DB への紐付け（news_symbols などの実際のマッピングロジック）は本実装から拡張が想定される。
- execution 層（実際の発注/約定処理）や monitoring 層の実装はこのリリースではスケルトンまたは未提供。

参考: 主要な定数・閾値（実装内デフォルト）
- ユニバースフィルタ最低株価: 300 円
- ユニバースフィルタ最低平均売買代金: 5e8（5 億円）
- Z スコアクリップ: ±3
- デフォルト BUY 閾値: 0.60
- ストップロス閾値: -0.08（-8%）
- J-Quants API レート上限: 120 req/min

以上。今後のリリースではテストケース、ドキュメント（API 仕様、テーブル定義、運用手順）、および execution/monitoring の具体実装・インテグレーションを追加予定です。必要であれば CHANGELOG のフォーマット調整や追加説明（モジュール毎の詳しい API 仕様など）を作成します。