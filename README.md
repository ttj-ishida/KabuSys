# KabuSys

日本株向けの自動売買システム（ライブラリ＋起動スクリプト群）。戦略・ポートフォリオ構築、発注実行、監視、AI（ニュース/レジーム判定）、研究用ユーティリティを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール群を提供します。

- シグナル → 銘柄選定 → ウェイト付与 → 発注数量決定（ポートフォリオ構築）
- ExecutionEngine による発注処理（本番 / ペーパートレード切替対応）
- モニタリング（システム稼働・データ鮮度・注文ログ・リスク監視）
- AI モジュール（ニュースセンチメントによる銘柄スコア、マクロニュースでの市場レジーム判定）
- 研究用ユーティリティ（ファクター計算・将来リターン・IC 解析）
- 各種 CLI ツール（.env ウィザード、設定検証、ペーパートレード検証レポート 等）

---

## 主な機能一覧

- Execution
  - ExecutionEngine（本番 / paper_trading 切替）
  - BrokerClientFactory（paper_trading 時は MockBroker を使用し DB を分離）
  - リスク管理（RiskManager）・注文管理（OrderManager）
- Monitoring
  - SystemMonitor（CPU/Mem/Disk/プロセス判定・データ鮮度）
  - TradeMonitor / RiskMonitor / KillSwitch / AlertManager 組合せによる自動アラート・停止
  - 永続化: SQLite（監視ログ） + DuckDB（分析用）
- Portfolio construction
  - 候補選定、等ウェイト・スコア加重、リスクベース配分、単元丸め、セクター制約、レジーム乗数
- Research
  - ファクター計算（モメンタム/バリュー/ボラティリティ等）
  - 将来リターン集計、IC 計算、統計サマリー
- AI
  - news_nlp.score_news(): OpenAI を用いたニュースセンチメント集約・AIスコア保存
  - regime_detector.score_regime(): ETF MA とマクロニュースを組合せたレジーム判定
- ツール
  - config_setup: .env 対話ウィザード
  - validate_config: 起動前チェック（--strict で警告も失敗扱い）
  - tools.paper_verification_report: ペーパートレード検証レポート生成

---

## 必要要件（想定）

- Python 3.10+
- 必要な外部パッケージ（用途に応じて）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML (設定ファイル検証を行う場合に推奨)
- 標準ライブラリ: sqlite3, logging, threading など

（実行環境に合わせて requirements.txt を用意してください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo> && cd <repo>

2. 仮想環境を作成・有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （PyYAML を使う場合）pip install pyyaml

4. 環境変数設定 (.env)
   - 対話式で作る（推奨）:
     - python -m kabusys.config_setup
   - または手動でルートに `.env` を作成
   - 自動ロード: 起動時にプロジェクトルートの `.env` と `.env.local` が読み込まれます。
     - OS 環境変数 > .env.local > .env の優先度
     - 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 厳格モード（警告を FAIL 扱い）:
     - python -m kabusys.validate_config --strict

6. （任意）ログディレクトリ / data ディレクトリ
   - 多くの処理は起動時に自動作成を試みますが、必要に応じて `data/` や `logs/` を作成してください。

---

## 主要な環境変数（重要なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境切替
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading の場合、MockBroker+別 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
- DB パス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB、デフォルト: data/paper_trading.db)
- ログ / PID / Kill
  - LOG_LEVEL (デフォルト: INFO)
  - LOG_DIR (デフォルト: logs/)
  - PID_FILE_PATH / KILL_FLAG_PATH
  - KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか: 0/1)
- Monitoring
  - MONITOR_POLL_INTERVAL: 監視のポーリング間隔（秒）。デフォルト: 60
- Paper trading の振る舞い
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- AI
  - OPENAI_API_KEY（news_nlp / regime_detector を使う場合に必要）

---

## 使い方

起動用スクリプトはパッケージモジュールとして提供されています。プロダクションでは Supervisor / systemd / コンテナ等から起動してください。

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 備考:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し DB は PAPER_TRADING_SQLITE_PATH に記録されます（本番 DB と分離）。
    - エンジンは data/execution.pid に PID を書き、停止制御は data/stop_requested.flag（手動）、および monitoring により書かれる data/kill.flag を監視します。
    - 起動前に data/kill.flag を自動クリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 を設定（本番は 0 推奨）。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - Monitoring は環境にかかわらず本番用の sqlite_path を使用して監視テーブルを初期化します。

- 停止方法
  - 手動停止（両スクリプト共通）
    - プロセスに SIGINT（Ctrl+C）送信、または `data/stop_requested.flag` を作成するとループ内で検知して穏やかに終了します。
  - Kill Switch（自動停止）
    - Monitoring の KillSwitch が条件を満たすと `data/kill.flag` を作成します。ExecutionEngine は kill.flag の存在により停止処理を受けます。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --db PATH で PAPER_TRADING_SQLITE_PATH を上書き可能

- AI 機能（プログラムから利用）
  - 例: ニューススコア（DuckDB 接続・target_date を渡す）
    - python -c "import duckdb; from datetime import date; from kabusys.ai.news_nlp import score_news; conn=duckdb.connect('data/kabusys.duckdb'); print(score_news(conn, date(2026,4,1), api_key='YOUR_KEY'))"
  - OPENAI_API_KEY を環境変数で指定しておくと api_key 引数を省略できます。

---

## 動作の重要な仕様メモ

- .env の読み込み順: OS 環境 > .env.local > .env。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
- Settings クラスは環境変数をラップし、バリデーション（有効な KABUSYS_ENV / LOG_LEVEL 等）を行います。
- Monitoring は SQLite（監視ログ）を用い、init_monitoring_db() により必要テーブルを冪等的に作成します。
- Paper trading は本番 DB と完全に分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- Logging は kabusys.utils.logging_setup.setup_logging() で統一的に設定され、stdout と日次ローテートファイル（logs/<app>.log）へ出力します。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 内の主なファイルと役割のサマリです。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env の読み込みと Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート CLI
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数算出・アグリゲート cap
    - risk_adjustment.py      — セクター上限・レジーム乗数
  - execution/                — 発注関連コンポーネント（Engine・OrderManager 等）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py       — CPU/MEM/DISK/プロセス・データ鮮度チェック
    - trade_monitor.py        — 注文滞留や約定異常検知（実装参照）
    - risk_monitor.py         — ドローダウン・ポジション上限チェック
    - kill_switch.py          — kill.flag 書込みロジック
    - monitoring_engine.py    — 各 Monitor を束ねる
  - research/
    - factor_research.py      — ファクター計算（momentum / value / volatility）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py             — ニュースセンチメント集約・OpenAI 呼び出し（score_news）
    - regime_detector.py      — 市場レジーム判定（score_regime）
  - data/                     — デフォルトのデータ・ログ格納想定（例: data/*.db, data/kill.flag）
  - logs/                     — ログ出力先（デフォルト）

---

## よくある運用アドバイス

- 本番運用時は KABUSYS_ENV=live とし、LINE 通知や KILL_FLAG 設定を十分に確認してください。
- データベースパスやログディレクトリは .env で明示的に設定して、環境ごとに分離してください。
- AI 機能は外部 API に依存するため、API キー、レート制限、費用、エラー時のフォールバックを運用・監視設計に反映してください。
- validate_config を CI / デプロイ前チェックに組み込むと安全です。

---

必要であれば、README にサンプル .env のテンプレートや systemd / Supervisor の起動ユニット例、Dockerfile / docker-compose の雛形も追加します。どの情報を優先して追記しますか？