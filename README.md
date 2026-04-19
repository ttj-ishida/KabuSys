# KabuSys

日本株向け自動売買システムのコードベース（README）。このファイルはリポジトリに含まれるスクリプト群・ユーティリティの概要、セットアップ方法、使い方、およびディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を行うためのライブラリ／実行スクリプト群です。主な機能は以下の通りです。

- ExecutionEngine（発注エンジン）: ブローカークライアントを介して発注管理、リスク管理、再突合（reconcile）等を行う。
- Monitoring（監視）: システム稼働状況、データ鮮度、注文ログ、リスク指標を定期的に収集・永続化し、Kill Switch による安全停止を実現。
- Portfolio Construction（ポートフォリオ構築）: 候補選定、重み付け、ポジションサイズ計算、セクター上限等の純粋関数群。
- Research（リサーチ）: DuckDB 上の市場データからファクター（モメンタム、バリュー、ボラティリティ等）を計算・解析する。
- AI（ニュースNLP／レジーム検出）: OpenAI（gpt-4o-mini）を利用したニュースのセンチメント評価、マクロセンチメントを使った市場レジーム判定。
- ツール: Paper Trading の検証レポート生成、設定ウィザード、設定検証 CLI など。

設計上の特徴:
- SQLite（監視・発注履歴）および DuckDB（分析用）を利用。
- Paper Trading（シミュレーション）モードでは本番 DB と完全分離（data/paper_trading.db 等）。
- 環境変数 / .env による設定管理。.env の自動読み込み機構あり（必要に応じて無効化可能）。
- ログはコンソール(stdout) とファイル（日次ローテーション）に出力。

---

## 機能一覧（主要なもの）

- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用して paper_trading DB に記録。
  - run_monitoring.py: SystemMonitor のポーリングループを起動（デフォルト 60 秒間隔）。MONITOR_POLL_INTERVAL で上書き可能。

