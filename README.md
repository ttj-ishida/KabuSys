# KabuSys

日本株向け自動売買システムのモジュール群。データ解析（リサーチ）・ポートフォリオ構築・発注エンジン・監視・AI（ニュース NLP / レジーム判定）などを含む、実運用を想定したコンポーネント設計です。

主な設計方針:
- DuckDB / SQLite を使ったオンプレ DB 層（本番データと Paper Trading を分離）
- 環境変数 / .env で設定を管理（自動ロード機能あり）
- 実運用向けの安全機構（監視、Kill Switch、Reconciler、アラート）
- 外部依存（ブローカー / OpenAI / LINE）は抽象化してフェイルセーフ設計

---

## 機能一覧

- 設定管理
  - `kabusys.config.Settings` : 環境変数 / .env による設定取得（KABUSYS_ENV: development | paper_trading | live）
- 実行エンジン / 発注
  - ExecutionEngine 起動スクリプト（`run_execution.py`）
  - OrderManager / OrderRepository / Reconciler（起動時の自動復旧）
  - Broker クライアントの抽象化（paper_trading では MockBrokerClient を使用）
- 監視
  - SystemMonitor：CPU/MEM/Disk、Execution プロセスの存在、データ鮮度を監視
  - TradeMonitor：滞留注文・約定異常価格を検出
  - RiskMonitor：ドローダウン・ポジション上限を監視
  - MonitoringEngine：各モニタを束ねて定期実行
  - AlertManager：LINE Push による通知（クールダウン管理）
  - KillSwitch：条件発生時に `data/kill.flag` を書き込み ExecutionEngine に停止指示
  - SQLite ベースの監視ログ（`monitoring_db.py`）
  - Streamlit ダッシュボード（監視データ表示）
- ポートフォリオ構築（純粋関数群）
  - 候補選定、等配分/スコア配分、セクター上限、ポジションサイズ計算
- リサーチ
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン、IC 計算、特徴量要約
- AI（ニュース NLP / レジーム判定）
  - OpenAI を用いたニュースのセンチメントスコアリング（ai_scores への書き込み）
  - ETF の MA とマクロセンチメントの合成による市場レジーム判定
  - API 呼び出しはリトライ／バックオフ・結果バリデーションを備える
- ツール
  - Paper Trading の検証レポート生成スクリプト（`kabusys.tools.paper_verification_report`）
- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティ（psutil ベース）

---

## 必要条件（推奨）

- Python 3.10+
- SQLite（OS 標準）
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード使用時)

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

（実際のプロジェクトでは requirements.txt / poetry / pipenv 等で依存管理してください）

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境を作成して依存をインストール（上の例参照）
3. .env ファイルの作成（プロジェクトルートに配置）
   - 自動ロード順序: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
4. 重要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=... (AI 機能を使う場合必須)
   - KABUSYS_ENV=development | paper_trading | live
   - PAPER_FILL_MODE=instant|partial|never|reject
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - SQLITE_PATH=data/monitoring.db
   - DUCKDB_PATH=data/kabusys.duckdb
   - LINE_CHANNEL_ACCESS_TOKEN=...
   - LINE_USER_ID=...
   - LOG_LEVEL=INFO
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - MONITOR_POLL_INTERVAL (run_monitoring 用、秒。デフォルト 60)
5. データディレクトリ作成
```
mkdir -p data
```
6. （必要に応じ）Paper Trading 用 DB は `PAPER_TRADING_SQLITE_PATH` に作成されます。初回は各スクリプトが必要なテーブルを作成します。

---

## 使い方（主なコマンド）

- ExecutionEngine（発注エンジン）起動
  - 本番/テストを切り替えるには KABUSYS_ENV を設定
  - Paper Trading の例:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 本番:
    ```
    KABUSYS_ENV=live python -m kabusys.run_execution
    ```
  - 実行時、`data/execution.pid` に PID を書き込みます。停止フラグ（data/stop_requested.flag）があると起動しません。

- Monitoring（監視ループ）起動
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は常に本番の sqlite_path を使用します（Monitoring は環境に依存せず本番 DB を参照）。

- Streamlit ダッシュボード
  - 読み取り専用で monitoring DB を表示します:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```

- Paper Trading 検証レポート生成
  - コマンドライン:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
    ```
  - 引数 `--db` を省略すると環境変数 `PAPER_TRADING_SQLITE_PATH` またはデフォルト `data/paper_trading.db` を使用します。

