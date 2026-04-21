# KabuSys

日本株自動売買システムのミニマルな実装サンプル（ライブラリ/実行スクリプト群）。  
このリポジトリはトレード実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI 補助（ニュース NLP / レジーム判定）などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を備えた自動売買基盤のサンプル実装です。

- ExecutionEngine：実際の（またはペーパー）発注の実行管理
- Monitoring：システム稼働状況・注文状態・リスク監視とアラート / Kill Switch
- Portfolio construction：銘柄選定・重み付け・ポジションサイズ計算
- Research：ファクター計算、特徴量探索、IC 計算などの分析ユーティリティ（DuckDB ベース）
- AI 支援：ニュースのセンチメントスコアリング、マクロセンチメントを利用したレジーム判定（OpenAI）
- ユーティリティ類：設定管理、ログ設定、プロセス優先度制御など

設計上のポイント：
- 環境変数 / .env による設定管理（自動読み込み）
- DuckDB を分析用に利用、SQLite を監視 / 発注ログ用に利用
- Paper trading モードは本番 DB と分離（`data/paper_trading.db`）
- フラグファイルでの停止（`data/stop_requested.flag` / `data/kill.flag`）

---

## 主な機能一覧

- 実行
  - run_execution.py: ExecutionEngine を起動（本番 / ペーパー切替）
  - BrokerClientFactory による実環境 / モック切替
- 監視
  - run_monitoring.py: SystemMonitor のポーリングループ起動
  - MonitoringEngine: System / Trade / Risk モニタを束ねてアラート・KillSwitch を評価
  - monitoring_db: 監視ログ（system_status, trade_logs, positions, risk_logs, dashboard）
- ポートフォリオ構築
  - 銘柄選定（スコア / 等分配）、セクター制約、ポジションサイズ計算
- リサーチ
  - ファクター（Momentum, Volatility, Value）計算（DuckDB）
  - 将来リターン・IC・統計サマリ
- AI
  - news_nlp: OpenAI を使ったニュースセンチメントスコアリング（ai_scores テーブルへ書き込み）
  - regime_detector: ETF ma200 比較 + マクロニュースで日次レジーム判定
- ユーティリティ
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 環境設定検証 CLI
  - logging_setup: 統一ログ設定（Stream + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定

---

## セットアップ手順

前提
- Python 3.9+
- 依存パッケージはプロジェクトの要件に応じてインストールしてください（duckdb, psutil, openai, PyYAML など）。

1. リポジトリをクローン
   - git clone ... （省略）

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストール
   - pip install -r requirements.txt
     - （requirements.txt がない場合は duckdb, psutil, openai, PyYAML 等を手動でインストール）

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは手動で `.env` を作成（下記主要環境変数を参照）

5. 設定検証（起動前確認）
   - python -m kabusys.validate_config
   - 本番準備で警告も FAIL にしたい場合:
     - python -m kabusys.validate_config --strict

6. DB 初期化は各スクリプト起動時に自動で行われます（monitoring は init_monitoring_db を実行）。

主要環境変数（必須 / 重要）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を利用する場合）
- LOG_LEVEL（DEBUG/INFO/...）
- LOG_DIR（ログ保存先）
- KILL_FLAG_CLEAR_ON_START（"1" で起動時に kill.flag を自動クリア）

.env の自動読み込み
- プロジェクトルートにある `.env` および `.env.local` が自動でロードされます（OS 環境変数優先）。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（実行例）

- 実行エンジン（本番 / ペーパー）
  - 本番モード（環境変数で切替）
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパートレード
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading モードでは MockBrokerClient を使用し、デフォルトで `data/paper_trading.db` に記録されます。
  - 停止方法（外部から）
    - プロセスを終了するか、プロジェクトルートの `data/stop_requested.flag` を作成すると安全停止処理が走ります。

- 監視プロセス
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト: 60）
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを記録します。
  - run_monitoring は stop_requested.flag を検知して終了します。

