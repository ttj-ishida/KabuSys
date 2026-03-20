# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株向けのデータ取得・ETL・特徴量生成・シグナル生成・監査・ニュース収集を備えた、研究〜運用向けの自動売買基盤コンポーネント群です。本リポジトリは以下の主要層を提供します：

- Data 層：J-Quants からの株価・財務・マーケットカレンダー取得、DuckDB スキーマ定義、ETL パイプライン
- Research 層：ファクター計算・特徴量探索ユーティリティ
- Strategy 層：特徴量正規化・シグナル生成
- Execution / Monitoring 層：発注・約定・ポジション・監査ログのスキーマ（実装は別途）
- News 集約：RSS からのニュース収集と銘柄紐付け

本 README ではプロジェクト概要、機能一覧、セットアップ手順、使い方（代表 API 例）、およびディレクトリ構成を日本語でまとめます。

## プロジェクト概要
- 目的：J-Quants API 等からデータを継続的に取得し、DuckDB に保存。研究で得られた生ファクターを正規化・統合して売買シグナルを生成し、発注・監査につなげられる基盤を提供します。
- 設計方針：
  - ルックアヘッドバイアスを防ぐ設計（target_date 時点のデータのみ使用）
  - 冪等性を重視（DB への保存は ON CONFLICT / トランザクションで原子操作）
  - 外部 API 呼び出しはデータ収集層に限定し、strategy 層は発注層に直接依存しない
  - ネットワーク安全性（RSS の SSRF 防止、gzip サイズ制限等）を考慮

## 機能一覧（主なモジュール）
- kabusys.config
  - .env / .env.local の自動読み込み（プロジェクトルートを探索）
  - 必須環境変数の取得ラッパー（ValueError を発生）
  - KABUSYS_ENV / LOG_LEVEL 等のシステム設定
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存メソッド、レート制御、リトライ、トークン自動リフレッシュ）
  - news_collector: RSS フィード取得、前処理、記事保存、銘柄抽出・紐付け（SSRF/サイズ制限/XML デフューズ対応）
  - schema: DuckDB のスキーマ定義と初期化（raw / processed / feature / execution 層）
  - pipeline: 日次 ETL（差分取得・保存・品質チェックフロー）、個別 ETL ジョブ（prices, financials, calendar）
  - calendar_management: market_calendar の管理、営業日判定ユーティリティ（next/prev/is_trading_day 等）
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.research
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、ファクターサマリー
- kabusys.strategy
  - feature_engineering.build_features: raw ファクターのマージ・ユニバースフィルタ・Z スコア正規化・features テーブルへの書き込み
  - signal_generator.generate_signals: features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを signals テーブルへ保存（Bear レジーム抑制・エグジット判定含む）
- kabusys.data.audit
  - 監査テーブル DDL（signal_events, order_requests, executions 等）と初期化方針

## 必要条件
- Python 3.10 以上（PEP 604 のユニオン型表記などを使用）
- 推奨依存パッケージ（少なくともこれらが必要）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API、RSS フィードなど）

（プロジェクトに pyproject.toml / requirements.txt がある場合はそちらに従ってください）

## 環境変数（主なキー）
以下は本コードベースで参照される主要な環境変数の一覧（.env に設定します）。

- JQUANTS_REFRESH_TOKEN        （必須）J-Quants のリフレッシュトークン
- KABU_API_PASSWORD           （必須）kabu API のパスワード
- KABU_API_BASE_URL           （任意）デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN             （必須）Slack 通知用トークン
- SLACK_CHANNEL_ID            （必須）通知先 Slack チャンネル ID
- DUCKDB_PATH                 （任意）デフォルト: data/kabusys.duckdb
- SQLITE_PATH                 （任意）デフォルト: data/monitoring.db
- KABUSYS_ENV                 （任意）development / paper_trading / live（デフォルト development）
- LOG_LEVEL                   （任意）DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD （任意）=1 にするとプロジェクト起点の .env 自動読み込みを無効化

注意：settings.jquants_refresh_token 等は未設定だと ValueError を発生させます。

## セットアップ手順（ローカル実行例）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - 最低限:
     ```
     pip install duckdb defusedxml
     ```
   - 開発用にパッケージをインストール可能な場合:
     ```
     pip install -e .
     ```
     （pyproject.toml / setup がある場合）

4. .env を作成
   プロジェクトルートに `.env` を置くと自動で読み込まれます（環境変数が未設定の場合のみセット）。例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   テスト時など自動読み込みを無効化する場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

5. DuckDB スキーマの初期化（Python REPL やスクリプトで）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

## 使い方（代表的な API・ワークフロー）

以下は対話的に実行できる最小例です（import パスはパッケージ化に依存します）。

