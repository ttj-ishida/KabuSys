# KabuSys

日本株向け自動売買システムのライブラリ & 実行スクリプト群。戦略・ポートフォリオ構築、リスク制御、実行エンジン（発注）、監視、AI（ニュース NLP / レジーム判定）、および解析用ユーティリティを含みます。

---

## 概要

このリポジトリは、以下の主要コンポーネントを提供します。

- ExecutionEngine：発注ロジック、注文管理、リスク管理、ブローカー抽象化（本番／ペーパー両対応）
- Monitoring：システム監視（CPU、メモリ、ディスク、データ鮮度）、トレード監視、リスク監視、Kill Switch
- Research：DuckDB 上で動作するファクター計算・特徴量解析ユーティリティ
- Portfolio：候補選定・重み計算・ポジションサイズ計算・セクター制限など
- AI：ニュースのセンチメントスコアリング（OpenAI）や市場レジーム判定
- Tools：Paper Trading 検証レポート生成などの CLI ユーティリティ
- 設定関連ツール：.env の対話式作成ウィザード、起動前設定検証

設計方針の一部：
- 本番 DB とペーパー（paper_trading）を分離
- DuckDB を分析用途に使用（prices_daily / raw_financials など）
- LLM（OpenAI）呼び出しはフェイルセーフで実装（リトライ、パース検証、部分失敗保護）
- ルックアヘッドバイアスの回避（内部で date.today()/datetime.today() を直接参照しない設計）

---

## 主な機能一覧

- 実行（Execution）
  - Broker クライアント抽象化（本番 / mock for paper trading）
  - 注文管理（OrderManager / OrderRepository）
  - リスク管理（最大ポジション比率、利用率、ドローダウン監視等）
  - 実行エンジンのデーモン実行（PID ファイル管理、停止フラグ検知）

- 監視（Monitoring）
  - システム状態（CPU / Memory / Disk）と Execution プロセスの監視
  - トレードログ監視（滞留注文、異常約定等）
  - リスク監視（ドローダウン、ポジション数上限）
  - Kill Switch（条件を満たしたら data/kill.flag を書き込んで ExecutionEngine を停止）
  - 監視ループ起動スクリプト（MONITOR_POLL_INTERVAL によるポーリング間隔調整）

- 研究 / 分析（Research）
  - モメンタム、ボラティリティ、バリューなどのファクター計算（DuckDB）
  - 将来リターン、IC（Information Coefficient）計算、ファクター統計

- ポートフォリオ構築（Portfolio）
  - 候補選定（スコア順）、等重・スコア加重、リスクベース配分
  - セクターキャップ適用、レジームに応じた投下資金乗数
  - 単元株丸め、アグリゲートキャップ処理

- AI
  - ニュース記事を LLM（gpt-4o-mini 等）で評価し銘柄ごとのスコアを ai_scores テーブルに書き込み
  - マクロニュース＋ETF MA を組み合わせた市場レジーム判定（market_regime テーブルへ書込）

