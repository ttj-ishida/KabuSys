# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム KabuSys の一部実装です。  
主に注文実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）、ニュースNLP を用いた AI モジュール等を提供します。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要コマンド）
- 主要設定項目（環境変数）
- 停止 / Kill Switch の扱い
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。本コードベースには以下の責務を持つモジュールが含まれます。

- ExecutionEngine（発注処理、リスク管理、オーダー管理、リコンシリエーション）
- Monitoring（システム稼働状態、注文監視、リスク監視、アラート管理、Kill Switch）
- Portfolio（銘柄選定、重み付け、ポジションサイズ計算、セクター制限）
- Research（ファクター計算、将来リターン・IC 計算、統計サマリ）
- AI（ニュースセンチメント・市場レジーム判定：OpenAI を利用）
- Config ユーティリティ（.env ウィザード、検証 CLI）
- Tools（ペーパートレード検証レポート等）

設計方針の一部：
- 本番 DB と paper_trading 用 DB を分離（KABUSYS_ENV に依存）
- できるだけルックアヘッドバイアスを避ける（日付参照を明示的引数化）
- 外部 API 呼び出しは明示的にキーを渡すか環境変数を利用

---

## 機能一覧

主な機能（抜粋）：
- 環境設定ウィザード（.env 生成 / 更新）: `kabusys.config_setup`
- 設定検証 CLI（.env と config/*.yaml のチェック）: `kabusys.validate_config`
- ExecutionEngine 起動スクリプト: `run_execution.py`（KABUSYS_ENV に応じて mock ブローカー使用）
- Monitoring ポーリング（SystemMonitor のループ）: `run_monitoring.py`
- モニタリング DB 層（SQLite）: テーブル作成・マイグレーション対応
- Trade / System / Risk の監視ロジック（滞留注文・約定異常・ドローダウン等）
- Kill Switch（フラグファイルによりエンジン停止）
- ポートフォリオ構築ユーティリティ（候補選定、等ウェイト・スコア重み、ポジションサイズ）
- リサーチ機能（モメンタム・ボラティリティ・バリュー等ファクター計算、IC・統計）
- ニュースNLP（OpenAI を利用した銘柄ごとのセンチメント生成）および市場レジーム判定
- ペーパートレード用検証レポート生成ツール

---

## セットアップ手順

1. Python 環境を準備（推奨: 仮想環境）
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要な Python パッケージをインストール
   - 主な依存（プロジェクト内で想定されるもの）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config の YAML 検証に使用、任意）
   - 例:
     - pip install duckdb psutil openai pyyaml

   > 注意: requirements.txt は本リポジトリに含まれていないため、実行環境に応じて適宜依存を管理してください。

3. プロジェクトルートに .env を作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参考に）

4. 設定の検証（任意）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリの用意
   - デフォルト DB パスの親ディレクトリ（例: data/）が存在しない場合は作成してください。
   - 一部スクリプトは起動時に親ディレクトリを自動作成しますが、権限等に注意してください。

---

## 使い方（主要コマンド）

一般的にはパッケージとしてモジュールを実行します。プロジェクトルートで以下を使います。

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 動作モード:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、データは paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に保存されます。
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。
  - 実行中は data/execution.pid（デフォルト）が作成され、プロセスの存在チェックに利用されます。

- Monitoring を起動（SystemMonitor 単体ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用します（環境にかかわらず）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 環境変数 PAPER_TRADING_SQLITE_PATH または --db オプションで DB を指定できます。

- AI モジュールの利用（プログラム的呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは api_key 引数か環境変数 OPENAI_API_KEY を使用
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 主要設定項目（環境変数）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

重要（代表的なもの）:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- OPENAI_API_KEY — OpenAI API キー（AI 機能使用時）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading 時の上書き）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知設定（任意）
- PAPER_FILL_MODE — paper_trading の約定モード（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

例（.env の一部）:
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

---

## 停止 / Kill Switch の扱い

- ExecutionEngine の停止は主にフラグファイル経由で行います。
  - data/stop_requested.flag: run_execution/run_monitoring が監視している停止フラグ（起動前に存在すると起動を中止／停止処理）。
  - data/kill.flag: KillSwitch により書き込まれ、ExecutionEngine を停止するために使用されます。KillSwitch はリスク監視（ドローダウン/ポジション上限等）に応じてこのファイルを作成します。
- KillSwitch 書き込みは冪等（既存ファイルがあれば再書き込みしない）です。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 設定すると kill.flag を自動で消去します（本番運用では 0 を推奨）。

---

## DB とマイグレーション

- 監視用 DB (SQLite): init_monitoring_db() がテーブルを作成し、既存 DB に対する簡単なマイグレーション（カラム追加）を行います。
  - system_status / trade_logs / positions / risk_logs / dashboard を定義。
  - 新しいカラム（例: trade_logs.latency_ms, dashboard.peak_value）を発見すると ALTER TABLE を実行して追加します（冪等）。

- Paper trading は本番 DB と分離され、KABUSYS_ENV=paper_trading 時は `PAPER_TRADING_SQLITE_PATH` に接続します。

---

## ディレクトリ構成（主なファイル・モジュール）

リポジトリ内の主要な構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数読み込み / Settings
  - config_setup.py        — .env 対話式ウィザード
  - validate_config.py     — 設定検証 CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py          — ニュース NLU/LLM スコアリング
    - regime_detector.py   — 市場レジーム判定（LLM + MA200 合成）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py   — 株数決定・資金配分
    - risk_adjustment.py   — セクター制限・レジーム乗数
  - research/
    - factor_research.py   — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン／IC／統計ユーティリティ
  - monitoring/
    - monitoring_db.py     — SQLite 永続化層（テーブル作成・API）
    - system_monitor.py    — システム/データ鮮度監視
    - trade_monitor.py     — 注文滞留・価格異常監視
    - risk_monitor.py      — ドローダウン / ポジション上限監視
    - kill_switch.py       — kill.flag 書き込みユーティリティ
    - monitoring_engine.py — 各 Monitor を束ねるループ
    - alert_manager.py     — （アラート送信の仲介 — 実装ファイルはここに）
  - execution/
    - （ExecutionEngine, BrokerFactory, OrderManager 等の実装）
  - utils/
    - process_priority.py  — プロセス優先度 / CPU affinity ユーティリティ
  - data/                  — デフォルトの DB / flag ファイルを置く場所（例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag, data/stop_requested.flag）
  - config/                — 設定用 YAML ファイル例（system_config.yaml 等）

---

補足 / 運用注意
- OpenAI を用いる機能（news_nlp, regime_detector）は API キーと通信の安定性に依存します。API レート制限や 5xx に対してはリトライ／フェイルセーフ設計がありますが、ログと運用監視を必ず行ってください。
- KABUSYS_ENV が `live` の場合は特に LINE 通知等の設定を確認してください（validate_config にガードが入っています）。
- process_priority.set_process_priority() により起動直後にプロセス優先度を上げますが、権限により失敗することがあります（その場合は警告でスキップ）。

---

この README は現在のコードベース（主要ファイル群）を元に記述しています。追加の実行スクリプトや補助ツール、外部設定ファイル（config/*.yaml）がある場合は、それらに従って設定・運用してください。疑問があれば、該当モジュールの docstring コメントや関数・クラスの説明を参照してください。