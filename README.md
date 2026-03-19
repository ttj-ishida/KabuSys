KabuSys
======

日本株向けの自動売買プラットフォーム用ライブラリ（モジュール群）。
データ取得（J-Quants）、DuckDB を用いたデータ基盤、特徴量作成、戦略シグナル生成、ニュース収集、監査ログ等のユーティリティを含み、研究→本番までのワークフローをサポートします。

主な設計方針（要点）
- ルックアヘッドバイアス防止：各処理は target_date 時点の情報のみを使うよう設計。
- 冪等性：DB への挿入は ON CONFLICT/アップサートやトランザクションで原子性を保証。
- 安全性：API レート制御、トークン自動リフレッシュ、RSS の SSRF 防御、XML 脆弱性対策などを含む。
- 依存軽量化：可能な限り標準ライブラリで実装（ただし DuckDB・defusedxml 等の外部パッケージは必要）。

機能一覧
- 環境設定管理（kabusys.config）
  - .env / .env.local から自動で読み込み（プロジェクトルート検出、無効化可）
  - 必須環境変数のチェック
- データ取得（kabusys.data.jquants_client）
  - J‑Quants API から日足・財務・マーケットカレンダーを取得（ページネーション対応）
  - レートリミット、リトライ、401 自動リフレッシュ対応
- データ基盤（kabusys.data.schema）
  - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - init_schema()/get_connection() を提供
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（backfill を含む）、保存、品質チェックの実行（run_daily_etl）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、raw_news への冪等保存、銘柄コード抽出（SSRF対策・XML対策あり）
- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - 研究で得られた生ファクターを正規化・フィルタし features テーブルへ保存（build_features）
- シグナル生成（kabusys.strategy.signal_generator）
  - features / ai_scores 等を統合して final_score を計算し BUY/SELL シグナルを生成（generate_signals）
  - Bear レジーム検知、売り（エグジット）ルール（ストップロス等）を実装
- 統計ユーティリティ（kabusys.data.stats）
  - クロスセクション Z スコア正規化など
- 監査ログ（kabusys.data.audit）
  - signal → order → execution のトレース用テーブル定義（監査・冪等設計）

動作要件（概略）
- Python >= 3.10（| 型ヒント等の構文を使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- J‑Quants API の利用にはリフレッシュトークンが必要

セットアップ手順（ローカル / 開発環境向け）
1. リポジトリをクローン
   - git clone ... (プロジェクトルートに .git / pyproject.toml があると自動で .env を読込みます)

2. 仮想環境作成・依存インストール
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -r requirements.txt
     （requirements.txt がない場合は最低限 duckdb, defusedxml をインストール）

3. 環境変数設定
   - プロジェクトルートに .env を置く（.env.local は上書き用）
   - 主な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須) — J‑Quants のリフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN (必須) — Slack 通知用トークン（利用する場合）
     - SLACK_CHANNEL_ID (必須) — Slack チャネル ID
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/…（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると自動 .env ロードを無効化

   - .env の自動読み込みは、KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することで無効化できます。

4. DuckDB スキーマ初期化
   - Python REPL / スクリプトで:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - またはインメモリでテスト:
     conn = init_schema(":memory:")

基本的な使い方（コード例）
- 日次 ETL（市場カレンダー取得 → 株価/財務データ 差分取得 → 品質チェック）
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- 特徴量作成（features テーブル更新）
  from datetime import date
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.strategy import build_features

  conn = init_schema("data/kabusys.duckdb")
  cnt = build_features(conn, target_date=date.today())
  print(f"features upserted: {cnt}")

- シグナル生成（signals テーブル更新）
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.strategy import generate_signals

  conn = init_schema("data/kabusys.duckdb")
  total_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"generated signals: {total_signals}")

- ニュース収集ジョブ（RSS 収集と保存）
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = init_schema("data/kabusys.duckdb")
  result = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(result)

注意・運用メモ
- ETL やシグナル生成は本番口座に発注を行う層（execution）と直接つながらないよう設計されています。発注部分は execution 層で別途実装する想定です。
- self-contained なテストのために KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして自動 .env 読み込みを抑制できます。
- DuckDB のファイルパスは settings.duckdb_path（環境変数 DUCKDB_PATH）で制御。
- J‑Quants API のレート・エラー処理は jquants_client に実装されていますが、API 利用量には注意してください（デフォルト 120 req/min）。

ディレクトリ構成（主要ファイルの説明）
- src/kabusys/
  - __init__.py — パッケージ定義（version など）
  - config.py — 環境変数、設定取得（settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py — J‑Quants API クライアント（取得・保存ユーティリティ）
    - schema.py — DuckDB スキーマ定義・初期化（init_schema）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - news_collector.py — RSS 取得・前処理・raw_news 保存、銘柄抽出
    - calendar_management.py — 市場カレンダー管理ユーティリティ（営業日判定等）
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - features.py — features 公開インターフェース（zscore 再エクスポート）
    - audit.py — 監査ログ用テーブル定義
    - (その他：quality モジュール等が想定される)
  - research/
    - __init__.py — 研究用ユーティリティの公開
    - factor_research.py — momentum/volatility/value の計算
    - feature_exploration.py — 将来リターン、IC、統計サマリの計算
  - strategy/
    - __init__.py — build_features / generate_signals を公開
    - feature_engineering.py — 生ファクターの統合・正規化・features テーブルへの保存
    - signal_generator.py — final_score 計算、BUY/SELL の生成、signals テーブルへの書込
  - execution/ — 発注ロジックはここに実装する想定（現状モジュールは空）
  - monitoring/ — 監視・モニタリング用実装（必要に応じ追加）

ライセンス・貢献
- 本 README ではライセンスファイル・貢献ガイドは含めていません。リポジトリに LICENSE / CONTRIBUTING.md を置き運用してください。

最後に
- この README はコード中のドキュメンテーションコメント（docstring）に基づき作成しました。実際の運用や拡張時には、品質チェックモジュール（quality）や execution 層の実装、テストケース・CI を追加することを推奨します。必要であれば、README に実行例スクリプトや運用フロー（cron/airflow など）サンプルを追加します。