- ツール
  - 環境設定ウィザード（.env の対話生成）
  - 起動前設定検証 CLI（必須環境変数や config/*.yaml の存在・構文確認）
  - Paper Trading 検証レポート生成（fill_rate / send_rate / latency / uptime などを出力）

---

## 前提条件 / 必要ソフトウェア

- Python 3.10 以上（typing の | 形式などを使用）
- SQLite（組み込み）
- 推奨 Python パッケージ（最低限）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証を行う場合）
- ネットワークアクセス（本番 API / OpenAI を利用する場合）

（パッケージはプロジェクト側で requirements.txt があればそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ
   - git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

4. .env の作成
   - 対話ウィザード（推奨）
     - python -m kabusys.config_setup
   - または手動でルートに `.env` を作成（後述の環境変数を設定）

   注意: .env は機密情報を含むため Git にコミットしてはいけません。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 本番起動前は厳密モード:
     - python -m kabusys.validate_config --strict

6. データディレクトリの準備（必要なら）
   - デフォルトでは `data/`、`logs/` を自動作成しますが、パスをカスタムした場合は事前に作成してください。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な任意 / デフォルト:
- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス — デフォルト: data/kabusys.duckdb
- SQLITE_PATH: SQLite（監視） — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite — デフォルト: data/paper_trading.db
- LOG_LEVEL: ログレベル — デフォルト: INFO
- LOG_DIR: ログディレクトリ — デフォルト: logs/
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- PAPER_FILL_MODE: paper_trading の fill モード（instant / partial / never / reject） — デフォルト: instant
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（1/0） — デフォルト: 0（本番推奨：0）

監視専用:
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒） — デフォルト: 60
  - 無効な値（0 以下や非数）はデフォルト（60 秒）にフォールバック

設定方法の例（.env）:
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_kabu_password
- KABUSYS_ENV=paper_trading
- OPENAI_API_KEY=sk-xxxxx
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

---

## 主要コマンド / 使い方

- 環境設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）起動
  - 本番 / 開発 / ペーパーは KABUSYS_ENV により振る舞いが切り替わります
  - python -m kabusys.run_execution
    - 起動時、KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録されるため本番 DB と分離されます。
    - 実行中の停止はプロジェクトルートの data/stop_requested.flag を作成すると検知して停止します。
    - PID は data/execution.pid に書き込まれます。

- 監視ループ起動
  - python -m kabusys.run_monitoring
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト: 60）
    - 監視は Settings に従い monitoring DB（デフォルト: data/monitoring.db）へログを書きます
    - 停止フラグは data/stop_requested.flag を参照

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH（優先）→ data/paper_trading.db
  - レポートには uptime、fill rate、send rate、latency（avg/max/P95）等を出力しパス/フェイル判定を行います

- AI 関連（ライブラリ関数）
  - ニュース NLP（銘柄ごとのスコアを ai_scores テーブルへ書き込む）
    - Python から呼び出し例:
      - from kabusys.ai import score_news
      - score_news(conn, target_date, api_key="sk-...")
    - conn は duckdb.connect(...) で取得した接続（DuckDBPyConnection）
  - 市場レジーム判定（score_regime は kabusys.ai.regime_detector 内）
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="sk-...")

  ※ AI 機能を実行する際は OPENAI_API_KEY を設定してください。API 呼び出しはリトライやパース検証を行い、失敗時は安全なデフォルト（例: 0.0）へフォールバックします。

---

## 停止・Kill Switch に関する挙動

- 実行停止フラグ:
  - run_execution.py / run_monitoring.py ともにプロジェクトの data/stop_requested.flag をチェックし、存在すればループを終了します（外部プロセスから停止する簡易手段）。
- Kill Switch:
  - Monitoring 内の評価結果に応じて `data/kill.flag` を作成（Settings.kill_flag_path）し、ExecutionEngine に停止シグナルを送る仕組みがあります（ExecutionEngine 側は起動時や監視ループで kill.flag をチェック／クリアの動作を持つ）。
  - Settings.KILL_FLAG_CLEAR_ON_START が 1 の場合、ExecutionEngine 起動時に kill.flag を自動でクリアします（本番では危険なので 0 推奨）。

---

## ログ

- 共通ロギング設定は `kabusys.utils.logging_setup.setup_logging` で行われます。
  - stdout（StreamHandler）に出力
  - 日次ローテーションするファイルハンドラ（logs/<app_name>.log、30日保持）に出力（ディレクトリ作成に失敗した場合はコンソールのみ）
- アプリケーション別ログファイル名例:
  - execution → logs/execution.log
  - monitoring → logs/monitoring.log

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル・モジュール構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動読み込み等）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前の設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - execution/
    - (OrderManager, ExecutionEngine, BrokerFactory, Reconciler, RiskManager 等)
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py       — システム状態 / データ鮮度チェック
    - trade_monitor.py        — 注文ログチェック等（ファイル参照）
    - risk_monitor.py         — ドローダウン／ポジション上限監視
    - monitoring_engine.py    — 各 Monitor を束ねる実行ループ
    - kill_switch.py          — kill.flag 管理
    - alert_manager.py        — 通知（LINE 等）抽象（実装ファイル参照）
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み付け
    - position_sizing.py      — 数量算出・アグリゲートキャップ処理
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — momentum/volatility/value ファクター計算
    - feature_exploration.py  — forward returns / IC / summary
  - ai/
    - news_nlp.py             — ニュースの LLM スコアリング
    - regime_detector.py      — レジーム判定（MA + LLM）
  - data/                     — デフォルトの DB / フラグファイル（実行時に作成）
  - logs/                     — ログディレクトリ（デフォルト）

（上記は主なファイルを抜粋しています。詳しくはソースツリーをご覧ください。）

---

## 開発メモ / 注意事項

- Paper Trading（KABUSYS_ENV=paper_trading）時は発注は仮想化され、データは paper_trading 用 DB に記録されます。本番 DB とデータを分離しているため安全に検証できます。
- OpenAI 等外部 API を使う機能は API キーが必要です。API 呼び出しはリトライや JSON 検証などの保護処理がありますが、API コスト／レート制限に注意してください。
- .env は機密情報を含むため絶対にリポジトリへコミットしないこと。
- 本 README はコードの注釈・実装に基づく概要です。実運用前に `python -m kabusys.validate_config` を実行し、すべての設定を確認してください。
- Python バージョンは typing の構文等から >=3.10 を推奨します。

---

必要があれば、README のサンプル .env テンプレート、起動スクリプトの systemd ユニット例、あるいは ExecutionEngine / Monitoring のデバッグ手順などを追加で作成します。どの情報をより詳しく載せたいか教えてください。