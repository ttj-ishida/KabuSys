# KabuSys — 日本株自動売買システム（README）

このリポジトリは日本株向けの自動売買システムの一部（コアユーティリティ・監視・ポートフォリオ構築・リサーチ・AI連携など）を含みます。ここではプロジェクトの概要、主な機能、セットアップ手順、基本的な使い方、およびディレクトリ構成を日本語でまとめます。

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件 / 依存パッケージ
- セットアップ手順
- 使い方（主なコマンドと環境変数）
- ファイル／ディレクトリ構成（抜粋）
- 追加の注意点

---

## プロジェクト概要

KabuSys は「日本株自動売買」を想定したモジュール群です。本リポジトリは以下の機能を提供するモジュールを含みます（発注/ブローカー実装・データパイプラインの一部は別実装や外部依存の想定）：

- 実行エンジン（ExecutionEngine）の起動スクリプト
- 監視（Monitoring）：システム状態、注文の滞留・約定異常、ドローダウン監視、Kill Switch
- .env の対話的セットアップウィザードと設定検証ツール
- Paper Trading 用検証レポート生成ツール
- ポートフォリオ構築（候補選定・重み算出・ポジションサイズ算出・セクター制限等）
- 研究用ファクター・特徴量解析（DuckDB を利用）
- AI（OpenAI）連携モジュール（ニュースの NLP スコアリング、レジーム判定）

設計上のポイント：
- 環境変数（.env）で設定を切り替え可能（KABUSYS_ENV: development | paper_trading | live）
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離して data/paper_trading.db を使用
- DuckDB を分析用 DB として利用
- 監視ログは SQLite（デフォルト: data/monitoring.db）に永続化

---

## 機能一覧

主な機能（モジュール別）

- config
  - Settings クラスによる環境変数読み込み・検証
  - .env 自動ロード（プロジェクトルート検出）
- config_setup.py
  - 対話式ウィザードで .env を作成 / 更新
