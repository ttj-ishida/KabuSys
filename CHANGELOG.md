# Changelog

すべての notable な変更点を記録します。This project adheres to "Keep a Changelog" のフォーマットを想定しています。

フォーマット:
- すべての変更はバージョンごとに分類されています。
- 日付はリリース日を示します。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システムの基盤となる設定管理、データ取得・保存、ニュース収集、ETLパイプライン、DuckDBスキーマを実装。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョンを `0.1.0` に設定（src/kabusys/__init__.py）。
  - public API モジュールのエクスポート (`data`, `strategy`, `execution`, `monitoring`) を定義。

- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダ実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env と .env.local の読み込み優先順位を実装。OS 環境変数を保護するための protected set を利用した上書き制御を実現。
  - 行パーサ `_parse_env_line`：export プレフィックス対応、クォート文字列内のエスケープ処理、インラインコメント処理等に対応。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用途）。
  - 必須環境変数取得用ヘルパ `_require` と Settings クラスを提供（J-Quants・kabuステーション・Slack・DB パス・環境種別・ログレベル等）。
  - KABUSYS_ENV / LOG_LEVEL の値検証ロジックを追加（許容値のチェック）。

- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - API 基本URL、レート制限（120 req/min）に基づく固定間隔レートリミッタ実装（_RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx のリトライ対象）。
  - 401 Unauthorized を検出した場合の自動トークンリフレッシュ（get_id_token）と 1 回限定の再試行。
  - ID トークンのモジュール内キャッシュ（ページネーション間で共有）と明示的 force_refresh 。
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar：ページネーション対応の取得関数を実装。
  - DuckDB へ冪等に保存する save_daily_quotes / save_financial_statements / save_market_calendar を実装（ON CONFLICT DO UPDATE）。
  - 型変換ユーティリティ `_to_float`, `_to_int` を実装（安全な None ハンドリングや小数丸め回避）。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し raw_news, news_symbols に保存する包括的モジュールを実装。
  - セキュリティ対策：
    - defusedxml を用いた XML パース（XML Bomb 等対策）。
    - SSRF 対策（URL スキーム検証、プライベート/ループバック/リンクローカル IP 検出、リダイレクト先検査を行うカスタムリダイレクトハンドラ）。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10 MB、Gzip 解凍後も検査）。
    - 許可スキームは http/https のみ。
  - URL 正規化とトラッキングパラメータ除去（utm_ 等のプレフィックス削除）を行い、記事ID を正規化 URL の SHA-256（先頭32文字）で生成。
  - テキスト前処理（URL 除去、空白正規化）。
  - fetch_rss：gzip 対応、Content-Length チェック、XML レスポンスのフォールバック処理（名前空間や非標準レイアウト）。
  - DB 保存：
    - save_raw_news：チャンク分割、トランザクション、INSERT ... ON CONFLICT DO NOTHING RETURNING id による新規挿入ID取得。
    - save_news_symbols / _save_news_symbols_bulk：一括で news_symbols を保存（重複除去、チャンク、トランザクション、RETURNING により正確な挿入数取得）。
  - 銘柄コード抽出ロジック（4桁数字、重複排除、既知コードフィルタ）extract_stock_codes。
  - run_news_collection：複数 RSS ソースを独立して処理し、記事保存と銘柄紐付けを行う（ソース単位でエラーハンドリング）。

- DuckDB スキーマ（src/kabusys/data/schema.py）
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature / Execution）をカバーするテーブル定義を実装。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw 層。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols を含む Processed 層。
  - features, ai_scores を含む Feature 層。
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance を含む Execution 層。
  - 各種制約 (PRIMARY KEY, CHECK, FOREIGN KEY) と適切な DECIMAL/BIGINT/BOOLEAN 型付け。
  - 頻出クエリ向けのインデックス定義（複数）。
  - init_schema(db_path): 親ディレクトリ自動作成、全 DDL とインデックスを順次実行して冪等に初期化。
  - get_connection(db_path): 既存 DB 接続を返すユーティリティ。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新を行う ETL の骨組みを実装。
  - ETLResult dataclass：取得・保存件数、品質問題（quality.QualityIssue 想定）、エラー一覧などを保持。to_dict によりログ用に変換可能。
  - 差分取得ヘルパ（_get_max_date, _table_exists）と市場カレンダーを用いた営業日調整（_adjust_to_trading_day）。
  - get_last_price_date / get_last_financial_date / get_last_calendar_date ヘルパ。
  - run_prices_etl（差分更新、backfill_days の導入、最小取得日 _MIN_DATA_DATE の定義）を実装（fetch -> save の流れ）。
  - 設計として、品質チェックは ETL を止めない（エラーを集約して戻す）方針。

### Security
- defusedxml を用いた XML パースにより XML 関連の脆弱性を軽減。
- RSS 取得時の SSRF 対策を多数実装（スキーム検証、ホストのプライベート判定、リダイレクト時検査）。
- .env 読み込み時に OS 環境変数を保護する protected セットを導入。
- URL 正規化によりトラッキングパラメータを除去し、ID 生成や重複判定の精度向上。

### Performance / Reliability
- J-Quants API に対するレート制限（固定間隔）を実装し、120 req/min を厳守。
- ネットワークリトライ（指数バックオフ）を導入し一時障害への耐性を向上。
- DuckDB への大量挿入はチャンク化してトランザクションで処理（news_collector）。
- save_* 系は冪等に設計（ON CONFLICT DO UPDATE / DO NOTHING）。

### Testing / Developer conveniences
- KABUSYS_DISABLE_AUTO_ENV_LOAD による自動 .env 読み込み無効化（テストでの環境制御に便利）。
- jquants_client の id_token を引数経由で注入可能（テスト容易性）。
- news_collector の _urlopen はモック差替え可能（テストでのネットワーク依存を排除）。

### Internal / Refactor notes
- 設計ドキュメント（DataPlatform.md / DataSchema.md）に基づいた実装注記をコード内ドキュメントとして記載。
- 各モジュールで詳細なログ出力（info/warning/exception）を行い、運用時のトラブルシュートを支援。

### Known limitations / TODO
- quality モジュール（品質チェック）の実装は外部依存（pipeline が参照）であり、本リリースでは quality の具体実装は含まれている前提。
- pipeline.run_prices_etl の戻り値の末尾にカンマで中途になっている箇所（コード切出しの関係で未完のように見える部分）があるため、呼び出し側との整合確認が必要（実装本体が続く想定）。
- strategy / execution / monitoring のパッケージ初期化ファイルは存在するが、各機能の具体実装は本バージョンで提供されていない（将来追加予定）。

## Notes
- 本 CHANGELOG はソースコードから推測して作成したものであり、リリース手順や付随する外部ドキュメント（README、設計書等）に基づく差分は含まれていません。
- 重大な設計変更や互換性の破壊的変更は次回以降のリリースで明確に記載してください。