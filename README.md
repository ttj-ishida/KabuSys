# KabuSys

日本株向け自動売買システム（KabuSys）のリポジトリ向け README。  
この README はコードベースの主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

- バージョン: 0.1.0（src/kabusys/__init__.py）

---

## プロジェクト概要

KabuSys は日本株自動売買のためのフレームワークです。以下の主要な責務を持ちます。

- 戦略（ファクター計算・特徴量解析）
- ポートフォリオ構築（候補抽出・重み付け・株数算出）
- 発注 ExecutionEngine（本番 / ペーパートレード対応）
- 監視（システム状態・注文・リスク監視、Kill Switch）
- AI 支援（ニュースの NLP によるセンチメント評価、レジーム判定）
- ツール（ペーパートレード検証レポート生成、設定ウィザード、設定検証）

設計上の特徴:
- DuckDB を使った分析用 DB（prices_daily / raw_financials 等）
- SQLite を使った監視 / 発注ログ（デフォルトで data/monitoring.db / data/paper_trading.db）
- OpenAI を利用したニュース NLP（gpt-4o-mini を想定）
- 本番（live）とペーパートレード（paper_trading）を明確に分離

---

## 機能一覧

主な機能とモジュール
- 実行系
  - run_execution.py: ExecutionEngine 起動スクリプト（KABUSYS_ENV により本番/ペーパートレードを切替）
  - BrokerClientFactory を経由して本番ブローカー／Mock ブローカーを注入
- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト
  - monitoring package: SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine / MonitoringDB
  - kill.flag / stop_requested.flag を用いた停止・Kill Switch
- ポートフォリオ構築
  - portfolio package: 候補選定、重み付け、ポジションサイズ決定、セクター制限、レジーム乗数
- リサーチ
  - research package: ファクター計算（モメンタム・バリュー・ボラティリティ）、将来リターン、IC 計算、統計サマリー
- AI
  - ai package: news_nlp（ニュースを OpenAI でスコアリング）、regime_detector（MA とマクロ NLP を合成）
- ユーティリティ
  - utils: ロギング設定、プロセス優先度 / CPU affinity 設定 等
