# KabuSys

日本株自動売買システムのコアライブラリと起動スクリプト群。  
このリポジトリは取引エンジン、監視、ポートフォリオ構築、リサーチ（ファクター計算）、AIによるニュース・レジーム判定などのコンポーネントを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動 / CLI）
- 主要環境変数
- 停止・Kill スイッチについて
- ディレクトリ構成（概略）
- 主要モジュール説明

---

## プロジェクト概要

KabuSys は日本株の自動売買システム（エンジン）と、それを支える周辺ツール群（監視、ポートフォリオ構築、リサーチ、AI スコアリング等）をまとめたパッケージです。  
設計方針として以下を重視しています：

- 発注ロジックとデータ処理を分離（DuckDB/SQLite を利用）
- Paper Trading（検証用）と Live（本番）を分離する設計
- 監視（Monitoring）により異常時に Kill Switch を発動して ExecutionEngine を安全停止
- LLM（OpenAI）を用いたニュースセンチメント評価やレジーム判定をサポート（API キー必須）

---

## 主な機能一覧

- Execution Engine（発注実行）- run_execution.py
  - 本番と Paper Trading を切り替え可能（KABUSYS_ENV）
  - BrokerClientFactory 経由でブローカークライアントを生成
  - RiskManager / OrderManager / Reconciler を組み合わせて注文実行を行う

- Monitoring（監視）- run_monitoring.py、monitoring.Engine
  - CPU / メモリ / ディスク使用率やプロセス存在確認
  - データ鮮度チェック（DuckDB 内の prices_daily 等）
  - Trade / Risk の各種チェックとアラート
  - KillSwitch により異常時に data/kill.flag を書き込み

- Portfolio（ポートフォリオ構築）
  - 銘柄選定（score / rank）、等金額・スコア重み配分
  - ポジションサイズ計算（リスクベース、単元丸め、aggregate cap）

- Research（リサーチ / ファクター計算）
  - Momentum / Volatility / Value ファクター計算（DuckDB を使用）
  - Forward returns、IC（スピアマン）計算、統計サマリー

- AI（ニュース NLP / レジーム判定）
  - OpenAI を使ったニュースセンチメント評価（ai.news_nlp）
  - ETF + マクロニュースに基づく市場レジーム判定（ai.regime_detector）

- ユーティリティ
  - ロギングセットアップ（logs 日次ローテーション）
  - プロセス優先度 / CPU affinity 設定
  - .env ウィザード（config_setup）と設定検証ツール（validate_config）
  - Paper Trading 検証レポート生成ツール（tools.paper_verification_report）

---

## セットアップ手順

前提:
- Python 3.10 以上（型注釈に | が使われているため）
- Git clone したプロジェクトルートを使用

1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

2. 必要なパッケージをインストール
   - 最小推奨（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（validate_config の YAML 検証を使う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt はリポジトリに含まれていない場合があります。用途に応じてパッケージを追加してください。

3. .env の準備
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動で .env を作成（.env は Git にコミットしないこと）

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告を厳格に扱う場合:
     - python -m kabusys.validate_config --strict

5. 必要ディレクトリ（data, logs）の確認
   - ログ等はデフォルトで logs/ に出力されます。存在しない場合は自動作成を試みますが、書き込み権限を確認してください。

---

## 使い方

基本的にはモジュールとして Python から起動します（プロジェクトルートで実行）。

- 環境変数の例（.env）:
  - KABUSYS_ENV=development|paper_trading|live
  - JQUANTS_REFRESH_TOKEN=...
  - KABU_API_PASSWORD=...
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  - LOG_LEVEL=INFO
  - OPENAI_API_KEY=...（AI 機能を使う場合）

- Execution Engine を起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い paper_trading.db に記録（本番 DB と分離）
    - 起動前に data/stop_requested.flag が存在すると起動をしない

- Monitoring を起動（監視ループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト: 60 秒）
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する点に注意

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db で別パス指定可。

- AI 機能（ライブラリとして利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定

ログ:
- デフォルト出力先: stdout と logs/<app_name>.log（日次ローテート・30日保存）
- app_name 例: "execution" や "monitoring"

