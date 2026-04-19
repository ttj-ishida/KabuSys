# KabuSys

日本株自動売買システムの軽量モジュール群（ライブラリ + 起動スクリプト群）

このリポジトリは、戦略・ポートフォリオ構築、発注実行、監視、研究用ユーティリティ、OpenAI を使ったニュース NLP 等を含む自動売買プラットフォームの一部実装です。ここではプロジェクト概要・主な機能・セットアップ手順・使い方・ディレクトリ構成をまとめます。

---

## プロジェクト概要

- Python で書かれたモジュール群で、以下の役割を持ちます：
  - 戦略研究・ファクター計算（DuckDB を想定）
  - ポートフォリオ構築（候補選定・重み付け・株数決定）
  - 発注系（ExecutionEngine）と Broker 抽象化（paper/live 切替）※発注実装は別モジュールに依存
  - 監視（System / Trade / Risk Monitor）と Kill Switch（フラグファイルで Execution を停止）
  - AI モジュール（ニュースセンチメント / レジーム判定） — OpenAI API を使用
  - 運用支援ツール（.env ウィザード、設定検証、Paper Trading レポート生成 など）

- 設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込みます（自動ロード機能あり、無効化オプションあり）。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py : ExecutionEngine を起動（KABUSYS_ENV により paper_trading モードを切替）
  - run_monitoring.py : SystemMonitor をポーリングで起動（MONITOR_POLL_INTERVAL で間隔変更可）
