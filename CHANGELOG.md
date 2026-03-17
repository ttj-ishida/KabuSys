Keep a Changelog
=================

すべての注目すべき変更を時系列で記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

[0.1.0] - 2026-03-17
-------------------

Added
- 初期リリース: KabuSys — 日本株自動売買システムの基盤機能群を追加。
  - パッケージエントリポイント（src/kabusys/__init__.py）を追加し、公開モジュールを明示（data, strategy, execution, monitoring）。パッケージバージョンは 0.1.0。
- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。プロジェクトルートの検出は .git または pyproject.toml を基準に行い、配布後も動作する設計。
  - .env と .env.local の読み込み優先度を実装（OS環境変数は保護）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env 行のパース処理を実装（export 形式、クォート・エスケープ、インラインコメント等に対応）。
  - Settings クラスを提供し、必須設定の取得（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）や各種既定値（KABU_API_BASE_URL、DBパス等）、値検証（KABUSYS_ENV / LOG_LEVEL）を行うユーティリティを追加。
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務データ（四半期BS/PL）、市場カレンダーの取得機能を実装（ページネーション対応）。
  - RateLimiter による固定間隔スロットリング（デフォルト 120 req/min）を実装。
  - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx を対象）を実装。429 に対しては Retry-After を尊重。
  - 401 Unauthorized を検出した場合の自動トークンリフレッシュを 1 回行う仕組みを実装（無限再帰を防止）。
  - ページネーション間で共有するモジュールレベルの ID トークンキャッシュを実装。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE により冪等性を保証。
  - データ取り込み時に fetched_at を UTC で記録してデータ取得時点をトレース可能に。
  - 型変換ユーティリティ（_to_float, _to_int）を実装し、不正値へ安全に対処。
- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからのニュース取得、前処理、DuckDB への冪等保存（raw_news）および銘柄紐付け（news_symbols）を実装。
  - セキュリティ設計: defusedxml を用いた XML パース、SSRF 対策（リダイレクト検査・プライベートホスト検出）、HTTP スキーム検証（http/https のみ）、受信サイズ上限（MAX_RESPONSE_BYTES=10MB）や gzip 解凍後のサイズ検査を実装。
  - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）と、それに基づく記事ID（SHA-256 の先頭32文字）生成で冪等性を担保。
  - テキスト前処理（URL 除去・空白正規化）、銘柄コード抽出（4桁数字マッチ・既知コードフィルタ）を実装。
  - DB への一括挿入はチャンク化とトランザクションで行い、INSERT ... RETURNING から実際に追加された行を正確に返す。
  - run_news_collection による統合収集ジョブを提供（各ソースは独立して例外処理し、1 ソース失敗で他ソースへ影響を与えない）。
- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の各レイヤーに対応するテーブル定義を追加（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 各カラムに制約（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY）を付与してデータ整合性を担保。
  - よく使うクエリ向けのインデックス群を定義。
  - init_schema(db_path) による初期化関数を提供（ディレクトリ自動作成、DDL の冪等実行）。get_connection() で既存 DB へ接続可能。
- ETL パイプライン基盤（src/kabusys/data/pipeline.py）
  - 差分取得とバックフィル戦略（デフォルト backfill_days=3）をサポートする ETL ヘルパーを実装。
  - ETLResult dataclass を導入し、取得件数、保存件数、品質チェック結果、エラーの集約を可能に。
  - 市場カレンダーの調整ヘルパー（非営業日の補正）、テーブル存在チェック、最終取得日の取得ユーティリティなどを実装。
  - run_prices_etl の差分更新フローを実装（最終取得日に基づく date_from 自動算出、J-Quants からの取得 → 保存 の流れ）。
- その他
  - モジュールレベルのロギング呼び出しを導入（各処理の進捗や警告を出力）。
  - 型アノテーションとドキュメンテーション（関数/クラス docstring）を充実させ、テストや保守性を向上。

Security
- news_collector:
  - defusedxml の使用による XML 関連攻撃対策。
  - SSRF 対策: リダイレクト時のスキーム検査・プライベートアドレス検査、初期 URL のプライベートホスト検証。
  - レスポンス長の上限検査（gzip 解凍後も確認）によりメモリ DoS を軽減。
- jquants_client:
  - 認証トークンの安全なリフレッシュとキャッシュ制御により誤った再帰を防止。

Configuration / Requirements
- 必須環境変数（Settings で _require される）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- 既定値:
  - KABU_API_BASE_URL: "http://localhost:18080/kabusapi"
  - DUCKDB_PATH: "data/kabusys.duckdb"
  - SQLITE_PATH: "data/monitoring.db"
  - KABUSYS_ENV の有効値: "development", "paper_trading", "live"
  - LOG_LEVEL の有効値: "DEBUG","INFO","WARNING","ERROR","CRITICAL"

Notes / Implementation details
- J-Quants API クライアントは 120 req/min のレート制限を想定したスロットリングを行うため、短時間に多数の要求を発生させる処理は意図した遅延を伴います。
- データ保存は基本的に冪等（ON CONFLICT DO UPDATE/DO NOTHING）を前提とし、再実行に耐える設計です。
- news_collector の記事IDは正規化後の URL を用いて生成するため、トラッキングパラメータの違い等による重複登録を防ぎます。
- ETL パイプラインは品質チェックモジュール（kabusys.data.quality）を利用する想定だが、本リリースでは品質チェックの呼び出し箇所は実行継続方針（重大度によらず収集継続）を採用。

Known issues / TODO
- パイプラインモジュールは完結したジョブ群（例えば価格・財務・カレンダーをまとめて実行する上位関数やスケジューリング）は今後整備予定。
- strategy, execution, monitoring パッケージの具体実装はスケルトン化されており、本リリースでは主要ロジックは data 層中心。
- 単体テスト・結合テストの追加（特にネットワーク周りのモックと DB 正常系/異常系テスト）は引き続き強化予定。

----- 

このリリースはシステム基盤（データ取得・保存・ETL）の初期実装を中心としたものです。今後、戦略（strategy）、発注/実行（execution）、監視（monitoring）機能の実装・拡張や、品質チェックのルール強化、運用上のドキュメント整備を行っていく予定です。