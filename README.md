# KabuSys

日本株向け自動売買システム（ライブラリ／実行スクリプト集）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に関するオーケストレーション・ツール群です。  
主な目的は次のとおりです。

- 戦略のためのファクター計算・特徴量探索（DuckDB を用いたリサーチ機能）
- ポートフォリオ構築・ポジションサイジングの純粋関数群
- 実行エンジン（ExecutionEngine）と監視コンポーネント（Monitoring）
- Paper Trading（切り離された SQLite DB を利用）と本番運用の切替
- ニュースの NLP（OpenAI）を用いたセンチメント評価および市場レジーム判定
- 運用用ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード・検証ツール 等）

設計方針として「できるだけ副作用を減らし、DB は明示的パスで分離」「本番とペーパーはデータベースで分離」「LLM 呼び出しはフェイルセーフに」などが採用されています。

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 設定ウィザード: `python -m kabusys.config_setup`
  - 設定検証: `python -m kabusys.validate_config`
- 実行エンジン（run_execution.py）
  - 本番 / paper_trading の切替（KABUSYS_ENV）
  - Paper Trading 時は専用 SQLite（data/paper_trading.db）を使用
  - プロセス優先度設定、PID 管理、停止フラグ対応
- 監視（run_monitoring.py / monitoring package）
  - SystemMonitor, TradeMonitor, RiskMonitor を用いた定期監視
  - MonitoringDB（SQLite）へのログ永続化
  - Kill Switch（条件により data/kill.flag を作成して Execution を停止）
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等重／スコア重み、ポジションサイジング、セクターキャップ、レジーム補正
- リサーチ（kabusys.research）
  - Momentum, Volatility, Value などのファクター計算（DuckDB 経由・SQL 実装）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計
- AI（kabusys.ai）
  - news_nlp: ニュース記事を集約して OpenAI（gpt-4o-mini 等）でセンチメント評価し ai_scores に書き込む
  - regime_detector: ETF (1321) の MA200乖離 と マクロニュースセンチメントを合成して market_regime を作成
  - OpenAI 利用は API キー（OPENAI_API_KEY）が必要
- ツール
  - Paper Trading の検証レポート生成: `python -m kabusys.tools.paper_verification_report`

---

## 前提（推奨）

- Python 3.10+
  - ソース内で型アノテーションに `X | None` を使っているため 3.10 以上を想定
- 必要な Python ライブラリ（主なもの）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（設定 YAML の検証を行う場合に推奨）
- ファイル／ディレクトリ:
  - data/（DB・フラグファイルが置かれる）
  - logs/（ログ出力先）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ
   - git clone ... && cd repo

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 例:
     pip install duckdb psutil openai
     # 設定検証で YAML 検証をする場合:
     pip install PyYAML

   （プロジェクトに requirements.txt があればそれを利用してください。）

4. .env の作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - もしくは手動で `.env` を作成（プロジェクトルート） — 最低必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（抜粋）
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR
     - OPENAI_API_KEY: （AI 機能利用時に必須）

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いになります:
     python -m kabusys.validate_config --strict

6. data/ と logs/ のディレクトリが自動作成されますが、必要なら手動で作成して権限を確認してください。

---

## 使い方（実行例）

- 監視ループを起動（継続実行）
  - MONITOR_POLL_INTERVAL で秒を指定可能（デフォルト 60 秒）
  - python -m kabusys.run_monitoring
  - 例（30秒間隔）:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使い、データは `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）に記録されます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- AI 機能（コードから呼ぶ）
  - OpenAI API キーを環境変数にセットしておく: OPENAI_API_KEY=...
  - 例（regime_detector を直接呼ぶ）:
    - Python REPL / スクリプト内で:
      from datetime import date
      import duckdb
      from kabusys.ai.regime_detector import score_regime
      conn = duckdb.connect("data/kabusys.duckdb")
      score_regime(conn, date(2026, 4, 1))

注意:
- AI 呼び出しはネットワーク・API 失敗時にフォールバックする設計ですが、API キーが未設定だと例外になります。
- ExecutionEngine 側は `data/kill.flag`（Kill Switch）を監視し、フラグが書かれると停止処理が開始されます。手動停止用のファイルは `Settings.kill_flag_path` に対応。

---

## 主要な環境変数（抜粋）

必須（最小限）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要な設定:
- KABUSYS_ENV: development | paper_trading | live
  - paper_trading: MockBroker を使用し DB を分離
  - live: 本番運用（注意して設定）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- OPENAI_API_KEY: OpenAI を使用する場合に必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒（整数）
- PID_FILE_PATH / KILL_FLAG_PATH 等は Settings で参照可能（デフォルトは data 以下）

より詳細は `src/kabusys/config.py` を参照してください。

---

## 動作・運用に関する注意事項

- Paper Trading は本番 DB と完全分離されることを意図しています。`KABUSYS_ENV=paper_trading` を利用することで `PAPER_TRADING_SQLITE_PATH` に記録されます。
- 監視（Monitoring）は本番の sqlite_path を常に参照する実装（run_monitoring の挙動に注意）。
- ログ:
  - デフォルトで `logs/<app_name>.log` に日次ローテートで保存（30日保持）
  - `kabusys.utils.logging_setup.setup_logging` を使って統一されたログ出力が行われます
- Kill Switch:
  - `kabusys.monitoring.kill_switch.KillSwitch` が条件判定して `data/kill.flag` を書き込むことで ExecutionEngine に停止シグナルを与えます
- プロセス優先度:
  - 起動時に `set_process_priority("high")` が呼ばれます（Linux/Windows 対応。権限不足時は警告でスキップ）
- DB マイグレーション:
  - `monitoring_db.init_monitoring_db` はテーブル作成と簡易マイグレーション（カラム追加）を行います（冪等）

---

## ディレクトリ構成（抜粋）

以下は主要ファイル配置の概略（`src/kabusys` 以下）。

- kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py  (参照あり)
    - kill_switch.py
    - alert_manager.py  (参照あり)
    - monitoring_engine.py
  - execution/
    - execution_engine.py (参照あり)
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/ (上記)
  - tools/
    - __init__.py
    - paper_verification_report.py

プロジェクトルートには `.env.example` / `pyproject.toml` / `.git` 等が存在する想定です。

---

## 参考（よくあるコマンドまとめ）

- .env 作成（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 監視プロセス起動
  - python -m kabusys.run_monitoring
- 実行エンジン起動
  - python -m kabusys.run_execution
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
- AI 機能（スクリプト／REPL から呼び出し）
  - OPENAI_API_KEY を設定してから `kabusys.ai` モジュールの関数を使用

---

もし README に追加したい「実行フロー図」「データベーススキーマ一覧」「構成ファイル（config/*.yaml）の説明」などがあれば、その内容に沿ってサンプルや詳細ドキュメントを作成します。必要な情報（実行例、運用手順、環境変数テンプレート 等）を教えてください。