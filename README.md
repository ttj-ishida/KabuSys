# KabuSys

日本株自動売買システムの Python コードベース用 README（日本語）

この README はリポジトリ内の主要スクリプト／モジュールの概要、セットアップ、実行方法、ディレクトリ構成などをまとめたものです。

重要: .env ファイルにはシークレット（APIキー等）を含めるため、絶対に Git にコミットしないでください。

---

## プロジェクト概要

KabuSys は日本株の自動売買やそれに付随するモニタリング／リサーチ／AI スコアリング機能を提供するコード群です。  
主な機能は次の通りです。

- ExecutionEngine：注文実行／リスク管理／注文再調整（本番/ペーパートレード対応）
- Monitoring：システム状態・注文状況・リスクを定期的に監視し、警告や停止フラグを書き込む
- Portfolio Construction：候補選定・重み付け・ポジションサイズ計算（純粋関数）
- Research：DuckDB の時系列データを使ったファクター計算・特徴量解析
- AI：ニュースの NLP によるセンチメントスコアリング、レジーム判定（OpenAI）
- CLI ツール：.env ウィザード、設定検証、Paper Trading 検証レポート生成 など

---

## 主な機能一覧

- 環境分離
  - KABUSYS_ENV により `development` / `paper_trading` / `live` を切替
  - ペーパートレード時は専用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離

- 実行・監視
  - run_execution: ExecutionEngine 起動（PID 管理、stop フラグ監視）
  - run_monitoring: SystemMonitor のポーリングループ（MONITOR_POLL_INTERVAL で間隔指定可）

- モニタリング DB（SQLite）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルを管理
  - マイグレーション（カラム追加）の冪等処理あり

- ポートフォリオ構築（純粋関数）
  - 候補選定、等金額／スコア加重、リスクベースの株数計算
  - セクターキャップやレジーム乗数の適用

- リサーチ（DuckDB）
  - momentum / volatility / value 等のファクター計算
  - 将来リターン、IC（Spearman）計算、ファクター統計

- AI（OpenAI）
  - ニュースのセンチメント集約（gpt-4o-mini を想定、JSON mode 利用）
  - 市場レジーム判定（ETF の MA200 とマクロセンチメントを合成）

