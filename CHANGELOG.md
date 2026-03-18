# Changelog

全ての注目に値する変更点を記録します。本ファイルは「Keep a Changelog」フォーマットに準拠しています。

## [0.1.0] - 2026-03-18

### Added
- 初期リリース: KabuSys — 日本株自動売買システムのベース実装。
  - パッケージエントリポイント (src/kabusys/__init__.py) を定義し、data, strategy, execution, monitoring を公開。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。プロジェクトルートは .git または pyproject.toml を探索して決定するため、CWD に依存しない。
  - .env のパースは次をサポート:
    - コメント行・空行の無視、export KEY=val 形式、シングル/ダブルクォート内のエスケープ処理、インラインコメント扱いの挙動。
    - override / protected オプションにより OS 環境変数を保護して上書き制御。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途）。
  - Settings クラスを提供し、J-Quants/Slack/DB/システム設定をプロパティ経由で取得。値検証（KABUSYS_ENV, LOG_LEVEL）と Path 型の返却（duckdb/sqlite パス）を行う。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - レート制限遵守のための固定間隔スロットリング実装（120 req/min）。
  - リトライロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx・ネットワークエラー対象）。
  - 401 受信時はリフレッシュトークンで自動的に id_token を再取得して 1 回リトライ（再帰防止フラグあり）。
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias のトレースを可能にする設計。
  - DuckDB へ保存する save_* 関数を提供。INSERT は ON CONFLICT DO UPDATE を用いて冪等性を確保。
  - 数値変換ユーティリティ（_to_float, _to_int）で不正値を安全に扱う。
- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news テーブルへ保存する機能を実装。
  - セキュリティ対策:
    - defusedxml を用いた安全な XML パース（XML Bomb 等の緩和）。
    - HTTP リダイレクト時のスキーム検証とプライベートアドレス拒否による SSRF 対策（カスタム RedirectHandler）。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンス最大バイト数制限（デフォルト 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - ホスト名がプライベート/ループバック/リンクローカルかを判定してアクセスをブロック。
  - URL 正規化と記事ID生成:
    - トラッキングパラメータ（utm_*, fbclid 等）除去、クエリのソート、スキーム/ホスト小文字化、フラグメント削除。
    - 正規化 URL の SHA-256（先頭32文字）を記事 ID に使用し冪等性を担保。
  - 前処理・抽出:
    - テキスト前処理（URL 除去、空白正規化）。
    - 記事本文／タイトルから 4 桁の銘柄コード抽出（既知コードセットでフィルタ）。
  - DB 保存:
    - save_raw_news: チャンク (最大 1000 件) にまとめて INSERT ... ON CONFLICT DO NOTHING RETURNING id を実行し、新規挿入 ID のリストを返す（1 トランザクション）。
    - save_news_symbols / _save_news_symbols_bulk: (news_id, code) ペアの一括保存（重複除去・チャンク化・トランザクション）。
  - 実行ラッパー run_news_collection: 複数 RSS ソースを並列ではなく逐次に安全に取得し、失敗したソースはスキップして処理を継続。既知銘柄リストが与えられた場合は新規挿入記事に対して銘柄紐付けを実行。
- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - DataPlatform 設計に基づくテーブル群を定義（Raw / Processed / Feature / Execution レイヤー）。
  - 代表的なテーブル: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等。
  - 頻出クエリ向けのインデックスを作成。
  - init_schema(db_path) にて親ディレクトリ自動作成、全 DDL とインデックスを実行して初期化済みの接続を返す。get_connection() で既存 DB に接続可能。
- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETLResult dataclass: ETL 実行結果・品質問題・エラー一覧を保持。辞書変換ユーティリティを提供。
  - テーブル存在確認・最大日付取得ユーティリティ (_table_exists, _get_max_date)。
  - 市場カレンダー補正ヘルパー (_adjust_to_trading_day)。
  - 差分更新ヘルパー get_last_price_date / get_last_financial_date / get_last_calendar_date。
  - run_prices_etl: 差分更新ロジック（最終取得日から backfill を考慮）で jquants_client を呼び出し、保存まで実行する設計（バックフィルデフォルト 3 日、calendar は先読み 90 日の方針を採用）。

### Security
- RSS・HTTP 周りの処理に対して多層の安全策を実装:
  - defusedxml による XML パース、リダイレクト検査、プライベート IP のブロック、受信サイズの厳格チェックにより SSRF / XML Bomb / メモリ DoS のリスクを低減。
- 環境変数の読み込みは OS 環境変数を保護する設計（protected set）で、不意の上書きを抑止。

### Performance & Reliability
- J-Quants API のレート制御（固定間隔）と指数バックオフリトライにより API 利用の安定性を確保。
- DuckDB へのバルク挿入はチャンク化してパラメータ数・SQL長を制御し、トランザクションで整合性を担保。
- fetch_* 系はページネーションに対応し、ページ間で id_token キャッシュを共有。

### Known issues / TODO
- run_prices_etl の実装において、ソース提供コード中の return 文が未完（"return len(records), " で終了）になっており、期待される (fetched_count, saved_count) を返していない可能性があります。実際の戻り値を正しく返すよう修正が必要です。
- strategy/ execution/ monitoring パッケージの実体は空 __init__.py のみで、各レイヤの実装（信号生成、発注処理、監視機能）は今後追加予定。

### Breaking Changes
- 初回リリースのため該当なし。

(注) 本 CHANGELOG はソースコードから推測して作成しています。実際のリリースノートとして公開する前に、リポジトリのコミット履歴・変更目的と照合してください。