- 設定操作
  - 対話式で .env を生成:
    - python -m kabusys.config_setup
  - 設定検証:
    - python -m kabusys.validate_config
    - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスの指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能
  - OpenAI を使う機能を呼ぶ際は `OPENAI_API_KEY` を設定してください。
  - news_nlp.score_news や regime_detector.score_regime をプログラムから呼び出して使用します。

ログ
- デフォルトでコンソール出力（stdout）と日次ローテートのファイル出力（logs/<app_name>.log）を併用します。
- ログ保存先は環境変数 `LOG_DIR` または `LOG_DIR` 引数で変更できます。

---

## ディレクトリ構成

（リポジトリのルートに `src/` がある前提。主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                   — 環境変数・設定管理（.env 自動ロード含む）
    - config_setup.py             — .env 対話ウィザード
    - validate_config.py          — 設定検証 CLI
    - run_execution.py            — ExecutionEngine 起動スクリプト
    - run_monitoring.py           — Monitoring ポーリングループ起動スクリプト
    - utils/
      - logging_setup.py          — ログ設定ユーティリティ
      - process_priority.py       — プロセス優先度 / CPU affinity
    - execution/                  — 実行関連（BrokerClientFactory, ExecutionEngine, OrderManager, RiskManager 等）
      - (実装ファイル群)
    - monitoring/
      - monitoring_db.py          — SQLite 監視 DB 層
      - system_monitor.py         — システム・データ鮮度監視
      - trade_monitor.py          — 注文 / 約定監視（存在）
      - risk_monitor.py           — ドローダウン・ポジション監視
      - kill_switch.py            — kill.flag の書き込み / 評価
      - monitoring_engine.py      — 複数モニタを束ねるエンジン
      - alert_manager.py          — アラート送信（LINE などの実装を想定）
    - portfolio/
      - portfolio_builder.py      — 候補選定・重み計算
      - position_sizing.py        — 株数決定・スケールダウン（lot 単位）
      - risk_adjustment.py        — セクター上限・レジーム乗数
    - research/
      - factor_research.py        — Momentum/Volatility/Value ファクター
      - feature_exploration.py    — 将来リターン・IC・統計サマリ
    - ai/
      - news_nlp.py               — ニュース NLP（OpenAI）による銘柄スコアリング
      - regime_detector.py        — ETF MA + マクロニュースでレジーム判定
    - tools/
      - paper_verification_report.py — Paper Trading の検証レポート生成ツール
    - data/                        — 実行時に使用するファイル（logs や DB）はここを想定
      - monitoring.db (default)
      - paper_trading.db (paper mode)
      - kabusys.duckdb (default)
      - execution.pid / stop_requested.flag / kill.flag

---

## 開発上の注意点・運用メモ

- 環境（KABUSYS_ENV）:
  - development: ローカル開発用
  - paper_trading: 発注はモック、DB は分離（PAPER_TRADING_SQLITE_PATH）
  - live: 本番（注意して使用）

- Kill Switch:
  - RiskMonitor 等が条件を満たすと `data/kill.flag` を書き込み、ExecutionEngine を停止対象にできます。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag が自動クリアされますが、本番では推奨されません。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等にテーブル・インデックス作成と簡易マイグレーション（カラム追加）を行います。

- ログ / 権限:
  - process_priority.set_process_priority はプラットフォーム依存で権限エラーが出る場合はログ警告を出してスキップします。

- AI 利用:
  - OpenAI 呼び出しはネットワークや 429/5xx 対応のためリトライを実装していますが、API コストに注意してください。

---

## 参考コマンドまとめ

- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 実行エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 監視起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README に書かれている動作やデフォルト値はソースコード（特に `kabusys/config.py`, `run_execution.py`, `run_monitoring.py`, `kabusys/monitoring/*`, `kabusys/ai/*`）に従います。運用前には必ず `python -m kabusys.validate_config` で設定を確認してください。