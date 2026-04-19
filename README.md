# KabuSys

日本株向け自動売買システムのリファレンス実装です。  
このリポジトリは取引実行エンジン、監視機構、ポートフォリオ構築・ポジションサイジング、リサーチ/ファクター計算、ニュース/NLP を用いた補助機能などを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール群で構成されています。

- 実際の注文送信処理（ExecutionEngine）およびペーパートレード実行
- システム稼働状況・データ鮮度・注文状況などの監視（Monitoring）
- ポートフォリオ構築（候補選定・重み付け）とポジションサイズ計算
- リサーチ用ファクター計算（DuckDB を利用した価格・財務データ処理）
- ニュース記事を LLM（OpenAI）でスコアリングする機能と市場レジーム判定
- 運用支援ツール（.env ウィザード、設定検証、Paper Trading レポート生成 等）

設計方針の一部:
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV により挙動を切替）
- .env / 環境変数で設定管理（自動ロード機能あり）
- ログは統一的にセットアップ（コンソール + 日次ローテートファイル）
- 外部 API 呼び出しは明確に分離。LLM 呼び出しはフェイルセーフでリトライ実装あり。

---

## 主な機能一覧

- run_execution.py: ExecutionEngine 起動（本番 / paper_trading 切替、BrokerFactory でクライアント生成）
  - paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
- run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可能）
- monitoring: SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager 等
- portfolio: 候補選定、等重・スコア重み、リスク調整（セクター上限）、ポジションサイズ計算
- research: ファクター計算（モメンタム・バリュー・ボラティリティ）・将来リターン・IC 計算 等
- ai:
  - news_nlp.score_news: OpenAI によるニュースセンチメント集計 → ai_scores テーブル書込み
  - regime_detector.score_regime: ETF の MA とマクロ記事の LLM スコア合成によるレジーム判定
- utils:
  - logging_setup: 統一ログ設定（stdout + TimedRotatingFileHandler）
  - process_priority: プロセス優先度 / CPU affinity 設定
- tools:
  - paper_verification_report: Paper Trading データから検証レポートを生成
- config_setup.py: 対話式 .env 作成ウィザード
- validate_config.py: 環境変数 / config/*.yaml の事前検証 CLI

---

## 動作環境・前提

- Python 3.10 以上（型注記の | ユニオン等を使用）
- 必要な Python パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証に必要、任意）
- 標準ライブラリ: sqlite3, logging, pathlib など

（実際の導入時は requirements.txt を用意して pip install -r でインストールしてください）

---

## セットアップ手順

1. リポジトリをチェックアウトし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate もしくは .venv\Scripts\activate

2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （requirements.txt がある場合は pip install -r requirements.txt）

3. .env の作成（対話式推奨）
   - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な設定:
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

5. データディレクトリ作成
   - デフォルトでは data/ や logs/ にファイルを作成します。権限やマウント先の確認を推奨。

---

## 基本的な使い方（起動 / 実行）

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は paper_trading DB（PAPER_TRADING_SQLITE_PATH）を使用
    - プロセス優先度を "high" に設定（可能な場合）
    - data/execution.pid に PID を書きます（設定により変更可）
    - 起動時に data/stop_requested.flag が存在すると起動せず終了

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（デフォルト 60）
  - 監視は Settings.sqlite_path（監視 DB）を常に使用（KABUSYS_ENV に依存せず）
  - data/stop_requested.flag を作成するとループを終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを明示可（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 関連（プログラム API）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数）
  - 例: DuckDB 接続を渡してニューススコアを取得・書込
    - from openai import OpenAI
    - import duckdb
    - conn = duckdb.connect("data/kabusys.duckdb")
    - import kabusys.ai.news_nlp as nn
    - nn.score_news(conn, target_date, api_key="sk-...")

- 停止（外部シグナル）
  - 監視・実行ループを強制的に止めたい場合はプロジェクトルートの data/stop_requested.flag ファイルを作成します（両スクリプトはこのファイルをチェックして正常終了します）。
  - KillSwitch は条件を満たすと data/kill.flag を書き、ExecutionEngine に停止要求を出します。kill.flag の削除は明示的に行うか、KillSwitch.clear() を使用します。

---

## 主要設定・環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能利用時）
- LOG_LEVEL（デフォルト: INFO）
- MONITOR_POLL_INTERVAL（監視のポーリング間隔[秒]、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START（本番での自動クリアは危険。デフォルトは 0）

簡易 .env 例:
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
OPENAI_API_KEY=sk-...

---

## ログ / PID / フラグファイル

- ログ:
  - デフォルト出力先: logs/<app_name>.log（日次ローテート、30日分保持）
  - コンソールは stdout に出力
  - ログ設定は kabusys.utils.logging_setup.setup_logging を各起動スクリプトで呼び出しています

- PID ファイル:
  - 実行エンジンは data/execution.pid（Settings.pid_file_path で上書き可）

- 停止 / キルフラグ:
  - data/stop_requested.flag: 手動で作成すると run_* スクリプトが検知して終了
  - data/kill.flag: KillSwitch が書き込み、ExecutionEngine に停止要求を出す（本番ガード）

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py              — 環境変数 / .env 自動ロード / Settings
  - config_setup.py        — .env 対話作成ウィザード
  - validate_config.py     — 起動前設定検証 CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - execution/             — Execution 関連の実装（BrokerFactory, Engine 等）
  - data/                  — 実行時生成される DB / フラグ / PID 等（data/*.db, data/*.flag）

（上記は主要モジュールのみ抜粋。細かな補助モジュールや未記載ファイルがあります。）

---

## 注意事項・運用メモ

- KABUSYS_ENV=live の場合は本番作業です。LINE 通知等の設定ミスはアラート欠落につながるため validate_config で十分に確認してください。
- run_monitoring は監視 DB（Settings.sqlite_path）を常に使用します。環境に関わらず監視データは本番用 DB に保管される設計です。
- paper_trading 環境は DB を分離します（PAPER_TRADING_SQLITE_PATH）。ペーパートレード中のログが本番 DB に混ざりません。
- OpenAI（または他の外部 API）を利用する機能は API キーやコストに注意して使用してください。通信エラーや 5xx はリトライロジックで扱いますが、API 呼び出し頻度には配慮が必要です。
- DB マイグレーション: monitoring_db.init_monitoring_db は既存 DB に対して列追加を行う簡易マイグレーションを含みます（冪等）。

---

## 開発・拡張のヒント

- DuckDB 接続を渡して research モジュールを呼び出すだけでローカル分析が可能（外部 API 不要）
- news_nlp と regime_detector は OpenAI クライアントの呼び出し部分を抑制/モックすればテスト容易
- logging_setup を各スクリプトで呼んでいるため、ログ挙動は統一済み。ローカルでは LOG_DIR 環境変数で出力先を変更可能

---

この README はコードベースの主要点をまとめたものです。詳細は各モジュールの docstring（ソース内コメント）を参照してください。質問や追加のドキュメント化が必要であれば教えてください。