# KabuSys

日本株向け自動売買システム（ライブラリ / 起動スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注実行・監視・解析・AI補助機能を含む自動売買プラットフォームの主要コンポーネントをまとめた実装です。

バージョン: 0.1.0

---

## 概要

- コア機能をモジュール化（execution, monitoring, portfolio, research, ai, utils 等）。
- 起動スクリプト（ExecutionEngine / Monitoring）を提供し、プロダクション運用を意識した設計（ログローテーション、プロセス優先度設定、フラグファイルによる停止など）。
- Paper Trading（ペーパートレード）モードをサポートし、本番DBと分離して検証可能。
- DuckDB を使ったリサーチ・ファクター計算、SQLite を使った監視ログ永続化。
- OpenAI（gpt-4o-mini）を利用したニュースNLP / レジーム判定モジュール（APIキーが必要）。

---

## 機能一覧

- 起動スクリプト
  - run_execution: ExecutionEngine の起動（KABUSYS_ENV により本番 / paper_trading 切替）
  - run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔調整）
- 環境設定 / 検証
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: .env と config/*.yaml の検証 CLI
- 監視
  - monitoring_db: SQLite ベースの監視ログ（system_status, trade_logs, positions, risk_logs, dashboard）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine
- 発注関連（execution パッケージ）
  - BrokerClientFactory 等（実コードは別ファイル群に依存）
  - ExecutionEngine（PIDファイル、停止フラグ対応、paper_trading 用DB分離）
- ポートフォリオ構築（純粋関数）
  - 銘柄選定、重み付け、ポジションサイズ計算、セクターキャップ、レジーム乗数
- 研究・解析
  - research パッケージ: ファクター計算（momentum/value/volatility）、特徴量解析（IC, forward returns）
- AI サポート
  - news_nlp: ニュース記事を LLM でセンチメント評価して ai_scores に書き込み
  - regime_detector: ETF の MA とマクロニュースを合わせて市場レジーム判定
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成

---

## 前提・依存関係

推奨 Python バージョン: 3.10+

主な依存パッケージ（最低限）:
- duckdb
- psutil
- openai
- (任意) PyYAML — validate_config で YAML の中身検証を行う場合

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（requirements.txt がある場合は `pip install -r requirements.txt` を使用してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・依存関係インストール（上記参照）

3. 初期環境変数設定（.env の作成）
   - 対話式ウィザードを利用:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは .env（デフォルト）を生成・更新します。重要な必須項目:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - KABUSYS_ENV: development | paper_trading | live
     - （AI機能を使う場合）OPENAI_API_KEY を環境変数として設定

   - 自動ロード:
     - 起動時にプロジェクトルート（.git または pyproject.toml がある階層）から `.env` と `.env.local` を自動読み込みします（既存 OS 環境変数を保護）。
     - 自動ロードを無効化する場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

4. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   # 警告をエラー扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ作成（必要に応じて）
   - デフォルト SQLite / DuckDB / ログは `data/`, `logs/` に作成されます。権限やマウントを確認してください。

---

## 使い方（起動方法 / 主要コマンド）

- ExecutionEngine を起動
  - 本番（KABUSYS_ENV=live）または開発（development）:
    ```
    python -m kabusys.run_execution
    ```
  - Paper Trading（ペーパートレード）:
    - .env で `KABUSYS_ENV=paper_trading` を設定すると、MockBrokerClient を使用し DB は `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に記録されます。

  挙動:
  - 起動時にプロセス優先度を "high" に設定
  - `data/stop_requested.flag` が既に存在する場合は起動せず終了
  - 起動中に `data/stop_requested.flag` を作成するとエンジンが停止する
  - PID ファイルは `data/execution.pid`（設定により変更可）

- Monitoring（監視ループ）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - デフォルトポーリング間隔: 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で秒数を上書き可能（正の整数）。
  - Monitoring は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用して監視情報を記録。
  - 停止: `data/stop_requested.flag` を置くとループが終了します。

- .env 作成・更新（対話式）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # デフォルト DB は data/paper_trading.db。--db で別ファイルを指定可。
  ```

---

## 主要環境変数（抜粋）

- KABUSYS_ENV: execution モード（development | paper_trading | live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_DIR: ログディレクトリ（デフォルト: logs/）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

注意: .env の自動読み込み順は OS 環境 > .env.local > .env。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ログ・監視・停止

- ログ:
  - 共通の logging 設定ユーティリティ `kabusys.utils.logging_setup.setup_logging` を通じて stdout と日次ローテーションファイル（logs/<app_name>.log）へ出力します。
  - ログ保管期間はデフォルト 30 日。

- 監視 DB:
  - `kabusys.monitoring.monitoring_db.init_monitoring_db` により必要テーブルを作成・マイグレーションします。
  - 監視テーブル: system_status, trade_logs, positions, risk_logs, dashboard

- 停止シグナル:
  - `data/stop_requested.flag` を作成すると run_execution / run_monitoring のループが終了します（外部プロセスからの安全な停止手段）。
  - KillSwitch（監視側）が条件に応じて `data/kill.flag` を書き込み、ExecutionEngine に停止を促すことがあります（Settings.kill_flag_clear_on_start を用いて起動時に自動クリアするか制御）。

---

## OpenAI（AI機能）に関する注意

- news_nlp や regime_detector は OpenAI API（gpt-4o-mini）を利用します。使用には `OPENAI_API_KEY` が必要です。
- API 呼び出しはリトライ・バックオフやレスポンスの厳密なバリデーションを行いますが、利用にあたってはレート制限・課金に注意してください。
- API キー未設定時、該当関数は ValueError を送出するか、安全にスキップする設計の箇所があります（実装により挙動は異なります）。

---

## ディレクトリ構成

省略可能なファイルは除き、主要な構成を示します:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - execution/                — 発注関連（BrokerClientFactory, ExecutionEngine, OrderManager 等）
  - monitoring/
    - monitoring_db.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (ランタイムで生成される想定データディレクトリ)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - stop_requested.flag, kill.flag, execution.pid など

---

## 運用上の注意点

- 本番運用時は KABUSYS_ENV=live を設定し、.env の設定を慎重に行ってください（validate_config は live 時に追加チェックを実施します）。
- `.env` は機密情報を含むため決してリポジトリにコミットしないでください。
- run_execution / run_monitoring はプロセス優先度の設定や PID 管理を行います。権限不足により一部処理がスキップされる場合があります（ログに警告が出ます）。
- Paper Trading は本番 DB と完全に分離されるよう設計されています。テストや検証は Paper Trading モードで行ってください。

---

この README はコードベースの主要部分を簡潔にまとめたものです。詳細な API や内部設計、さらなるセットアップ手順は該当モジュール（kabusys/ 以下）内の docstring を参照してください。必要であれば、各コンポーネント向けの詳細ドキュメントを別途作成します。