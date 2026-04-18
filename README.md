# KabuSys

日本株向けの自動売買 / リサーチ基盤ライブラリ群です。  
本リポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築・資金配分、ファクター計算、LLM を使ったニュースセンチメント評価などのモジュールを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- 日次・リアルタイムの売買ロジック実行（ExecutionEngine）
- システム・発注状況の監視とアラート／Kill Switch（Monitoring）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- DuckDB を使ったファクター計算・リサーチ処理（momentum / value / volatility 等）
- OpenAI 等を使ったニュース NLP（銘柄別センチメント）・市場レジーム判定
- Paper Trading 用の検証レポート生成ツール

設計方針として、実行部分とリサーチ部分を分離し、DB は DuckDB / SQLite を組み合わせて利用します。環境変数・.env による設定管理、起動前検証と対話式ウィザードを備えています。

---

## 主な機能一覧

- Execution
  - 実際の（または Mock）ブローカークライアント経由での発注処理
  - RiskManager、OrderManager、Reconciler 組み込み
  - paper_trading 環境では MockBroker を使用し DB を分離
- Monitoring
  - システムリソース（CPU/メモリ/ディスク）・プロセス死活監視
  - 発注ログ・滞留注文・約定異常の検出
  - Kill Switch（data/kill.flag）による安全停止
  - RiskMonitor によるドローダウン監視・ポジション上限監視
- Portfolio
  - 候補選定（スコア順）、等金額 / スコア加重配分
  - セクター上限適用、レジームに応じた乗数
  - ポジションサイズ計算（単元株丸め、aggregate cap）
- Research
  - DuckDB 接続でのファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ
- AI
  - ニュース記事を LLM で銘柄別に評価し ai_scores に保存（score_news）
  - ETF とマクロニュースを使った市場レジーム判定（score_regime）
- Tools
  - Paper Trading の検証レポート生成スクリプト（paper_verification_report）

---

## 要件（依存ライブラリ）

必須（最低限）:

