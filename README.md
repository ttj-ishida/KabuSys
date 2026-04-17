# KabuSys

日本株向け自動売買システムの一部（ライブラリ／運用ユーティリティ）。  
このリポジトリには注文実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ／ファクター計算、AI（ニュース NLP / レジーム判定）等のモジュール群が含まれます。

以下はリポジトリ内の主要機能・セットアップ・起動方法・ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は以下の目的を持つコンポーネント群を提供します。

- 注文作成・送信・状態管理を行う ExecutionEngine（発注ロジック、リスク管理、リコンシリエーション）
- ExecutionEngine の状態・注文イベント・ポジションを永続化する SQLite ベースの監視 DB（Monitoring）
- 監視用のポーリングループおよびアラート（LINE 送信）の管理
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数）
- リサーチ用ファクター計算（momentum / volatility / value 等）および特徴量解析ユーティリティ
- ニュースの NLP スコアリング（OpenAI を使用）および市場レジーム判定
- 運用支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード など）

設計方針の一部：
- 本番と Paper Trading（検証）は DB を分離して運用可能
- LLM 呼び出し（OpenAI）部分は失敗時にフォールバックする（フェイルセーフ）
- .env / .env.local による環境変数自動読み込みを行う（必要に応じて無効化可能）

---

## 機能一覧（抜粋）

- Execution:
  - 注文作成・送信・同期（OrderManager / OrderRepository / Reconciler）
  - RiskManager による発注制限（最大ポジション比率・利用率など）
  - 起動時の自動リコンシリエーション

- Monitoring:
  - SystemMonitor: CPU／メモリ／ディスク／プロセス稼働／データ鮮度監視
  - TradeMonitor: 滞留注文（stale order）・約定異常価格検出
  - RiskMonitor: ドローダウン／ポジション上限の検出とログ化
  - KillSwitch: 一定条件で ExecutionEngine を停止するためのフラグファイル書き込み
  - AlertManager: LINE Push による通知（クールダウン管理あり）
  - Monitoring DB: system_status / trade_logs / positions / risk_logs / dashboard の永続化

- Portfolio:
  - 候補選定（スコアでソート）、等配分・スコア重み配分
  - ポジション決定ロジック（risk_based、等配分 等）
  - セクター上限適用、レジーム乗数

- Research:
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Information Coefficient）等の統計処理

- AI:
  - ニュース NLP（OpenAI）で銘柄ごとのセンチメントスコアを ai_scores に書き込み
  - レジーム検出（ETF MA + マクロニュースセンチメントの合成）

- Tools:
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
  - Streamlit 監視ダッシュボード

---

## 必要条件

- Python 3.10+
- duckdb
- psutil
- requests
- streamlit（ダッシュボード使用時）
- openai（AI 機能使用時）
- （その他、requirements.txt があればそれに従ってください）

開発環境では仮想環境を作成して依存をインストールすることを推奨します。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

requirements.txt がない場合は上記ライブラリを個別にインストールしてください。

---

## 環境変数と設定

config.py が環境変数を扱います（プロジェクトルートの `.env` / `.env.local` を自動で読み込みます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

主な環境変数（重要）:

- KABUSYS_ENV: 実行環境（development | paper_trading | live）デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- LINE_CHANNEL_ACCESS_TOKEN: LINE 通知用トークン（任意）
- LINE_USER_ID: LINE 通知先ユーザー ID（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の成行・部分約定挙動（instant | partial | never | reject）デフォルト: instant
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など監視関連のオプション
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

注意:
- Paper Trading モード（KABUSYS_ENV=paper_trading）の場合、専用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番データと分離します。
- MONITOR_POLL_INTERVAL が 1 未満または不正値の場合はデフォルト（60秒）へフォールバックします。

---

## セットアップ手順（簡易）

1. リポジトリをクローン／チェックアウト。
2. Python 仮想環境を作成して依存をインストール。
3. データディレクトリを作成（例: data/）。
   ```
   mkdir -p data
   ```
