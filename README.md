# KabuSys

日本株向け自動売買システムの骨格ライブラリ / 起動スクリプト群です。  
このリポジトリは以下の主要機能を提供します（実装済みのモジュール群に基づく説明）。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買パイプラインを構成するモジュール群です。主な責務は次のとおりです。

- 市場データ（DuckDB）を使ったファクター計算・リサーチ機能
- ポートフォリオ構築（候補選定・重み付け・単元丸め・リスク調整）
- ExecutionEngine の起動スクリプト（本番/ペーパートレード切替）
- 監視用モニタリング（リソース・プロセス・注文・リスク監視）と Kill Switch
- OpenAI を用いたニュース NLP（センチメント）・市場レジーム判定の補助
- 設定ウィザード・検証ツール・レポート生成ツールなどのユーティリティ

設計上の特徴として、
- DuckDB / SQLite をローカル DB として利用
- .env による環境変数管理（config_setup による対話式作成）
- 実行スクリプトはプロセス優先度設定・ロギング設定を統一
- Paper Trading は本番 DB と分離（別 SQLite を使用）
などがあります。

---

## 機能一覧（抜粋）

- 設定関連
  - .env 対話式ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
- 実行系
  - ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading 時は MockBroker を使い、別 DB（data/paper_trading.db）へ記録
  - Monitoring 起動スクリプト: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60s）
    - monitoring 側は環境にかかわらず本番 sqlite_path を利用する（監視 DB の一元管理）
- モジュール（主要）
  - kabusys.portfolio: 候補選定・重み計算・ポジションサイズ計算・セクター上限適用・レジーム乗数
  - kabusys.research: DuckDB を使ったファクター計算（モメンタム / ボラティリティ / バリュー 等）および IC 等の解析ユーティリティ
  - kabusys.ai: ニュース NLP スコアリング（OpenAI）・市場レジーム判定
  - kabusys.monitoring: system/trade/risk の各モニタ、MonitoringEngine、kill switch、監視 DB（SQLite）ラッパー
  - kabusys.utils: ログセットアップ、プロセス優先度 / CPU affinity ユーティリティ 等
- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

---

## セットアップ手順（ローカル開発向け）

以下は一般的な Python 開発環境の前提です。requirements.txt は本リポジトリに明示されていないため、必要なパッケージは次を含みます（実行する機能に応じて追加してください）:

- Python 3.9+
- 必要ライブラリ例:
  - psutil
  - duckdb
  - openai
  - PyYAML（設定検証で YAML を検査する場合のみ）
  - その他：logging, sqlite3 は標準ライブラリ

手順例:

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install psutil duckdb openai PyYAML

   （本プロジェクトを package としてインストール可能なら pip install -e . など）

3. プロジェクトルートで初期ディレクトリを作成
   - mkdir -p data logs

4. 環境変数設定
   - 対話式で .env を作る: python -m kabusys.config_setup
   - もしくは .env を直接作成して以下の主要な環境変数を設定してください（下の「重要な環境変数」参照）。

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 問題があれば .env を編集し再検証

6. DB 初期化は起動スクリプトが自動で行います（monitoring / execution 起動時に init_monitoring_db を呼びます）。

---

## 重要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: 発注はモック・DB を分離
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper トレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant | partial | never | reject）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY: OpenAI を使う機能で必要（news_nlp / regime_detector 等）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: アラート通知に使用（任意）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）
- MONITOR_POLL_INTERVAL: run_monitoring に渡すポーリング間隔（秒、デフォルト 60）

ファイル・フラグ:
- data/execution.pid: ExecutionEngine の PID ファイル（実行スクリプトが使用）
- data/kill.flag: Kill Switch を発動するためのフラグファイル（作成すると ExecutionEngine 停止）
- data/stop_requested.flag: run_execution/run_monitoring での停止フラグ（手動で作成するとループを抜ける）

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになる: python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番 / Paper は KABUSYS_ENV に従う）
  - python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - ペーパートレード時（KABUSYS_ENV=paper_trading）は paper_sqlite_path を使用し本番 DB と分離します。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（例: export MONITOR_POLL_INTERVAL=30）
  - run_monitoring は monitoring 用の SQLite（settings.sqlite_path）を使用します（KABUSYS_ENV に関係なく本番の sqlite_path を参照する実装上の挙動に注意）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH またはデフォルト data/paper_trading.db を使用。

