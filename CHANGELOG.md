# Changelog

すべての非互換性のある変更はメジャー番号を上げることで示します。
このファイルは Keep a Changelog の形式に準拠します。

/ [Unreleased]
- （今後のリリースに向けた未公開の変更点をここに記載）

[0.1.0] - 2026-03-17
—————————
最初の公開リリース。日本株自動売買プラットフォームのコア機能を実装しました。

Added
- パッケージ初期化
  - kabusys パッケージの基本設定（src/kabusys/__init__.py）。バージョン 0.1.0 を設定。
- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルートの自動検出（.git または pyproject.toml）に基づく .env/.env.local のロード順序を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加。
  - export KEY=val 形式やクォート文字列、インラインコメントの扱いに対応した .env パーサを実装。
  - 必須設定を取得して未設定時に例外を投げる _require と、settings オブジェクトを公開。
  - 環境（development/paper_trading/live）やログレベルなどの検証ロジックを実装。
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日次株価（OHLCV）、四半期財務データ、マーケットカレンダー取得用 API 呼び出し関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）を実装。ページネーション対応。
  - レートリミッタ（120 req/min）による固定間隔スロットリングを実装。
  - リトライ（指数バックオフ、最大3回）とステータスコードによる再試行判定（408/429/5xx）。
  - 401 Unauthorized を受けた際にリフレッシュトークンで id_token を自動更新して1回リトライする処理を実装。
  - id_token 取得用の get_id_token（/token/auth_refresh への POST）を実装。
  - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE による上書きで重複排除。
  - データ取り込み時の fetched_at（UTC）記録、NULL/不正値の安全な数値変換ユーティリティ（_to_float / _to_int）を提供。
- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し、raw_news と news_symbols に保存する一連の機能を実装。
  - URL 正規化（トラッキングパラメータ除去、クエリ整列、フラグメント除去）と SHA-256 を使った記事ID生成（先頭32文字）を導入し冪等性を確保。
  - defusedxml を用いた XML パースで XML Bomb 等の攻撃を防止。
  - SSRF 対策：HTTP リダイレクト時のスキーム検証、ホストがプライベート IP（ループバック/リンクローカル/プライベート/マルチキャスト）かの検査、スキームは http/https のみ許可。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズチェックを導入しメモリDoS対策を実装。
  - RSS 取得（fetch_rss）、記事保存（save_raw_news: INSERT ... RETURNING を用いて実際に挿入されたIDを返す）、記事と銘柄の紐付け保存（save_news_symbols / _save_news_symbols_bulk）を実装。トランザクション処理とエラーロールバックを実装。
  - テキスト前処理（URL除去、空白正規化）と、本文からの銘柄コード抽出（4桁数字・known_codes フィルタ）を実装。
  - デフォルト RSS ソースに Yahoo!Finance のビジネスカテゴリを設定（DEFAULT_RSS_SOURCES）。
  - 統合収集ジョブ run_news_collection を実装（各ソース独立ハンドリング、挿入された新規記事数を集計）。
- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の多層スキーマを実装。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw レイヤー。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols を含む Processed レイヤー。
  - features, ai_scores を含む Feature レイヤー。
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance を含む Execution レイヤー。
  - 頻出クエリ向けのインデックスを複数定義（code/date、status など）。
  - init_schema(db_path) による自動ディレクトリ作成と全DDL実行、get_connection を提供。
- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新に基づく ETL ワークフロー支援（最終取得日の判定、差分取得の自動算出）。
  - backfill_days（デフォルト 3 日）に基づく後出し修正吸収ロジック。
  - 市場カレンダー先読み（_CALENDAR_LOOKAHEAD_DAYS = 90）等の定数。
  - ETL 実行結果を表す ETLResult dataclass（品質問題・エラーの集約）を実装。
  - テーブル存在チェック、最大日付取得ユーティリティ、営業日調整ロジックを実装。
  - run_prices_etl（差分取得→保存）などの個別ジョブ処理の骨格を実装（fetch/save を呼ぶ流れを確立）。
- パッケージ構成
  - data, strategy, execution, monitoring を __all__ で公開（各サブパッケージの雛形を整備）。

Security
- SSRF 対策と XML パースの安全化（defusedxml）をニュース収集に導入。
- 外部に公開するトークン等の自動上書きを防ぐため .env ロード時に OS 環境変数を保護（protected set）。

Notes / Migration
- 初回利用時は init_schema(db_path) を呼んで DuckDB のスキーマを作成してください。
- .env ファイルの自動読み込みはデフォルトで有効です。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants の refresh token、Slack トークンなど必須環境変数は settings オブジェクト経由で取得します。未設定時は ValueError が発生します。
- news_collector の extract_stock_codes は known_codes（有効銘柄コード集合）を参照して抽出するため、紐付けを有効にするには known_codes を提供してください。

Acknowledgements / Implementation details
- API リクエストは urllib を用いて実装。レート制御は単純な固定間隔（スロットリング）で実装されているため、将来的にトークンバケット等への置換を検討してください。
- DuckDB に対する複数行 INSERT はプレースホルダとチャンク処理で行い、トランザクションで整合性を保っています。

今後の予定（例）
- strategy / execution モジュールの具体的な戦略実装および発注ロジックの追加
- 品質チェックモジュール（quality）の本格実装と ETL への統合強化
- テストカバレッジの追加（ネットワーク、DB、Edge case）
- 非同期処理や並列化による性能改善

------------------------------------------------------------
（注）本 CHANGELOG はソースコードからの推測に基づき作成しています。実際のコミット履歴や変更履歴が存在する場合はそちらを優先してください。