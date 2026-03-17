# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
このファイルはコードベース（src/kabusys/ 以下）から機能・修正・既知の問題を推測して作成したリリースノートです。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

### 追加
- なし（現状は初期リリースに相当する機能群が実装されています）。

### 既知の問題 / TODO
- run_prices_etl の末尾に不完全な return 文が存在します（実装ミスにより tuple を返すべき箇所が途切れている）。ETL の呼び出し側で期待する戻り値（fetched / saved）が正しく返らない可能性があります。
- strategy/execution パッケージは __init__.py のみで中身が未実装（プレースホルダ）。
- 単体テスト・統合テストのためのテストケース整備（モックや固定データ）が必要。

---

## [0.1.0] - 2026-03-17

初回公開（推測）。以下の主要機能と設計方針を実装。

### 追加
- パッケージ基本情報
  - kabusys パッケージ初期化（src/kabusys/__init__.py）とバージョン `0.1.0` を導入。
  - パッケージ公開モジュール: data, strategy, execution, monitoring。

- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動ロードする機能を実装。
    - プロジェクトルート判定は __file__ の親ディレクトリを検索し、.git または pyproject.toml を基準とするため CWD に依存しない。
    - 読み込み優先順位: OS環境 > .env.local（override）> .env。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env パーサは export プレフィックス、クォート、インラインコメント、エスケープシーケンスに対応。
  - Settings クラスを導入し、アプリケーションで使用する設定をプロパティで安全に取得可能に。
    - 必須環境変数を _require() でチェック（未設定時は ValueError）。
    - J-Quants・kabuステーション・Slack・DBパスなどの設定項目を定義。
    - 環境（development/paper_trading/live）とログレベルの妥当性チェック、is_live/is_paper/is_dev ユーティリティを提供。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - ベースの HTTP リクエストラッパーを実装（JSON デコード、タイムアウト、ヘッダ管理）。
  - レート制御: 固定間隔スロットリング実装（120 req/min に対応する RateLimiter）。
  - リトライロジック: 指数バックオフ（最大 3 回）、408/429/5xx を対象、429 の Retry-After ヘッダ優先。
  - 認証: refresh_token から id_token を取得する get_id_token、モジュールレベルのトークンキャッシュ（ページネーション間で共有）を実装。401 受信時にトークン自動リフレッシュして 1 回リトライする仕組みを導入。
  - データ取得関数（ページネーション対応）:
    - fetch_daily_quotes（株価日足 OHLCV）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への冪等保存関数:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE を使って重複を排除・更新
    - fetched_at に UTC 時刻を記録し、Look-ahead Bias 防止に留意
  - 型変換ユーティリティ (_to_float / _to_int) を実装（不正値は None にする等の安全仕様）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード収集 → 前処理 → DuckDB 保存 の一連処理を実装。
  - セキュリティ対策:
    - defusedxml を使用して XML Bomb 等を防御。
    - SSRF 対策: URL スキーム検証 (http/https のみ)、ホストのプライベートアドレス検査、リダイレクト時の事前検査用 HTTPRedirectHandler を実装。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）、gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - URL 正規化（トラッキングパラメータ除去、クエリのソート、フラグメント削除）と記事ID生成（SHA-256 の先頭32文字）を実装して冪等性を確保。
  - テキスト前処理: URL 除去・空白正規化。
  - RSS パース: content:encoded の名前空間対応、pubDate の RFC2822 パース（UTC 換算、失敗時は現在時刻で代替）。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事IDを返す。チャンク分割 & 単一トランザクションで挿入。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けを一括で挿入（ON CONFLICT でスキップ、INSERT RETURNING で挿入数を返す）。
  - 銘柄抽出: 正規表現で 4 桁の数値を抽出し、known_codes に存在するもののみ返す関数 extract_stock_codes を提供。
  - run_news_collection: 複数 RSS ソースを巡回して収集・保存・銘柄紐付けを行う統合ジョブ。各ソースは独立して例外処理され、1ソース失敗でも他を継続。

- DuckDB スキーマ管理（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の多層スキーマを定義。
  - 主要テーブルを含む DDL を定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 必要な CHECK 制約・FOREIGN KEY・PRIMARY KEY を設定し、データ整合性を担保。
  - インデックス定義を用意（頻出クエリ向け）。
  - init_schema(db_path) を実装し、データベース/親ディレクトリ作成およびテーブル作成を行う（冪等）。get_connection() を追加。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新を行う ETL の基本設計（差分取得、バックフィル、品質チェックフック）を実装。
  - ETLResult データクラスを提供（target_date、取得/保存件数、品質問題リスト、エラーリスト等）と便利プロパティ（has_errors, has_quality_errors）。
  - テーブル存在チェック、最大日付取得ユーティリティを実装（_table_exists, _get_max_date）。
  - 市場カレンダーに基づく営業日調整関数 _adjust_to_trading_day を実装。
  - 差分更新ヘルパー（get_last_price_date 等）を実装。
  - run_prices_etl（株価差分ETL）を実装（差分計算、バックフィル、fetch/save の呼び出し）。ただし現在の実装には戻り値に関する不備あり（Unreleased に記載）。

### 変更
- N/A（初回実装のため既存コードの変更はなし）

### 修正
- N/A（初回実装）

### セキュリティ
- ニュース収集で SSRF 対策、XML パースの安全化、受信サイズ制限を導入。

### ドキュメント / 注記
- 環境変数（必須）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings で必須化されている（未設定時は ValueError を発生）。
  - DB デフォルトパス: DuckDB -> data/kabusys.duckdb、SQLite -> data/monitoring.db（expanduser 対応）。
  - KABUSYS_ENV は development/paper_trading/live のいずれかを指定。LOG_LEVEL は標準的なログレベル（DEBUG 等）で妥当性チェックあり。

- テスト支援
  - news_collector._urlopen や jquants_client の id_token 注入により、ネットワーク呼び出しをモックしてテスト可能な設計になっている。

---

## 既知の問題 / 注意点（まとめ）
- run_prices_etl の戻り値が不完全であり、ETL の呼び出し結果取得が期待どおりに動作しない可能性がある（優先修正事項）。
- strategy / execution の具体的実装は未提供（今後の実装が必要）。
- .env パーサは多くのケースに対応しているが、極端なエッジケース（複雑なネストされたクォート等）では追加のテストが必要。
- モジュールレベルの ID トークンキャッシュはプロセス単位で動作。マルチプロセス運用時の共有は想定していない（必要なら外部キャッシュを検討）。

---

（この CHANGELOG はコードベースの実装内容から推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース方針に合わせて調整してください。）