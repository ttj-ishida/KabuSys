# KabuSys

KabuSys は日本株向けの自動売買・リサーチ・監視を行う小規模システムです。本リポジトリは戦略ファクター計算、ポートフォリオ構築、発注エンジン、監視・アラート、Paper Trading 検証ツール、LLM を用いたニュースセンチメント評価などのモジュール群を含みます。

以下はこのコードベース向けの README（日本語）です。

## 概要

- 自動売買を安全に運用するための以下の機能を含む：
  - 発注実行エンジン（ExecutionEngine 周辺）
  - 発注管理・リコンシリエーション（OrderManager / Reconciler）
  - リスク管理（RiskManager / RiskMonitor）
  - システム監視（SystemMonitor / MonitoringEngine）
  - モニタリング DB（SQLite）と簡易ダッシュボード（Streamlit）
  - リサーチ用ファクター計算（DuckDB を利用）
  - Paper Trading 用の分離環境と検証レポート生成
  - OpenAI を利用したニュース NLP（銘柄ごとのセンチメントスコア）および市場レジーム判定

- データ永続化:
  - DuckDB: 価格・財務・ニュース等の時系列/分析データ（既定: `data/kabusys.duckdb`）
  - SQLite: 監視・発注ログ（既定: `data/monitoring.db`）
  - Paper Trading は環境 `paper_trading` 時に `data/paper_trading.db` を使用（本番 DB と完全分離）

## 主な機能一覧

- portfolio
  - 銘柄候補選定、等分配/スコア重み配分、ポジションサイズ計算、セクター上限・レジーム乗数の適用
- research
  - Momentum / Volatility / Value 等のファクター計算、将来リターン、IC（スピアマン）計算、統計サマリ
- execution
  - 発注フロー（OrderManager）、ブローカーファクトリ、再起動時のリコンシリエーション（Reconciler）
- monitoring
  - SystemMonitor（CPU/メモリ/Disk、Execution プロセス生存、データ鮮度）
  - TradeMonitor（滞留注文、約定価格異常）
  - RiskMonitor（ドローダウン・ポジション上限判定）
  - KillSwitch（フラグファイルによる Execution 停止指示）
  - AlertManager（LINE Push によるアラート）
  - Streamlit ダッシュボード（監視 UI）
- ai
  - news_nlp: OpenAI を使った銘柄別ニュースセンチメントの集約スコア化（ai_scores テーブルへ書き込み）
  - regime_detector: ma200 とマクロニュースセンチメントを合成して市場レジームを判定

## 必要環境・依存パッケージ

推奨 Python バージョン: 3.10+

