# KabuSys

日本株向け自動売買システムのライブラリ / 実行スクリプト群。  
バックテスト・ポートフォリオ構築・注文実行・監視・AIを用いたニュース評価などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

このリポジトリは以下の主要機能を持ちます。

- ExecutionEngine：発注ロジックとリスク管理を含む実行エンジン（本番 / ペーパートレード対応）。
- Monitoring：システム状態・注文状況・リスクを監視し、アラートや Kill Switch を発動。
- Portfolio 構築：候補選定、重み算出、ポジションサイジング、セクター制約などの純粋関数群。
- Research：DuckDB を使ったファクタ計算・特徴量探索用ユーティリティ。
- AI モジュール：ニュースを LLM で評価（sentiment scoring）、市場レジーム判定（regime scoring）。
- CLI ユーティリティ：
  - 環境設定ウィザード（`.env` 作成支援）
  - 設定検証ツール（環境変数・config YAML のチェック）
  - Paper Trading 検証レポート生成スクリプト

---

## 主な機能一覧

- 実行（Execution）
  - 本番 / ペーパートレード切替（`KABUSYS_ENV`）
  - MockBroker を用いたペーパートレード（DB を本番と分離）
  - リスク管理（ポジション上限、ドローダウン等）
- 監視（Monitoring）
  - CPU / メモリ / ディスク / プロセス生存チェック
  - 注文の滞留・約定異常の検出
  - Kill Switch 発動（`data/kill.flag`）によるExecutionEngine停止指示
- ポートフォリオ構築
  - 候補選定、等金額 / スコア加重、リスクベースのサイジング、セクター制約
- 研究（Research）
  - モメンタム／ボラティリティ／バリューなどのファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI（OpenAI）
  - ニュースのセンチメントスコア算出（`gpt-4o-mini` を想定）
  - マクロニュースと指数 MA 乖離を組み合わせた市場レジーム判定
- ツール
  - .env 対話式ウィザード（`python -m kabusys.config_setup`）
  - 設定検証（`python -m kabusys.validate_config`）
  - Paper Trading 検証レポート（`python -m kabusys.tools.paper_verification_report`）

---

## 必要条件 / 依存パッケージ

最低限の実行に必要な主なパッケージ（pip インストール例）:

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（`validate_config` で YAML の検証を行う場合に任意）

例：
pip install duckdb psutil openai PyYAML

（プロジェクトに requirements.txt がある場合はそちらを使用してください。）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

3. `.env` の初期作成（対話式ウィザードを推奨）
   - python -m kabusys.config_setup
   - ウィザードの指示に従って J-Quants トークン、kabu API パスワード等を設定します。

4. 設定検証
   - python -m kabusys.validate_config
   - 必須環境変数や config/*.yaml の存在、DB パスの親ディレクトリ等をチェックします。
   - `--strict` を付けると警告も失敗として扱います。

5. 必要な初期ディレクトリ
   - data/（データファイル、pid、flag 等）
   - logs/（デフォルトのログ出力先）

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
  - paper_trading の場合、Execution は専用 DB（PAPER_TRADING_SQLITE_PATH）を使用
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB、デフォルト: data/paper_trading.db）
- DUCKDB_PATH（分析用 DuckDB、デフォルト: data/kabusys.duckdb）
- OPENAI_API_KEY（AI 機能使用時に必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意、アラート通知用）
- LOG_LEVEL（ログレベル、デフォルト: INFO）
- LOG_DIR（ログ出力先、デフォルト: logs/）
- MONITOR_POLL_INTERVAL（監視ループのポーリング間隔（秒）、デフォルト: 60）
- PAPER_FILL_MODE（ペーパートレードの約定モード、instant|partial|never|reject、デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START（Execution 起動時に kill.flag を自動クリアするか、0/1、デフォルト: 0）

注意:
- Monitoring（run_monitoring）は KABUSYS_ENV にかかわらず本番用 sqlite_path（SQLITE_PATH）を使用します（設計上の意図）。
- Execution（run_execution）は KABUSYS_ENV=paper_trading の場合は PAPER_TRADING_SQLITE_PATH を使用して本番 DB と分離します。

---

## 使い方（実行例）

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine（注文実行エンジン）起動
  - python -m kabusys.run_execution
  - ペーパートレードに切り替える: KABUSYS_ENV=paper_trading を設定する（.env に記載）

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH を参照）

- AI モジュール（プログラム的使用）
  - `kabusys.ai.score_news(conn, target_date, api_key=...)` を呼び出してニューススコアを生成し ai_scores テーブルへ保存します。
  - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)` で市場レジームを判定・保存します。
  - いずれも OpenAI API キー（OPENAI_API_KEY）が必要です。

ログ:
- デフォルトは logs/ にアプリ別ログ（execution.log, monitoring.log 等）を日次ローテーションで出力します。`LOG_DIR` で変更可能。

停止制御:
- 実行中プロセスを停止するにはプロジェクトの data/ ディレクトリに stop/kill フラグファイルを作成します。
  - run_execution と run_monitoring は `data/stop_requested.flag` の存在を検出すると安全に終了処理を行います。
  - KillSwitch は `data/kill.flag` を書き込むことで ExecutionEngine に停止を指示します。

---

## ディレクトリ構成（主なファイル）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数・設定読み込みロジック
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 起動前設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity 設定
  - execution/               — Execution 関連（Engine, BrokerFactory, OrderManager 等）
  - monitoring/
    - monitoring_db.py      — SQLite テーブル定義・永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュースを LLM で評価し ai_scores へ書込み
    - regime_detector.py     — マクロ + ETF MA によるレジーム判定
  - tools/
    - paper_verification_report.py

補足:
- DB 関連
  - SQLite は監視・トレード履歴やペーパートレード保存に使用（SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）
  - DuckDB は分析（research、AI の集計等）用途（DUCKDB_PATH）
- ローカルデータ/ログのデフォルト場所は project_root/data や project_root/logs です。`.env` で上書き可能。

---

## 開発・運用上の注意

- .env は秘密情報を含むため Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）では特に LINE の通知設定や KILL_FLAG_CLEAR_ON_START の値に注意してください。`validate_config` に本番向けのチェックがあります。
- Monitoring は本番監視用 DB（SQLITE_PATH）を常に参照します。テストする際は意図的に DB パスを切り替えてください。
- AI 機能は OpenAI の料金・レート制限の影響を受けます。API 呼び出しのリトライや部分失敗時の保護ロジックが実装されていますが、運用設計（バッチサイズ、API キー管理等）に注意してください。
- プロセス優先度変更や CPU affinity の設定は psutil に依存し、OS によって挙動が異なります。権限不足で設定に失敗するケースはログに警告が出ます。

---

README はこのコードベースの概要と運用上の重要点をまとめたものです。実装の詳細や設計資料（PortfolioConstruction.md / StrategyModel.md 等）が別途参照できる場合はそちらも合わせてご確認ください。質問や補足があれば教えてください。