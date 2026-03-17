# Changelog

すべての重要な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠しています。
リリースはセマンティックバージョニングに従います。

- [Unreleased]
- [0.1.0] - 2026-03-17

## [Unreleased]
（現時点では未リリースの変更はありません。コードベースから推測される既知の問題点・注意点を下記に記載します。）

### 注意事項 / 既知の問題
- data/pipeline.py の run_prices_etl 関数の戻り値が途中で切れており（`return len(records),` のまま）、期待される (fetched, saved) タプルの2番目の値を返していません。ETL フローでの呼び出し側に影響するため修正が必要です。
- パッケージのサブモジュール（`strategy`, `execution`）は empty パッケージとしてプレースホルダが存在しており、実装はこれからです。

---

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装。

### Added
- パッケージとバージョン
  - パッケージ初期化: kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたはOS環境変数から設定を自動読み込み。
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動検出し、CWD 非依存で動作。
  - .env のパース機能を実装:
    - コメント、export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理などをサポート。
    - override / protected 機能により OS 環境変数を保護して .env を上書きする制御が可能。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラス:
    - J-Quants / kabuステーション / Slack / DB パス 等のプロパティを提供。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証ロジック。
    - duckdb/sqlite の既定パス設定（expanduser 対応）と is_live / is_paper / is_dev ヘルパー。

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装:
    - レート制限管理: 固定間隔スロットリングで 120 req/min を遵守する _RateLimiter を実装。
    - リトライロジック: 指数バックオフ、最大 3 回、HTTP 408/429/5xx の再試行、429 の場合は Retry-After ヘッダを優先。
    - 401 受信時のトークン自動リフレッシュ（1 回まで）とモジュールレベルの ID トークンキャッシュを実装。
    - ページネーション対応で日足（fetch_daily_quotes）・財務（fetch_financial_statements）・市場カレンダー（fetch_market_calendar）を取得。
    - 取得時刻のトレーサビリティ: fetched_at を UTC 形式で付与。
  - DuckDB 保存ユーティリティ:
    - raw_prices / raw_financials / market_calendar への保存関数（save_*）を実装。
    - 冪等性: INSERT ... ON CONFLICT DO UPDATE を用いて重複を上書き（upsert）する設計。
    - 型変換ユーティリティ _to_float / _to_int を提供し、変換失敗時は None を返す。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news / news_symbols に保存する一連の処理を実装。
  - セキュリティ対策:
    - defusedxml を使用して XML BOM や XML 関連攻撃を軽減。
    - SSRF 対策: リダイレクト時にスキーム検査・ホストのプライベートアドレス判定を行う _SSRFBlockRedirectHandler を実装。
    - URL スキームは http/https のみ許可し、それ以外は拒否。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を設定し、gzip 解凍後も再検証（Gzip bomb 対策）。
  - 正規化 / 同定:
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ（utm_ 等）の除去、フラグメント削除、クエリキー順ソートを実施。
    - 記事IDは正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を確保。
  - DB 保存の実装:
    - save_raw_news: チャンク INSERT + トランザクション + INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、新規挿入IDを返却。
    - save_news_symbols / _save_news_symbols_bulk: 銘柄紐付けをバルクで保存し、INSERT ... RETURNING で実際に挿入された件数を返す。トランザクションで一括処理し失敗時はロールバック。
  - 文章前処理や日付パース:
    - URL 除去、空白正規化を行う preprocess_text。
    - RSS pubDate を RFC2822 から UTC naive datetime にパースする _parse_rss_datetime（失敗時は現在時刻で代替）。

- データベーススキーマ (kabusys.data.schema)
  - DuckDB 用スキーマ定義と初期化関数 init_schema を実装。
  - 3 層設計に基づくテーブル群を定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型チェック制約・PRIMARY KEY・FOREIGN KEY を設定。
  - 頻出クエリのためのインデックス群を作成（idx_prices_daily_code_date など）。
  - get_connection ヘルパーを提供（スキーマ初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の基本フローを実装:
    - 差分更新ロジック（DB の最終取得日を参照して差分のみ取得、backfill サポート）。
    - 市場カレンダーの先読み（lookahead）パラメータ。
    - 品質チェックモジュール（quality）との連携を想定した ETLResult dataclass を実装。品質問題を集約して返却できる構造。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date といった差分判定ユーティリティ。
    - run_prices_etl: date_from 自動算出（最終取得日 - backfill_days + 1）と fetch/save の実行ロジック（ただし現状戻り値の不整合あり、要修正）。
  - 設計方針: backfill_days による API 後出し修正の吸収、品質チェックは検出しても ETL を継続する方針（呼び出し元で判断）。

- パッケージ構造
  - 空のサブパッケージ / モジュールプレースホルダ（kabusys.execution, kabusys.strategy, kabusys.data.__init__ 等）を含む。

### Changed
- （初回リリースのため履歴上の変更はありません）

### Fixed
- （初回リリースのため修正履歴はありません。ただし pipeline の戻り値は実装漏れのため今後修正予定。）

### Security
- news_collector における SSRF 対策、defusedxml 利用、レスポンスサイズ制限、許可スキームの厳格化などを実施し外部データ取り込み時の攻撃面を低減。

### Notes / Implementation details
- jquants_client のレート制御は単純な固定間隔スロットリングを採用（120 req/min を満たす実装）。将来的にバースト対応やトークンバケットに変更する余地あり。
- DuckDB への保存はできる限り冪等にしてある（ON CONFLICT DO UPDATE / DO NOTHING）。
- NewsCollector の URL 正規化や記事ID生成はトラッキングパラメータの除去を前提としているため、同一実体の重複挿入を抑制できる設計。
- run_news_collection は各ソースごとに独立して例外処理を行い、一つのソース失敗が他へ影響しないようにしている。

---

（補足）
この CHANGELOG は提供されたコード内容から推測して作成しています。実際のリリースノートでは追加の運用情報、既知の制約、互換性ポリシー、マイグレーション手順などを追記することを推奨します。