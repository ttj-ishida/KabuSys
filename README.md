# KabuSys

日本株自動売買システムのリポジトリ（ライブラリ / 起動スクリプト / ツール群）。  
この README はリポジトリ内の主要なモジュールを元に、導入・実行手順、機能一覧、ディレクトリ構成などをまとめたものです。

---

## プロジェクト概要

KabuSys は以下の目的を持つ Python ベースの自動売買システムです。

- 株価データおよび財務データを用いたファクター計算・特徴量探索（research）
- ポートフォリオ構築（候補選定、配分、サイズ決定、セクター制約など）
- Execution エンジン（ブローカークライアントを通じた発注処理。paper_trading モードあり）
- 監視（System / Trade / Risk）と Kill Switch による自動停止
- Paper Trading の検証レポート生成
- ニュース NLP（OpenAI を用いた銘柄ごとのセンチメント評価）および市場レジーム判定

設計上の方針は「ロジックの分離」「外部サービス（取引 API, OpenAI）への接続は明示的に与える」「フェイルセーフ（API失敗時は安全側にフォールバック）」などです。

---

## 主な機能一覧

- 環境設定ウィザード（.env 作成・更新）: python -m kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml の事前チェック）: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト（発注エンジン）: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
  - 停止は data/stop_requested.flag により制御。PID ファイル (data/execution.pid) を生成
- Monitoring ポーリングループ起動: python -m kabusys.run_monitoring
  - 環境にかかわらず本番の sqlite_path を使用して監視ログを永続化
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（既定 60 秒）
- MonitoringEngine（System / Trade / Risk を束ねてアラート・Kill Switch 評価）
- Risk モニタ（ドローダウン・ポジション数監視、閾値超過で risk_logs / dashboard 更新）
- MonitoringDB：SQLite への永続化（system_status / trade_logs / positions / risk_logs / dashboard）
- Paper Trading 検証レポート生成ツール: python -m kabusys.tools.paper_verification_report
- ニュース NLP（OpenAI を使用した銘柄センチメント算出）: kabusys.ai.score_news
- 市場レジーム判定（MA + マクロニュースの LLM スコアを合成）: kabusys.ai.regime_detector.score_regime
- research（ファクター計算、将来リターン、IC、統計サマリー）
- portfolio（候補選定、重み計算、ポジションサイズ決定、セクター制約、レジーム乗数）

---

## セットアップ手順

1. Python 環境の準備（推奨: 仮想環境）
   - 例:
     ```
     python -m venv .venv
     source .venv/bin/activate   # Unix/macOS
     .venv\Scripts\activate      # Windows
     ```

2. 依存パッケージをインストール
   - 必要な代表パッケージ（プロジェクトに `requirements.txt` がない場合の例）:
     ```
     pip install duckdb psutil openai PyYAML
     ```
   - 実行環境により追加で必要なパッケージがある場合があります（例: duckdb のバイナリ、OpenAI SDK バージョンなど）。

3. プロジェクト ルート（pyproject.toml / .git がある場所）に移動して作業
   - ソースは `src/` 下にあります。パッケージを開発編集モードでインストールする場合:
     ```
     pip install -e .
     ```

4. 初期設定ファイル（.env）の作成
   - 対話式ウィザードを推奨:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは手動で `.env` を作成してください（下に主要な環境変数の一覧あり）。

5. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリの確認
   - デフォルトでは `data/` に DB ファイルやフラグファイル、PID ファイルが置かれます。
   - ログは `logs/` に日次ローテーションで出力されます（utils.logging_setup が設定）。

---

## 環境変数（主なもの）

※ .env を使用して設定します。必須・推奨の一覧:

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）

- データベース / ファイルパス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用、デフォルト: data/paper_trading.db）
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag をクリアするか: "0"/"1"、デフォルト 0）

- ログ / 実行制御
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
  - LOG_DIR（ログ保存ディレクトリ、デフォルト: logs/）

- Paper Trading 挙動
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- LINE（アラート用、任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID

- OpenAI（ニュース NLP / レジーム判定 用）
  - OPENAI_API_KEY

- 監視間隔（Monitoring 実行時に一時的に指定可能）
  - MONITOR_POLL_INTERVAL（秒、デフォルト 60）

- その他（しばしば上書きされる）
  - KABU_API_BASE_URL（kabu API ベース URL、デフォルト: http://localhost:18080/kabusapi）

