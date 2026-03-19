# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
このプロジェクトでは Keep a Changelog の形式に準拠しています。  
https://keepachangelog.com/ja/

## [0.1.0] - 2026-03-19
最初の公開リリース。日本株自動売買フレームワークのコア機能を提供します。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期モジュールを追加（__version__ = 0.1.0）。
  - サブパッケージのエクスポート: data, strategy, execution, monitoring（execution は空の初期モジュール）。

- 設定管理
  - 環境変数・設定管理モジュール (kabusys.config.Settings) を実装。
    - .env / .env.local ファイルの自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 必須環境変数チェック (例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD)。
    - 環境（KABUSYS_ENV）やログレベル（LOG_LEVEL）の妥当性検証。
    - データベースパスのデフォルト (DUCKDB_PATH, SQLITE_PATH) と Path 型での提供。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - 固定間隔のレート制御（120 req/min）を行う RateLimiter を実装。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 応答時の自動トークンリフレッシュ（1 回のみ再試行）。
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務データ）
      - fetch_market_calendar（マーケットカレンダー）
    - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
      - save_daily_quotes → raw_prices
      - save_financial_statements → raw_financials
      - save_market_calendar → market_calendar
    - 取得時刻を UTC isoformat で記録（fetched_at）して Look-ahead バイアスを抑止。

- ニュース収集（kabusys.data.news_collector）
  - RSS ベースのニュース収集モジュールを追加。
    - URL 正規化（トラッキングパラメータ除去、ソート、スキーム/ホスト小文字化、フラグメント削除）。
    - defusedxml を用いた安全な XML パース。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）や SSRF 対策を考慮。
    - raw_news テーブルへの冪等保存を前提とした処理設計（記事ID は正規化 URL の SHA-256 を用いる想定）。
    - バルク INSERT チャンク処理。

- 研究用ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum（1/3/6ヶ月モメンタム、MA200 乖離）
    - calc_volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）
    - calc_value（per / roe の計算、raw_financials から最新財務レコード参照）
  - feature_exploration:
    - calc_forward_returns（任意ホライズンの将来リターン計算）
    - calc_ic（Spearman ランク相関による IC 計算）
    - factor_summary（各ファクターの基本統計量）
    - rank（同順位は平均ランクを与えるランク関数）
  - zscore_normalize ユーティリティを再エクスポート。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features 実装:
    - research モジュールから取得した生ファクターをマージ、ユニバースフィルタ（最低株価、20日平均売買代金）適用。
    - Z スコア正規化（指定カラム）と ±3 クリップ。
    - DuckDB の features テーブルへ日付単位で置換（DELETE → INSERT トランザクション）して冪等性を確保。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals 実装:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を算出。
    - 重み付け合算により final_score を算出（デフォルト重みを提供）。合計が 1 でない場合は再スケール。
    - Bear レジーム判定（ai_scores の regime_score の平均が負かつサンプル数閾値を満たす場合）。
    - BUY 閾値（デフォルト 0.60）を超えた銘柄に BUY シグナルを生成（Bear 時は BUY を抑制）。
    - 保有ポジション（positions テーブル）に対するエグジット判定（ストップロス、スコア低下）で SELL シグナルを生成。
    - signals テーブルへ日付単位で置換（DELETE → INSERT、トランザクション）して冪等性を確保。

### 変更 (Changed)
- 初期リリースのため過去バージョンからの変更はありません。

### 修正 (Fixed)
- 初期リリースのため既知のバグ修正はありません。

### ドキュメント/設計ノート (Documentation / Design Notes)
- 多くの処理は「ルックアヘッドバイアス」を防ぐことを優先して設計されています（例: データは target_date 時点までのもののみを参照、fetched_at を記録）。
- DB 操作は可能な限りトランザクション＋バルク挿入で原子性を保証。
- 外部 API 呼び出しは RateLimiter とリトライで保護。
- news_collector はセキュリティ（XML 脆弱性、SSRF、メモリ DoS）を考慮して実装。

### 既知の制限 / TODO (Known issues / TODO)
- generate_signals の一部エグジット条件は未実装:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過の判定）
- calc_value では PBR・配当利回りなどは未実装。
- news_collector の記事ID生成や銘柄紐付け（news_symbols）などの詳細実装は想定されているが、実運用向けの追加整備が必要。
- RateLimiter はスリープベースの実装のため、非同期処理や高スループット環境では見直しの余地あり。
- jquants_client の HTTP 実装は urllib を使用（より高度な制御が必要な場合は requests 等への移行を検討）。

### マイグレーション / 設定メモ (Migration / Configuration)
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- 任意 / デフォルト:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト "development"
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) — デフォルト "INFO"
  - DUCKDB_PATH — デフォルト data/kabusys.duckdb
  - SQLITE_PATH — デフォルト data/monitoring.db
- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml）を基に .env を自動で読み込みます。
  - テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必要な DB スキーマ（このリリースで参照／更新されるテーブルの例）:
  - raw_prices (date, code, open, high, low, close, volume, turnover, fetched_at) — save_daily_quotes が使用
  - raw_financials (code, report_date, period_type, eps, roe, fetched_at) — save_financial_statements が使用
  - market_calendar (date, is_trading_day, is_half_day, is_sq_day, holiday_name) — save_market_calendar が使用
  - prices_daily — research/strategy モジュールが参照
  - features — build_features が更新
  - ai_scores — generate_signals が参照
  - positions — generate_signals のエグジット判定が参照
  - signals — generate_signals が更新
  - raw_news — news_collector が想定

### 依存 / 要求事項 (Dependencies)
- Python 標準ライブラリを中心に実装（ただし DuckDB と defusedxml が必要）。
- 実行にあたっては duckdb ライブラリがインストールされていること。

---

今後の予定:
- トレーリングストップや時間決済などのエグジット条件の追加実装。
- 非同期対応 / 高スループット向けのレート制御改善。
- ニュース収集の記事→銘柄マッチング強化、自然言語処理パイプラインの統合。
- 各種ユニットテスト・統合テストの充実。

--- 

（注）この CHANGELOG は現行コードベースの実装内容から推測して作成しています。実際の仕様や内部設計の変更に応じて更新してください。