1. データベース初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

2. 日次 ETL 実行（市場カレンダー・株価・財務の差分取得）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)   # target_date を渡すことも可能
   print(result.to_dict())
   ```

3. 特徴量の構築（features テーブルへの保存）
   ```python
   from datetime import date
   from kabusys.strategy import build_features

   cnt = build_features(conn, target_date=date(2024, 1, 31))
   print(f"inserted features: {cnt}")
   ```

4. シグナル生成（signals テーブルへの保存）
   ```python
   from datetime import date
   from kabusys.strategy import generate_signals

   total = generate_signals(conn, target_date=date(2024, 1, 31))
   print(f"signals generated: {total}")
   ```

5. RSS ニュース収集（raw_news, news_symbols へ保存）
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   ```

6. カレンダー更新ジョブ
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print(f"saved calendar rows: {saved}")
   ```

7. J-Quants からの個別取得（直接呼び出す場合）
   ```python
   from kabusys.data import jquants_client as jq
   rows = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   saved = jq.save_daily_quotes(conn, rows)
   ```

注意点：
- run_daily_etl は内部でカレンダーを先に更新し、営業日調整した上で株価/財務を取得します。
- jquants_client は API レート制限（120 req/min）とリトライ/トークン自動更新ロジックを内蔵しています。
- features / signals の処理は target_date 単位で日付ごとに置換（DELETE→INSERT）するため冪等です。

## 開発者向けの便利な仕組み・設計上の注意
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われ、テスト中は無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- DuckDB への接続は init_schema でスキーマ作成、以降は get_connection で既存 DB へ接続できます。
- NewsCollector は SSRF 対策・gzip サイズ制限・defusedxml を適用しています。
- Strategy 層は発注/Execution 層へ直接依存しないように設計されています（signals テーブルへ出力することで実行層に連携）。

## ディレクトリ構成（主要ファイル）
プロジェクトの主要パッケージ構成（src/kabusys の下）：

- src/kabusys/
  - __init__.py
  - config.py                           — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py                  — J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py                  — RSS 取得・前処理・保存・銘柄抽出
    - schema.py                          — DuckDB スキーマ定義と init_schema()
    - pipeline.py                        — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py             — market_calendar 管理・営業日ユーティリティ
    - features.py                         — zscore_normalize 再エクスポート
    - stats.py                            — 統計ユーティリティ（zscore_normalize）
    - audit.py                            — 監査ログ DDL（signal_events / order_requests / executions）
    - ...（その他 quality, etc. がある想定）
  - research/
    - __init__.py
    - factor_research.py                 — momentum/volatility/value 計算
    - feature_exploration.py             — 将来リターン/IC/summary utilities
  - strategy/
    - __init__.py
    - feature_engineering.py             — features テーブル構築
    - signal_generator.py                — signals 生成ロジック（BUY/SELL/エグジット）
  - execution/                            — 発注・実行に関する実装（空または別途実装）
  - monitoring/                           — 監視・メトリクス（将来的に追加）

（ファイル一覧は一部抜粋です。実際のリポジトリ全体は src 以下を参照してください）

## ログ・デバッグ
- settings.log_level でログレベルを制御できます（環境変数 LOG_LEVEL）。
- 大きなトランザクションを伴う DB 操作（ETL / features / signals 等）は内部で BEGIN/COMMIT を利用し、異常時は ROLLBACK を試みます。

## セキュリティ上の注意
- API トークンやパスワードは必ず .env / 環境変数で管理し、ソース管理に含めないでください。
- RSS フィード等の外部 URL は SSRF 対策（スキーム検査・プライベート IP 判定）を行っていますが、実稼働環境では更にネットワーク制御（プロキシ/ファイアウォール）を検討してください。
- DuckDB ファイルのパス（DUCKDB_PATH）や Slack トークンの取り扱いに注意してください。

## よくある操作のコマンド例
- duckdb スキーマを初期化して日次 ETL を実行する簡単なスクリプト例（run_etl.py）:
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  res = run_daily_etl(conn)
  print(res.to_dict())
  ```

- 特徴量作成からシグナル生成までを実行する（例）:
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features, generate_signals

  conn = get_connection("data/kabusys.duckdb")
  td = date.today()
  build_features(conn, td)
  generate_signals(conn, td)
  ```

## 貢献・ライセンス
- この README はコードベースの説明に特化しています。実際の貢献ポリシーやライセンスはリポジトリの LICENSE / CONTRIBUTING ドキュメントに従ってください。

---

何か特定の操作（テストデータ生成、CI 用のスクリプト、より詳しい ETL の設定方法、品質チェックモジュールの説明など）について README に追記を希望であれば、どのトピックを詳しく書くか教えてください。