4. 必要な環境変数を設定（.env を作成するのが便利）。
   - 例: `.env`
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     ```
5. （初回）Monitoring DB は起動時に自動作成・マイグレーションされます。

---

## 使い方（起動／コマンド例）

必須: Python のパッケージがインポート可能な状態であること（パッケージをインストールするか、`PYTHONPATH=src` を指定）。

- 監視ループを開始（SystemMonitor をポーリング）:
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL を指定してポーリング間隔を変更可能（秒）。デフォルト 60 秒。
  - 停止は Ctrl+C またはプロジェクトルートの `data/stop_requested.flag` ファイルを作ることで行えます。

- ExecutionEngine を起動（実注文または Paper Trading）:
  ```
  # 本番モード（KABUSYS_ENV=live 等に応じて broker が切替わる）
  python -m kabusys.run_execution

  # Paper Trading で起動（MockBroker を使用し、data/paper_trading.db に記録）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
  - 起動前に `data/stop_requested.flag` が存在する場合は起動をスキップします。
  - ExecutionEngine は PID を `data/execution.pid` に書きます。古い PID が残っていると起動時や監視で検知・処理されます。

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB は `data/paper_trading.db`。`--db` でパス指定可。

- Streamlit ダッシュボード（監視ビュー）:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - ダッシュボードは監視用 SQLite を読み取り専用で開きます。MonitoringEngine が DB に書き込んでいることを前提とします。

- AI 周り（ニュース NLP / レジーム判定）をプログラムから実行する例:
  - Python スクリプト内で:
    ```
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect('data/kabusys.duckdb')
    from datetime import date
    score_news(conn, target_date=date(2026,4,10), api_key='sk-...')
    ```
  - OPENAI_API_KEY を環境変数に設定していれば api_key 引数は省略できます。

---

## 運用上のファイル・フラグ

- data/stop_requested.flag
  - run_monitoring / run_execution が停止を検知するためのフラグファイル（存在を検出して終了）。
- data/kill.flag
  - KillSwitch が書き込むファイル。存在すると ExecutionEngine 停止対象とみなされる（呼び出し側で扱う）。
- data/execution.pid
  - ExecutionEngine の PID を保存するファイル。SystemMonitor はこの PID の存在／生存をチェックします。
- SQLite / DuckDB ファイル:
  - data/monitoring.db（監視用 SQLite、init_monitoring_db によりテーブル作成）
  - data/paper_trading.db（Paper Trading 用 SQLite）
  - data/kabusys.duckdb（DuckDB、価格・財務データ等）

kill.flag をクリアするには
```
rm data/kill.flag
```
または KillSwitch オブジェクトの clear() を利用してください。

---

## 開発ノート / 実装上のポイント

- config.py はプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動で読み込みます。テストなどで自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- Monitoring の DB 初期化（init_monitoring_db）は冪等で、既存 DB のマイグレーション（カラム追加等）も行います。
- Process priority は utils.process_priority.set_process_priority によって起動時に "high" に設定されます（Windows/Linux を吸収）。
- Paper Trading モードは BrokerClientFactory により MockBrokerClient を使用し、本番とは別 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。
- AI（OpenAI）呼び出しはネットワークエラー・429・5xx に対して指数バックオフでリトライします。失敗時はフォールバックして処理継続する設計です。
- DuckDB を使って大規模な価格データやファイナンスデータ（prices_daily / raw_financials / raw_news 等）に対する SQL ベースの集計処理を行います。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル／ディレクトリの簡易ツリーです（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py
  - run_monitoring.py
  - run_execution.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - monitoring/
    - __init__.py
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py
    - broker_factory.py
    - broker_api.py
    - order_record.py
    - (その他発注関連モジュール)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - utils/
    - __init__.py
    - process_priority.py
  - data/  (推奨作業ディレクトリ、実行時に使用される DB / PID / flag )

（実際のファイルは上記以外にも多数あります。上は主要モジュールの一覧です。）

---

## よくある質問 / トラブルシュート

- .env が読み込まれない／無効にしたい
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化できます。テスト時に有効です。

- Monitoring / Execution が起動しない（PID 関連）
  - data/execution.pid を確認し、古い PID の場合は削除してください。SystemMonitor は stale PID を検知すると削除します。

- OpenAI API 呼び出しで失敗する
  - 環境変数 OPENAI_API_KEY の設定を確認してください。ネットワーク・レート制限による失敗はリトライしますが、上限に達するとそのチャンクはスキップされます。

---

必要であれば README に以下の追加情報を追記できます：
- requirements.txt の実例（ピン留めされた依存）
- CI/CD（テスト実行方法）
- DB スキーマ詳細ドキュメント
- API（Broker API）の仕様書

他に追記したい章（例: デプロイ手順 / systemd ユニット例 / ロギング設定 / 単体テストの実行方法）があれば教えてください。