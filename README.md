# KabuSys

日本株向け自動売買システムのライブラリ／実行スクリプト群です。本リポジトリは発注エンジン、監視、ファクター研究、ポートフォリオ構築、AI（ニュースNLP／レジーム判定）などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能を持つモジュール群から構成されています。

- ExecutionEngine（発注エンジン、paper/live モード対応）
- Monitoring（システム監視・リスク監視・アラート／Kill Switch）
- Portfolio（銘柄選定・配分・ポジションサイズ計算）
- Research（ファクター計算・将来リターン・IC計算など）
- AI（ニュースの NLP によるセンチメントスコア、レジーム判定）
- ユーティリティ（設定読み込み、ログ設定、プロセス優先度設定 等）
- CLI ツール（.env ウィザード、設定検証、Paper Trading レポート生成）

設計方針の抜粋:
- 本番用 DB とペーパートレード DB を明確に分離
- Docker や外部サービスからの設定は環境変数／.env で管理
- LLM (OpenAI) 呼び出しはフェイルセーフ（失敗時は既定値で継続）
- ルックアヘッドバイアスに配慮（date.today() を直接参照しない等）

---

## 主な機能一覧

- 実行（run_execution.py）
  - KABUSYS_ENV に依存して実運用 / ペーパートレードを切替
  - Broker クライアントのファクトリ、OrderManager、RiskManager、Reconciler 等の組立て
  - 実行中は `data/execution.pid` を作成し、`data/stop_requested.flag` を監視して停止

- 監視（run_monitoring.py + Monitoring エンジン）
  - CPU/メモリ/ディスク使用率、Execution プロセスの存否、データ鮮度を定期記録
  - RiskMonitor によるドローダウン／ポジション上限監視、Kill Switch の発動
  - 監視ログは SQLite（デフォルト: data/monitoring.db）へ永続化

- AI（kabusys.ai）
  - news_nlp: raw_news をまとめて OpenAI に投げ、銘柄ごとのセンチメントを ai_scores テーブルへ書き込む
  - regime_detector: ETF（1321）の MA200 とマクロニュースの LLM センチメントを合成しレジーム判定

- Research（kabusys.research）
  - calc_momentum / calc_volatility / calc_value などのファクター計算
  - calc_forward_returns / calc_ic / factor_summary 等の解析ユーティリティ

- Portfolio（kabusys.portfolio）
  - 銘柄選定（select_candidates）、重み算出（等金額・スコア加重）
  - ポジションサイズ計算（複数方式、lot 単位で丸め、aggregate cap 処理）
  - セクターキャップ適用、レジーム乗数算出

- ツール
  - config_setup.py: .env の対話式作成/更新ウィザード
  - validate_config.py: .env / config/*.yaml の事前検証用 CLI
  - tools.paper_verification_report: Paper Trading 結果の検証レポート生成

---

## セットアップ手順

1. Python 環境の用意（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - 必須: duckdb, psutil, openai
   - 開発／追加機能: PyYAML（validate_config の YAML 検証で使用）
   - 例:
     - pip install duckdb psutil openai
     - pip install pyyaml  # 任意（validate_config の YAML 検証）

3. リポジトリルートに移動（自動 .env ロードはプロジェクトルート検出を行います）

4. .env の作成
   - 対話式で作る（推奨）:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合:
     - python -m kabusys.validate_config --strict

6. DB ディレクトリ／ログディレクトリの作成（通常は自動作成されます）
   - data/
   - logs/

---

## 環境変数（主なもの）

以下は主要な環境変数とデフォルト値／必須性の概要です。

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
  - KABU_API_PASSWORD — kabuステーション API 用パスワード（必須）

- 動作モード
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
    - paper_trading の場合、専用 SQLite（PAPER_TRADING_SQLITE_PATH）へ記録

- DB パス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB、デフォルト: data/paper_trading.db）

- ログ
  - LOG_LEVEL（デフォルト: INFO）
  - LOG_DIR（デフォルト: logs/）

- OpenAI
  - OPENAI_API_KEY — AI モジュール（news_nlp / regime_detector）使用時に必要

- モニタリング
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — Kill Switch / PID の設定

- Paper trading 動作
  - PAPER_FILL_MODE — instant | partial | never | reject（デフォルト: instant）

詳細は `kabusys.config.Settings` を参照してください。

---

## 使い方（主要コマンド）

- .env の生成（対話式）
  - python -m kabusys.config_setup

- 設定の検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- 実行エンジン起動
  - 本番／ペーパー／開発は KABUSYS_ENV で切替
  - python -m kabusys.run_execution
    - 起動時に `data/stop_requested.flag` が存在すると起動しません
    - 実行中は `data/execution.pid` が作成されます
    - 停止は `data/stop_requested.flag` を作成することで行えます

- 監視プロセス起動
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能（秒、デフォルト60）
    - 監視は常に production 用 sqlite_path を使用（KABUSYS_ENV に依らない）
    - 停止は `src/…/data/stop_requested.flag` の存在で検知

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（--db で指定可、または環境変数 PAPER_TRADING_SQLITE_PATH）

- AI モジュールを直接利用する例（プログラム内）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key="…")

注意:
- OpenAI を使う機能は OPENAI_API_KEY が必要です。指定がない場合、該当関数は ValueError を投げます。
- run_execution は paper_trading の場合、記録先 DB が分離されます（データの混在を防ぐ）。

---

## 動作に関する注意点

- Kill Switch / Stop Flag
  - `data/kill.flag` : Kill Switch が発動した際に書き込まれるフラグ（Execution 停止トリガ）
  - `data/stop_requested.flag` : 実行・監視プロセスの外部停止要求で使用
  - `KILL_FLAG_CLEAR_ON_START`=1 を本番で設定するのは危険（自動クリアされます）

- ログ
  - デフォルトで stdout に出力し、logs/<app_name>.log に日次ローテーションで保存（30日保持）
  - ログディレクトリ作成に失敗するとファイル出力はスキップされます

- データベース
  - monitoring は sqlite に永続化（監視テーブル等は init_monitoring_db で自動作成・マイグレーションを行います）
  - DuckDB は主にリサーチ・AI 集計用途

- OpenAI 呼び出しはリトライ・バックオフ実装が入っており、429/タイムアウト/サーバーエラーはリトライされます。その他のエラーはスキップしてフェイルセーフに動作します。

---

## ディレクトリ構成（抜粋）

ソースは `src/kabusys` 以下に配置されています。主要ファイル・ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py            # （存在する想定）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py            # （存在する想定）
  - execution/
    - execution_engine.py        # （存在する想定）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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

（上記のうち、コメントに「存在する想定」とあるものはリポジトリ内で補完されている他のモジュールと連携します。README は含まれるファイル群の主要な役割を表しています。）

---

## 開発者向けメモ

- 自動で .env を読み込む挙動は `KABUSYS_DISABLE_AUTO_ENV_LOAD` 環境変数で無効化できます（テスト時に便利）。
- DuckDB 接続は分析用途に最適化されており、研究モジュールは SQL+Python の組合せで計算します。
- テスト時に OpenAI 呼び出しを差し替えるため、news_nlp／regime_detector の内部 API 呼び出しは簡単にモックできます（ユニットテストでの patch 推奨）。

---

## 参考コマンドまとめ

- .env ウィザード: python -m kabusys.config_setup
- 設定検証:    python -m kabusys.validate_config
- 実行エンジン: python -m kabusys.run_execution
- 監視開始:    python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

ご不明点や README に追記したい項目（例: example .env、依存関係の requirements.txt、Docker/CICD の例など）があれば教えてください。必要に応じて追補・詳細化します。