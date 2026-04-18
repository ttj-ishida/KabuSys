# KabuSys

日本株向け自動売買プラットフォームのサブコンポーネント群（ライブラリ + 起動スクリプト群）。

このリポジトリは、以下の機能を提供するモジュール群で構成されています（シグナル生成／ポートフォリオ構築／発注実行／監視／AI 補助解析 等）。本 README は開発者・運用者向けのセットアップおよび使い方ガイドです。

## プロジェクト概要
- 目的: 日本株の自動売買ワークフローを構築するための共通コンポーネント群。
- 設計方針:
  - DuckDB / SQLite を用いたローカルデータ参照・永続化（本番・ペーパートレードを分離）
  - LLM（OpenAI）を活用したニュースセンチメント / レジーム判定機能
  - モニタリング（プロセス生存／データ鮮度／リスク監視）と Kill Switch 機構
  - 可搬性を重視し環境変数（.env）で設定を管理

## 主な機能一覧
- 実行エンジン起動スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading 時は MockBroker を使用し、paper_trading DB を利用して本番とデータを分離します。
- 監視プロセス起動スクリプト
  - run_monitoring.py: SystemMonitor をポーリングして system_status / risk_logs / trade_logs 等を記録。MONITOR_POLL_INTERVAL によるポーリング間隔上書きに対応。
- 設定関連ツール
  - config_setup.py: .env の対話式ウィザード（作成・更新支援）
  - validate_config.py: .env と config/*.yaml の整合性検証 CLI（--strict オプションあり）
- 解析 / 研究用モジュール
  - research: ファクター計算（momentum/value/volatility）、特徴量解析（IC, summary）
  - portfolio: 候補選定、重み算出、ポジションサイズ計算、セクター制限、レジーム乗数
- AI モジュール
  - ai/news_nlp.py: ニュースを LLM でスコアリングし ai_scores テーブルへ書込む
  - ai/regime_detector.py: ETF MA と LLM を組合せた市場レジーム判定
- 運用ツール
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポートを出力
- ユーティリティ
  - utils/logging_setup.py: 一貫したログ設定（コンソール + 日次ローテートファイル）
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定
- 監視周り
  - monitoring: SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch / DB 層

## 依存関係（主要）
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を利用する場合)
- PyYAML（validate_config.py が YAML を検証する場合に推奨）
- 標準ライブラリ: sqlite3, threading, logging, datetime など

依存は環境に合わせて requirements.txt / Poetry 等で管理してください。

## セットアップ手順（ローカル開発向け）
1. リポジトリをチェックアウトし、仮想環境を作成・有効化する:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール:
   - pip install -r requirements.txt
   （requirements.txt がない場合は上の主要パッケージを個別にインストールしてください）

3. .env を作成（対話式ウィザード推奨）:
   - python -m kabusys.config_setup
   ウィザードで入力した内容がプロジェクトルートの `.env` に保存されます。

4. 設定検証:
   - python -m kabusys.validate_config
   - 本番前は `--strict` を付けて警告も失敗扱いにできます:
     python -m kabusys.validate_config --strict

5. ディレクトリ・ファイル
   - デフォルトでは以下ファイル/ディレクトリに DB / PID / フラグが保存されます（必要に応じて .env で上書き）:
     - data/monitoring.db (SQLite, 監視ログ用)
     - data/paper_trading.db (ペーパートレード用 SQLite)
     - data/kabusys.duckdb (DuckDB 分析用)
     - data/execution.pid
     - data/kill.flag
     - data/stop_requested.flag
     - logs/ (ログファイル: logs/execution.log, logs/monitoring.log 等)

## 主要な環境変数（.env 例）
必須:
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_password_here

一般 / 推奨（デフォルト値を示します）:
- KABUSYS_ENV=development|paper_trading|live (default: development)
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- LOG_LEVEL=INFO
- LOG_DIR=logs
- OPENAI_API_KEY=（AI 機能使用時に設定）
- PAPER_FILL_MODE=instant|partial|never|reject (default: instant)
- KILL_FLAG_CLEAR_ON_START=0 (production 推奨)

（config_setup.py を使うと上の多くを対話式で生成できます）

## 使い方（起動と実行）
- ExecutionEngine（発注エンジン）起動:
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は paper_trading DB を使用し MockBrokerClient を利用（本番 DB を汚さない）
    - 起動時に data/stop_requested.flag が存在すると起動を中止します
    - data/execution.pid に PID を書きます
    - プロセス優先度を high に設定しようとします（psutil 権限が必要な場合あり）

- Monitoring（監視プロセス）起動:
  - python -m kabusys.run_monitoring
  - 挙動:
    - SystemMonitor のポーリングを継続（デフォルト 60 秒）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定可能（例: MONITOR_POLL_INTERVAL=30）
    - 監視は設定の sqlite_path（monitoring.db）を使用（環境に依存せず本番 DB を参照）

- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告でも exit(1)（CI 用）

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: env の PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能（ライブラリ関数として利用）
  - ニューススコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらをコマンドラインから直接呼ぶ軽量スクリプトは含まれていません（ライブラリ関数として呼び出す設計）。
  - OpenAI を使用する場合は OPENAI_API_KEY を環境変数に設定するか、関数呼び出し時に api_key を渡してください。

## 運用上の注意点
- 監視（monitoring）は設定された sqlite_path（デフォルト data/monitoring.db）を常に使用します。KABUSYS_ENV に関係なく監視 DB は本番パスを使う設計です。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_trading 用 DB を使用して本番と完全分離されます。
- Kill Switch:
  - RiskMonitor / KillSwitch によって条件が合致すると data/kill.flag が書き込まれ、ExecutionEngine に停止を要求できます。
  - 本番では KILL_FLAG_CLEAR_ON_START を 0（クリアしない）に設定することを推奨します。
- プロセス優先度や CPU affinity の設定には OS 権限が必要な場合があります。psutil の例外は警告扱いでスキップされます。
- ログは logs/ に日次ローテートで保存されます。ログディレクトリの作成に失敗した場合はコンソール出力のみになります。
- .env は絶対に Git にコミットしないでください（config_setup のヘッダにも警告あり）。

## ディレクトリ構成（主要ファイル）
（パッケージルート = src/kabusys を前提）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込みロジック
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (参照: 実装あり)
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (参照: 実装あり)
  - execution/                 — Execution / Order 関連（Engine, BrokerFactory, OrderManager 等）
  - portfolio/                 — portfolio_builder, position_sizing, risk_adjustment
  - research/                  — factor_research, feature_exploration
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                      — 既定の DB / PID / flag を置くディレクトリ（実行時に自動作成されることがある）

（リポジトリ全体のファイルは上記以外にも多数のモジュールがあります。ここでは主要な整理を示しています。）

## 開発・テストのヒント
- 単体テストでは環境変数の自動ロードを無効化できます:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- AI 呼び出し部分は外部クライアント呼び出しをラップした関数で行っているため、unittest.mock で簡単に差し替えてテストできます。
- DuckDB 接続を渡して関数単位で検証できる設計です（副作用を極力排除した純粋関数が多い）。

---

不明点や追加で README に載せたい事例（例: systemd / supervisor 用の起動 unit、Dockerfile、CI 設定例など）があれば教えてください。必要に応じて運用手順やトラブルシューティング節を追加します。