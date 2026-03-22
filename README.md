KabuSys
=======

KabuSys は日本株向けの自動売買プラットフォームの核となるライブラリ群です。データ取得・ETL、ファクター計算、特徴量生成、シグナル生成、バックテスト、ニュース収集、バックテスト用シミュレーターなど、アルゴリズム運用に必要な主要機能を含みます。

この README はソースコード（src/kabusys 以下）に基づく概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

プロジェクト概要
----------------
- 目的：J-Quants 等から市場データを取り込み、特徴量を作成して戦略シグナルを生成し、バックテスト／実運用のための基盤を提供します。
- デザイン方針：ルックアヘッドバイアス回避、冪等性（DB 保存は ON CONFLICT/DO UPDATE 等で上書き可能）、テスト容易性（id_token 注入等）、外部依存最小化（多くは標準ライブラリで実装）を重視。

主な機能一覧
-------------
- 環境設定管理（kabusys.config）
  - .env/.env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得と検証（例: JQUANTS_REFRESH_TOKEN）
  - KABUSYS_ENV / LOG_LEVEL 等の検証ロジック

- データ取得 / ETL（kabusys.data）
  - J-Quants API クライアント（jquants_client.py）：ページネーション対応、レート制御、リトライ、トークン自動更新、DuckDB への冪等保存
  - ETL パイプライン（pipeline.py）：差分更新、バックフィル、品質チェックフック
  - ニュース収集（news_collector.py）：RSS 取得、前処理、SSRF 対策、記事→銘柄紐付け
  - スキーマ初期化（schema.py）：DuckDB のテーブル定義とインデックス、init_schema() を提供
  - 統計ユーティリティ（stats.py）：クロスセクション Z スコア正規化 等

- リサーチ（kabusys.research）
  - ファクター計算（factor_research.py）：モメンタム / ボラティリティ / バリュー 等
  - 特徴量探索（feature_exploration.py）：将来リターン計算、IC（Spearman）計算、統計サマリー

- 戦略（kabusys.strategy）
  - 特徴量構築（feature_engineering.build_features）：research の生ファクターを正規化・フィルタして features テーブルへ保存
  - シグナル生成（signal_generator.generate_signals）：features + ai_scores 等から final_score を算出し signals テーブルへ書き込む（BUY/SELL）

- バックテスト（kabusys.backtest）
  - エンジン（engine.run_backtest）：本番 DB からインメモリ DuckDB にデータをコピーして日次ループでシミュレーション
  - シミュレータ（simulator.PortfolioSimulator）：擬似約定（スリッページ・手数料モデル）、ポートフォリオ評価、トレード記録
  - メトリクス（metrics.calc_metrics）：CAGR, Sharpe, Max Drawdown, 勝率 等
  - CLI ランナー（backtest.run）：コマンドラインからバックテスト実行可能

- 実行（execution）／監視（monitoring）
  - パッケージのエクスポート対象に含まれています（実装はプロジェクトに応じて拡張）。

セットアップ手順
----------------

前提
- Python 3.10 以上（型注釈で X | None 形式を使用）
- DuckDB を利用するため環境に合わせたインストール

1. リポジトリをチェックアウトし、開発環境を作成
   - 例（仮想環境）:
     python -m venv .venv
     source .venv/bin/activate
     pip install --upgrade pip

2. 依存パッケージをインストール
   - 必要な最低依存（例）:
     pip install duckdb defusedxml
   - 開発用に pip install -e . などでパッケージとして扱うことを推奨します。

3. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD : kabu ステーション API のパスワード（実運用）
     - SLACK_BOT_TOKEN : Slack 通知用トークン（必要に応じて）
     - SLACK_CHANNEL_ID : Slack チャンネル ID
   - 任意（デフォルト値あり）:
     - KABUSYS_ENV : development / paper_trading / live（デフォルト development）
     - LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH : 監視 DB（デフォルト data/monitoring.db）
   - .env の例:
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456789
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

4. DuckDB スキーマ初期化
   - Python で:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
   - :memory: でインメモリ DB を使うことも可能（テスト用）:
     init_schema(":memory:")

使い方（例）
------------

1) スキーマ初期化（既に上で実行済みであれば不要）
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

2) データ取得 & 保存（J-Quants から株価・財務・カレンダーを取得して保存）
   from kabusys.data import jquants_client as jq
   records = jq.fetch_daily_quotes(date_from=..., date_to=..., id_token=None)
   jq.save_daily_quotes(conn, records)

   なお ETL を自動で差分実行するには pipeline.run_prices_etl 等を利用してください:
   from kabusys.data.pipeline import run_prices_etl
   res = run_prices_etl(conn, target_date=date.today())

