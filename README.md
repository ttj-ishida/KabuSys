# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買システム向けライブラリおよび実行スクリプト群です。取引エンジン（ExecutionEngine）、監視（Monitoring）機能、ポートフォリオ構築、研究用ファクター計算、AI を使ったニュースセンチメント評価などのコンポーネントを備えています。本 README はリポジトリの利用開始手順、主要機能、起動方法、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

- 自動売買エンジン（ExecutionEngine）とそれを監視・運用するための監視モジュール群を提供します。
- ペーパートレード（paper_trading）モードをサポートし、本番データベースと完全分離された SQLite（data/paper_trading.db）に記録できます。
- DuckDB を使ったリサーチ・ファクター計算（prices_daily / raw_financials 等を想定）や、OpenAI を用いたニュース NLP（センチメント評価）機能を含みます。
- 監視（Monitoring）ではシステム稼働状態、注文ログ、リスク（ドローダウン・ポジション上限）を定期的にチェックし、必要に応じて Kill Switch（data/kill.flag）を発動して ExecutionEngine を安全に停止できます。

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアントの抽象化（実運用 / モックによる paper_trading）
  - 注文管理・リスク管理・照合処理
- Monitoring
  - SystemMonitor：CPU/メモリ/Disk、データ鮮度（DuckDB）チェック
  - TradeMonitor：注文滞留や約定異常検出（trade_logs）
  - RiskMonitor：ドローダウン・ポジション上限の監視、ダッシュボードの upsert
  - KillSwitch：flag ファイルによる停止指示
  - MonitoringEngine：上記モニタを束ねるポーリングループ
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算・IC（Information Coefficient）や統計サマリ
- Portfolio
  - 候補選定・重み計算（等金額 / スコア重み）
  - セクター上限適用、レジーム乗数、ポジションサイズ計算（lot 単位丸め・aggregate cap）
- AI
  - news_nlp：OpenAI を使ったニュースセンチメントスコアリング（ai_scores への書き込み）
  - regime_detector：ETF MA とマクロニュースの LLM センチメントを合成して市場レジーム判定
- Utilities
  - 環境設定ウィザード（config_setup.py）で .env を対話的に生成
  - 設定検証 CLI（validate_config.py）
  - ロギング設定ユーティリティ（logs/<app>.log の日次ローテーション）
  - プロセス優先度・CPU affinity 設定ユーティリティ
- Tools
  - paper_verification_report: ペーパートレードの検証レポート生成

---

## 前提 / 必要パッケージ

- Python 3.9+（型ヒントの Union 省略記法等のため）
- 主要外部ライブラリ（少なくとも以下が必要）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（validate_config の YAML 検証を使う場合）

インストール例（pip）:
```
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. Python 仮想環境を作成・有効化（任意）
3. 必要な依存パッケージをインストール（上記参照）
4. .env の作成
   - 対話式ウィザードで作成（推奨）:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは .env.example を参考に .env を手動作成。必須項目:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（代表例）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO（例）
     - OPENAI_API_KEY: OpenAI を使う場合に必須
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時のモック約定挙動）
5. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   # strict モードで警告も失敗扱いにする場合
   python -m kabusys.validate_config --strict
   ```
   - PyYAML が入っていれば config/*.yaml のパース検証も行います。
6. DB 初期化は各スクリプトが起動時に必要テーブルを冪等的に作成します（init_monitoring_db）。

---

## 使い方（起動 / 停止）

- ExecutionEngine の起動
  - 通常（デフォルト環境に応じて DB を選択）:
    ```
    python -m kabusys.run_execution
    ```
  - ペーパートレードで起動する場合:
    - .env で `KABUSYS_ENV=paper_trading` を設定するか、環境変数を指定して起動
    - ペーパートレード時は MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録されます。

- Monitoring の起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（秒、デフォルト 60）。
  - 監視は Settings の sqlite_path（monitoring DB）と duckdb を使用します。Monitoring は環境にかかわらず本番 sqlite_path を使用します。

- 停止（外部からの停止指示）
  - run_execution および run_monitoring はプロジェクトの data ディレクトリにあるフラグファイルを参照します。
  - 両スクリプトが参照する停止フラグ: data/stop_requested.flag
    - 例: 停止させたい場合は `touch data/stop_requested.flag`（中身は任意）
  - Kill Switch（kill.flag）
    - Monitoring 内の判定により `data/kill.flag` が書き込まれると ExecutionEngine 側で停止判断を行えます（Execution 起動時に kill_flag_clear_on_start を設定していると自動クリアする挙動があるため .env の設定に注意）。
  - 実行中の ExecutionEngine は data/execution.pid に PID を書きます（プロセス管理や強制停止に利用可）。

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

---

## 環境変数の主な一覧（要点）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用 / オプション:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
  - LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs）
  - OPENAI_API_KEY: OpenAI を利用する機能で必要
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
  - PID_FILE_PATH / KILL_FLAG_PATH などは Settings 経由で参照されます
  - PAPER_FILL_MODE (paper_trading 用): instant | partial | never | reject

詳細は `kabusys.config.Settings` を参照してください。

---

## 停止 / フラグ操作の注意

- data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検知して安全に終了します（両スクリプトで利用）。
- Monitoring の KillSwitch は `data/kill.flag` を作成して ExecutionEngine に停止シグナルを送ります。Kick は冪等（既存ファイルがある場合は再書き込みしない）です。
- 本番環境（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START=0` を推奨します（意図しない自動クリアは危険）。

---

## ログ

- ログは標準出力（stdout）とファイル（logs/<app_name>.log）に出力されます。ファイルは日次ローテーション（30 日分保持）。
- ログレベルは LOG_LEVEL 環境変数や setup_logging の引数で制御します。

---

## その他の補助スクリプト

- 環境設定ウィザード（対話式）:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config [--strict]
  ```
- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report
  ```

---

## ディレクトリ構成（抜粋）

（リポジトリの src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - execution/                — 実行系ロジック（broker, engine, order_manager 等）
  - monitoring/
    - monitoring_db.py        — monitoring DB（SQLite）作成・抽象層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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
  - data/                     — デフォルト DB / PID / flag の配置想定（例: data/*.db, data/kill.flag）
  - tools/
    - paper_verification_report.py

（実際のファイル一覧はリポジトリを参照してください）

---

## 開発上の注意 / トラブルシューティング

- OpenAI を利用する機能（news_nlp, regime_detector）を使う場合は `OPENAI_API_KEY` を必ず設定してください。未設定時は ValueError が発生します。
- validate_config が PyYAML を検出できない場合、config/*.yaml の内容検証はスキップされますが起動自体は可能です。
- DuckDB / SQLite ファイルの親ディレクトリが存在しない場合は起動時に自動作成されることが多いですが、パーミッション等で失敗する場合があるため注意してください。
- プロセス優先度の設定（set_process_priority）は環境によって権限が必要です。権限不足の場合は警告ログが出てスキップされます。

---

この README はコードベースの主要ポイントを簡潔にまとめたものです。詳細な API 仕様や設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）が別途ある場合はそちらを参照してください。必要であれば起動例や API 使用例、開発フローに関する追加ドキュメントを作成します。