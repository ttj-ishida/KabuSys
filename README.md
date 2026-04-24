# KabuSys

日本株自動売買システムのコアライブラリ群。戦略・ポートフォリオ構築、発注エンジン、監視、研究ツール、ニュースNLP／レジーム判定などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。主な責務は以下のとおりです。

- 戦略・ファクター計算（research）
- ポートフォリオ構築・ポジションサイズ計算（portfolio）
- 発注ロジック・ExecutionEngine（execution）
- システム監視・リスク監視・Kill Switch（monitoring）
- ニュースを用いた NLP スコアリング・レジーム判定（ai）
- 運用支援スクリプト（config_setup / validate_config / tools）

設計方針としては「本番環境で安全に動かせること」を重視し、Paper Trading 用 DB の分離、Kill Switch、冪等な DB 書き込み、ルックアヘッドバイアス回避などの配慮が組み込まれています。

---

## 主な機能一覧

- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を用い、Paper 用 SQLite に記録
  - 起動時にプロセス優先度を設定、PID 管理、停止フラグ監視
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor: CPU/メモリ/ディスク・プロセス存在チェック、データ鮮度チェック
  - TradeMonitor: 発注ログの監視（滞留注文・約定異常など）
  - RiskMonitor: ドローダウン・ポジション上限監視。dashboard の永続化
  - KillSwitch: 条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止
  - AlertManager（通知管理：LINE などを想定）
- config_setup（対話式 .env ウィザード）および validate_config（設定検証 CLI）
- 研究用モジュール（research）
  - ファクター計算（momentum, volatility, value）
  - 将来リターン・IC 計算・特徴量サマリ
- portfolio（候補選定・重み付け・ポジションサイズ計算・セクターキャップ）
- ai
  - news_nlp: OpenAI を使ったニュースセンチメント集約・ai_scores への書き込み
  - regime_detector: ETF MA とマクロ記事の LLM スコアを合成して市場レジーム判定
- utils
  - logging_setup: 統一されたログ設定（stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ
- tools
  - paper_verification_report: Paper Trading の検証レポート生成

---

## セットアップ手順（開発／ローカル実行向け）

注: requirements.txt はリポジトリに含まれていないため、用途に応じて下記パッケージをインストールしてください。

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai

   追加で便利なパッケージ:
   - pip install pyyaml  # validate_config の YAML 構文チェックに利用（任意）

3. 初期設定ファイル (.env) を生成
   - 対話式ウィザード: python -m kabusys.config_setup
     - .env のテンプレートが自動生成されます。J-Quants / kabu API トークンなど必須項目を入力してください。

4. 設定検証
   - python -m kabusys.validate_config
   - 問題がなければ OK が表示されます。--strict を付けると警告も失敗扱いになります。

5. データ格納ディレクトリ
   - デフォルトで以下ファイル・フォルダを使用します（必要に応じて .env で上書き）
     - data/kabusys.duckdb
     - data/monitoring.db
     - data/paper_trading.db（paper_trading 用）
     - logs/（ログ出力先）

---

## 環境変数（主要）

重要な環境変数（.env に設定）:

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行環境・動作制御
  - KABUSYS_ENV — one of: development, paper_trading, live（デフォルト: development）
  - LOG_LEVEL — DEBUG/INFO/…（デフォルト: INFO）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（開発用; デフォルト: 0）

- DB / ファイルパス
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — Execution の pid ファイルパス（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch フラグパス（デフォルト: data/kill.flag）

- Paper Trading 固有
  - PAPER_FILL_MODE — instant | partial | never | reject（デフォルト: instant）

- Monitoring
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト: 60）

- OpenAI
  - OPENAI_API_KEY — news_nlp / regime_detector が使用

自動 .env ロード
- パッケージ起動時、プロジェクトルートに `.env` / `.env.local` があれば自動読み込みします（OS 環境変数より優先度は低い）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 使い方（代表的なコマンド）

