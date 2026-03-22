KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けのデータプラットフォーム＋自動売買基盤のプロトタイプ実装です。  
主な目的は以下です。

- J-Quants API から市場データ・財務データを取得して DuckDB に保存する ETL
- RSS ニュース収集と記事→銘柄紐付け
- 研究用ファクター計算（momentum / volatility / value 等）
- 特徴量（features）生成とシグナル（signals）生成ロジック
- バックテストフレームワーク（ポートフォリオシミュレータ・評価指標）
- 発注／実行層・監視（execution / monitoring）を想定したレイヤード設計

本リポジトリは「Raw → Processed → Feature → Execution」の多層データモデルを採用し、DuckDB を中心にデータを管理します。各モジュールはルックアヘッドバイアス回避・冪等性・エラーハンドリングを重視して設計されています。

機能一覧
--------
主な機能（モジュール別）

- config
  - .env / .env.local から環境変数を自動読み込み
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN 等）
  - KABUSYS_ENV / LOG_LEVEL のバリデーション

- data
  - jquants_client: J-Quants API クライアント（レートリミット、リトライ、トークン自動リフレッシュ、ページネーション対応）
  - news_collector: RSS フィード収集、前処理、SSRF 対策、DB への冪等保存
  - pipeline: 差分 ETL、バックフィル、品質チェックフック（quality モジュール想定）
  - schema: DuckDB のスキーマ初期化（raw / processed / feature / execution レイヤー）
  - stats: z-score 正規化などの共通統計ユーティリティ

- research
  - factor_research: momentum / volatility / value 等のファクター計算（prices_daily / raw_financials を利用）
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー

- strategy
  - feature_engineering: 研究で得た raw factor を正規化・フィルタして features テーブルへ保存
  - signal_generator: features と ai_scores を統合し final_score を計算、BUY/SELL を signals テーブルへ保存

- backtest
  - engine: DB をコピーしたインメモリ環境で日次ループのバックテストを実行
  - simulator: ポートフォリオシミュレータ（スリッページ、手数料モデル）、約定記録
  - metrics: CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio 等の算出
  - run: CLI ラッパー（python -m kabusys.backtest.run）

- execution / monitoring
  - 基盤用プレースホルダ（発注 API 統合、監視・通知機能を想定）

セットアップ手順
----------------

1. 必要環境
   - Python 3.10 以上（typing の "|" 演算子を使用）
   - DuckDB（Python パッケージ）
   - defusedxml（RSS パースの安全対策）
   - （任意）その他ライブラリ（プロジェクトに requirements.txt がある場合はそちらを参照）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (macOS/Linux) または .venv\Scripts\activate (Windows)

3. 依存パッケージのインストール（例）
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. パッケージのインストール（開発モード）
   - プロジェクトルートで：
     - pip install -e .

5. 環境変数の設定
   - プロジェクトルートに .env または .env.local を作成する（config.py が自動読み込み）
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード（execution 用）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — 通知先チャンネル ID
   - オプション:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH — データベースパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
   - .env の自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   例（.env）
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb

6. DuckDB スキーマ初期化
   - Python で:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")
     - conn.close()

使い方
------

- DB 初期化（例）
  - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

- J-Quants からデータ取得 → 保存（概念）
  - from kabusys.data import jquants_client as jq
  - rows = jq.fetch_daily_quotes(date_from=..., date_to=..., id_token=None)
  - conn = init_schema('data/kabusys.duckdb')
  - jq.save_daily_quotes(conn, rows)

- RSS ニュース収集と保存（一括ジョブ）
  - from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  - conn = init_schema('data/kabusys.duckdb')
  - known_codes = set([...])  # 既知の銘柄コードリスト（抽出用）
  - run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)

- 特徴量作成（features テーブルへの書き込み）
  - from datetime import date
  - import duckdb
  - from kabusys.strategy import build_features
  - conn = duckdb.connect('data/kabusys.duckdb')
  - build_features(conn, target_date=date(2024, 1, 31))

- シグナル生成（signals テーブルへの書き込み）
  - from kabusys.strategy import generate_signals
  - generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)

- バックテスト（CLI）
  - python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2024-12-31 \
      --cash 10000000 \
      --slippage 0.001 \
      --commission 0.00055 \
      --max-position-pct 0.20 \
      --db data/kabusys.duckdb

  - または Python API:
    - from kabusys.backtest.engine import run_backtest
    - conn = init_schema('data/kabusys.duckdb')
    - result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
    - result.metrics などで結果確認

- その他ユーティリティ
  - research.calc_forward_returns, research.calc_ic, data.stats.zscore_normalize などの関数は研究用途に直接呼べます。

注意点 / 運用上のヒント
-----------------------
- config.Settings は環境変数を必須チェックします。必要な値が設定されていないと ValueError が発生します。
- J-Quants API にはレート制限（120 req/min）があります。jquants_client は内部的にレートリミッタとリトライを実装しています。
- news_collector は SSRF 対策や受信サイズ制限を実装していますが、運用時は収集先の信頼性とスループットを考慮してください。
- バックテストでは本番 DB を変更しないためにインメモリ (":memory:") にデータをコピーして実行します。
- features / signals / positions は生成処理が日付単位で「削除→挿入」の置換（トランザクション）になっており冪等です。
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれかに設定してください（不正値はエラー）。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - pipeline.py
      - schema.py
      - stats.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - backtest/
      - __init__.py
      - engine.py
      - metrics.py
      - simulator.py
      - clock.py
      - run.py
    - execution/
      - __init__.py
    - monitoring/
      - (監視関連モジュールを配置する想定)

主な役割の対応
- データ取得・保存: src/kabusys/data/*
- ファクター・研究: src/kabusys/research/*
- 戦略処理: src/kabusys/strategy/*
- バックテスト: src/kabusys/backtest/*
- 設定管理: src/kabusys/config.py

貢献・拡張案
-------------
- execution 層に実際の kabuステーション API 統合を追加（注文送信・注文状態取得）
- monitoring に Slack 通知やメトリクス送信（Prometheus 等）を追加
- quality モジュールの実装を補完し ETL パイプラインの品質評価を自動化
- feature / ai 統合（ai_scores の生成パイプライン）やモデル管理の追加

ライセンス・作者
----------------
（ここにライセンス情報や作者情報を追記してください）

以上。必要であれば README にサンプル .env.example を追加したり、セットアップ用スクリプト（docker-compose / Makefile）を追記するREADME拡張を作成します。どの情報を追記しますか？