- 設定関連
  - config_setup.py : 対話式 .env ウィザード（初期設定）
  - validate_config.py : .env / config/*.yaml の検証 CLI（--strict オプションあり）
- 監視（モジュール）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - MonitoringDB: SQLite ベースの監視ログ層（system_status, trade_logs, positions, risk_logs, dashboard など）
  - KillSwitch: 条件に応じて `data/kill.flag` を書き、Execution を停止
- ポートフォリオ構築（純粋関数群）
  - 候補選定、重み付け（等重・スコア重み）、セクター上限適用、レジーム乗数、株数計算（単元丸め・aggregate cap）
- 研究（research）
  - ファクター計算（momentum, volatility, value）
  - 特徴量探索（forward returns, IC, summary）
- AI（ai）
  - news_nlp: OpenAI を使ったニュースセンチメント集計 → `ai_scores` テーブルへ書き込み
  - regime_detector: ETF の MA200 等とマクロセンチメントを合成して市場レジームを判定
- ユーティリティ
  - logging_setup: 日次ローテートファイル + stdout を統一的に設定
  - process_priority: プロセス優先度 / CPU affinity の設定
- 運用ツール
  - tools.paper_verification_report: Paper Trading DB から PASS/FAIL 判定を行う検証レポート生成

---

## セットアップ手順（開発/運用向け）

1. リポジトリをクローンしてルートへ移動
   - 例: git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - Unix: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 必要なパッケージをインストール
   - 最低限必要になる外部パッケージ（プロジェクトに requirements.txt がない場合の例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML をパースする場合に必要）
   - インストール例:
     - pip install duckdb psutil openai PyYAML

4. データディレクトリの作成（必要に応じて）
   - デフォルトのパス:
     - データベース: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db
     - ログ: logs/
     - 実行 PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag
   - 例:
     - mkdir -p data logs

5. 環境変数設定
   - 対話式で `.env` を作る:
     - python -m kabusys.config_setup
   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN — J-Quants 用（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
   - その他主要な環境変数（デフォルト値あり）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (data/kabusys.duckdb)
     - SQLITE_PATH (data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
     - LOG_LEVEL (INFO)
     - LOG_DIR (logs/)
     - OPENAI_API_KEY （AI 機能を使う場合）
     - PAPER_FILL_MODE (instant | partial | never | reject)
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒） — デフォルト 60）
     - KILL_FLAG_CLEAR_ON_START（1 にすると Execution 起動時に kill.flag を自動クリア）

6. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする: python -m kabusys.validate_config --strict

---

## 使い方

以下は代表的なコマンド例です。各スクリプトはパッケージモジュールとして起動できます。

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper DB（PAPER_TRADING_SQLITE_PATH）へ記録します。本番（live）では本番 DB を使用。
    - 起動前に `data/stop_requested.flag` が存在すると起動しません。
    - 実行中は `data/execution.pid` に PID を書きます。停止は kill.flag（KillSwitch）がトリガーされるか stop フラグで行います。

- Monitoring（監視プロセス）を起動
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60）
  - 監視は常に本番 sqlite_path（SQLITE_PATH）を使用して監視ログを永続化します。

- .env 対話ウィザード（初期設定）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いで exit(1)

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数の代替）

- AI / Research 機能（プログラムから利用）
  - AI ニューススコアリング:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - 要: OpenAI API Key（api_key 引数または環境変数 OPENAI_API_KEY）
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- 停止・Kill スイッチ
  - monitoring の評価により `data/kill.flag` が書かれると ExecutionEngine は停止される設計です。
  - 強制停止やメンテナンス時には `data/stop_requested.flag` を作成すると run_* スクリプトが検知してループから抜けます。

- ログ
  - デフォルトで stdout と logs/<app_name>.log（日次ローテーション）に出力されます。
  - ログ設定は kabusys.utils.logging_setup.setup_logging で統一管理。

---

## 環境変数の主な一覧（要点）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- OPENAI_API_KEY (AI 機能を使う場合)
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db（monitoring は常にこの本番パスを使用）
- PAPER_TRADING_SQLITE_PATH — デフォルト data/paper_trading.db（paper_trading モード用）
- PAPER_FILL_MODE — instant | partial | never | reject（paper_trading 挙動）
- LOG_LEVEL — DEBUG/INFO/…（デフォルト: INFO）
- LOG_DIR — デフォルト logs/
- MONITOR_POLL_INTERVAL — 監視ポーリング（秒）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動削除するか（0/1）
- PID_FILE_PATH / KILL_FLAG_PATH — カスタムパス指定可

---

## 運用上の注意

- Monitoring は本番の SQLITE_PATH を常に使用するため、monitoring を開発環境で動かす際は別途 DB パスを指定する等の配慮が必要です（Settings で上書き可能）。
- Kill Switch、stop flag（data/stop_requested.flag）、kill.flag の扱いに注意してください。`KILL_FLAG_CLEAR_ON_START=1` は開発用途でのみ推奨（本番では誤って Kill スイッチを消してしまうリスクがあるため 0 を推奨）。
- OpenAI API 呼び出し部はリトライ・フェイルセーフを備えていますが、API キー管理やコスト管理は運用側で行ってください。
- ログディレクトリの作成権限がない場合はファイル出力が無効化されコンソールのみの出力になります。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env ロード / Settings クラス
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (参照: 実装ファイルあり)
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (参照: 実装ファイルあり)
  - execution/
    - execution_engine.py (エンジン本体)
    - broker_factory.py (Broker クライアント生成)
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - data/                    — 実行時に作る想定のディレクトリ（DB / pid / flag 等）
  - utils/
    - logging_setup.py
    - process_priority.py
  - research/, portfolio/, etc.

（上記は本 README に記載されている主要ファイルを抜粋したものです。詳細はソースを参照してください。）

---

## よくある操作例

- 初期セットアップ（対話式）
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- Paper モードで Execution 起動（環境変数上書き例）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Monitoring を指定間隔で起動（環境変数で間隔変更）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート（過去期間指定）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

---

## 追加情報 / 貢献

- 依存関係や実行環境（OS 権限など）により process priority / CPU affinity の設定が失敗することがあります。警告ログが出ますが処理自体は継続します。
- テストや CI では自動 .env ロードを無効化するために環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定できます。
- バグ修正・機能追加は Issue / PR を歓迎します。ドキュメントや config/*.yaml のテンプレート生成スクリプトは別途用意してください（validate_config では config/*.yaml の存在チェックを行います）。

---

必要であれば、README にサンプル .env テンプレートや systemd / supervisor 用のサービスユニット例、Docker / docker-compose の簡易構成例を追加できます。どの情報を優先して追加しましょうか？