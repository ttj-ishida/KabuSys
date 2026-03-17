# CHANGELOG

すべての注目すべき変更点をここに記録します。本ファイルは Keep a Changelog の形式に準拠しています。

0.1.0（2026-03-17）
------------------

Added
- 初回リリース: KabuSys — 日本株自動売買支援ライブラリ。
- パッケージ初期化:
  - パッケージバージョンを `0.1.0` として公開（src/kabusys/__init__.py）。
  - 公開サブパッケージ: data, strategy, execution, monitoring。
- 環境設定管理（src/kabusys/config.py）:
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサーは `export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理に対応。
  - OS 環境変数の上書きを制御する protected 機能を実装（.env.local は既存の OS 環境変数を上書きしない）。
  - Settings クラスを提供し、必要な環境変数をプロパティ経由で取得（J-Quants, kabu API, Slack, DBパス等）。KABUSYS_ENV / LOG_LEVEL の妥当性検証、is_live / is_paper / is_dev 補助プロパティを実装。
- J-Quants データ取得クライアント（src/kabusys/data/jquants_client.py）:
  - 日次株価、財務（四半期BS/PL）、マーケットカレンダーの取得機能を実装。
  - API レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）を導入。
  - リトライロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx およびネットワークエラーに対応）。
  - 401 受信時の自動トークンリフレッシュ（最大1回）とモジュールレベルの ID トークンキャッシュ実装。
  - ページネーション対応（pagination_key）で全ページを取得。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は冪等性を保つため ON CONFLICT DO UPDATE を利用。fetched_at を UTC ISO 形式（Z）で記録。
  - 値変換ユーティリティ（_to_float / _to_int）で不正値や小数誤変換を安全に扱う。
- ニュース収集モジュール（src/kabusys/data/news_collector.py）:
  - RSS フィードから記事を収集 → 前処理 → DuckDB の raw_news に冪等保存するパイプラインを実装。
  - defusedxml を用いた安全な XML パースで XML Bomb 等を軽減。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - ホストがプライベート/ループバック/リンクローカル/IP マルチキャストでないかをチェック（IP直解析と DNS 解決による検証）。
    - リダイレクト時に先行検査するカスタム HTTPRedirectHandler を導入。
  - レスポンスサイズ制限（既定 10 MB）と gzip 解凍後サイズ検査を導入しメモリ DoS を防止。
  - URL 正規化（スキーム・ホスト小文字化、追跡用パラメータ（utm_* 等）削除、フラグメント削除、クエリキーソート）。
  - 記事IDは正規化 URL の SHA-256 の先頭32文字で生成し冪等性を担保。
  - テキスト前処理（URL 除去、空白正規化）。
  - DB 保存ロジックはチャンク化された INSERT ... RETURNING を行い、実際に挿入された記事IDを返す。トランザクションでまとめてコミット/ロールバック。
  - 銘柄コード抽出ユーティリティ（4桁数字候補から known_codes に含まれるものを返す）。
  - run_news_collection により複数ソースの収集を統括（個別ソースは独立してエラー処理）。
- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）:
  - Raw / Processed / Feature / Execution 層にわたるテーブル定義を用意（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
  - カラム制約（NOT NULL, CHECK, PRIMARY/FOREIGN KEY）を多く設定しデータ整合性を向上。
  - 頻出クエリ向けのインデックス群を作成。
  - init_schema(db_path) により親ディレクトリ自動作成 → DDL 実行 → インデックス作成 → DuckDB 接続を返す。
  - get_connection(db_path) で既存 DB への接続を返す（スキーマ初期化は行わない）。
- ETL パイプライン骨格（src/kabusys/data/pipeline.py）:
  - 差分更新を行う ETL 戦略（最終取得日から backfill_days 日分を再取得して後出し修正を吸収）。
  - ETLResult データクラス（target_date, fetched/saved カウント、品質問題リスト、エラーリスト）を実装。品質問題は辞書化可能。
  - テーブル存在チェック、最大日付取得ユーティリティ、取引日調整ヘルパーを実装。
  - run_prices_etl: 差分取得ロジック（date_from 自動算出、最小データ開始日考慮）、J-Quants から取得して保存する流れを用意。
- ロギング: 各主要処理で情報・警告・例外ログを出力するよう実装。

Security
- RSS パースに defusedxml を使用、SSRF 対策、レスポンスサイズチェック、gzip 解凍後検査など多層の防御を実装。
- .env の読み込みでは OS 環境変数を保護する仕組みを採用。

Fixed
- （初回リリースのため該当なし）

Changed / Deprecated / Removed
- （初回リリースのため該当なし）

Notes / Known issues
- run_prices_etl の戻り値処理に不整合の痕跡（コード断片が途中で切れているように見える箇所）が存在します。期待される戻り値は (fetched_count, saved_count) のタプルですが、実装の最終確認・ユニットテストを推奨します。
- strategy / execution / monitoring パッケージは public API としてエクスポートされているものの、今回のコードスナップショットではモジュール本体が空のイニシャライザ（__init__.py）が含まれており、戦略実装・発注実装は今後の実装対象です。

参考
- .env 自動読み込みはプロジェクトルート検出に .git または pyproject.toml を使用するため、配布・インストール後の実行環境では環境変数の供給方法に注意してください。
- DuckDB スキーマは多くの外部キー・制約を含みます。既存データとのマイグレーション時は順序や制約違反に注意してください。

今後の予定（例）
- strategy / execution の実装（発注ループ、kabuステーション API 統合）
- 品質チェックモジュール（quality）の実装・テスト強化
- 単体テスト・統合テストの追加（ネットワーク操作・DB 操作のモック化）
- CI による安全性・静的解析の導入

-----