# KabuSys — 日本株自動売買システム（README）

このリポジトリは日本株向けの自動売買システムの一部実装です。取引エンジン、監視 / アラート、ポートフォリオ構築、研究用ファクター計算、LLM を用いたニュース NLP 等のモジュールで構成されています。本 README はプロジェクトの概要、機能、セットアップ、使い方、ディレクトリ構成をまとめたものです。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動・コマンド例）
- 主要環境変数（よく使うもの）
- 停止 / Kill スイッチについて
- ディレクトリ構成（主要ファイル説明）
- 補足（依存関係等）

---

## プロジェクト概要

KabuSys は次を目的としたモジュール群を提供します：

- 発注エンジン（ExecutionEngine）とブローカークライアント
- 実行/約定ログの永続化（SQLite）および分析用 DB（DuckDB）
- システム監視（CPU/メモリ/ディスク、データ鮮度、プロセス生存確認）
- リスク監視（ドローダウン、保有上限など）と Kill Switch（自動停止）
- Portfolio construction（銘柄選定・重み付け・枚数算出）
- 研究用モジュール（ファクター計算・IC、将来リターンなど）
- AI モジュール（ニュース NLP、レジーム検出：OpenAI API 使用）
- 各種 CLI ツール（.env ウィザード、設定検証、Paper Trading レポート）

設計方針の抜粋：
- DB・ファイルパスは環境変数／.env で管理（.env ウィザードあり）
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離（別 SQLite）
- AI 機能は OpenAI API キーが必要（失敗時はフェイルセーフ動作）

---

## 主な機能一覧

- run_execution.py: ExecutionEngine 起動スクリプト
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し paper_trading DB に書き込む
  - プロセス優先度を上げて実行、PID ファイル出力、stop フラグ監視
