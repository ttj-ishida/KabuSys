# KabuSys

日本株向けの自動売買 / 研究プラットフォーム（ミニマル実装）。  
このリポジトリには取引実行エンジン、監視システム、ポートフォリオ構築ロジック、研究用ファクター計算、AI（ニュース）モジュールなどの主要コンポーネントが含まれます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 前提と依存
- セットアップ手順
- 環境変数（主要）
- 使い方（コマンド例）
- ディレクトリ構成（主要ファイル）
- 運用上の注意

---

## プロジェクト概要

KabuSys は、日本株向けの自動売買システムのコンポーネント群です。  
主な目的は次のとおりです。

- 戦略で生成したシグナルに基づく発注エンジン（ExecutionEngine）の起動・管理
- システム稼働状況や注文状況を監視してアラートや Kill Switch を発動
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 研究用ファクター計算・特徴量解析（DuckDB を利用）
- ニュースの NLP によるセンチメント評価（OpenAI API を利用）
- ペーパートレード用の分離された DB サポートと検証ツール

コア設計方針として、本番 DB とペーパートレード DB を分離し、ルックアヘッドバイアスを避けるために日付参照の取り扱いに注意した実装がされています。

---

## 主な機能

- 実行エンジン起動スクリプト（run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、data/paper_trading.db に記録
  - プロセス優先度の設定、PID 管理、停止フラグ対応
- 監視ループ起動スクリプト（run_monitoring）
  - CPU/メモリ/ディスク、プロセス生存、データ鮮度などの監視ログを SQLite に記録
  - Kill Switch（条件に応じて data/kill.flag を作成）やアラート連係
  - MONITOR_POLL_INTERVAL によりポーリング間隔を調整可能（デフォルト 60 秒）
- MonitoringDB（SQLite）永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
- RiskMonitor：ドローダウン・ポジション上限監視とログ／アラート生成
- MonitoringEngine：各 Monitor の束ねとアラート発火ロジック
- Portfolio モジュール
  - 候補選定、等重・スコア重み付け
  - ポジションサイズ計算（risk_based / equal / score）
  - セクターキャップ適用、レジーム乗数
- Research モジュール（DuckDB ベース）
  - momentum / volatility / value 等のファクター計算
  - forward returns / IC 計算 / 統計サマリ等
- AI モジュール
  - news_nlp: raw_news を OpenAI（gpt-4o-mini）で評価し ai_scores に保存
  - regime_detector: MA200 とマクロ記事センチメントを合成して market_regime を判定
  - API 呼び出しはリトライ・フェイルセーフ実装
- ユーティリティ
  - 統一的な logging 設定（stdout + 日次ローテーション）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - .env 対話式設定ウィザードと設定検証 CLI
- ツール
  - paper_verification_report: ペーパートレード結果の検証レポート生成

---

## 前提と依存

推奨 Python バージョン: 3.9+（型ヒントや一部の標準ライブラリ API を使用）

