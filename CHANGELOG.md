# Changelog

すべての重要な変更点を記録します。本プロジェクトは Keep a Changelog の慣習に従って管理されています。

リリース日はコミット時点の推定日付を記載しています。

## [0.1.0] - 2026-03-17

### 追加 (Added)
- 基本パッケージ構成を追加
  - パッケージ名: `kabusys`
  - エントリポイント: `src/kabusys/__init__.py`（バージョン `0.1.0`、公開モジュール `data`, `strategy`, `execution`, `monitoring`）
  - 空のプレースホルダモジュール: `strategy` と `execution`（今後の戦略・発注ロジック実装用）
- 環境設定管理モジュール (`src/kabusys/config.py`)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートを `.git` または `pyproject.toml` から特定）
  - `.env` / `.env.local` の読み込み優先度制御、OS 環境変数の保護機構（protected set）
  - `.env` のパースは export プレフィックス、クォート、エスケープ、インラインコメント等に対応
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート
  - 必須設定取得ヘルパー `_require`、`Settings` クラスで各種設定プロパティを公開（J-Quants トークン、kabu API、Slack、DB パス、環境判定、ログレベル検証など）
- J-Quants API クライアント (`src/kabusys/data/jquants_client.py`)
  - API 呼び出しユーティリティを実装（基本 URL、JSON デコード、タイムアウト）
  - レートリミッタ実装（120 req/min を固定間隔スロットリングで遵守）
  - リトライ用の指数バックオフ（最大 3 回、408/429/5xx を対象）、429 の `Retry-After` ヘッダ優先処理
  - 401 受信時にリフレッシュトークンで自動的に ID トークンを更新して 1 回だけ再試行する仕組み（再帰防止のため allow_refresh 制御）
  - トークンのモジュールレベルキャッシュ（ページネーション間で共有）
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB へ冪等に保存する save_* 関数:
    - save_daily_quotes（`raw_prices` に ON CONFLICT DO UPDATE）
    - save_financial_statements（`raw_financials` に ON CONFLICT DO UPDATE）
    - save_market_calendar（`market_calendar` に ON CONFLICT DO UPDATE）
  - 保存時に取得時刻（fetched_at）を UTC ISO 形式で記録
  - 型変換ユーティリティ `_to_float`, `_to_int`（不正値・空値は None、"1.0" 等の文字列浮動小数を安全に整数化）
- ニュース収集モジュール (`src/kabusys/data/news_collector.py`)
  - RSS フィードからの記事収集と DuckDB への保存を実装
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等への対策）
    - SSRF 対策: 非 http/https スキーム拒否、プライベート/ループバック/リンクローカル IP 検査、リダイレクト検査用ハンドラ（_SSRFBlockRedirectHandler）
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズ再検査（Gzip bomb 対策）
    - URL 正規化でトラッキングパラメータ除去、フラグメント削除、キー順ソート
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保（utm_* 等を除去してからハッシュ化）
  - パース・前処理機能:
    - preprocess_text（URL 除去・空白正規化）
    - RSS pubDate パース（RFC2822 → UTC naive datetime、パース失敗時は現在時刻で代替）
    - fetch_rss（フィード取得、XMLパース、記事抽出、エラーハンドリング）
  - DB 保存:
    - save_raw_news（チャンク単位で INSERT ... ON CONFLICT DO NOTHING RETURNING id、1 トランザクションで実行）
    - save_news_symbols / _save_news_symbols_bulk（記事と銘柄コードの紐付けをチャンク挿入、RETURNING ベースで正確な挿入件数を返す）
  - 銘柄コード抽出:
    - extract_stock_codes（4桁数字パターンを検出し、known_codes に基づきフィルタリング）
  - 統合ジョブ run_news_collection（複数ソース処理、個別ソースのエラーハンドリング、銘柄紐付けの一括挿入）
  - デフォルト RSS ソースに Yahoo Finance を追加（`news.yahoo.co.jp` のカテゴリ RSS）
- DuckDB スキーマ定義と初期化 (`src/kabusys/data/schema.py`)
  - Raw / Processed / Feature / Execution 層のテーブルを包括的に定義
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（主キー・外部キー・CHECK 制約）と型付けを明示
  - 頻出クエリ向けインデックス定義（複数の CREATE INDEX）
  - init_schema(db_path) でディレクトリ作成→テーブル/インデックス作成（冪等）、get_connection ヘルパーを提供
- ETL パイプライン基盤 (`src/kabusys/data/pipeline.py`)
  - ETL の設計ドキュメントに準拠した差分更新・バックフィル機能
  - ETLResult dataclass（品質チェックやエラー情報を含む実行結果オブジェクト）
  - 最終取得日の照会ヘルパー（get_last_price_date / get_last_financial_date / get_last_calendar_date）
  - 日付調整ヘルパー（_adjust_to_trading_day: 非営業日から直近営業日に補正）
  - run_prices_etl の骨子（差分更新ロジック、backfill_days デフォルト 3、API からの取得→保存のフロー）を実装

### 変更 (Changed)
- 初期リリースのため該当なし（ベース実装の追加が中心）

### 修正 (Fixed)
- 初期リリースのため該当なし

### セキュリティ (Security)
- RSS 関連で XML パーサに defusedxml を導入し、XML 関連の脆弱性を低減
- SSRF 対策を導入（スキーム検査、IP のプライベート判定、リダイレクト時の検査）
- HTTP レスポンスサイズ制限や gzip 解凍後のサイズチェックによりメモリ DoS のリスクを軽減

### 既知の問題 / 注意点 (Known issues / Notes)
- ETL の run_prices_etl の末尾が不完全に見えます（提供されたコードは最後の return が途中で切れているように見受けられます）。このため、現状の実装では戻り値のタプルが不正になる可能性があります。リリース後の修正が必要です（期待される戻り値は (fetched_count, saved_count) のはずです）。
- jquants_client の HTTP 呼び出しは urllib を直接使用しており、外部テスト/モック時はタイムアウトやネットワーク依存の扱いに注意が必要です（単体テストでは _rate_limiter や _urlopen のモック化が想定されます）。
- news_collector のホスト名の DNS 解決失敗時は「安全側（非プライベート）」として処理する方針になっており、厳格にブロックしたい環境では設定の見直しが必要です。

---

今後の予定（例示）
- run_prices_etl の戻り値/エラーハンドリング修正
- strategy / execution モジュールの実装（シグナル生成、発注ロジック、kabu API 統合）
- 品質チェックモジュール（quality）の実装と ETL との統合テスト強化
- 単体テスト・統合テストの追加、CI パイプラインの整備

（以上）