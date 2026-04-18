# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ＋起動スクリプト群）。  
この README はコードベース（src/kabusys 以下）の主要コンポーネント、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめたものです。

注意: 実行には外部サービス API（kabuステーション、J‑Quants、OpenAI など）やネイティブライブラリ（duckdb, psutil 等）が必要になる場合があります。まずはローカル開発用に .env を作成して設定検証を行ってください。

---

目次
- プロジェクト概要
- 機能一覧
- 必要要件（依存）
- セットアップ手順
- 環境変数（主なもの）
- 使い方（代表的なコマンド）
- 実装上の注意点 / 動作のポイント
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買／研究用ツール群です。主に以下を提供します。

- 実運用向け ExecutionEngine（発注・オーダー管理・リスク管理）
- 監視（Monitoring）コンポーネント（プロセス監視、データ鮮度、リスク監視、Kill Switch）
- ポートフォリオ構築ユーティリティ（銘柄選定、重み付け、ポジションサイズ）
- リサーチ用モジュール（ファクター計算、特徴量探索）
- AI を用いたニュースセンチメント（OpenAI 経由のスコアリング）と市場レジーム判定
- ユーティリティ（ログセットアップ、プロセス優先度設定、設定ウィザード／検証）
- ペーパートレード検証用レポート生成ツール

---

## 機能一覧

- run_execution.py
  - ExecutionEngine の起動スクリプト
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使い paper_trading 専用 SQLite DB（data/paper_trading.db など）へ記録
  - プロセス優先度を上げて実行、停止フラグ（data/stop_requested.flag）を監視
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - Monitoring は環境に関わらず本番 sqlite_path を使用して監視ログを永続化
- monitoring パッケージ
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch / MonitoringDB など
  - system_status, trade_logs, positions, risk_logs, dashboard 等のテーブルを管理
- portfolio パッケージ
  - 候補選定、等重・スコア重み、ポジション数計算、セクター上限適用、レジーム乗数
- research パッケージ
  - ファクター（Momentum, Value, Volatility 等）計算、将来リターン、IC 計算、統計サマリ
- ai パッケージ
  - news_nlp: raw_news を集約して OpenAI へ送信し銘柄別センチメントを ai_scores へ書込
  - regime_detector: ETF の MA 差分とマクロニュースを合成して market_regime を判定
- utils
  - logging_setup: stdout + 日次ローテーションログ設定
  - process_priority: psutil を使った優先度・CPU affinity 設定