- run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
  - 監視結果を SQLite（監視 DB）へ記録、DuckDB は分析用に接続
  - MONITOR_POLL_INTERVAL でポーリング間隔を指定可能
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する
- monitoring/*: MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch 等
- portfolio/*: 候補選定・等重/スコア重み・ポジションサイズ決定・セクター制限など純粋関数
- research/*: DuckDB ベースのファクター計算（モメンタム・バリュー・ボラティリティ等）、IC 計算
- ai/*: OpenAI を使ったニュースセンチメント（news_nlp）・市場レジーム判定（regime_detector）
- utils: ロギング設定、プロセス優先度 / CPU affinity、設定読み込みロジック等
- tools/paper_verification_report.py: ペーパートレードの検証レポート生成ツール
- config_setup.py: 対話式 .env 生成ウィザード
- validate_config.py: .env / config/*.yaml の起動前チェック CLI

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate （Windows は .venv\Scripts\activate）

2. 依存パッケージをインストール
   - 推奨（プロジェクトに requirements.txt がある想定）:
     - pip install -r requirements.txt
   - 最低限必要なライブラリ（コードで使用されているもの）:
     - duckdb, psutil, openai
   - （YAML の内容検証を行う場合）PyYAML が必要

3. .env の初期作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 作成後、設定を検証:
     - python -m kabusys.validate_config
     - 問題があれば .env を編集して修正してください

4. データディレクトリの準備（必要に応じて）
   - デフォルトはプロジェクト直下の data/ および logs/
   - 例: mkdir -p data logs

5. OpenAI を使う機能を利用する場合
   - 環境変数 OPENAI_API_KEY に API キーを設定するか、関数呼び出し時に渡す

---

## 使い方（主要な起動方法・例）

基本的に以下のコマンドでモジュールを起動します（プロジェクトルートから実行）。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit(1)

- 発注エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 起動前に KABUSYS_ENV を設定:
    - export KABUSYS_ENV=paper_trading  （ペーパートレード）
    - export KABUSYS_ENV=live           （本番）
  - paper_trading の場合は PAPER_TRADING_SQLITE_PATH（env）に記録され、本番 DB と分離されます

- 監視プロセス起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - export MONITOR_POLL_INTERVAL=30  # 秒

- Paper Trading 検証レポート（標準出力へ）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または環境変数 PAPER_TRADING_SQLITE_PATH を指定して DB を切り替え

- AI 機能（Python API として呼び出す）
  - 例（news_nlp の呼び出し）:
    - from openai import OpenAI
      import duckdb, datetime
      from kabusys.ai.news_nlp import score_news
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, datetime.date(2026,4,20), api_key="sk-...")

  - 注意: OpenAI API の呼び出しはレート制限やネットワークエラーを考慮した実装になっていますが、API キーが必須です

- 研究用 / ファクター計算（Python API）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - DuckDB 接続を渡して target_date を指定して呼ぶ

---

## 主要環境変数（概要とデフォルト）

- KABUSYS_ENV
  - 値: development | paper_trading | live
  - デフォルト: development
  - 影響: 発注挙動（paper_trading は mock ブローカー）や安全チェック

- JQUANTS_REFRESH_TOKEN
  - J-Quants API 用（必須）

- KABU_API_PASSWORD
  - kabuステーション API パスワード（必須）

- KABU_API_BASE_URL
  - デフォルト: http://localhost:18080/kabusapi

- DUCKDB_PATH
  - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）

- SQLITE_PATH
  - 監視 DB（monitoring）SQLite のパス（デフォルト: data/monitoring.db）
  - 監視プロセスは KABUSYS_ENV にかかわらずこの本番 sqlite_path を使用します

- PAPER_TRADING_SQLITE_PATH
  - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - KABUSYS_ENV=paper_trading のとき run_execution がこちらを使います

- PAPER_FILL_MODE
  - Paper Trading の注文埋め方: instant | partial | never | reject
  - デフォルト: instant

- OPENAI_API_KEY
  - OpenAI 呼び出し用 API キー（AI 機能を使う場合必須）

- LOG_LEVEL, LOG_DIR
  - ログレベル・ログディレクトリ（デフォルト: INFO / logs/）
  - setup_logging() により stdout と日次ローテートファイルが設定されます

- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔（秒）。デフォルト 60 秒

- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
  - PID ファイルや Kill フラグのパス、起動時に Kill フラグを自動クリアするかどうか

---

## 停止 & Kill スイッチ

- 停止フラグ（手動／外部からの停止指示）
  - ファイル: data/stop_requested.flag
  - run_monitoring / run_execution はこのファイルの存在を検知してループを終了します
  - 手動で停止したいときはプロジェクトの data/ ディレクトリに空の stop_requested.flag を作成してください

- Kill Switch（自動停止トリガ）
  - KillSwitch モジュールが条件を満たすと data/kill.flag を書き込みます（ExecutionEngine に停止を促す）
  - 条件例: ドローダウン閾値超過、ポジション上限超過 など
  - kill.flag が存在する間は ExecutionEngine は起動を控えたり停止します
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に KillFlag を自動クリアできますが、本番では 0 を推奨します

---

## ディレクトリ構成（主要ファイルと説明）

以下は src/kabusys 配下の主なファイル/パッケージです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数/.env の自動読み込み・Settings クラスを提供
  - config_setup.py
    - 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
  - validate_config.py
    - 起動前チェック CLI（python -m kabusys.validate_config）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（発注エンジン）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
      - ペーパートレード検証レポート生成（sqlite DB を集計）
  - ai/
    - news_nlp.py
      - raw_news を LLM で評価して ai_scores に書き込む
    - regime_detector.py
      - MA200 乖離 + マクロ NLP を合成して market_regime を計算
  - monitoring/
    - monitoring_db.py
      - SQLite テーブル作成 / 永続化 API（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py
      - CPU/メモリ/ディスク監視、データ鮮度チェック、プロセス生存確認
    - risk_monitor.py
      - ドローダウン・ポジション上限監視
    - trade_monitor.py (存在)
      - 発注履歴の監視（滞留注文や約定異常など）
    - kill_switch.py
      - 条件に応じて kill.flag を書くユーティリティ
    - monitoring_engine.py
      - 各 Monitor をまとめるポーリングエンジン
    - alert_manager.py (存在)
      - アラート通知（LINE など）を統合（コード内で参照）
  - portfolio/
    - portfolio_builder.py
      - 候補選定・重み計算
    - position_sizing.py
      - 枚数決定・aggregate cap／lot 単位への調整
    - risk_adjustment.py
      - セクターキャップ・レジーム乗数
  - research/
    - factor_research.py
      - Momentum / Volatility / Value ファクター計算（DuckDB 前提）
    - feature_exploration.py
      - 将来リターン・IC・統計サマリ等
  - utils/
    - logging_setup.py
      - 共通ロギング設定（stdout + 日次ローテート）
    - process_priority.py
      - プロセス優先度設定 / CPU affinity（psutil 使用）
  - monitoring/*、execution/*、data/* （その他の実装ファイル群）

（注）上記はコードベースの代表ファイルを抜粋した一覧です。実際の完全なツリーはリポジトリルートで tree コマンド等を使って確認してください。

---

## 補足 / 運用上の注意

- 監視（monitoring）は常に本番用 sqlite_path（SQLITE_PATH）を参照します。監視 DB を別にしたい場合は SQLITE_PATH を適切に設定してください。
- ペーパートレード実行は PAPER_TRADING_SQLITE_PATH を使用して本番 DB と分離されます。
- OpenAI を利用する機能は API 呼び出し回数とコストに注意してください。失敗時はフォールバック（0.0 等）やスキップする実装になっていますが、API キー漏洩や課金には注意。
- ログは logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリが作成できない場合はコンソール出力のみになります。
- process_priority.set_process_priority() は psutil の権限に依存します。権限不足で設定できない場合は警告が出力されます。
- DuckDB はローカル分析向けに利用。research モジュールは prices_daily / raw_financials 等のテーブルが前提です。

---

必要があれば以下も作成します：
- 具体的なシステム運用手順（デプロイ・サービス化 / systemd ユニット例）
- 開発者向けのユニットテスト実行手順
- 依存パッケージの pinned requirements.txt

ほかに README に追加したい情報（例: systemd ユニット、Docker 化、CI 設定など）があれば教えてください。