- CLI ユーティリティ
  - config_setup：.env の対話式作成・更新
  - validate_config：.env & config/*.yaml の前提チェック
  - tools.paper_verification_report：Paper Trading 検証レポート生成

---

## 必要条件（開発環境）

- Python 3.10+
- OS: Linux / macOS / Windows（process priority 等はプラットフォーム依存の挙動あり）
- 外部ライブラリ（主なもの）:
  - duckdb
  - psutil
  - openai
  - pyyaml（config YAML を検証する場合に必要）
- SQLite は標準ライブラリで動作

インストール例（仮の requirements がないため手動で）:
```
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install duckdb psutil openai pyyaml
```

（実際のプロジェクトでは requirements.txt / poetry / pipfile を用意することを推奨します）

---

## セットアップ手順

1. リポジトリをクローンしてソースを取得する
2. Python 仮想環境を作成して依存ライブラリをインストールする（上記参照）
3. .env を作成する
   - 対話式ウィザードを利用:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動で `.env` を作成し、必須項目を設定:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live; デフォルト development）
     - OPENAI_API_KEY（AI 機能を利用する場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB。デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパー用 DB。デフォルト: data/paper_trading.db）
     - LOG_LEVEL（デフォルト: INFO）
4. 設定検証（起動前チェック）:
   ```
   python -m kabusys.validate_config
   # 警告を FAIL としたい場合:
   python -m kabusys.validate_config --strict
   ```
5. データディレクトリ作成（必要に応じて）
   - `data/` と `logs/` は起動時に自動作成されることが多いですが、権限等の確認を行ってください。

---

## 使い方（実行例）

- ExecutionEngine を起動（本番 or ペーパーは KABUSYS_ENV に依存）:
  ```
  python -m kabusys.run_execution
  ```
  - 実行中に `data/stop_requested.flag` を作成すると安全に終了します（スクリプトが検知して停止）。
  - ExecutionEngine は pid ファイルを `data/execution.pid`（Settings.pid_file_path デフォルト）に書きます。
  - Paper Trading（KABUSYS_ENV=paper_trading）の場合は MockBrokerClient を使用し、ペーパー DB (`data/paper_trading.db` または PAPER_TRADING_SQLITE_PATH) に記録します。

- Monitoring を起動（定期ポーリング）:
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
  - Monitoring は常に本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを残します。
  - 停止: `data/stop_requested.flag` を作成するとループを抜けます。

- .env の対話式セットアップ:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI スコアリング / レジーム判定（プログラム的に呼ぶ場合）
  - news_nlp.score_news(conn, target_date, api_key=...)
  - regime_detector.score_regime(conn, target_date, api_key=...)
  - これらは DuckDB 接続（duckdb.connect(...) の返り値）を渡して呼び出します。
  - OPENAI_API_KEY が環境変数に設定されていれば api_key 引数は省略可能。

---

## 主要ファイルと挙動（簡易説明）

- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト。Paper Trading では専用 DB に切替。stop フラグ・PID 管理あり。

- src/kabusys/run_monitoring.py
  - SystemMonitor をポーリングするループ。MONITOR_POLL_INTERVAL で間隔調整可。

- src/kabusys/config.py
  - 環境変数の読み込み・ラッパー。プロジェクトルートの .env / .env.local を自動で読み込む（無効化可）。

- src/kabusys/config_setup.py
  - .env の対話式ウィザード。デフォルトや現在値の取り込み、シークレットのマスク表示など。

- src/kabusys/validate_config.py
  - 起動前チェック CLI。必須環境変数や config/*.yaml の存在・簡易パースを行う。

- src/kabusys/monitoring/*
  - monitoring_db.py：SQLite テーブル定義 / DB 操作ラッパー（MonitoringDB）
  - system_monitor.py：システムリソース・データ鮮度・PID チェック
  - risk_monitor.py：ドローダウン・ポジション上限監視（RiskMonitor）
  - kill_switch.py：条件により data/kill.flag を書く KillSwitch
  - monitoring_engine.py：複数 Monitor を束ねた実行エンジン

- src/kabusys/portfolio/*
  - portfolio_builder.py：候補選定・等重/スコア重み算出
  - risk_adjustment.py：セクターキャップ、レジーム乗数
  - position_sizing.py：株数計算、lot 単位丸め、aggregate cap

- src/kabusys/research/*
  - factor_research.py / feature_exploration.py：DuckDB を用いたファクター計算・IC・統計

- src/kabusys/ai/*
  - news_nlp.py：ニュース記事を集約して OpenAI に投げ、ai_scores に書き込む
  - regime_detector.py：ETF MA とマクロセンチメントを合成して market_regime テーブルに書き込む

- src/kabusys/utils/*
  - logging_setup.py：統一ロギング（stdout + 日次ローテートファイル）
  - process_priority.py：psutil を用いたプロセス優先度 / CPU affinity 設定（プラットフォーム差分吸収）

---

## ディレクトリ構成

（リポジトリの src/kabusys 以下を抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - risk_monitor.py
      - trade_monitor.py (この README 作成時点では省略)
      - kill_switch.py
      - monitoring_engine.py
    - utils/
      - logging_setup.py
      - process_priority.py

プロジェクトルートには .env, data/, logs/ 等が想定されます（初回は自動作成される場合あり）。

---

## 重要なファイル／フラグの場所（デフォルト）

- data/monitoring.db — 監視用 SQLite（Settings.sqlite_path）
- data/paper_trading.db — ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）
- data/kabusys.duckdb — DuckDB（Settings.duckdb_path）
- data/execution.pid — ExecutionEngine の PID（Settings.pid_file_path）
- data/kill.flag — KillSwitch が書き込む停止フラグ（Settings.kill_flag_path）
- data/stop_requested.flag — run_* スクリプト群がポーリングで監視している停止フラグ
- logs/<app_name>.log — 日次ローテートされるログファイル（logs ディレクトリ）

---

## 知っておくと良い注意点

- 本番（KABUSYS_ENV=live）では LINE 通知等の設定が未配置だとアラートが届きません。validate_config による事前確認を推奨します。
- Monitoring は監視ログに対して常に「本番の sqlite_path」を使用します。ペーパートレード DB とは分離されます。
- AI（OpenAI）関連は API キーの管理に注意してください。過剰なリクエストは課金やレート制限の原因になります。
- run_execution / run_monitoring の安全停止は `data/stop_requested.flag` の作成で行えます（外部からファイルを置く）。KillSwitch はリスク条件により `data/kill.flag` を書き、エンジンを停止させるトリガーになります。
- ログディレクトリ作成に失敗した場合はコンソールログのみで継続する設計です。

---

この README はコードベースの主要な利用方法と構成をまとめたものです。詳細な設計やアルゴリズム（PortfolioConstruction.md、StrategyModel.md 等）は別ドキュメントを参照してください。必要であれば README を拡張してインストール手順や CI / デプロイ方法、詳細な設定例を追加します。