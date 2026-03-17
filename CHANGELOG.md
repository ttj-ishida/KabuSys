CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

- 継続作業 / 今後の予定
  - ETL パイプラインの追加ジョブ（財務データ・カレンダーの差分ETL等）および品質チェックの統合（quality モジュールと連携した自動アクション）。
  - strategy / execution パッケージの実装（現状はプレースホルダ）。
  - 単体テストと統合テストの追加（ネットワーク、DB、SSRF対策のモックを含む）。
  - run_prices_etl 等の ETL 戻り値整備や追加のエラーハンドリング強化。

0.1.0 - 2026-03-17
------------------

Added
- 全体
  - 初回公開リリース。パッケージバージョンを kabusys.__version__ = "0.1.0" に設定。
  - パッケージ公開インターフェースに data, strategy, execution, monitoring をエクスポート（__all__）。

- 環境設定 (kabusys.config)
  - .env ファイルまたは環境変数から設定値を読み込む自動ロード実装。
    - プロジェクトルートを .git または pyproject.toml から特定して .env/.env.local を読み込む（CWD 非依存）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
  - .env パーサーは export プレフィックス、クォート値、インラインコメント、バックスラッシュエスケープに対応。
  - Settings クラス提供（jquants_refresh_token, kabu_api_password, slack_bot_token 等の必須値取得、duckdb/sqlite パス、環境チェック、ログレベル検証）。
  - 環境値検証: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の妥当性チェック。

- J-Quants クライアント (kabusys.data.jquants_client)
  - API クライアントを実装:
    - ベース URL とパス指定で JSON を取得する汎用 _request 実装。
    - レートリミッタ（120 req/min）を固定間隔スロットリングで実装。
    - 再試行 (最大 3 回)、指数バックオフ、HTTP 408/429/5xx のリトライ処理。429 の場合は Retry-After ヘッダを優先。
    - 401 受信時は ID トークンを自動でリフレッシュして 1 回リトライ（無限再帰回避のため allow_refresh 制御）。
    - id_token のモジュールレベルキャッシュ（ページネーション間で共有）。
  - データ取得関数:
    - fetch_daily_quotes: 日次株価（OHLCV）をページネーション対応で取得。
    - fetch_financial_statements: 四半期財務データをページネーション対応で取得。
    - fetch_market_calendar: JPX マーケットカレンダーを取得。
    - 取得時に fetched_at（UTC）を記録する設計で look-ahead bias を防止。
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes: raw_prices テーブルへ INSERT ... ON CONFLICT DO UPDATE（date, code を PK）。
    - save_financial_statements: raw_financials テーブルへ冪等保存（code, report_date, period_type が PK）。
    - save_market_calendar: market_calendar テーブルへ冪等保存。
  - 値変換ユーティリティ _to_float / _to_int: 不正値や空文字列の扱い、"1.0" のような浮動小数点文字列を安全に int に変換するロジックを実装。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集し raw_news / news_symbols に保存する完全なパイプラインを実装。
    - RSS 取得とパース（defusedxml を使用して XML Bomb 等に対処）。
    - Gzip 対応と受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時にスキームと到達先ホストの検査を行うカスタム HTTPRedirectHandler（_SSRFBlockRedirectHandler）。
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストかを判定してブロック。
    - URL 正規化:
      - スキーム・ホストを小文字化、トラッキングパラメータ（utm_ 等）除去、フラグメント削除、クエリソート。
      - 記事 ID は正規化 URL の SHA-256 ハッシュ先頭32文字を使用し冪等性を確保。
    - テキスト前処理: URL 除去、空白正規化。
    - DB 保存:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された ID を返す。チャンク分割と 1 トランザクションで処理しオーバーヘッドを抑制。
      - save_news_symbols / _save_news_symbols_bulk: (news_id, code) ペアを重複除去の上バルク挿入。INSERT ... RETURNING により実際に挿入された件数を返す。
    - 銘柄コード抽出: 4桁数字パターンを抽出し、既知の銘柄セットでフィルタ（重複除去）。
    - run_news_collection: 複数 RSS ソースを個別に処理しソース障害時も他ソースは継続、既知銘柄との紐付けを実行。

- DuckDB スキーマ (kabusys.data.schema)
  - DataSchema.md に基づく 3 層 + 実行層のスキーマを定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（NOT NULL / CHECK / PRIMARY KEY / FOREIGN KEY）を設計に反映。
  - 頻出クエリ用のインデックスを定義（コード×日付スキャン、ステータス検索等）。
  - init_schema(db_path) による初期化関数:
    - 親ディレクトリ自動作成、全テーブル/インデックスを冪等に作成して DuckDB 接続を返す。
  - get_connection(db_path) で既存 DB への接続を取得（初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の枠組みを実装:
    - 差分更新の考え方（DB の最終取得日を参照し未取得分のみ取得）。
    - backfill_days による直近再取得（デフォルト 3 日）で API の後出し修正に対応。
    - 市場カレンダーの先読み設定（_CALENDAR_LOOKAHEAD_DAYS = 90）。
    - ETLResult dataclass: ETL 実行結果、品質問題（quality.QualityIssue）とエラーの集約、to_dict によるシリアライズ。
    - テーブル存在チェック、最大日付取得ヘルパー。
    - _adjust_to_trading_day: 非営業日の調整ロジック（最大 30 日遡る）。
    - 差分 ETL ジョブ: run_prices_etl を実装し、date_from 自動算出、J-Quants からの取得および保存を実行（jq.fetch_daily_quotes / jq.save_daily_quotes を利用）。（注: pipeline はさらに拡張予定）

Security
- ニュース収集モジュールで SSRF 対策を導入（スキーム検証、プライベートIP検査、リダイレクト時チェック）。
- XML パースに defusedxml を使用し XML ベースの攻撃に対応。
- ネットワーク取得時の受信サイズ制限と Gzip 解凍後の二次チェックによるリソース攻撃対策。

Performance & Reliability
- API 呼び出しに対するレート制限実装により J-Quants のレート上限（120 req/min）を順守。
- 再試行と指数バックオフで一時障害耐性を向上。
- DuckDB 側はバルク挿入・チャンク化・トランザクションまとめでオーバーヘッドを削減。
- 各保存処理は冪等性（ON CONFLICT DO UPDATE / DO NOTHING）を担保。

Breaking Changes
- 初回リリースのため該当なし。

Notes
- quality モジュールは参照されているが本リリースのソースには含まれていないため、品質チェックの詳細実装は今後の追加対象。
- strategy と execution パッケージは名前空間を用意済みだが、具体実装は未提供（将来の拡張対象）。
- ETL の各ジョブ（財務・カレンダー・ニュース ETL 等）については run_prices_etl をベースに同様の差分更新パターンで実装可能。

ライセンスやリリース手順、マイグレーション方針等は別途ドキュメントを参照してください。