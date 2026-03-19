# Changelog

すべての重要な変更は本ファイルに記録します。本ファイルは "Keep a Changelog" の形式に準拠します。

- リリース日付は YYYY-MM-DD 形式で記載します。
- このプロジェクトはまだ初期バージョンです。

## [Unreleased]

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買プラットフォームのコアライブラリを追加。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（バージョン: 0.1.0）。
  - パッケージエントリポイント: kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring を公開。

- 設定管理 (src/kabusys/config.py)
  - .env/.env.local からの自動読み込み機能を実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD非依存）。
    - 読み込み順は OS環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env 行パーサーは export 形式、クォート、インラインコメント等に対応。
  - 必須環境変数取得ヘルパー _require を提供（未設定時は ValueError）。
  - 設定オブジェクト Settings を提供。主な設定:
    - J-Quants / kabu ステーション / Slack 用トークン取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須）
    - DBパス (DUCKDB_PATH, SQLITE_PATH のデフォルト設定)
    - 環境種別検証 (KABUSYS_ENV: development|paper_trading|live)
    - ログレベル検証 (LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL)
    - is_live / is_paper / is_dev のヘルパープロパティ

- Data 層 (src/kabusys/data)
  - J-Quants API クライアント (src/kabusys/data/jquants_client.py)
    - レート制限（120 req/min）のための固定間隔 RateLimiter 実装。
    - HTTP リクエストの共通処理: リトライ（指数バックオフ、最大 3 回）、429 の Retry-After 優先、401 受信時の自動トークンリフレッシュ（1 回のみ）。
    - ページネーション対応の取得関数:
      - fetch_daily_quotes
      - fetch_financial_statements
      - fetch_market_calendar
    - DuckDB へ冪等に保存する関数（ON CONFLICT DO UPDATE を使用）:
      - save_daily_quotes (raw_prices)
      - save_financial_statements (raw_financials)
      - save_market_calendar (market_calendar)
    - 型変換ユーティリティ: _to_float / _to_int（不正値は None）
    - id_token キャッシュと共有（ページネーション間で使い回し）
    - Base URL / レート等の定数を明示

  - ニュース収集モジュール (src/kabusys/data/news_collector.py)
    - RSS フィードの取得と前処理機能を実装。
      - デフォルトRSSソース登録 (例: Yahoo Finance ビジネスカテゴリ)。
      - defusedxml を使用した安全な XML パース（XML Bomb 対策）。
      - HTTP レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
      - リダイレクト時の SSRF 防止（スキーム検証、プライベートアドレス拒否）。
      - URL 正規化（トラッキングパラメータ除去、クエリソート）と SHA-256 ベースの記事 ID 生成（先頭32文字）。
      - テキスト前処理（URL 除去、空白正規化）。
      - 銘柄コード抽出ユーティリティ（4桁数字、既知コードセットでフィルタ）。
    - DB 保存関数（DuckDB を前提）:
      - save_raw_news: INSERT ... RETURNING id を使用して新規挿入された記事IDのリストを返す（チャンク/1トランザクション）。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols への紐付けをチャンク挿入（ON CONFLICT DO NOTHING、RETURNING を使い実挿入数を取得）
    - 統合ジョブ run_news_collection を提供（ソース単位で独立エラーハンドリング、既知コードで記事と銘柄の紐付け実行）。

  - スキーマ定義 (src/kabusys/data/schema.py)
    - DuckDB 用の DDL を実装（Raw Layer のテーブル定義を含む）。
      - raw_prices, raw_financials, raw_news, raw_executions 等（初期DDLの一部を含む）。

- Research 層 (src/kabusys/research)
  - 特徴量探索モジュール (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 指定日から各ホライズンに対する将来リターンを DuckDB の prices_daily から一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算（ランク計算ブラックスワン対策あり）。有効レコード < 3 の際は None を返す。
    - rank: 同順位は平均ランクで扱うランク化ユーティリティ（round(v, 12) による丸めで ties 検出漏れを低減）。
    - factor_summary: count/mean/std/min/max/median を計算する基本統計ユーティリティ。
    - 設計上 pandas 等の外部ライブラリに依存せず標準ライブラリのみで実装（DuckDB 接続を受け取る）。

  - ファクター計算モジュール (src/kabusys/research/factor_research.py)
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。
    - calc_value: raw_financials の最新財務データと当日の株価を使い PER（EPS が 0/欠損時は None）、ROE を算出。PBR・配当利回りは未実装。
    - すべて DuckDB の prices_daily / raw_financials テーブルのみを参照し、本番API等にはアクセスしない設計。

- ロギング
  - 各主要処理で logger を使用して処理数や警告・例外を記録。

### 修正 (Fixed)
- 該当なし（初回リリース）

### セキュリティ (Security)
- ニュース収集での SSRF 対策を実装:
  - リダイレクト先のスキーム検証、ホストのプライベートアドレス判定による拒否。
  - defusedxml を用いた XML パースで XML関連攻撃に対処。
  - レスポンスサイズ制限と gzip 解凍後チェックでリソース枯渇攻撃を緩和。

### 既知の制限 / TODO
- research/factor_research のドキュメントに Liquidity が言及されているが、PBR・配当利回り等の一部バリュー指標は未実装。
- DuckDB スキーマは初期DDLの一部を含む。必要なテーブル（prices_daily 等）は外部で整備されることを前提としている。
- ニュース収集の URL 正規化や銘柄抽出は簡易ルール（4桁）に基づいているため誤抽出の可能性がある。
- J-Quants API クライアントは urllib を直接使用。将来的に HTTP クライアントの差し替え（requests / httpx 等）や非同期化が考えられる。

### 開発者向け注意
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- DuckDB 接続を引数で受け取る関数群が多いため、ユニットテストではモック接続またはテスト用DBファイルを準備すること。
- news_collector._urlopen はテスト時にモック可能な設計。

---

この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートには運用での変更や既存ユーザへの移行手順（DB マイグレーション、環境変数追加など）を追記してください。