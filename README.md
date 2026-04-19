# KabuSys

日本株自動売買システムのサンプル実装（ライブラリ + 起動スクリプト群）。  
本リポジトリはトレーディングロジック（シグナル生成・ポートフォリオ構築）と、発注実行・モニタリング・AI（ニュース NLP）等の運用周りのユーティリティを含みます。

---

## 概要

- トレード戦略（ファクター計算、特徴量解析、ポートフォリオ構築、ポジションサイズ計算）
- ExecutionEngine（発注・リスク管理・リコンシリエーション）
- Monitoring（システム状態・注文状態・リスク監視、Kill Switch）
- AI モジュール（OpenAI を使ったニュースのセンチメント評価・市場レジーム判定）
- ユーティリティ（設定ウィザード、設定検証、ログ設定、プロセス優先度設定）
- Paper Trading モード（実データ DB と分離された専用 DB を使用）

設計方針の一部：
- DuckDB を分析用に、SQLite を監視／注文ログ用に使用
- .env ファイルによる環境変数管理（自動ロード機能あり）
- 起動スクリプトはモジュールとして実行可能（python -m kabusys.<module>）

---

## 主な機能一覧

- 設定関連
  - 対話式 .env 作成ウィザード: `kabusys.config_setup`
  - 起動前チェック: `kabusys.validate_config`
  - 設定の自動読み込み（プロジェクトルートの .env / .env.local）
- 実行・監視
  - Execution エンジン起動スクリプト: `kabusys.run_execution`
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し DB を分離
  - Monitoring 起動スクリプト: `kabusys.run_monitoring`
    - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
  - MonitoringEngine による複数モニタ（System/Trade/Risk）ポーリングとアラート評価
  - Kill Switch（リスク条件で data/kill.flag を作成し ExecutionEngine 停止）
- ポートフォリオ関連（純粋関数、DB 参照なし）
  - 銘柄選定 / 等重・スコア重み計算 / ポジションサイズ計算 / セクター上限適用 等
- 研究用（Research）
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン計算・IC 計算・統計サマリ
- AI（OpenAI）
  - ニュース NLP を用いた銘柄別センチメントスコア生成（ai_scores への書き込み）
  - マクロニュース + ETF MA200 を用いた市場レジーム判定（market_regime への書き込み）
- ツール
  - Paper Trading 検証レポート生成: `kabusys.tools.paper_verification_report`

---

## 前提・依存関係

推奨 Python バージョン: 3.10+

主なサードパーティ依存:
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（設定ファイル YAML の検証を行う場合、任意）

インストール例:
- 仮想環境作成
  - python -m venv .venv
  - source .venv/bin/activate（Windows は .venv\Scripts\activate）
- パッケージインストール（最低限）
  - pip install duckdb psutil
- AI 機能を使う場合:
  - pip install openai
- 設定検証で YAML を検証したければ:
  - pip install pyyaml

（requirements.txt は本リポジトリに含まれていないため、プロジェクト要件に応じて適宜作成してください）

---

## セットアップ手順

1. リポジトリをクローン / ルートに移動
2. 仮想環境を作る（推奨）
3. 必要パッケージをインストール（上記参照）
4. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 手動で .env を作成する場合は .env.example を参考に必要な環境変数を設定してください
5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合: python -m kabusys.validate_config --strict
6. DB 初期化
   - 起動スクリプト実行時に監視用 / DuckDB のテーブル・スキーマ初期化が行われます（monitoring の init_monitoring_db 等）
7. （AI 機能を使う場合）OpenAI API キーを設定
   - 環境変数 OPENAI_API_KEY を .env に設定

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（例: INFO）
- OPENAI_API_KEY（AI 機能を使用する場合）
- MONITOR_POLL_INTERVAL（監視スクリプトのポーリング間隔を秒で上書き）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）から .env と .env.local を自動読み込みします
- OS 環境変数が優先され、.env.local は .env を上書きします
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## 使い方（主要なコマンド）