- Python 3.9+（typing 機能を前提）
- duckdb
- psutil
- openai (AI 機能を使う場合)
- sqlite3（標準ライブラリ）
- （オプション）PyYAML：config/*.yaml のパース検証に使用

pip でのインストール例:

    python -m venv .venv
    source .venv/bin/activate
    pip install duckdb psutil openai

PyYAML を使う場合:

    pip install pyyaml

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動

2. 仮想環境作成（任意）と依存インストール（上記参照）

3. .env を作成
   - 対話式ウィザードで生成するのが簡単です（下記参照）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を利用する場合:
     - OPENAI_API_KEY を環境変数にセット（config ウィザードでは扱いません）

4. （任意）DuckDB / SQLite データディレクトリ作成:

    mkdir -p data logs

注意: .env は絶対に Git にコミットしないでください。

---

## 環境設定（.env）とウィザード

対話式ウィザードで .env を作成・更新できます。

    python -m kabusys.config_setup

- 生成される `.env` の場所はプロジェクトルートの `.env`（引数で変更可）。
- 既存の `.env` がある場合は現在値を再利用できます。

自動ロード:
- パッケージ起動時に自動で .env をロードします（OS 環境変数が優先）。
- 自動ロードを無効化する場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

設定検証:
- 起動前に設定の整合性をチェックできます。

    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict  # 警告も FAIL 扱い

このコマンドは必須環境変数、KABUSYS_ENV、パスの存在、config/*.yaml の有無（PyYAML があれば中身のパース）などを検査します。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: 必須
- KABU_API_PASSWORD: 必須
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒, デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: 0/1（本番で自動クリアするかの安全フラグ。推奨 0）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env の自動ロードを無効化

---

## 実行方法（使い方）

プロジェクトはモジュールとして実行できます（各スクリプトは package のエントリポイントを提供）。

1. ExecutionEngine を起動（通常の本番 or paper_trading）

    # paper_trading 例
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution

    # 本番
    export KABUSYS_ENV=live
    python -m kabusys.run_execution

- paper_trading の場合は MockBrokerClient を使用し、デフォルトで `data/paper_trading.db` を使用して本番 DB と分離します。
- 実行中に停止したい場合は `data/stop_requested.flag` を作るとスレッドが検知して終了処理を行います。
- 実行時にプロセス優先度を "high" に設定します（psutil の権限に依存）。

2. Monitoring を起動

    python -m kabusys.run_monitoring

- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定できます（デフォルト 60）。
- 監視モジュールは SQLite の監視 DB（settings.sqlite_path）を使用し、環境にかかわらず本番の sqlite_path を参照します。
- 停止制御: `data/stop_requested.flag` の存在で監視ループを終了します。

3. Paper Trading 検証レポート（ローカルツール）

    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
    # デフォルト DB パスは env PAPER_TRADING_SQLITE_PATH or data/paper_trading.db

出力には稼働率、注文成功率、送信率、レイテンシ（P95 など）を表示し PASS/FAIL 判定を行います。

4. AI / Regime scoring（プログラム API）

- ニュース NLP スコアを生成して DB に書き込む:

    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect('data/kabusys.duckdb')
    score_news(conn, target_date=date(2026,4,10), api_key='YOUR_OPENAI_KEY')

- 市場レジーム判定:

    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,10), api_key='YOUR_OPENAI_KEY')

注意: OpenAI を用いる場合は `OPENAI_API_KEY` を環境に設定するか、引数で渡してください。

---

## ログ

- ログは `kabusys.utils.logging_setup.setup_logging` により共通設定され、標準出力（stdout）と日次ローテーションファイル（logs/<app_name>.log）に出力されます。
- デフォルト 30 日分を保持します。ログディレクトリは環境変数 `LOG_DIR` で上書き可。

---

## Kill / Stop フラグ

- ExecutionEngine 側への停止要求は `data/kill.flag`（Kill Switch）で行います。KillSwitch は条件を満たしたときにこのファイルを書き、Execution 側はこれを検知して安全に停止します。
- 単純な「即時停止」用に `data/stop_requested.flag` を置くと run_execution / run_monitoring のループが終了します（運用上の停止フラグ）。
- kill.flag を自動でクリアする設定（危険）: `KILL_FLAG_CLEAR_ON_START=1`（本番では `0` 推奨）。

---

## ディレクトリ構成

主要なファイル・ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings 管理 (.env 自動読み込み)
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 起動前の設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動用スクリプト
  - run_monitoring.py       — SystemMonitor 起動用スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py           — ニュース NLP / LLM 呼び出しロジック
    - regime_detector.py    — 市場レジーム判定
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - (ExecutionEngine 関連コンポーネント: broker_factory, order_manager, repo, reconciler, risk_manager, ...)
  - data/
    - pipeline.py           — DuckDB データ取得ユーティリティ等
  - utils/
    - logging_setup.py
    - process_priority.py

データ・ファイル（デフォルト）:
- data/kabusys.duckdb
- data/monitoring.db
- data/paper_trading.db (paper_trading 用)
- data/execution.pid, data/kill.flag, data/stop_requested.flag

ログ:
- logs/<app_name>.log

---

## 注意事項 / 運用上のヒント

- 本番環境（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START` を `0` にし、.env を厳密に管理してください。
- .env は絶対にバージョン管理に含めないでください。
- OpenAI API を利用する処理は外部 API に依存するため、レート制限や障害に対してリトライ・フォールバックの実装がありますが、API キー管理・料金にはご注意ください。
- 複数プロセスで SQLite を同時更新する場合は注意が必要です（本実装では簡便化のためシンプルなロックや retry を想定していません）。
- ローカルでの検証は paper_trading モードで行い、本番 DB と完全に分離してテストしてください。
- DuckDB 経由のリサーチは大量データを扱うので、ファイルサイズやメモリに注意して運用してください。

---

## さらに詳しく / 開発者向け

各モジュールには docstring とコメントで詳細な仕様・設計意図が記載されています。ファクター設計やポートフォリオ構築の理論的背景はソース内コメント（PortfolioConstruction.md 等参照想定）に従って実装されています。

不明点や拡張するときは、まず `kabusys.config.Settings` と `monitoring/monitoring_db.py`、`execution` ディレクトリの主要クラスを確認してください。

---

必要であれば、README に含めるコマンド例や環境変数のサンプル .env テンプレートも作成できます。どの情報をもっと詳しく追加しますか？