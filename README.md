# KabuSys

日本株自動売買システム（KabuSys）の簡易ドキュメント。  
本リポジトリはトレーディングエンジン、監視・アラート、ポートフォリオ構築、研究用ファクター計算、AI を使ったニュースセンチメント評価などの機能を含むモジュール群で構成されています。

---

## プロジェクト概要

KabuSys は日本株自動売買に必要な以下の主要機能を持つ Python パッケージです。

- ExecutionEngine（発注エンジン）：ブローカークライアントを通じて注文を発行・管理
- Monitoring（監視）：システム状態・注文状態・リスク（ドローダウン・ポジション数）を定期監視し、必要時に Kill Switch を発動
- Portfolio construction：候補選定、重み付け、ポジションサイズ計算、セクター制約などの純粋関数群
- Research：DuckDB を用いたファクター計算・将来リターン・統計解析
- AI：OpenAI（gpt-4o-mini 等）でニュースを評価して銘柄別スコアを生成・保存
- ユーティリティ：設定ウィザード・設定検証・ログ設定・プロセス優先度設定など

本 README はローカル開発／デプロイ時に必要なセットアップ手順、実行方法、ディレクトリ構成をまとめたものです。

---

## 主な機能一覧

- 環境設定ウィザード（.env 生成 / 更新）: python -m kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml 検査）: python -m kabusys.validate_config [--strict]
- ExecutionEngine 起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db 等）に記録
- Monitoring 起動: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で監視ポーリング間隔（秒）を変更可能（デフォルト 60 秒）
  - 監視は本番用の sqlite_path を使用（KABUSYS_ENV に依らず）
- Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- AI ニューススコアリング（プログラム API）: kabusys.ai.score_news(conn, target_date, api_key=None)
- 市場レジーム判定（プログラム API）: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- ポートフォリオ構築用純粋関数群（候補選定・重み付け・ポジションサイズ計算・セクター制約など）
- ログ出力は stdout と日次ローテートファイル（logs/<app_name>.log）を併用

---

## セットアップ手順

1. Python 環境を準備
   - 推奨: Python 3.9+
   - 仮想環境を作成して有効化（venv / conda 等）

