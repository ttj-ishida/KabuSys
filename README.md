# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリ群です。J-Quants からのデータ取得（株価・財務・カレンダー） / DuckDB ベースの ETL / ニュースの NLP スコアリング（OpenAI） / 市場レジーム判定 / 研究用ファクター計算 / 監査ログ（発注〜約定追跡）等のユーティリティを提供します。

特徴（設計方針の抜粋）
- Look-ahead バイアスを避ける設計（ほとんどの関数は target_date を明示的に受け取り、内部で datetime.now() を参照しない）
- DuckDB を用いたローカルデータレイク形式の保存と効率的な SQL 処理
- J-Quants API のページネーション / レート制御 / トークンリフレッシュ対応
- OpenAI（gpt-4o-mini）を用いた JSON モードでのニュースセンチメント評価（リトライ・フォールバック機構あり）
- ニュース収集は SSRF 対策・トラッキングパラメータ除去・受信サイズ制限を実装
- 監査ログ（signal → order_request → execution）のスキーマと初期化ユーティリティ

主な機能一覧
- Data ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）：fetch/save 系
  - データ品質チェック（kabusys.data.quality）
  - カレンダー管理（kabusys.data.calendar_management）
- ニュース関連 / AI
  - RSS ニュース取得・保存（kabusys.data.news_collector）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp: score_news）
  - 市場レジーム判定（kabusys.ai.regime_detector: score_regime）
- 研究用
  - ファクター計算（kabusys.research.factor_research）
  - 特徴量解析ユーティリティ（kabusys.research.feature_exploration）
  - 統計ユーティリティ（kabusys.data.stats: zscore_normalize）
- 監査ログ
  - 監査スキーマ初期化（kabusys.data.audit.init_audit_schema / init_audit_db）

セットアップ手順（ローカル開発向け）
1. Python（推奨 3.10+）を用意する。
2. 依存パッケージをインストール（最低限の推奨）
   - duckdb
   - openai
   - defusedxml
   - その他標準ライブラリで実装されているため追加は最小限です。
   例:
   ```
   pip install duckdb openai defusedxml
   ```
3. 環境変数 / .env を準備する
   - プロジェクトルートに `.env` または `.env.local` を置くと自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu ステーション向けパスワード（発注関連）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot Token
     - SLACK_CHANNEL_ID: Slack チャンネル ID
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime の引数で上書き可能）
   - 任意 / デフォルト値
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると自動 .env 読み込みを無効化
     - KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db
   - 例 .env（簡易）
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxx
     OPENAI_API_KEY=sk-....
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```
4. データベース親ディレクトリの作成（必要に応じて）
   - DuckDB の保存先はデフォルト `data/kabusys.duckdb`。親ディレクトリがなければ自動生成するユーティリティがありますが事前に作ることもできます。
5. （任意）OpenAI と J-Quants の API キー確認

基本的な使い方（Python から呼び出す例）
- DuckDB 接続の作成と日次 ETL 実行
  ```
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect('data/kabusys.duckdb')
  result = run_daily_etl(conn, target_date=None)  # target_date=None で今日
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（ai_scores への書込み）
  ```
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect('data/kabusys.duckdb')
  n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None は env を参照
  print('scored', n)
  ```

- 市場レジーム判定
  ```
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect('data/kabusys.duckdb')
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ用 DuckDB 初期化（監査専用 DB）
  ```
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db('data/kabusys_audit.duckdb')
  # これで signal_events / order_requests / executions テーブルが作成されます
  ```

重要な実装上の注意点
- OpenAI 呼び出しは JSON モードを前提に厳密な JSON を期待していますが、API の不安定時にはパース失敗をフォールバック（0.0 やスキップ）します。テストでは内部の _call_openai_api をモックできます。
- ETL / 保存関数は冪等（ON CONFLICT DO UPDATE / ON CONFLICT DO NOTHING）を意識して設計されています。
- 多くの処理は target_date を引数で受け取り、内部で現在時刻を参照しないようになっています（バックテストでの Look-ahead 防止）。
- news_collector は RSS フィードから記事を取得する際に SSRF 対策・サイズ制限・トラッキング除去などを行います。

ディレクトリ構成（概略）
- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数の自動読み込み / Settings オブジェクト
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py — ニュースの LLM ベースのセンチメント評価（score_news）
  - regime_detector.py — ETF（1321）MA とマクロニュースを合成して市場レジームを評価（score_regime）
- src/kabusys/data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch / save / auth / rate limit）
  - pipeline.py — ETL パイプライン（run_daily_etl 他）
  - etl.py — ETL 用の公開インターフェース（ETLResult の再エクスポート）
  - news_collector.py — RSS 取得・正規化・raw_news 保存ロジック
  - calendar_management.py — 市場カレンダー管理 / 営業日判定ユーティリティ
  - quality.py — データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - audit.py — 監査ログ（signal / order_request / execution）DDL と初期化ユーティリティ
- src/kabusys/research/
  - __init__.py
  - factor_research.py — momentum/volatility/value 等のファクター計算
  - feature_exploration.py — forward returns / IC / summary / rank
- その他補助モジュール（logging などは標準ロガーを利用）

開発・運用上のヒント
- 自動 .env 読み込みはプロジェクトルートを .git または pyproject.toml の位置から推定して行います。CI テストなどで読み込みを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のファイルパスや SQLite パスは Settings から取得できます。テスト時は ":memory:" を利用するか、別パスを指定してください。
- OpenAI 呼び出しはコストとレイテンシを考慮してバッチ化・チャンク化されていますが、API キー／モデルの制約にご注意ください（gpt-4o-mini を使用）。
- J-Quants API はレート上限（120 req/min）に合わせた内部 RateLimiter を備えていますが、大量取得のスケジュールは慎重に設計してください。

ライセンス / 責任範囲
- 本リポジトリはデータ取得・解析・戦略構築を支援するツール群を提供します。実運用での売買・リスク管理は利用者の責任で行ってください。実際の発注に関わる部分（kabu ステーション等）の設定・認証は慎重に管理してください。

この README で扱っていない詳細（スキーマ定義、各関数の細かい挙動、パラメータの意味など）はソースの docstring を参照してください。必要があれば、具体的な利用シナリオ（例: バックテスト環境でのデータ初期化手順、定期ジョブの cron サンプル）も追記できます。希望があれば教えてください。