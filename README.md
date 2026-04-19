# KabuSys

日本株自動売買システム (KabuSys)

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたシステムです。市場データの解析・ファクター算出、ポートフォリオ構築、発注エンジン、監視・アラート機構、Paper Trading 検証、AI を使ったニュースセンチメント/レジーム判定などを備えています。設計方針として本番データとペーパートレードの分離、ルックアヘッドバイアス防止、フェイルセーフ（API 失敗時でも継続）を重視しています。

主な特徴:
- DuckDB / SQLite を用いたデータ集計・ログ保存
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- ExecutionEngine（本番/ペーパートレード対応）
- 監視サブシステム（システム状態、注文監視、リスク監視、Kill Switch）
- AI を使ったニュースセンチメント（OpenAI）および市場レジーム判定
- 設定ウィザード・検証ツール・検証レポート生成ツール

---

## 機能一覧

- 設定管理
  - .env の自動ロード / 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
- 実行/発注
  - ExecutionEngine（run_execution.py）
  - Paper Trading サポート（KABUSYS_ENV=paper_trading 時に MockBroker と専用 DB を使用）
  - PAPER_FILL_MODE によるペーパートレードの約定挙動制御（instant / partial / never / reject）
- 監視
  - SystemMonitor（CPU/メモリ/ディスク、データ鮮度、Execution プロセス監視）
  - TradeMonitor（滞留注文・約定異常検出 等）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件を満たしたら data/kill.flag を書き込み Execution を停止）
  - モニタリングループ起動スクリプト（run_monitoring.py）
- データ処理 / 研究
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）等の統計解析
- AI 機能
  - ニュース NLP による銘柄別センチメント（OpenAI API）
  - マクロニュース + ma200 による市場レジーム判定（OpenAI API）
- ツール
  - ペーパートレード検証レポート生成（tools/paper_verification_report.py）

---

## 必要条件（例）

- Python 3.9+
- 必須ライブラリ（一部）:
  - duckdb
  - psutil
  - openai
- あると便利/任意:
  - PyYAML（config/*.yaml の構文チェック時に使われる）
- これらは pip でインストールしてください:
  - pip install duckdb psutil openai
  - 任意: pip install pyyaml

（プロジェクトに requirements.txt / pyproject.toml があればそちらを参照してください）

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートへ移動
   - 例: git clone ... && cd kabusys

2. Python 仮想環境の作成（任意推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) / .venv\Scripts\activate (Windows)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - （YAML 検証を使う場合）pip install pyyaml

4. 環境変数設定 (.env)
   - 対話式で生成: python -m kabusys.config_setup
   - 生成後、内容を確認・編集してください（.env は絶対に Git にコミットしないでください）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も厳密に扱う場合: python -m kabusys.validate_config --strict

6. DB ファイルとログディレクトリ
   - デフォルトでは data/ と logs/ が使われます。設定でパスを上書きできます。
   - 監視 DB（SQLite）・DuckDB ファイルは初回起動時に自動作成・初期化されます（init_monitoring_db が呼ばれます）。

---

## 環境変数（主要なもの）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意/重要:
  - KABUSYS_ENV: 実行環境 (development | paper_trading | live) — default: development
  - DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時に使用、default: data/paper_trading.db）
  - PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject、default: instant）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...、default: INFO）
  - LOG_DIR: ログ出力ディレクトリ（default: logs/）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、default: 60）
  - KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1、default: 0。本番では 0 推奨）

上記以外にも細かい設定項目があります。.env.example を参考にしてください。

---

## 使い方（コマンド例）

- .env を作る（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も fail）: python -m kabusys.validate_config --strict

- Execution (発注エンジン) を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）へ記録されます。
  - run_execution は起動時に data/execution.pid を作成し、data/stop_requested.flag を検出すると安全に停止します。

- Monitoring を起動（監視ループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）
  - run_monitoring は data/stop_requested.flag を検出するとループを終了します

- Kill Switch（手動）
  - リスク条件を満たした際に monitoring により data/kill.flag が作成されます。
  - Execution 起動時の挙動や停止は kill.flag の存在を参照します。
  - Kill Flag を手動でクリアするにはファイルを削除するか、設定で起動時自動クリアを有効にしてください（KILL_FLAG_CLEAR_ON_START=1 が該当）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)  # OpenAI キーは環境変数 OPENAI_API_KEY か引数で指定
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## ログ・DB・フラグファイルの場所（デフォルト）

- ログ: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
- 監視 SQLite (monitoring DB): data/monitoring.db
- DuckDB: data/kabusys.duckdb
- Paper Trading SQLite: data/paper_trading.db
- 実行 PID: data/execution.pid
- 停止/制御フラグ:
  - data/stop_requested.flag — スクリプトがこのファイルを検出すると安全に停止します（run_execution / run_monitoring が参照）
  - data/kill.flag — Kill Switch によって書き込まれる Execution 停止フラグ

---

## 注意点 / 運用上のヒント

- 本番環境 (KABUSYS_ENV=live) では LINE 通知等の設定を必ず確認してください（validate_config にガードあり）。
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- OpenAI 関連機能を利用する場合、API キーの使用料やレート制限に注意してください。AI 呼び出し部はリトライ・フェイルセーフ実装がありますが、運用ポリシーに従ってください。
- run_execution / run_monitoring はプロセス優先度を高く設定しようとします（プラットフォーム依存で失敗する場合は警告を出力して続行）。
- Paper Trading と本番 DB は完全分離されます（ペーパートレード時は PAPER_TRADING_SQLITE_PATH が使用されます）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / Settings 管理（自動 .env ロード含む）
  - config_setup.py        — .env 対話ウィザード
  - validate_config.py     — 起動前設定検証 CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (存在想定)
    - kill_switch.py
    - alert_manager.py (存在想定)
  - execution/             — ExecutionEngine 周りの実装（broker, order_manager, risk_manager 等）
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (ランタイムに作成される)
    - *.db, *.pid, *.flag

（上はコードベースから主要ファイルを抜粋した構成です。プロジェクト全体は pyproject.toml / setup 等により変わる可能性があります）

---

## 開発者向け補足

- DuckDB 接続を受け取る関数群（research / ai）は外部 API に依存せずローカル DB（prices_daily / raw_financials / raw_news 等）を参照する設計です。
- 多くのモジュールは「フェイルセーフ」設計で、API エラーやデータ不足時は例外を吸収してログ出力し続行します。運用時はログと monitoring の出力を監視してください。
- テスト時の自動化を想定して一部の外部呼び出し（OpenAI 呼び出し等）を差し替え可能な設計になっています（ユニットテストでモック可）。

---

必要であれば、この README をベースに「インストール手順を Docker 化」「systemd ユニットファイル例」や「運用手順書（起動/停止/トラブルシュート）」を追記します。どの情報を追加しますか？