- validate_config.py
  - .env と config/*.yaml の検証（--strict オプションあり）
- run_execution.py
  - ExecutionEngine を起動するランチャー
  - paper_trading モードでは MockBrokerClient を使用し DB を分離
- run_monitoring.py
  - SystemMonitor を周期的に実行する監視プロセスのランチャー
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能
- monitoring/*
  - monitoring_db: 監視ログ用 SQLite スキーマ・CRUD
  - system_monitor: CPU/メモリ/Disk/データ鮮度/プロセス存在チェック
  - trade_monitor: 滞留注文・約定異常チェック
  - risk_monitor: ドローダウン・ポジション上限チェック（ダッシュボード更新 / リスクログ）
  - monitoring_engine: 各 Monitor を束ねるループとアラート判定
  - kill_switch: 条件を満たしたら data/kill.flag を書き込む
  - alert_manager: （アラート送信管理、実装ファイルは省略）
- ai/*
  - news_nlp: raw_news を集約して OpenAI に投げ、ai_scores テーブルへ書込み
  - regime_detector: ETF の MA 乖離＋マクロニュースで市場レジーム判定（OpenAI 使用オプションあり）
- research/*
  - factor_research: momentum / volatility / value 等のファクター計算（DuckDB）
  - feature_exploration: 将来リターン計算・IC（情報係数）等
- portfolio/*
  - 候補選定、等重・スコア重み、セクター制限、ポジションサイズ計算（丸め・lot 対応）
- tools
  - paper_verification_report: Paper Trading の検証レポート生成（期間指定可能）

---

## 前提条件 / 依存パッケージ

推奨 Python バージョン: 3.10+

主な外部依存（一部は任意）:
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（validate_config が YAML 検証を行う場合に必要）

例（pip インストール）:
pip install duckdb psutil openai PyYAML

標準ライブラリで用意される:
- sqlite3, logging, threading, argparse, datetime など

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. Python 仮想環境の作成と有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install -r requirements.txt  （requirements.txt がある場合）
   - または個別に: pip install duckdb psutil openai PyYAML
4. .env を作成
   - 対話式ウィザードを使う: python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考にしてください（リポジトリにある場合）
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使用する場合）
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB。デフォルト: data/paper_trading.db）
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告も失敗にする場合: python -m kabusys.validate_config --strict
6. データディレクトリの作成（必要に応じて）
   - デフォルトで data/ 下のファイルを参照するため、実行時に自動作成されますが手動で作成しても良いです。

---

## 使い方（主なコマンド）

基本的にパッケージモジュールとして起動します。プロジェクトルート（pyproject.toml または .git がある場所）で実行してください。

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード（警告も FAIL）: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
    - 実行中は data/execution.pid に PID が書き込まれます。
    - 停止には data/stop_requested.flag を作成する、または監視側で kill.flag を書くなどがあります。

- 監視プロセス起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で変更可能（デフォルト 60 秒）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用します（監視 DB は環境に依存しない仕様）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能（プログラムから呼ぶ）
  - OpenAI API キー（OPENAI_API_KEY）が必要
  - ニュース NLP スコアリング（ai.news_nlp.score_news）
    - 関数呼び出し例（ Python スクリプト内 ）:
      from kabusys.ai.news_nlp import score_news
      score_news(duckdb_conn, target_date, api_key=os.environ["OPENAI_API_KEY"])
  - レジーム判定（ai.regime_detector.score_regime）
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=os.environ["OPENAI_API_KEY"])
  - ※両者は CLI エントリポイントを直接提供していないため、スクリプトやジョブから関数を呼び出す形が想定されています。

停止フラグと Kill Switch:
- 監視ループ・エンジンがチェックする停止フラグ: data/stop_requested.flag
  - このファイルが存在すると各ループは安全に停止します。
- 強制停止（Kill Switch）:
  - KillSwitch がトリガーすると data/kill.flag が書き込まれます。ExecutionEngine は起動時にこのフラグを確認し、既存の場合は起動を抑止します（KILL_FLAG_CLEAR_ON_START の設定に注目）。

ログレベル:
- LOG_LEVEL 環境変数で制御（DEBUG, INFO, WARNING, ERROR, CRITICAL）

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル・モジュールの一覧（提供コードに基づく抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（OpenAI 連携）
    - regime_detector.py           — 市場レジーム判定（OpenAI 連携）
  - monitoring/
    - monitoring_db.py             — SQLite スキーマ & DB 操作用ラッパ
    - system_monitor.py            — システム・データ鮮度監視
    - trade_monitor.py             — 注文滞留・約定異常監視
    - risk_monitor.py              — ドローダウン・ポジション制限監視
    - monitoring_engine.py         — 各 Monitor を束ねるエンジン
    - kill_switch.py               — kill.flag 書き込みロジック
    - alert_manager.py             — アラート管理（実装を参照）
  - portfolio/
    - __init__.py
    - portfolio_builder.py         — 候補選定・重み算出
    - position_sizing.py           — 株数決定・資金配分・丸め
    - risk_adjustment.py           — セクター制限・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算（momentum/value/volatility）
    - feature_exploration.py       — 将来リターン・IC・統計サマリー
  - utils/
    - __init__.py
    - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ

プロジェクトルートでは data/ 以下に SQLite/DuckDB 等のデータファイルが作られる想定です（例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）。

---

## 追加の注意点 / 運用上のヒント

- KABUSYS_ENV を間違えると本番口座にアクセスするリスクがあります。live 環境は特に注意して設定と .env を管理してください。
- .env ファイルは絶対にバージョン管理（Git）にコミットしないでください。
- OpenAI を利用する機能は API コストとレイテンシを考慮して運用してください。score_news / score_regime はリトライやフェイルセーフを備えていますが、運用時はレート上限や課金を管理してください。
- validate_config.py で PyYAML がインストールされていない場合、config/*.yaml の内容検証はスキップされます（警告が出ます）。
- run_monitoring.py は MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できますが、0 や負の値は無効でデフォルトにフォールバックします。
- process_priority.set_process_priority が権限不足で失敗する場合は警告でスキップされます（多くの環境で root 権限が必要な操作が含まれます）。

---

この README はコードベースに含まれる主要な機能・運用方法をまとめたものです。実際の導入や運用前には必ず環境変数の確認と validate_config によるチェックを実行してください。必要であれば、各モジュールの docstring やソース内コメントも併せて参照してください。