- .env を作成（対話）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- モニタリングループ起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止方法:
    - プロジェクトルートの data/stop_requested.flag を作成するとループは終了します（監視側の停止フラグ）。

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると Paper Trading 用 DB（data/paper_trading.db）へ記録され、本番 DB と分離されます。
  - 既に data/stop_requested.flag が存在する場合は起動しません。
  - Execution を停止するには data/stop_requested.flag を作成するか、Kill Switch（data/kill.flag）を書き込ませます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- ai / regime 判定（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、内部で ai スコア / market_regime を書き込みます。OPENAI_API_KEY を環境に設定してください。

ログ
- setup_logging を各スクリプトが呼び出します。デフォルトは stdout への出力と logs/<app_name>.log への日次ローテーション（30日保持）。

プロセス優先度
- 起動時に set_process_priority("high") が呼ばれます（プラットフォーム依存）。失敗時は警告のみで継続します。

Kill Switch / stop フローまとめ
- monitoring がリスク条件を検知すると data/kill.flag を書き込みます。
- ExecutionEngine は kill_flag_path を参照して停止するか、起動時に kill_flag_clear_on_start の設定で自動クリアできます（本番ではクリアしないことを推奨）。

---

## ディレクトリ構成（主要ファイル）

下記は src/kabusys 以下の主要モジュール構成です（抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数・設定管理（.env 自動読み込み含む）
    - config_setup.py           — .env 対話式ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — Monitoring 起動スクリプト
    - ai/
      - __init__.py
      - news_nlp.py             — ニュース NLP（OpenAI 経由）
      - regime_detector.py      — レジーム判定（ETF MA + LLM）
    - monitoring/
      - __init__.py
      - monitoring_db.py        — SQLite のスキーマ・永続化層
      - system_monitor.py       — システム状態・データ鮮度監視
      - trade_monitor.py        — 注文ログ監視（※ファイルに示されている想定）
      - risk_monitor.py         — ドローダウン・ポジション上限監視
      - kill_switch.py          — kill.flag 書き込みユーティリティ
      - monitoring_engine.py    — 各 Monitor を束ねるエンジン
      - alert_manager.py        — アラート送信（※実装を読み替え）
    - execution/
      - (発注エンジン・OrderManager 等)  # run_execution が組み立てて起動
    - portfolio/
      - portfolio_builder.py    — 候補選定 / equal/score 重み計算
      - position_sizing.py      — 株数計算・aggregate cap
      - risk_adjustment.py      — セクター制限・レジーム乗数
      - __init__.py
    - research/
      - factor_research.py      — momentum / volatility / value
      - feature_exploration.py  — 将来リターン / IC / 統計
      - __init__.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - utils/
      - logging_setup.py        — ロギング統一設定
      - process_priority.py     — プロセス優先度 / CPU affinity
      - __init__.py

補足:
- data/ 以下に各 SQLite / pid / flag ファイルを置く設計です（リポジトリに含めないこと）。
- logs/ がログ出力先として使われます（設定で変更可能）。

---

## 運用上の注意・ベストプラクティス

- 本番（KABUSYS_ENV=live）では .env を厳重に管理し、Git 管理から除外してください（config_setup にもその旨が注記されています）。
- KILL_FLAG_CLEAR_ON_START は本番で 1 に設定しないでください（危険）。
- Paper Trading を実行する場合は PAPER_TRADING_SQLITE_PATH を指定して本番 DB と分離してください。
- OpenAI API を使用する処理は API 利用料が発生します。API キー管理、レート制限、コストに注意してください。
- ログ・DB の権限・バックアップ・監視を運用フローに組み込んでください。
- validate_config を起動前チェックに組み込み、致命的な設定漏れを防止してください。

---

必要であれば、README に「依存パッケージ一覧（推奨バージョン）」「実行例の詳細ログ出力例」「CI 向けの設定（ヘルスチェック／自動デプロイ）」などを追記できます。どの情報を優先して追加しますか？