主な外部依存（requirements.txt を別途用意している想定）:
- duckdb
- psutil
- requests
- openai
- streamlit
- (標準ライブラリ: sqlite3, logging, argparse, etc.)

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
# 追加パッケージがあればここに記載
```

## セットアップ手順（クイックスタート）

1. リポジトリをチェックアウト:
   - この README はパッケージソースが `src/kabusys` 配下にある構成を前提としています。

2. 仮想環境を作成して依存をインストール:
   - 上記の「必要環境・依存パッケージ」を参照。

3. data ディレクトリの作成:
```bash
mkdir -p data
```

4. 環境変数の設定:
   - ルートに `.env` / `.env.local` を置くと自動で読み込まれます（既定では OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（デフォルト含む）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用トークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで使用）
- KABUSYS_ENV — `development` / `paper_trading` / `live`（既定: `development`）
- PAPER_FILL_MODE — Paper Trading の約定モード: `instant`（既定） | `partial` | `never` | `reject`
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（既定: `data/paper_trading.db`）
- DUCKDB_PATH — DuckDB ファイル（既定: `data/kabusys.duckdb`）
- SQLITE_PATH — 監視 SQLite ファイル（既定: `data/monitoring.db`）
- PID_FILE_PATH — Execution PID ファイル（既定: `data/execution.pid`）
- KILL_FLAG_PATH — kill.flag ファイル（既定: `data/kill.flag`）
- LOG_LEVEL — `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`（既定: `INFO`）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用

5. DB 初期化:
   - 監視 DB（SQLite）は各起動スクリプトが自動でテーブルを作成します（冪等）。
   - DuckDB 側は分析データをロードしてください（prices_daily, raw_financials, raw_news などのテーブルが想定されます）。

## 使い方（主要スクリプト・起動例）

注意: パッケージをインストールするか、`PYTHONPATH=src` を指定して `python -m` でモジュール実行してください。

- Monitoring（システム監視）を起動:
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 例:
    ```bash
    # 直接スクリプト実行（開発環境）
    python src/kabusys/run_monitoring.py

    # またはパッケージとして実行（src を PYTHONPATH に含める）
    PYTHONPATH=src python -m kabusys.run_monitoring
    ```
  - Monitoring は常に本番用の sqlite_path（`SQLITE_PATH`）を使用します（監視ログは本番 DB と共有される設計）。

- Execution（発注エンジン）を起動:
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し、Paper Trading 用 DB（`PAPER_TRADING_SQLITE_PATH`）に記録します。
  - 例:
    ```bash
    # 本番（例）
    KABUSYS_ENV=live python -m kabusys.run_execution

    # Paper Trading（本番 DB と分離）
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```

- Streamlit ダッシュボード（監視 UI）:
  - 監視 DB を読み取り専用で開きます。MonitoringEngine が先に起動してデータを作成している必要があります。
  - 起動例:
    ```bash
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```

- Paper Trading 検証レポート生成:
  - CSV ではなく標準出力にレポートを出力します。デフォルト DB は `data/paper_trading.db`。
  - 例:
    ```bash
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    # または DB 指定
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
    ```

- AI ニューススコアリング / レジーム判定（ライブラリ呼び出し）:
  - OpenAI キーが必要です（`OPENAI_API_KEY`）。
  - Python REPL や管理スクリプトから呼び出す例:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    written = score_news(conn, target_date=date(2026,4,12), api_key="sk-...")
    print("written:", written)
    ```

## 設定（.env / .env.local）

- プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先）。
- 自動読み込みを無効にする場合:
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- .env のパースはシンプルですが、シングル/ダブルクォートのエスケープ、`export KEY=val` 形式、行末コメントの処理などに対応しています。

## 運用上の注意

- Paper Trading は実稼働 DB と分離する設計です。必ず `KABUSYS_ENV=paper_trading` と `PAPER_TRADING_SQLITE_PATH` を使って検証してください。
- KillSwitch は `data/kill.flag` を作成することで Execution 停止を伝達します。Execution 起動時にフラグをクリアするオプションがあるため、運用時の動作を確認してください。
- LLM 呼び出しは外部 API に依存し、429/ネットワーク/5xx に対して指数バックオフでリトライします。API キーやコストに注意してください。
- Streamlit UI は監視 DB を read-only で開くため、MonitoringEngine のロックや書き込みに影響を与えません（URI に `?mode=ro` を付与している）。

## 開発（ローカル実行・テスト時のヒント）

- src を PYTHONPATH に追加してモジュールとして実行すると、パッケージインポートが安定します:
  ```bash
  PYTHONPATH=src python -m kabusys.run_monitoring
  ```
- 単体関数（ポートフォリオ計算、ファクター計算など）は外部副作用が少ない純粋関数設計です。ユニットテストが書きやすくなっています。
- DuckDB クエリは prices_daily / raw_financials / raw_news 等のテーブルを前提にしています。テスト用の小さなサンプルデータを準備すると開発が楽です。

## ディレクトリ構成

（重要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                  — 環境変数/.env 読み込みと Settings
    - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py           — ExecutionEngine 起動スクリプト
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート生成
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py               — OpenAI を使ったニューススコアリング
      - regime_detector.py        — 市場レジーム判定
    - monitoring/
      - monitoring_db.py         — SQLite テーブル定義 + MonitoringDB ラッパ
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - （ブローカー関連 etc.）
    - utils/
      - process_priority.py
    - research/                   — ファクター計算・統計ユーティリティ（DuckDB 前提）

## 追加情報・連絡先

- 本 README はソースコードの docstring / コメントをもとにまとめたものです。詳細な API 仕様や追加の運用手順はソースコード内の docstring を参照してください。
- 実運用前に Paper Trading 環境での十分な検証（レポート確認、KillSwitch 動作確認、アラート設定）を推奨します。

---

何か追加で README に入れたい情報（例えばサンプル .env、requirements.txt、docker-compose 設定の例など）があれば教えてください。必要に応じて追記します。