例（`.env` の一部）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
OPENAI_API_KEY=sk-...
LOG_LEVEL=INFO
```

---

## 使い方（よく使うコマンド）

- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ExecutionEngine を起動（本番/ペーパートレードを .env の KABUSYS_ENV で切り替え）
  ```
  python -m kabusys.run_execution
  ```
  - 起動前に `data/stop_requested.flag` があると起動しません（停止）。
  - 実行中に `data/stop_requested.flag` を作成するとエンジン停止を試みます。
  - PID ファイルは `data/execution.pid` に書き込まれます。

- Monitoring を起動（監視ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更するには環境変数を指定:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - Monitoring は設定に関係なく `Settings.sqlite_path`（監視用 sqlite）を使用します。

- Paper Trading 検証レポート生成
  ```
  # 引数で期間指定可
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- OpenAI を使う処理（プログラムから）
  - ニュース NLP:
    from kabusys.ai import score_news
    score_news(conn, target_date, api_key="sk-...")
  - 市場レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="sk-...")

  いずれも api_key が渡されない場合は環境変数 `OPENAI_API_KEY` を参照します。未設定だと例外が発生します。

---

## 運用上の注意点

- Kill Switch / stop flag
  - `data/kill.flag` は ExecutionEngine に停止シグナルを送るために KillSwitch が書き込みます。`KILL_FLAG_CLEAR_ON_START=1` にすると起動時に自動クリアされますが、本番では 0 を推奨します。
  - `data/stop_requested.flag` は run_* スクリプトが監視している停止フラグ（マニュアル停止等に使用）。

- ログ
  - ログは標準出力（console）と `logs/<app_name>.log` に日次ローテーションで出力されます。ログディレクトリの作成に失敗した場合はファイル出力が無効化され、コンソール出力のみになります。

- OpenAI 利用
  - レート制限や 5xx エラーに対しては指数バックオフでリトライするよう実装されていますが、API キーの管理・コストに注意してください。API 失敗時は安全側のフォールバック（0.0 等）を行う設計です。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブル作成と簡単なカラム追加マイグレーションを行います。

---

## ディレクトリ構成（主要ファイル説明）

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス：環境変数からの設定取得、自動 .env ロード等
  - config_setup.py
    - 対話式 .env 作成ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（スレッド実行・停止フラグ処理）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - utils/
    - logging_setup.py: ログ設定ユーティリティ（Stream + TimedRotatingFile）
    - process_priority.py: プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py: SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py: システム状態 / データ鮮度監視
    - trade_monitor.py: （注文監視ロジックが入る想定）
    - risk_monitor.py: ドローダウン・ポジション数監視
    - kill_switch.py: kill.flag 制御
    - monitoring_engine.py: 各モニタを束ねるエンジン
    - alert_manager.py: （アラート送信ロジックが入る想定）
  - execution/
    - execution_engine.py: 実行エンジン本体（EngineConfig など）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
      （発注・注文管理・リスク管理に関するモジュール）
  - portfolio/
    - portfolio_builder.py: 候補選定、重み計算
    - position_sizing.py: 株数計算、上限・スケール処理
    - risk_adjustment.py: セクターキャップ、レジーム乗数
  - research/
    - factor_research.py: momentum / volatility / value 等のファクター計算
    - feature_exploration.py: 将来リターン、IC、統計サマリー
  - ai/
    - news_nlp.py: ニュース NLP（OpenAI 呼び出し、結果検証、ai_scores への書き込み）
    - regime_detector.py: MA と LLM を使った市場レジーム判定
  - tools/
    - paper_verification_report.py: Paper Trading 用検証レポート生成ツール

- data/（実行時に使用されるデータディレクトリ。デフォルトパス）
  - monitoring.db（デフォルト SQLITE_PATH）
  - paper_trading.db（paper_trading モード用）
  - kabusys.duckdb（デフォルト DUCKDB_PATH）
  - execution.pid, kill.flag, stop_requested.flag, ...

- logs/
  - execution.log, monitoring.log など（TimedRotatingFileHandler）

---

## 開発・拡張のヒント

- 新しい設定を追加したら config_setup.py と validate_config.py に項目を追加してください。
- DuckDB を用いた research / ai モジュールはテスト用にモック可能です（OpenAI 呼び出しはラッパー関数を patch して差替え推奨）。
- ExecutionEngine のブローカーは BrokerClientFactory で抽象化されているため、実ブローカー / Mock の切替が容易です。
- logging_setup.setup_logging を全起動スクリプトで使うことでログ出力が統一されます。

---

もし README に追加したい具体的な内容（例: サンプル .env.example、requirements.txt、起動ユースケース別の手順、データベーススキーマ詳細、テストの実行方法など）があれば教えてください。必要に応じてその内容を追記して README.md を更新します。