2. 依存パッケージをインストール
   - 必要パッケージ（主なもの）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config/*.yaml の検証を行う場合）
   - 例（pip）:
     pip install duckdb psutil openai pyyaml

3. リポジトリルートで `.env` を作成
   - 対話式ウィザードを推奨:
     python -m kabusys.config_setup
   - ウィザード実行後、設定を検証:
     python -m kabusys.validate_config
     （--strict を付けると警告も失敗として 1 を返します）

4. データディレクトリ作成（通常は自動作成されますが、手動で作る場合）:
   mkdir -p data logs

5. 必須環境変数
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - OPENAI_API_KEY（AI 機能を使う場合必須）
   - 上記は .env に記載してください（.env は Git にコミットしないこと）

基本的な .env の最小例（参考）
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

注意: .env.example を参照して適切に設定してください。

---

## 実行方法（使い方）

- 設定検証
  - python -m kabusys.validate_config
  - 重要なチェック（必須 env, KABUSYS_ENV 値, DB パス確認, YAML パース etc.）

- 環境設定ウィザード（.env 作成/更新）
  - python -m kabusys.config_setup

- ExecutionEngine 起動
  - 実行:
    python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード専用の SQLite（PAPER_TRADING_SQLITE_PATH）に記録
    - 起動時に data/stop_requested.flag があると起動しない
    - 実行中に data/stop_requested.flag が作成されると停止処理が行われます
    - 実行時に execution.pid（デフォルト data/execution.pid）を作成してプロセス監視に使用

- Monitoring 起動
  - 実行:
    python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）を上書き（デフォルト 60）
  - 動作:
    - SystemMonitor / TradeMonitor / RiskMonitor を使って監視を行う
    - 監視は sqlite_path（本番 DB）を使用（環境に依存しない）
    - data/stop_requested.flag を検知すると監視ループを終了
    - KillSwitch は条件を満たすと data/kill.flag を書き込み、ExecutionEngine 停止の合図を出す

- 強制停止 / 停止フロー
  - 両プロセスを止める一般的な手順:
    - data/stop_requested.flag を作成すると run_execution / run_monitoring は検知して終了します
    - KillSwitch（条件に応じて）data/kill.flag を作成し ExecutionEngine に停止指示を出します
  - 設定例:
    echo "stop" > data/stop_requested.flag

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 環境変数 PAPER_TRADING_SQLITE_PATH を指定して DB を変更可能

- AI 関連（プログラム API）
  - ニューススコアリング:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーが必要（api_key 引数または環境変数 OPENAI_API_KEY）
  - 市場レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 主要環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY（AI 機能を使う場合）
- KABUSYS_ENV（development | paper_trading | live、デフォルト development）
  - paper_trading: 発注はモック。データベースは paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用
  - live: 本番挙動（実発注等）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視 DB のデフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパー用 DB のデフォルト data/paper_trading.db）
- LOG_LEVEL（デフォルト INFO）
- MONITOR_POLL_INTERVAL（run_monitoring 用: ポーリング間隔秒）
- PID_FILE_PATH（ExecutionEngine の PID ファイル path、デフォルト data/execution.pid）
- KILL_FLAG_PATH（KillSwitch が書き込むファイル、デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動でクリアするか: 0/1、本番では 0 を推奨）

---

## ログと DB

- ログ:
  - stdout（コンソール）と logs/<app_name>.log に日次ローテーションで出力
  - ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一

- DB:
  - DuckDB: 分析用（prices_daily, raw_financials, raw_news 等）
  - SQLite: 監視ログ（monitoring.db）およびペーパートレード用（paper_trading.db）
  - Monitoring 用テーブルは init_monitoring_db() によって自動作成 / マイグレーションされる

---

## ディレクトリ構成（主要部分）

src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings 管理
- config_setup.py          — 対話式 .env ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

subpackages:
- ai/
  - news_nlp.py            — ニュースの LLM スコアリング
  - regime_detector.py     — マクロ + MA200 を使ったレジーム判定
- portfolio/
  - portfolio_builder.py   — 候補選定・重み計算
  - position_sizing.py     — 発注株数決定、スケーリング、単元丸め
  - risk_adjustment.py     — セクター上限・レジーム乗数
- research/
  - factor_research.py     — Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- monitoring/
  - monitoring_db.py       — SQLite 永続化レイヤ（テーブル作成・CRUD）
  - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - risk_monitor.py        — ドローダウン / ポジション上限監視
  - trade_monitor.py       — （注文履歴の健全性検査 ※実装参照）
  - kill_switch.py         — kill.flag の生成/評価
  - monitoring_engine.py   — 各 Monitor の束ね（テスト用 run_once / run ループ）
  - alert_manager.py       — （通知周りを担当、実装参照）
- execution/
  - execution_engine.py    — エンジン本体（セッション実行）
  - broker_factory.py      — ブローカークライアント生成（Mock/実装）
  - order_manager.py       — オーダー管理
  - order_repository.py    — 発注ログ保存 (SQLite)
  - reconciler.py          — ブローカーとローカル状態の整合
  - risk_manager.py        — 注文前のリスクチェック
- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity 設定
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

（注）一部ファイルはこの README のコードスニペットに含まれない補助スクリプト・ファイルがある場合があります。詳細は各モジュールの docstring を参照してください。

---

## 運用上の注意

- 本番環境（KABUSYS_ENV=live）では設定を慎重に行ってください。validate_config は本番用の追加警告を出力します。
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- kill.flag / stop_requested.flag / pid ファイル等は data/ ディレクトリに作成されます。自動クリア設定（KILL_FLAG_CLEAR_ON_START=1）は本番での誤動作につながる恐れがあるため推奨しません。
- OpenAI API を使用する処理は API 呼び出しに失敗した場合フォールバック（0.0 等）して安全に継続する設計ですが、API キーや料金に注意してください。

---

## 開発者向けメモ

- DuckDB 接続を渡すだけでデータ参照やファクター計算を行う設計のため、研究用途で本番口座にアクセスする必要はありません。
- 多くの関数は純粋関数（副作用なし）または DB 接続を受けてのみ永続化する実装になっています。単体テストが書きやすい設計です。
- ロギング、プロセス優先度設定、DB 初期化は起動スクリプトで統一的に行われます（setup_logging, set_process_priority, init_monitoring_db）。

---

問題や追加のドキュメント化したい箇所があれば、どの機能について詳しく記載するか教えてください。