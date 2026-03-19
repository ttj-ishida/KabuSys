README
=====

概要
----
KabuSys は日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants からマーケットデータや財務データ、RSS ニュースを収集して DuckDB に保存し、研究用ファクター計算、特徴量の正規化、戦略シグナル生成、監査ログや発注レイヤーのためのスキーマを備えています。  
設計上、ルックアヘッドバイアス防止や冪等性（IDempontent 保存）、API レート制御、堅牢なエラーハンドリングを重視しています。

主な特徴
--------
- データ収集
  - J-Quants API から株価（日足）・財務データ・市場カレンダーをページネーション対応で取得
  - RSS フィードからニュース収集（SSRF 対策・トラッキング除去・gzip 上限等の安全対策あり）
- ETL / Data Platform
  - 差分更新（最終取得日からの差分取得）とバックフィル対応
  - 品質チェック（欠損・スパイク等を検出する仕組み／quality モジュール）
- データ保存
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution 層）と初期化機能
  - 生データは ON CONFLICT を使った冪等保存
- 研究（Research）
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Spearman の ρ）やファクター統計サマリー
- 特徴量エンジニアリング
  - 生ファクターをユニバースフィルタ（株価・流動性）で絞り、Z スコア正規化・クリッピングして features テーブルへ保存
- 戦略シグナル生成
  - features と ai_scores を統合し、コンポーネントスコアを合成して BUY/SELL シグナルを生成
  - Bear レジーム抑制・ストップロス等のエグジット条件を実装
- 発注・監査
  - signal_queue / orders / executions / positions 等のテーブル定義、監査用テーブル群を提供
- Logging / 設定管理
  - 環境変数経由の設定（.env 読み込みの自動処理あり）
  - 環境 (development / paper_trading / live) とログレベル設定

必要なソフトウェア / 依存
------------------------
- Python 3.9+（typing の一部記法に依存）
- 推奨パッケージ（最小限）
  - duckdb
  - defusedxml
- 実運用では requests 等の追加パッケージや、Slack 連携用クライアントなどが必要になる場合があります。

セットアップ手順
----------------

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

3. パッケージのインストール（開発）
   - プロジェクトルートで:
     - pip install -e .

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env/.env.local を置くと自動で読み込まれます。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 読み込みの優先順位: OS 環境変数 > .env.local > .env

必須（主要）環境変数
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabu ステーション API パスワード（必須）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV : 実行環境 (development / paper_trading / live)（デフォルト: development）
- LOG_LEVEL : ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)（デフォルト: INFO）

使い方（簡単な例）
-----------------

※ 事前に上記必須環境変数を設定してください。

1) DuckDB スキーマの初期化
- Python REPL やスクリプトで:
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  conn = init_schema(settings.duckdb_path)
  # conn は duckdb.DuckDBPyConnection

2) 日次 ETL を実行（データ収集）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())

3) 特徴量の構築
  from kabusys.strategy import build_features
  from datetime import date
  n = build_features(conn, date(2024, 1, 1))
  print(f"features upserted: {n}")

4) シグナル生成
  from kabusys.strategy import generate_signals
  from datetime import date
  total_signals = generate_signals(conn, date.today())
  print(f"signals generated: {total_signals}")

5) ニュース収集ジョブ
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄抽出に使う有効銘柄コードのセット（任意）
  results = run_news_collection(conn, known_codes={"7203", "6758"})
  print(results)

6) J-Quants API を直接使ってデータ取得（テストやバックフィル時）
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  recs = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,12,31))
  # 保存: save_daily_quotes を使用

設定管理と自動 .env 読み込み
---------------------------
- パッケージは起動時にプロジェクトルートを探して .env/.env.local を自動読み込みします（OS 環境変数は上書きされません）。
- 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 必須設定が欠けている場合、kabusys.config.Settings のプロパティアクセス時に ValueError が発生します。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要モジュールと簡単な説明です。

- kabusys/
  - __init__.py                 — パッケージ定義（バージョン等）
  - config.py                   — 環境変数・設定管理（.env 自動読み込み、Settings）
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（取得/保存/リトライ/レート制御）
    - news_collector.py        — RSS ニュース収集・前処理・DB保存
    - schema.py                — DuckDB スキーマ定義と init_schema()
    - stats.py                 — Z スコア等の統計ユーティリティ
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - features.py              — data.stats の再エクスポート
    - calendar_management.py   — 市場カレンダー管理（営業日判定・更新ジョブ）
    - audit.py                 — 発注フローの監査ログスキーマ
    - (その他 quality 等モジュール想定)
  - research/
    - __init__.py
    - factor_research.py       — Momentum / Volatility / Value の計算
    - feature_exploration.py   — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py   — features テーブル作成（正規化・フィルタ）
    - signal_generator.py      — features と ai_scores からシグナル生成
  - execution/                  — 発注・実行層（空/拡張用）
  - monitoring/                 — 監視・メトリクス（空/拡張用）

設計上の注意点
--------------
- ルックアヘッドバイアスを防ぐため、各モジュールは target_date 時点のデータのみを参照する設計です。
- DuckDB に対する INSERT は可能な限り冪等にしており、ON CONFLICT を利用しています。
- J-Quants API はレート制限（120 req/min）に合わせたスロットリングとリトライ制御を行います。
- RSS 取得は SSRF/XML Bomb/サイズ制限などのセキュリティ対策を実装しています。

開発・テスト
------------
- 自動 .env 読み込みを無効にして単体テストを行う場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB のインメモリ接続は init_schema(":memory:") で使用可能です（テスト用途に便利）。

ライセンス / 貢献
-----------------
（プロジェクトのライセンス情報をここに追記してください）

問い合わせ
----------
問題の報告や改善提案は Issue を立ててください。ドキュメントや設計仕様（StrategyModel.md / DataPlatform.md / DataSchema.md 等）に基づいて実装されています。README に無い操作や内部仕様の確認が必要な場合は該当モジュールの docstring を参照してください。

以上。