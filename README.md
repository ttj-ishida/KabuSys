# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買システム用ライブラリ・ツール群です。戦略・ポートフォリオ構築、実行エンジン、監視、研究用ユーティリティ、ニュースNLP / レジーム判定などを含みます。

---

## 概要

- モジュール化された自動売買基盤（戦略計算・ポジションサイズ算出・発注管理・リスク管理）。
- 実行（ExecutionEngine）と監視（MonitoringEngine）は別プロセスとして起動可能。
- Paper Trading（ペーパートレード）用に本番 DB と分離されたモードをサポート。
- DuckDB を用いた研究／ファクター計算、SQLite を用いた監視ログ永続化。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価や市場レジーム判定機能（APIキー必須）。
- .env ベースの環境設定ウィザード & 設定検証 CLI を提供。

---

## 主な機能一覧

- Execution
  - 実行エンジン起動スクリプト（python -m kabusys.run_execution）
  - ブローカークライアント工場（実運用 / モック切替）
  - リスク管理、リコンサイル、注文管理、発注履歴記録（SQLite）
- Monitoring
  - システム状態・データ鮮度・注文状況の定期チェック（python -m kabusys.run_monitoring）
  - Kill Switch（条件に応じた停止フラグ生成）
  - アラート送信フック（LINE 等）
- Portfolio / Strategy（純関数）
  - 候補選定、重み計算、ポジションサイズ決定、セクター制約、レジーム乗数
- Research
  - DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）等
- AI
  - ニュース NLP による銘柄単位センチメント評価（kabusys.ai.score_news）
  - レジーム判定（kabusys.ai.regime_detector.score_regime）
- ツール
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
- 設定管理
  - 対話式 .env 作成（python -m kabusys.config_setup）
  - 起動前設定検証 CLI（python -m kabusys.validate_config）

---

## セットアップ手順（開発者向け）

1. Python 環境
   - 推奨: Python 3.10+
   - 仮想環境を作成・有効化してください。

2. 依存パッケージのインストール（例）
   - 必須ライブラリ（プロジェクトの使用機能に依存）:
     - duckdb
     - psutil
     - openai
     - （オプション）PyYAML（config/*.yaml の構文チェック用）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ 本リポジトリに requirements.txt がない場合は、必要なパッケージを上記のように個別にインストールしてください。

3. 環境変数設定
   - 対話式ウィザードで .env を作成するのが簡単です:
     - python -m kabusys.config_setup
   - あるいはリポジトリルートに `.env` を作成して手動で設定してください。
   - 自動ロード:
     - `kabusys.config` はプロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` / `.env.local` を自動的に読み込みます。
     - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. 最低限必要な環境変数（.env に設定）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - OPENAI_API_KEY（AI 機能を使う場合）
   - KABUSYS_ENV（development / paper_trading / live。デフォルト: development）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB。デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB。デフォルト: data/paper_trading.db）
   - LOG_LEVEL（例: INFO）
   - そのほか README 末尾のサンプル参照

5. データディレクトリ
   - ログ: logs/
   - DB・フラグ: data/
   - 起動時にディレクトリが自動作成されますが、権限等に注意してください。

---

## 使い方（実行例）

- 設定検証
  - python -m kabusys.validate_config
  - 警告もエラー扱いにする場合: python -m kabusys.validate_config --strict

- .env 対話式ウィザード
  - python -m kabusys.config_setup

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading DB（PAPER_TRADING_SQLITE_PATH）へ記録します。
    - 実行中は data/execution.pid に PID が記録され、停止は data/stop_requested.flag を作成して指示できます。

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用してログを保存します。
  - 停止はプロジェクトルートの `data/stop_requested.flag` を作成してください。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI（プログラムから呼び出す）
  - ニュース NLP（銘柄別スコアを ai_scores テーブルへ書く）
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")
  - レジーム判定
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

- ログ
  - デフォルト出力先: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
  - ローテーション: 日次、30日保持

---

## 注意事項 / 実装上のポイント

- 環境分離
  - Monitoring は常に `SQLITE_PATH`（production 監視 DB）を参照します。
  - Execution は `KABUSYS_ENV=paper_trading` の場合 `PAPER_TRADING_SQLITE_PATH` を使用して本番 DB と完全分離します。
- Kill / Stop
  - Kill Switch（危険時の停止指示）は `data/kill.flag` を書き込みます（KillSwitch クラス）。
  - 実行停止（外部指示）は `data/stop_requested.flag` を作成すると run_* スクリプトが検知して停止します。
- .env パース
  - シングル／ダブルクォートや export プレフィックス、インラインコメントに対応した独自パーサを使用しています。
- OpenAI
  - API 呼び出しはリトライ／バックオフを実装していますが、APIキー未設定の場合は例外を投げるかフェイルセーフ（0.0）で継続する箇所があります。
- DuckDB / SQLite
  - DuckDB は分析用（prices_daily / raw_financials / raw_news 等のスキーマ想定）。
  - monitoring.db（SQLite）は監視ログ用に init でテーブル作成・マイグレーション処理を行います。

---

## 主要ディレクトリ構成

（リポジトリルートに src/ 配下でパッケージ化されています。以下は主要ファイル/ディレクトリの抜粋）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数読み込み / Settings
  - config_setup.py            — .env 対話式ウィザード（CLI）
  - validate_config.py         — 起動前設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - ai/
    - news_nlp.py              — ニュース NLP スコアリング
    - regime_detector.py       — 市場レジーム判定
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py        — システム・データ鮮度監視
    - risk_monitor.py          — ドローダウン / ポジション上限監視
    - trade_monitor.py         — （注文関連監視: 省略されたが存在想定）
    - monitoring_engine.py     — モニタ束ねループ
    - kill_switch.py           — kill.flag 管理
    - alert_manager.py         — アラート送信（LINE 等、実装箇所）
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 発注株数計算・単元丸め・キャップ適用
    - risk_adjustment.py       — セクター制約・レジーム乗数
  - research/
    - factor_research.py       — Momentum/Volatility/Value ファクター計算（DuckDB）
    - feature_exploration.py   — 将来リターン・IC・統計サマリー
  - utils/
    - logging_setup.py         — 統一ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity 設定ユーティリティ

- data/
  - （デフォルトの SQLite / PID / フラグ / paper_trading DB 等が置かれる想定）
  - stop_requested.flag
  - kill.flag
  - execution.pid
  - monitoring.db (デフォルト)
  - paper_trading.db (ペーパートレード時)

- logs/
  - execution.log
  - monitoring.log
  - ... （アプリ名ごとに日次ローテーション）

---

## サンプル .env（最低限）

例:
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

注意: .env は絶対にソース管理に含めないでください。

---

## 追加情報 / 開発メモ

- config.py はプロジェクトルートを探索して .env 自動読み込みを行います（テスト時などに無効化可能）。
- monitoring_db.init_monitoring_db は冪等的にテーブル作成および簡単なマイグレーションを行います。
- AI 関連は API 呼び出しの失敗に比較的寛容に設計されており、部分失敗でもシステム全体が停止しないようになっています。
- ログディレクトリの作成に失敗した場合はファイル出力をスキップしてコンソール（stdout）のみで継続します。

---

必要であれば README にサンプルコマンド、より詳しい環境変数一覧（全キーと意味）、データベーススキーマ、運用手順（デプロイ / systemd / Supervisor 用の例）などを追記できます。どの情報を追加しますか？