- 設定ウィザード（対話式 .env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - note: KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に記録されます
  - ExecutionEngine 起動時に data/execution.pid に PID が書き込まれます（設定で上書き可能）

- Monitoring 起動（デーモン的に監視ループを回す）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（例: export MONITOR_POLL_INTERVAL=30）
  - 停止制御: プロジェクトの data/stop_requested.flag を作成するとループが終了します
  - 監視は Settings の sqlite_path（本番 DB）を常に使用します（環境に依らず）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを直接指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI / リサーチ機能の利用（プログラム内から）
  - 例: ニュースセンチメントを生成する
    - from open import duckdb などで DuckDB 接続を用意し、
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key は None なら環境変数 OPENAI_API_KEY を参照
  - 市場レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

ログ:
- ログ設定は kabusys.utils.logging_setup.setup_logging が行います
- デフォルトは logs/<app_name>.log に日次ローテーションで出力（30日分保持）および stdout へ出力

停止・Kill Switch:
- リスク条件（ドローダウンやポジション上限）により data/kill.flag が書かれると ExecutionEngine に停止シグナルを送信できます
- 停止フラグ（run_execution/run_monitoring で監視）:
  - data/stop_requested.flag — これが存在するとスクリプトは安全に停止します
  - data/kill.flag — KillSwitch による Execution 停止指示

---

## ディレクトリ構成（主要ファイル）

（抜粋: src/kabusys 以下）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理、自動 .env 読み込み
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 起動前設定検証ツール
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポートツール
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - execution/               — 発注周り（Engine, OrderManager, BrokerFactory 等）
    - (実装ファイル群)
  - monitoring/              — 監視関連（system_monitor, trade_monitor, risk_monitor, kill_switch, monitoring_db, monitoring_engine, alert_manager 等）
  - portfolio/               — ポートフォリオ構築（builder, position_sizing, risk_adjustment）
  - research/                — 研究・ファクター計算（factor_research, feature_exploration）
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロセンチメント合成）
  - data/ (実行時に使用)
    - kill.flag              — Kill Switch フラグ
    - stop_requested.flag    — 停止フラグ（run_* が監視）
    - execution.pid          — Execution の PID（run_execution が管理）
    - monitoring.db          — 監視 SQLite（デフォルト SQLITE_PATH）
    - paper_trading.db       — ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）
  - config/                  — YAML 設定テンプレート（system_config.yaml 等。generate スクリプトで作成想定）

---

## 注意事項 / 運用上のヒント

- 本番環境（KABUSYS_ENV=live）の設定は慎重に確認してください。validate_config は live 時の追加チェックを行います（LINE 通知設定、KILL_FLAG_CLEAR_ON_START など）。
- Monitoring は常に Settings.sqlite_path（本番の monitoring.db）を使用します。Paper trading モードでも監視 DB は分離されません（監視は本番 DB を参照する設計）。
- Paper trading（KABUSYS_ENV=paper_trading）では発注先は MockBroker となり、PAPER_TRADING_SQLITE_PATH に記録されます（実口座と分離）。
- OpenAI を使う機能は API キーが必要です。API 呼び出しはリトライ・フォールバック実装（429/5xx/タイムアウト対応）がありますが、API 利用料やレート制限に注意してください。
- ログディレクトリ作成に失敗するとファイル出力は無効化され、コンソール出力のみになります（その旨が stderr に出ます）。
- .env は絶対に Git にコミットしないでください（config_setup のヘッダにも記載あり）。

---

## 追加情報 / 開発メモ

- DB スキーマの移行処理（例: monitoring_db の ALTER TABLE によるカラム追加）は init 時に冪等に実行されます
- 一部の低レベル関数（OpenAI 呼び出し等）はテスト時にモック可能な設計になっています（例: _call_openai_api を patch）
- research / portfolio の関数群は純粋関数ベースで副作用がなく単体テストが容易です

---

必要であれば、README に動作例（コマンド一式）、.env.example の雛形、あるいは Docker / systemd ユニット例を追加できます。どの情報を優先して追記しますか？