- 設定支援ツール
  - config_setup.py: .env 作成ウィザード（対話式）
  - validate_config.py: .env および config/*.yaml の存在・形式を検証
- tools
  - paper_verification_report.py: ペーパートレード DB 解析と PASS/FAIL レポート生成

---

## 必要要件（依存）

最低限の Python パッケージ（抜粋）:

- Python 3.9+ を想定
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML (validate_config が YAML 検証を行う場合に推奨)

インストール例（仮）:
- 仮想環境作成:
  - python -m venv .venv
  - source .venv/bin/activate (Windows: .venv\Scripts\activate)
- 必要パッケージのインストール:
  - pip install duckdb psutil openai pyyaml

プロジェクト配布に requirements.txt があればそれを使用してください。

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. 仮想環境を作成して有効化
3. 必要パッケージをインストール（上記参照）
4. .env を作成
   - 対話式で作る:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に直接作成
   - 自動読み込み:
     - プロジェクトルートに .env/.env.local があると自動で読み込まれます
     - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. 設定検証:
   - python -m kabusys.validate_config
   - 問題があれば修正して再実行
6. SQLite / DuckDB の初期化はスクリプト起動時に行われます（monitoring_db.init_monitoring_db が必要テーブルを冪等に作成します）

---

## 環境変数（主なもの）

必須（実行に必要）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要な設定:
- KABUSYS_ENV (development | paper_trading | live) — 動作モード
  - paper_trading: ExecutionEngine は paper_trading 用 DB / MockBroker を使用
  - live: 本番モード（注意）
- DUCKDB_PATH (デフォルト data/kabusys.duckb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB パス、デフォルト data/paper_trading.db)
- OPENAI_API_KEY (AI 機能を使う場合)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒数、デフォルト 60)

Kill / Stop 関連ファイル:
- data/kill.flag — KillSwitch が書き込むと ExecutionEngine に停止シグナルを送る
- data/stop_requested.flag — run_monitoring / run_execution が存在を検出して自プロセスを終了

その他:
- PAPER_FILL_MODE (instant|partial|never|reject) — paper_trading の約定挙動
- KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動でクリア（本番では推奨しない）

---

## 使い方（代表的なコマンド）

1. 設定ウィザード（.env 作成）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いで exit 1

3. ExecutionEngine を起動
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使い MockBrokerClient 動作

4. Monitoring を起動（SystemMonitor のポーリングループ）
   - python -m kabusys.run_monitoring
   - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒数指定可能（例: MONITOR_POLL_INTERVAL=30）

5. ペーパートレード検証レポート
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     - --from YYYY-MM-DD --to YYYY-MM-DD
     - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）

6. AI ニューススコア / レジーム判定（ライブラリ関数として使用）
   - kabusys.ai.score_news(conn, target_date, api_key=None)
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - これらは DuckDB の接続オブジェクトを受け取り処理します。OpenAI API キーを環境変数 OPENAI_API_KEY で設定するか引数で渡してください。

ログ:
- ログは stdout と logs/<app_name>.log（日次ローテーション、30 日保管）に出力されます。ログの設定は kabusys.utils.logging_setup.setup_logging で統一的に行われます。

停止 / Kill:
- Monitoring / Execution は data/stop_requested.flag や data/kill.flag の有無を見て動作を停止・制御します。KillSwitch（監視側）は条件に応じて data/kill.flag を書き込みます。

---

## 実装上の注意点 / 動作のポイント

- 設定自動ロード:
  - プロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動で読み込みます。
  - OS 環境変数の上書きを防ぐ保護機構あり。テスト等で自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- DB 分離:
  - run_monitoring は環境に関わらず本番 sqlite_path を使います（監視ログ一元化）。
  - run_execution は KABUSYS_ENV=paper_trading 時に paper_sqlite_path を使うため本番 DB と分離できます。
- ロギング:
  - すべての起動スクリプトは setup_logging を呼び出して統一的にログを扱います。ログディレクトリ作成に失敗するとファイル出力は無効化され、コンソール出力のみになります。
- プロセス優先度:
  - 起動時に set_process_priority("high") を呼び出します（psutil を使用）。環境により設定できない場合は警告ログが出ます。
- AI 機能:
  - OpenAI の呼び出しはリトライ／バックオフ、JSON レスポンス検証、スコアのクリップなどに慎重な実装になっています。
  - API キー未設定時は ValueError を投げるか、フォールバック（macro_sentiment=0.0）する設計の箇所がありますので注意してください。
- マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブルを作成し、一部の既存スキーマに対する簡易マイグレーション（カラム追加）も行います。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要なファイル・ディレクトリ構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings ラッパー、自動 .env ロード
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前チェック CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py             — ニュース NLP / OpenAI スコアリング
    - regime_detector.py      — 市場レジーム判定
    - __init__.py
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py        — （取引監視、コード中に存在）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        — アラート通知をまとめる（コード内に参照あり）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                     — 実行時に .env で指定するデフォルト DB / PID / flag ファイルが置かれる想定（リポジトリには含まれないことが多い）

※ 上記は実装の一部を抜粋したものです。詳細はソース（src/kabusys 以下）を参照してください。

---

問題が発生した場合や追加のドキュメント（API 使用例、開発者向けセットアップ、テスト手順、Docker 化等）を希望される場合は、どの項目を詳しく知りたいか教えてください。README の例や .env のサンプルテンプレートの作成も対応できます。