3) 特徴量構築（features テーブルへの書き込み）
   from kabusys.strategy import build_features
   build_features(conn, target_date=date(2024, 1, 31))

4) シグナル生成（signals テーブルへの書き込み）
   from kabusys.strategy import generate_signals
   generate_signals(conn, target_date=date(2024, 1, 31))

5) ニュース収集 & 銘柄紐付け
   from kabusys.data.news_collector import run_news_collection
   known_codes = {"7203", "6758", ...}
   run_news_collection(conn, known_codes=known_codes)

6) バックテスト（Python API）
   from kabusys.backtest.engine import run_backtest
   result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
   # result.history, result.trades, result.metrics を参照

   CLI 実行例（パッケージとしてインストール済み or PYTHONPATH 調整）
   python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2024-12-31 \
       --cash 10000000 --db data/kabusys.duckdb

7) ETL 全体ジョブ（パイプライン）
   - pipeline モジュールは差分計算・バックフィル・品質チェックを行います。詳細は pipeline.run_* 系関数を参照してください。

注意点 / トラブルシューティング
--------------------------------
- 環境変数が未設定だと Settings._require が ValueError を投げます。必須環境変数は .env を作成して設定してください。
- .env 自動読み込みの挙動:
  - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を起点に .env/.env.local を読み込みます。
  - 読み込み順: OS 環境 > .env.local（override=True）> .env（override=False）
  - テスト等で自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- DuckDB のパスが正しくないと接続に失敗します。init_schema を利用して親ディレクトリを自動作成できます。
- news_collector は外部ネットワークを利用するため、SSRF・大容量レスポンス対策を組み込んでいます。fetch_rss の呼び出し時はネットワーク例外に注意してください。

ディレクトリ構成（主なファイル）
--------------------------------
src/kabusys/
- __init__.py                  : パッケージエクスポート（data, strategy, execution, monitoring）
- config.py                    : 環境変数 / 設定管理（Settings）

サブパッケージ: data
- data/__init__.py
- jquants_client.py             : J-Quants API クライアント、保存関数
- news_collector.py            : RSS 取得・前処理・raw_news 保存・銘柄抽出
- pipeline.py                  : ETL 差分更新パイプライン
- schema.py                    : DuckDB スキーマ定義・init_schema
- stats.py                     : zscore_normalize 等の統計ユーティリティ

サブパッケージ: research
- factor_research.py           : モメンタム / ボラティリティ / バリュー ファクター
- feature_exploration.py       : 将来リターン / IC / 統計サマリー
- __init__.py                  : 便利なエクスポート

サブパッケージ: strategy
- feature_engineering.py       : ファクター正規化・ユニバースフィルタ・features 書込
- signal_generator.py          : final_score 計算・BUY/SELL 判定・signals 書込
- __init__.py                  : build_features / generate_signals のエクスポート

サブパッケージ: backtest
- engine.py                    : run_backtest（インメモリコピー + 日次ループ）
- simulator.py                 : PortfolioSimulator（擬似約定・評価）
- metrics.py                   : バックテスト指標計算
- run.py                       : CLI エントリポイント
- clock.py                     : SimulatedClock（将来拡張用）
- __init__.py

サブパッケージ: execution
- __init__.py                  : 発注周りのモジュールを想定（現状は空）

その他
- README.md                    : （このファイル）
- pyproject.toml / setup.cfg 等（プロジェクトに応じて）

拡張・開発のヒント
-------------------
- 新しい API クライアントや戦略を追加する際は、既存の設計方針（ルックアヘッド回避、冪等性）に従ってください。
- SQL クエリは DuckDB のウィンドウ関数や OVER を多用しています。大規模データでのパフォーマンスはインデックス設計とクエリ範囲（date 範囲）で制御します。
- テストを書く際は環境変数の自動読み込みを無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）し、id_token 等を関数引数で注入してモックしてください。

ライセンス / 貢献
-----------------
- 本リポジトリのライセンスや貢献ルールはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

上記は src/kabusys のコードを元にした README です。必要であれば、実際のインストール手順（requirements.txt / pyproject.toml の依存解消）、CI/CD や運用フロー（ETL スケジューリング、Slack 通知、監視）についての章も追加できます。どの部分を詳細化したいか教えてください。