- 設定関連
  - config_setup.py: 対話式ウィザードで .env を作成・更新。
  - validate_config.py: .env および config/*.yaml の検証 CLI。

- 監視・リスク関連
  - monitoring/monitoring_db.py: 監視ログの永続化（SQLite）。
  - monitoring/system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py: 監視ロジックとアラート／Kill Switch。
  - monitoring/kill_switch.py: data/kill.flag による ExecutionEngine 停止シグナル。

- ポートフォリオ構築（純粋関数）
  - portfolio/portfolio_builder.py: 候補選定、等重・スコア重み付け。
  - portfolio/position_sizing.py: 株数計算、上限・集約キャップ、単元株丸め。
  - portfolio/risk_adjustment.py: セクター制限、レジーム乗数。

- リサーチ
  - research/factor_research.py: momentum / volatility / value などのファクター計算（DuckDB ベース）。
  - research/feature_exploration.py: 将来リターンの計算、IC 計測、統計サマリー。

- AI（OpenAI）
  - ai/news_nlp.py: ニュース記事を LLM で評価して ai_scores テーブルへ書き込み。
  - ai/regime_detector.py: ETF(1321) の MA とマクロニュースを組合せて市場レジームを判定。

- ツール
  - tools/paper_verification_report.py: Paper Trading DB から検証レポートを生成。

---

## セットアップ手順

前提:
- Python 3.10 以降（コードで `X | None` 等の構文を使用）
- git リポジトリのルートにプロジェクトファイル (.env/.env.local, config/, data/ 等) を置く想定

1. リポジトリをクローン / ワークディレクトリへ移動
   - git clone ...
   - cd <project_root>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須: duckdb, psutil, openai
   - オプション: PyYAML（config/*.yaml のパース検証に使用）
   例:
     pip install duckdb psutil openai
     pip install pyyaml   # 任意

   （プロジェクトに requirements.txt がある場合はそれを使用）

4. 環境変数設定（.env）
   - 対話式で作成:
     python -m kabusys.config_setup
   - 手動で作成: ルートに `.env` ファイルを置き、必要なキーを設定してください。
     主な必須環境変数:
       JQUANTS_REFRESH_TOKEN
       KABU_API_PASSWORD
     推奨・デフォルト:
       KABUSYS_ENV=development | paper_trading | live  (default: development)
       DUCKDB_PATH=data/kabusys.duckdb
       SQLITE_PATH=data/monitoring.db
       PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
       LOG_LEVEL=INFO

   - 自動読み込み:
     パッケージ起動時、プロジェクトルートを .git または pyproject.toml で検出し、`.env` と `.env.local` を自動読み込みします。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も厳密に失敗扱いにする場合:
     python -m kabusys.validate_config --strict

6. データディレクトリの作成（必要に応じて）
   - data/ ディレクトリや logs/ はスクリプト起動時に自動作成されますが、権限等で作成できない場合は手動で用意してください。

---

## 使い方（主要スクリプト）

- ExecutionEngine を起動
  - 通常（本番 or 開発）:
    KABUSYS_ENV によって動作が変わります。
    - 本番: KABUSYS_ENV=live
    - ペーパートレード: KABUSYS_ENV=paper_trading
  - 起動:
    python -m kabusys.run_execution
  - 動作
    - プロセス優先度を high に設定（可能な環境で）
    - Settings から DB パス等を読み取り、SQLite / DuckDB に接続
    - Paper trading の場合は paper_sqlite_path に接続し MockBrokerClient を使用（本番 DB と分離）
    - `data/stop_requested.flag` が存在すると起動しない／稼働中に検知すると停止する
    - PID ファイル: data/execution.pid

- Monitoring を起動
  - 起動:
    python -m kabusys.run_monitoring
  - 動作
    - プロセス優先度を high に設定
    - Settings.sqlite_path（本番用の sqlite_path）を使用して監視テーブルを初期化
    - DuckDB に接続
    - SystemMonitor.check_once() をポーリング実行
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）
    - 停止フラグ: data/stop_requested.flag を検知するとループ終了

- 設定ウィザード
  - python -m kabusys.config_setup
  - 対話式で .env を生成 / 更新します。

- 設定検証
  - python -m kabusys.validate_config
  - .env の必須キー、DB パス、config/*.yaml の存在や YAML パース（PyYAML 必須）をチェックします。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 簡易レポート（稼働率、注文成功率、送信率、レイテンシ等）を標準出力に出力

- AI / レジーム判定
  - OpenAI API キー: 環境変数 OPENAI_API_KEY を設定するか、API を呼ぶ関数に明示的に渡してください。
  - 関数利用例（Python API）:
      from kabusys.ai import score_news
      score_news(duckdb_conn, target_date, api_key="...")

      from kabusys.ai.regime_detector import score_regime
      score_regime(duckdb_conn, target_date, api_key="...")

- ライブラリ API（Python 内から呼び出す）
  - Research:
      from kabusys.research import calc_momentum, calc_volatility, calc_value
  - Portfolio:
      from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - Monitoring DB:
      from kabusys.monitoring.monitoring_db import MonitoringDB
  - 設定クラス:
      from kabusys.config import settings

---

## 重要な環境変数（主なもの）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）。default: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力先ディレクトリ（default: logs）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動読み込みを無効化

---

## 停止・Kill Switch の取り扱い

- 停止フラグ（管理用）
  - data/stop_requested.flag
    - run_execution / run_monitoring の起動ループでチェックされる停止フラグ。作成されるとスクリプトは安全に停止します。
- Kill Switch（自動停止）
  - monitoring/kill_switch.py は条件（ドローダウン超過、ポジション上限超過など）を満たした場合に `data/kill.flag` を書き込みます。
  - ExecutionEngine は起動時に kill_flag_clear_on_start（Settings）で自動クリアの挙動を制御します（本番では通常 0 を推奨）。
  - kill.flag が存在すると、ExecutionEngine 側は停止シグナルを受け取ってプロセスを停止します。

---

## ログ設定

- 共通ユーティリティ: kabusys.utils.logging_setup.setup_logging
  - stdout（StreamHandler） + 日次ローテートファイル（TimedRotatingFileHandler）をルートロガーに設定
  - デフォルトディレクトリ: logs/
  - 日次ローテーション、30日分保持
  - ログレベルは引数 > 環境変数 LOG_LEVEL > INFO の順で決定

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュールとスクリプトの抜粋です。実際のリポジトリではさらにファイル・サブディレクトリが存在します。

- src/
  - kabusys/
    - __init__.py
    - config.py                 # 環境変数 / Settings
    - config_setup.py           # .env ウィザード
    - validate_config.py        # 設定検証 CLI
    - run_execution.py          # ExecutionEngine 起動スクリプト
    - run_monitoring.py         # Monitoring 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - (trade_monitor.py, alert_manager.py 等のモジュールが想定)
    - utils/
      - logging_setup.py
      - process_priority.py

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  （これらはプロジェクトに合わせて用意／編集）

- data/
  - monitoring.db (デフォルト SQLite)
  - paper_trading.db (ペーパートレード用)
  - kill.flag
  - stop_requested.flag
  - execution.pid

- logs/
  - execution.log
  - monitoring.log
  - ...（日次ローテーション）

---

## 補足／開発者向けメモ

- DuckDB と SQLite を併用しています。DuckDB は分析用途（prices_daily / raw_financials 等）、SQLite は監視・トレードログや簡易永続化に使われます。
- AI モジュールは OpenAI の Chat Completions API（gpt-4o-mini）を使う想定です（OpenAI SDK の互換性に注意）。
- config/*.yaml は存在しないと警告になります。validate_config.py は PyYAML が存在すると YAML のパース検証も行います。
- .env は絶対にリポジトリにコミットしないでください（config_setup.py のヘッダに注意書きがあります）。
- テストのために自動環境読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

もし README の内容をプロジェクトの実際の README.md として保存する場合、必要に応じて「依存関係の正確なバージョン」「Python のサポート範囲」「CI / デプロイ手順」「もっと詳細な API リファレンス」を付け加えることを推奨します。補足すべき点や、あるモジュールの詳細な説明が必要であれば教えてください。