主な外部依存（抜粋）
- duckdb
- psutil
- openai
- （任意）PyYAML — config/*.yaml の検証を行う場合

注: requirements.txt はこのコードスニペットには含まれていません。実プロジェクトでは requirements.txt / pyproject.toml に依存を明記してください。

---

## セットアップ手順

1. リポジトリをクローンしてワークツリーへ移動
   - git clone ... && cd <repo>

2. （仮想環境作成）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - 必要に応じて PyYAML も追加: pip install PyYAML

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - J-Quants / kabu API キー等の必須項目を入力
   - あるいは .env.example を参考に .env を作成

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告を厳格に扱いたい場合は --strict を付与

6. データフォルダとログディレクトリ
   - デフォルトで以下が想定されます（自動作成処理あり）
     - data/ (SQLite / PID / flag 用)
     - logs/ (ログ出力)
   - 必要に応じて環境変数でパスを上書き（下記参照）

---

## 環境変数（主要）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading のフィルモード（instant/partial/never/reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力ディレクトリ（デフォルト logs）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 監視・停止用フラグ関連

注意:
- run_monitoring のコメントにある通り、Monitoring は環境にかかわらず（実装注釈）本番 sqlite_path を使用する挙動になっています。run_execution は KABUSYS_ENV=paper_trading の場合ペーパートレード用 DB を使用します。

---

## 使い方（コマンド例）

- 環境ウィザード（.env を生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - 起動時にデータベース接続を確立し、BrokerClientFactory によりブローカークライアントを生成
    - KABUSYS_ENV=paper_trading のときは paper_trading.db に記録（本番 DB と分離）
    - 停止は data/stop_requested.flag の作成で受け付ける（フラグ検知で優雅に停止）

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔（秒）を指定可能
  - 停止フラグ: data/stop_requested.flag（存在でループ終了）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

- プログラム的に利用する（例）
  - from kabusys.research import calc_momentum
  - from kabusys.ai.news_nlp import score_news
  - DuckDB 接続を渡してファクター計算や AI スコアリングを呼び出せます

---

## ディレクトリ構成（主要）

以下は src/kabusys 以下を抜粋した構成（説明目的）。実際のリポジトリに合わせて展開してください。

- src/kabusys/
  - __init__.py
  - config.py                 # Settings クラス、.env 自動ロード
  - config_setup.py           # .env 対話式ウィザード（CLI）
  - validate_config.py        # 起動前設定検証 CLI
  - run_execution.py          # ExecutionEngine 起動スクリプト
  - run_monitoring.py         # SystemMonitor ポーリング起動スクリプト

  - utils/
    - __init__.py
    - logging_setup.py        # 共通ログ設定（stdout + 日次ローテーション）
    - process_priority.py     # プロセス優先度 / CPU affinity

  - monitoring/
    - monitoring_db.py        # SQLite 永続化層（表定義 + Migration）
    - system_monitor.py       # CPU/メモリ/ディスク・データ鮮度監視
    - risk_monitor.py         # ドローダウン / ポジション上限検出
    - monitoring_engine.py    # 各 Monitor を束ねるエンジン
    - kill_switch.py          # Kill Switch 管理
    - trade_monitor.py        # （滞留注文・約定異常監視など — 実装あり）

  - execution/
    - execution_engine.py     # ExecutionEngine（起動・セッション管理）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - research/
    - factor_research.py
    - feature_exploration.py

  - ai/
    - news_nlp.py             # ニュース NLP（OpenAI 呼び出し・バリデーション）
    - regime_detector.py      # マクロ + MA200 によるレジーム判定

  - tools/
    - paper_verification_report.py

- data/                       # （デフォルト）DB・フラグ・PID
  - kabusys.duckdb
  - monitoring.db
  - paper_trading.db
  - execution.pid
  - kill.flag
  - stop_requested.flag

- logs/                       # ログファイル（appname.log）

---

## 運用上の注意 / 補足

- Kill Switch / stop フラグ
  - kill.flag: 監視が致命的リスクを検出した場合に作成され、ExecutionEngine の停止トリガーになり得ます。
  - stop_requested.flag: run_* スクリプトを外部から終了させたいときに作成（存在検知でループ終了）。
  - KILL_FLAG_CLEAR_ON_START=1 に設定すると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨します。

- データベース分離
  - ペーパートレードは settings.is_paper 判定で paper_trading.db を利用し、本番の monitoring.db 等と分離します。

- ログ
  - logging_setup.setup_logging を各スクリプト最初に呼ぶことでログ振る舞いを統一します。
  - デフォルトでは stdout に出力し、logs/<app_name>.log に日次ローテーションで保存します。

- 外部 API（OpenAI 等）
  - OpenAI を利用する機能（news_nlp, regime_detector）は OPENAI_API_KEY を必要とします。API の失敗はリトライやフォールバック（例: macro_sentiment=0）を行う実装ですが、キー未設定時は呼び出し先で例外を投げます。

- テスト / CI
  - .env の自動ロードは Settings モジュールで行われます。テスト時に自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

疑問点や README の追記希望（例えば各モジュールの詳しい API 仕様や追加の運用手順）があれば教えてください。必要に応じてコマンド例やサンプル .env テンプレートも追加します。