- AI 機能（プログラムから利用）
  - ニューススコアリング:
    ```
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026, 4, 10), api_key="YOUR_OPENAI_KEY")
    ```
  - レジーム判定:
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,10), api_key="YOUR_OPENAI_KEY")
    ```

- 停止方法
  - 即時に Monitoring / Execution を停止させたい場合:
    - 監視ループ / エンジンが参照する停止フラグ: `data/stop_requested.flag`
      - このファイルが存在することで `run_monitoring` / `run_execution` のループは終了します。
    - KillSwitch が発動すると `data/kill.flag` が書き込まれ、ExecutionEngine 側で検知され停止されます。
  - 手動で削除:
    ```
    rm -f data/stop_requested.flag data/kill.flag
    ```

---

## 環境変数と設定（主な項目）

- KABUSYS_ENV: development | paper_trading | live （デフォルト development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定モード）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite ファイルパス
- SQLITE_PATH: 監視用 SQLite（monitoring）パス（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE 通知）用
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env ロードを無効化

注意: Settings クラスは必須の環境変数が未設定の場合 ValueError を投げます。テスト時に自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（抜粋）

（ソースは `src/kabusys` 下に配置されています。主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / .env ロード / Settings
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
    - __init__.py
  - ai/
    - news_nlp.py                  — ニュース NLP スコアリング（OpenAI 呼び出し）
    - regime_detector.py           — 市場レジーム判定（MA + LLM）
    - __init__.py
  - monitoring/
    - monitoring_db.py             — SQLite 監視 DB 層
    - system_monitor.py            — システム・データ鮮度監視
    - trade_monitor.py             — 注文滞留・約定異常監視
    - risk_monitor.py              — ドローダウン・ポジション制限監視
    - alert_manager.py             — LINE 通知
    - kill_switch.py               — kill.flag 管理
    - monitoring_engine.py         — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py       — Streamlit ダッシュボード
    - __init__.py
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py          — （実装ファイル群、発注ロジック）
    - broker_factory.py
    - broker_api.py
    - order_record.py
    - order_repository.py
    - order_manager.py
    - ...
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - data/                          — 実行時に参照 / 生成される（リポジトリには含めない）
    - monitoring.db
    - paper_trading.db
    - kabusys.duckdb
    - execution.pid
    - stop_requested.flag
    - kill.flag

---

## 運用上の注意（トラブルシューティング）

- プロセス優先度設定に失敗することがあります（psutil の権限不足）。警告が出ますが処理は継続されます。
- OpenAI API キー未設定の場合、AI 関連関数は ValueError を送出します。API 呼び出しはネットワークエラーや 429/5xx に対してリトライ処理を行いますが、最終的に失敗した場合は安全にフォールバックします（例: macro_sentiment=0.0）。
- Monitoring / Execution は停止フラグ（stop_requested.flag）や kill.flag を利用しています。誤ってフラグが残っていると起動しません。起動前に `data/kill.flag` をクリアする設定 `kill_flag_clear_on_start` があります（Settings 経由）。
- DuckDB / SQLite のファイルパーミッション・パスに注意してください。Streamlit ダッシュボードは監視 DB を読み取り専用で開きます（URI に ?mode=ro を付与）。
- Paper Trading は本番 DB と完全分離されるよう設計されています。`KABUSYS_ENV=paper_trading` で paper_db が使用されます。

---

## 開発・拡張のヒント

- OpenAI 呼び出し用の関数はテスト時に patch / stub しやすいように実装されています（例: `_call_openai_api` をモックする）。
- モニタ・リスクロジックは純粋な入出力（DB 接続・設定を受け取る）になっているためユニットテストが容易です。
- ポートフォリオ構築・ポジションサイズ決定は純粋関数群なので外部依存を気にせずロジック実験が可能です。
- DuckDB を用いたリサーチクエリは SQL を活用して高速に集計できます。prices_daily / raw_financials テーブルを用意して検証してください。

---

必要に応じて README に追記します（例: 実行例のログ、SQL スキーマ詳細、CI/デプロイ手順）。追加で載せたい情報や深掘りしたいセクションがあれば教えてください。