- OpenAI を使った機能
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡して呼び出します。api_key が None の場合は環境変数 OPENAI_API_KEY を参照。

ログ:
- setup_logging 関数により logs/<app_name>.log に日次ローテートで出力（既定: logs/）
- LOG_DIR 環境変数でログディレクトリを変更可能

停止:
- 実行中の run_execution/run_monitoring を停止するには data/stop_requested.flag を作成するか、ターミナルで Ctrl+C（KeyboardInterrupt）を送ります。
- Kill Switch は条件を満たした際に data/kill.flag を書き込むことで ExecutionEngine 停止のための外部トリガーになります。

---

## ディレクトリ構成（主要ファイル・モジュール）

以下は src/kabusys 以下の主要ファイル／パッケージ構成の抜粋です。実際のリポジトリにはさらにファイルが存在する場合があります。

- src/
  - kabusys/
    - __init__.py
    - config.py                 # 環境変数読み込み・Settings クラス（.env 自動読み込み含む）
    - config_setup.py           # .env 対話式ウィザード
    - validate_config.py        # 起動前設定検証ツール
    - run_execution.py          # ExecutionEngine 起動スクリプト
    - run_monitoring.py         # Monitoring 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py             # ニュースから OpenAI を使ってスコアを生成
      - regime_detector.py      # マクロ + ETF ma200 でレジーム判定
    - monitoring/
      - monitoring_db.py        # SQLite 操作用ラッパー / スキーマ初期化
      - system_monitor.py
      - trade_monitor.py        # （実装参照）
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py        # （実装参照）
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - data/                      # 実行時に作成されることが多い（data/*.db, *.flag, *.pid）
    - logs/                      # デフォルトログ出力先

---

## 実装上の注意点 / 運用メモ

- run_monitoring のポーリング間隔は MONITOR_POLL_INTERVAL で制御できます。0 以下や不正な値は無視されてデフォルト 60 秒が使われます。
- run_monitoring は「監視用の SQLite を常に本番用 sqlite_path に接続する」実装になっています（KABUSYS_ENV に依存しない）。運用時は監視 DB の扱いに注意してください。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使って本番 DB と分離します。
- process priority / CPU affinity の設定は utils.process_priority を通して行われます。権限がない場合は警告が出ますが起動自体は継続します。
- OpenAI を使うモジュールは API のレート制限や一時障害を考慮してリトライやフェイルセーフ（スコア 0 相当）を実装していますが、API キーの管理・コストには注意してください。
- monitoring/monitoring_db.py の init_monitoring_db は冪等的にテーブルを作成し、既存 DB のマイグレーション（カラム追加）も行います。
- .env は絶対にコミットしないでください（config_setup のヘッダにも記載あり）。

---

## 追加情報 / 開発者向け

- テスト: 各モジュールは純粋関数や副作用の少ないクラスに分かれているため、ユニットテストの追加が容易です（OpenAI 呼び出し等はモック可能）。
- DuckDB のクエリは大量データでも高速に動作しますが、テーブルスキーマ（prices_daily / raw_financials / raw_news 等）に依存するため、分析用データの整備が必要です。
- 将来的拡張のポイント（ソース内 TODO あり）:
  - 銘柄ごとの lot_size を持つマスタ参照
  - price のフォールバックロジック（欠損時の処理）
  - ログのさらなる集中管理（外部ローテーションや監視ツール連携）

---

何か特定の起動方法、設定項目の追加説明、あるいは各モジュール単体のドキュメント（関数仕様や使用例）を README に追加したい場合は、どの部分を詳しく記載するか教えてください。