---

## 主要環境変数（抜粋）

- KABUSYS_ENV
  - development / paper_trading / live（必須ではないが有効値である必要がある）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading 時のモック約定挙動。instant|partial|never|reject）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL（監視ポーリング秒数、run_monitoring が参照）
- LOG_DIR（ログディレクトリを上書き）
- KILL_FLAG_CLEAR_ON_START（本番起動時の Kill Flag 自動クリア: 0/1）

validate_config は .env および config/*.yaml（存在すれば）を検査します。PyYAML がない場合は YAML 検証をスキップします。

---

## 停止・Kill スイッチについて

- 停止リクエスト（手動でループを止めたい場合）
  - run_monitoring.py / run_execution.py はプロジェクト/data/stop_requested.flag の存在を監視しており、存在するとループを終了します。
  - ファイルを作成するだけで停止リクエストを実行できます（例: touch data/stop_requested.flag）。

- Kill Switch（リスク条件で自動的にエンジン停止）
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。
  - KillSwitch の評価条件（例）:
    - ドローダウン閾値超過（RiskMonitor が検出）
    - ポジション上限超過
  - ExecutionEngine は Settings.kill_flag_path（デフォルト data/kill.flag）を参照して停止処理を行います。

- 起動時のクリア挙動
  - Settings.kill_flag_clear_on_start が 1 の場合、起動時に kill.flag を自動でクリアします（本番環境では危険な設定なので注意）。

---

## ディレクトリ構成（主要ファイルのみ）

（プロジェクトルート）
- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数/.env ロードと Settings
    - config_setup.py          # 対話式 .env ウィザード
    - validate_config.py       # 設定検証 CLI
    - run_execution.py         # ExecutionEngine 起動スクリプト
    - run_monitoring.py        # SystemMonitor 起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - __init__.py
    - execution/                # Execution 関連（OrderManager 等）
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconcilier.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py

プロジェクトルートに次のような運用ディレクトリを置いて使います（デフォルト）:
- data/          # SQLite / PID / flag 等
  - monitoring.db
  - paper_trading.db
  - kill.flag
  - stop_requested.flag
  - execution.pid
- logs/          # 日次ローテートログ

---

## 主要モジュールの簡単説明

- config.py
  - .env 自動読み込み（.env, .env.local）機能と Settings クラス
  - env の検証（KABUSYS_ENV / LOG_LEVEL 等）

- config_setup.py
  - 対話式に .env を生成・更新するウィザード

- validate_config.py
  - 起動前チェックツール（必須環境変数・ファイルパス・config YAML の存在/パース等）

- run_execution.py
  - ExecutionEngine を組み立ててバックグラウンドスレッドで run_session を実行
  - paper_trading 環境では専用 SQLite を使い本番 DB と分離

- run_monitoring.py
  - SystemMonitor を定期実行して system_status / risk_logs / trade_logs 等を更新
  - MONITOR_POLL_INTERVAL でループ間隔を指定可能（秒）

- monitoring/monitoring_db.py
  - SQLite に対する永続化レイヤ（テーブル作成 / マイグレーション / CRUD）

- ai/news_nlp.py
  - raw_news を集約して OpenAI に投げ、ai_scores テーブルへ書き込み

- ai/regime_detector.py
  - ETF（1321）200 日 MA とマクロニュースの LLM スコアを合成して market_regime を決定

- portfolio/*
  - 候補選定、重み計算、ポジションサイズ決定、セクター上限適用

- research/*
  - DuckDB を使ったファクター計算（momentum / volatility / value）と IC・統計算出

- utils/logging_setup.py
  - すべての起動スクリプトで統一されたログ設定を提供（stdout + 日次ファイル）

- utils/process_priority.py
  - psutil を使ってプラットフォーム間のプロセス優先度差を吸収

---

README は以上です。運用上の注意点や本番移行のチェックポイント（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の確認、バックアップ等）を必ず確認してから Live 環境で起動してください。必要であれば導入手順や運用手順のテンプレート（systemd ユニット、プロセスマネージャ設定など）も追記可能です。必要であればお知らせください。