# KabuSys

日本株自動売買システムのコアライブラリ（モジュール群）。  
このリポジトリはシグナル生成・ポートフォリオ構築・発注エンジン・監視・AI補助モジュールなどを含む、取引システムの主要コンポーネントを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした Python 製モジュール群です。

- DuckDB / SQLite を用いたデータ処理・ストレージ
- ファクター計算・特徴量探索（research）
- ポートフォリオ構築 / ポジションサイズ決定（portfolio）
- 発注実行エンジン（execution） — 本番 / ペーパートレード切替対応
- 監視・アラート・Kill Switch（monitoring）
- ニュースの NLP スコアリング・レジーム判定（AI モジュール）
- 運用補助ツール（設定ウィザード・設定検証・検証レポート等）

設計上の特徴:
- 環境変数 / .env による構成管理
- 本番 DB とペーパートレード DB の分離
- ログはコンソール + 日次ローテーションファイル出力
- LLM を利用する処理は API キーの有無を安全に扱い、失敗時はフェイルセーフで継続

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、専用 DB（data/paper_trading.db）へ記録
  - 停止は data/stop_requested.flag / data/kill.flag によるフラグ操作で制御
- Monitoring（python -m kabusys.run_monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期ポーリングし監視ログ（SQLite）へ保存
  - MONITOR_POLL_INTERVAL でポーリング間隔を設定可能（デフォルト 60 秒）
- AI:
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
  - 市場レジーム判定（kabusys.ai.regime_detector）
  - OpenAI API（gpt-4o-mini 等）を利用。API キーは環境変数 OPENAI_API_KEY
- 研究用モジュール:
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC 計算、統計サマリ
- 運用ツール:
  - paper_trading の検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順（開発 / ローカル実行向け）

1. Python 環境を準備（推奨: 3.10+）
   - 仮想環境作成例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 最低限の依存例:
     - pip install duckdb psutil openai
   - 設定検証で YAML を検証したい場合:
     - pip install pyyaml
   - （プロジェクトに requirements.txt がある場合はそれを使用してください）

3. リポジトリルートに移動し .env を作成
   - ウィザードを使う（対話式）:
     - python -m kabusys.config_setup
   - または .env を手動作成（.env.example を参考にしてください）
   - 自動読み込み:
     - デフォルトでプロジェクトルートの `.env` および `.env.local` を自動ロードします
     - 自動ロードを無効にするには: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定検証（必須環境変数などをチェック）
   - python -m kabusys.validate_config
   - 警告も許容しない厳密モード:
     - python -m kabusys.validate_config --strict

5. データディレクトリ作成（必要に応じて）
   - data/ logs/ 等は起動時に自動作成される場合がありますが、権限に注意してください。

---

## 環境変数（主要なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要（代表例）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、発注は MockBrokerClient を使用し、別 sqlite（PAPER_TRADING_SQLITE_PATH）へ記録
- OPENAI_API_KEY: OpenAI を利用する AI 機能用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: monitoring 用ポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行エンジン監視・停止制御関連

詳細は kabusys.config.Settings のプロパティにコメントがあります。`.env` は絶対に VCS にコミットしないでください。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定するとペーパートレードモードで起動します
  - 停止: data/stop_requested.flag を作成するとループ終了 → Engine 停止
  - Kill Switch: monitoring 側から data/kill.flag が書き込まれると ExecutionEngine 停止のトリガーに

- Monitoring 起動（プロセス監視・アラート）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite パス指定可。環境変数 PAPER_TRADING_SQLITE_PATH も使用可。

- AI 機能（スクリプトから利用）
  - OpenAI API キーが必要（OPENAI_API_KEY または引数で指定）
  - 例: kabusys.ai.score_news / kabusys.ai.score_regime を呼び出して ai_scores / market_regime に書き込み

---

## ロギング / 実行環境

- ログ設定は kabusys.utils.logging_setup.setup_logging で統一
  - コンソール(stdout) と日次ローテーションファイル（logs/<app_name>.log）を出力
- プロセス優先度設定: kabusys.utils.process_priority.set_process_priority を使用し、起動時に優先度を high に設定しています（権限により失敗する場合は警告のみ）

---

## 監視 / 停止フラグ

- 停止フラグ（run_monitoring / run_execution の停止連携）:
  - data/stop_requested.flag — 実行スクリプト側で監視し、存在するとループを終了します
- Kill Switch:
  - monitoring モジュールが条件（ドローダウン超過等）を満たすと data/kill.flag を書き込み、ExecutionEngine を停止させる仕組みがあります
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアします（本番では 0 推奨）

---

## ディレクトリ構成

（重要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数読み込み・Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング
    - regime_detector.py      — 市場レジーム判定
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (参照)
    - kill_switch.py
    - alert_manager.py (参照)
  - execution/                 — 発注関連コンポーネント群（OrderManager 等）
  - utils/
    - logging_setup.py
    - process_priority.py

data/ や logs/ は実行時に使用されるファイル群（SQLite/duckdb ファイル、pid/flag、ログ）です。

---

## 開発・運用上の注意

- .env は絶対に Git 等へコミットしないこと。
- 本番（KABUSYS_ENV=live）時は LINE 通知や kill switch 設定等を十分確認してください。
- OpenAI を用いる機能は API コスト・レイテンシに注意し、API キーの管理を厳格に行ってください。
- monitoring は本番 sqlite_path を参照するよう設計されています（環境にかかわらず監視 DB は共通を利用）。
- paper_trading モードは発注系を分離しているため実運用の安全確認に便利ですが、シミュレーション挙動は実際の発注とは異なります。

---

## よく使うコマンドまとめ

- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

必要に応じて README に追記します。特に CI / デプロイ手順や requirements.txt、systemd / Supervisor 用のサービスユニット例が必要であれば教えてください。