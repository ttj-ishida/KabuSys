CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。  
この CHANGELOG はリポジトリ内のコードから推測して作成した初期リリース向けの変更履歴です。

Unreleased
----------

（現時点の未リリースの変更はありません）

[0.1.0] - 2026-03-18
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ情報を追加
    - src/kabusys/__init__.py に __version__ = "0.1.0"、および __all__ の公開モジュール定義を追加。

- 環境変数・設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数からの設定値自動読み込み機能を実装。
      - プロジェクトルートを .git または pyproject.toml から探索して自動読み込み（CWD 非依存）。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env。
      - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env 行パーサ（クォート・エスケープ・インラインコメント処理対応）を実装。
    - 必須環境変数取得用の _require ユーティリティを提供。
    - Settings クラスを導入し、主要な設定プロパティを提供:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
      - KABUSYS_ENV（development / paper_trading / live の検証）、LOG_LEVEL の検証
      - is_live / is_paper / is_dev のユーティリティ

- Data (J-Quants クライアント)
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装（urllib ベース、依存ライブラリを最小化）。
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - リトライロジック（最大 3 回、指数バックオフ、429 の Retry-After を尊重、408/429/5xx を再試行対象）。
    - 401 発生時は自動でリフレッシュして 1 回リトライ（トークンリフレッシュは安全に制御）。
    - ページネーション対応の fetch_* API を提供:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - DuckDB への保存ユーティリティ（冪等性を考慮）:
      - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE で保存
      - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE
      - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE
    - 文字列→数値変換ユーティリティ: _to_float / _to_int（厳密な挙動、"1.0" → 1 を許容、1.9 のような小数部を含む文字列は None を返す等）
    - fetched_at を UTC ISO 形式で格納して look-ahead bias のトレースを可能に

- News Collector（RSS ニュース収集）
  - src/kabusys/data/news_collector.py
    - RSS フィード取得と raw_news/raw_news_symbols への冪等保存を実装。
    - セキュリティと堅牢性:
      - defusedxml を使用して XML 脆弱性を防止。
      - SSRF 対策: リダイレクト時のスキーム検証、ホストのプライベートアドレス検査（DNS 解決して A/AAAA を検査）、_SSRFBlockRedirectHandler を用いた防御。
      - 許可スキームは http / https のみ。
      - レスポンスサイズ上限 MAX_RESPONSE_BYTES = 10MB（Content-Length チェック＋読み込み時オーバー確認）。
      - gzip 圧縮検証（解凍後のサイズチェック含む）と Gzip bomb 対策。
    - URL 正規化と追跡パラメータ除去（utm_* など）。記事IDは正規化 URL の SHA-256 先頭32文字で生成して冪等性を担保。
    - テキスト前処理（URL 除去、空白正規化）。
    - DB 挿入はチャンク化して 1 トランザクションで実行、INSERT ... RETURNING を用いて実際に挿入された ID/件数を正確に返す。
    - 銘柄コード抽出ユーティリティ（4桁数字を抽出して known_codes に基づきフィルタ）と、一括紐付け保存の実装。
    - デフォルト RSS ソース: Yahoo Finance のビジネスカテゴリ（DEFAULT_RSS_SOURCES）。

- Research（ファクター計算 / 特徴量探索）
  - src/kabusys/research/factor_research.py
    - StrategyModel に基づく定量ファクター群を実装:
      - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（MA200 乖離）の計算。必要データ不足時は None を返す。
      - calc_volatility: atr_20（20日 ATR の単純平均）, atr_pct, avg_turnover（20日平均売買代金）, volume_ratio（当日 / 平均）の計算。tr（true range）の NULL 伝播を慎重に扱う。
      - calc_value: raw_financials の最新財務データと当日の株価を組み合わせて per / roe を算出（EPS が無効な場合は None）。
    - DuckDB の prices_daily / raw_financials テーブルのみを参照する設計。外部 API にはアクセスしない。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算: calc_forward_returns（複数ホライズン対応、ホライズンは営業日ベース、SQL で一括取得）
    - IC（Information Coefficient）計算: calc_ic（Spearman の ρ、ランク関数を内部実装し ties を平均ランクで処理）
    - rank（同順位は平均ランク、丸め処理で浮動小数の ties 検出漏れを防止）
    - factor_summary（count/mean/std/min/max/median を標準ライブラリのみで計算）
    - すべて pandas 等の外部依存なしで実装

  - src/kabusys/research/__init__.py
    - 主要ユーティリティをエクスポート: calc_momentum, calc_volatility, calc_value, zscore_normalize（data.stats から）, calc_forward_returns, calc_ic, factor_summary, rank

- DuckDB スキーマ定義
  - src/kabusys/data/schema.py
    - DataSchema に基づく 3 層（Raw / Processed / Feature）取得・初期化用モジュールを実装。
    - raw_prices, raw_financials, raw_news, raw_executions などの DDL 定義を含む（NOT NULL/チェック制約や PRIMARY KEY 指定を含む）。

Changed
- （初回リリース）N/A

Fixed
- （初回リリース）N/A

Security
- ニュース収集での SSRF 対策、defusedxml による XML 攻撃防御、レスポンスサイズと gzip 解凍後の上限チェック、HTTP リダイレクト時の検証などを導入。
- J-Quants クライアントでは 401 時のトークンリフレッシュを安全に行い、無限再帰を防止。

Notes / Usage
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - これらは Settings クラスのプロパティ呼び出し時に未設定だと ValueError を送出する。
- .env 自動読み込み:
  - プロジェクトルートが .git または pyproject.toml で検出される場合に .env/.env.local を自動読み込み。
  - テストや一時的な環境下では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- DuckDB/SQLite のデフォルトパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- J-Quants API:
  - レート制限: 120 req/min（内部でスロットル）
  - リトライ: 最大 3 回（指数バックオフ）
  - 401 は自動トークン更新を試みる（1 回のみ）
- News Collector:
  - レスポンス最大許容サイズ: 10MB（解凍後も同様）
  - 記事ID: 正規化 URL の SHA-256 先頭 32 文字で一意化
  - DB への保存はチャンク化・トランザクションで実行。挿入された ID を返す。
- Research:
  - 全ての関数は DuckDB 接続と prices_daily/raw_financials（など）テーブルに依存。外部 API 呼び出しは行わないため、安全にオフライン分析可能。
  - pandas 等に依存しない純 Python 実装（標準ライブラリ + duckdb）。

既知の制限 / TODO（コードから推定）
- 一部テーブル定義（raw_executions など）がスニペット中で途中までの定義になっている。完全なスキーマとマイグレーション機構の整備が今後必要。
- zscore_normalize は data.stats から参照されているため、dataパッケージの stats モジュールが正しく存在することが前提。
- NewsCollector の URL 正規化やホスト検証は DNS 解決失敗時に安全側（非プライベート）として扱うため、場合によっては内部アドレスの漏れ検出が難しいケースがある（設計上のトレードオフ）。

開発者向け補足
- 単体テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って環境依存の自動ロードを無効化すると安定する。
- news_collector._urlopen や jquants_client._request などはテストでモック差し替えしやすい設計になっている（内部関数を呼び出し可能）。

---
この CHANGELOG は、提供されたソースコードの内容から挙動・意図を推測して作成しています。実際のリリースノートとして使用する場合は、リポジトリのコミット履歴・変更差分に基づいて調整してください。