- ツール
  - config_setup.py: .env を対話式に生成 / 更新するウィザード
  - validate_config.py: .env や config/*.yaml の事前検証 CLI
  - tools.paper_verification_report: ペーパートレード検証レポート生成スクリプト

---

## 動作要件（概要）

必須（概ね）
- Python 3.10+ を想定（型アノテーション等の利用から）
- パッケージ依存:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証のため。任意）
- 標準ライブラリ: sqlite3 等

実際のバージョンや追加パッケージはプロジェクトの requirements.txt / pyproject.toml を参照してください（このリポジトリに存在する場合）。

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境の作成と依存インストール
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install --upgrade pip
   - pip install duckdb psutil openai
   - （PyYAML が必要なら: pip install pyyaml）
   - 任意: pip install -e . で編集可能インストール

3. ディレクトリ作成（初回）
   - mkdir -p data logs

4. 環境変数（.env）設定
   - 対話ウィザードで作成:
     - python -m kabusys.config_setup
   - 主要な環境変数（代表例・デフォルト）:
     - KABUSYS_ENV: development | paper_trading | live  (default: development)
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, default: data/paper_trading.db)
     - PAPER_FILL_MODE (instant | partial | never | reject) (paper_trading 用挙動)
     - OPENAI_API_KEY (AI 機能を使う場合に必須)
     - LOG_LEVEL (DEBUG/INFO/...)
     - KILL_FLAG_CLEAR_ON_START (0/1)
   - .env の自動ロード:
     - src/kabusys/config.py がプロジェクトルートの .env / .env.local を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit 1）扱い

---

## 使い方（主要スクリプト）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- ExecutionEngine を起動（本番 / ペーパートレードは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 備考:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使用され、ペーパートレード DB（PAPER_TRADING_SQLITE_PATH）へ記録します。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中の停止は data/stop_requested.flag を作成するか、Kill Switch によって data/kill.flag が書き込まれると検出して停止します。
    - PID ファイル: data/execution.pid（Settings.pid_file_path）

- Monitoring（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - 備考:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト 60 秒）。
    - 監視は本番 sqlite_path を使う（KABUSYS_ENV に関わらず monitoring 用 DB は本番 DB を参照する仕様）。
    - 停止: data/stop_requested.flag を作成するとループ内で検出して終了します。

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は PAPER_TRADING_SQLITE_PATH 環境変数、未設定時は data/paper_trading.db

- AI / リサーチ関数（プログラム内呼び出し例）
  - DuckDB 接続を作成して呼び出す例:
    - import duckdb
      conn = duckdb.connect("data/kabusys.duckdb")
      from kabusys.ai.news_nlp import score_news
      from datetime import date
      score_news(conn, date(2026, 4, 1), api_key="...")  # api_key を渡すか OPENAI_API_KEY を環境変数に
  - regime_detector.score_regime も同様に呼び出せます。

---

## 主要な環境変数一覧（抜粋とデフォルト）

- KABUSYS_ENV: development | paper_trading | live (default: development)
- JQUANTS_REFRESH_TOKEN: （必須）
- KABU_API_PASSWORD: （必須）
- KABU_API_BASE_URL: http://localhost:18080/kabusapi
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject (default: instant)
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- LOG_LEVEL: INFO（DEBUG/INFO/...）
- LOG_DIR: logs/
- MONITOR_POLL_INTERVAL: 監視ループの秒数（default: 60）
- KILL_FLAG_CLEAR_ON_START: 0/1 （本番で 1 は危険）

---

## 停止／Kill の仕組み

- Stop（手動停止）:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のループで検出して安全終了します。
- Kill Switch（自動停止）:
  - monitoring の評価で条件（大幅ドローダウン等）に該当すると data/kill.flag が書き込まれます。
  - ExecutionEngine は起動時やループ中にこの flag をチェックして停止します。
- kill.flag の自動クリアは KILL_FLAG_CLEAR_ON_START で制御（本番では 0 推奨）。

---

## ログ

- ロギングは kabusys.utils.logging_setup.setup_logging を通して統一的に設定されます。
- 出力先:
  - コンソール stdout（常に）
  - 日次ローテーションでファイル: logs/<app_name>.log（デフォルトで logs ディレクトリ、30 日保存）
- ログレベルは環境変数 LOG_LEVEL または setup_logging の引数で変更可能。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys をルートとした構成の抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数／.env 自動読み込み・Settings
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/                — ExecutionEngine, OrderManager, Reconciler, BrokerFactory 等（実行系）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（注）上記はコードベースの要点のみ列挙しています。詳細は該当ファイルの docstring を参照してください。

---

## よくある運用メモ / トラブルシューティング

- .env を Git にコミットしないこと（config_setup にもその旨の注意が記載されています）。
- DB パスの親ディレクトリが未作成でも自動作成されることがありますが、権限やパス誤設定に注意してください。
- OpenAI を使う機能は API キーとネットワークが必須。API エラーはリトライやフォールバックロジックがありますが、キー未設定だと例外になります。
- run_monitoring はデフォルトで本番 monitoring DB（sqlite_path）を使用します。開発で monitoring を実行する場合は sqlite_path を別 DB に変更すると本番データを汚しません。
- MONITOR_POLL_INTERVAL に不正な値を設定するとデフォルト (60s) にフォールバックします。
- プロセス優先度設定は OS によって挙動が異なり、権限不足で警告が出る場合があります（psutil を使用）。

---

README はこのコードベースの概要と主要な操作手順に焦点を当てています。実装や挙動の詳細は各モジュールの docstring / ソースコメントを参照してください。必要であれば運用手順（systemd ユニット、Dockerfile、CI 設定等）のテンプレートも作成できます。必要な場合は目的を教えてください。