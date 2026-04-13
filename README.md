# KabuSys

日本株自動売買システムのライブラリ群（モジュール単位）。このリポジトリはトレーディング実行、監視、ポートフォリオ構築、リサーチ、AI（ニュースNLP / レジーム判定）などの主要コンポーネントを提供します。

以下はコードベースの概要、機能、セットアップ・起動方法、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームのコンポーネント群です。主な設計方針は以下のとおりです。

- 実取引（live）とペーパー取引（paper_trading）を環境変数で切り替え可能。paper_trading は本番 DB と分離して専用 SQLite を使用します。
- DuckDB を用いた時系列・ファクター計算（prices_daily / raw_financials 等のテーブル参照）。
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価とレジーム判定（API キーを環境変数で指定）。
- 監視（Monitoring）モジュールにより、プロセス生存、データ鮮度、注文滞留、ドローダウンなどをログ・アラート（LINE）で管理。
- 各種ユーティリティ（プロセス優先度設定、DB 初期化、ストリームリットダッシュボード等）を提供。

---

## 主な機能一覧

- 実行・リスク管理
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - OrderManager / Reconciler による注文管理・再同期
  - RiskManager による発注時のリスク制御

- 監視（Monitoring）
  - SystemMonitor: CPU/MEM/DISK、プロセス生存、株価データ鮮度の監視
  - TradeMonitor: 注文滞留・約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視
  - KillSwitch: フラグファイルで ExecutionEngine 停止を指示
  - AlertManager: LINE による通知（クールダウン管理）
  - Streamlit ダッシュボード（monitoring/streamlit_dashboard.py）

- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 重み計算（等金額 / スコア重み）
  - リスク調整（セクター上限、レジーム乗数）
  - ポジションサイジング（単元丸め・aggregate cap の調整）

- リサーチ
  - ファクター計算（momentum / volatility / value）
  - Forward returns / IC（情報係数）計算
  - 統計サマリー（factor_summary）

- AI（ニュース NLP / レジーム検出）
  - news_nlp.score_news: raw_news を集約して OpenAI に送り、銘柄別センチメントを ai_scores テーブルに保存
  - regime_detector.score_regime: ETF MA とマクロニュースを合成して市場レジーム判定を書き込み

- ツール
  - paper_verification_report: Paper Trading の検証レポート出力（注文成功率・稼働率・レイテンシ等）

---

## セットアップ手順

前提
- Python 3.10 以上を想定（Union 型記法などを使用）。
- SQLite は標準ライブラリに含まれます。

推奨パッケージ（最低限）
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボードを使う場合）

例: pip でインストール
- 仮想環境作成（任意）
  - python -m venv .venv
  - source .venv/bin/activate（Windows: .venv\Scripts\activate）
- インストール
  - pip install duckdb psutil requests openai streamlit

環境変数 / .env
- config.Settings は起動時に .env / .env.local（プロジェクトルートに存在すれば）を自動で読み込みます。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要な環境変数（デフォルトや用途を併記）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN（必須: J-Quants API 用）
- KABU_API_PASSWORD（必須: kabuステーション API 用）
- OPENAI_API_KEY（AI モジュール利用時に必須）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定動作、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
- DUCKDB_PATH（DuckDB ファイル, デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用 SQLite, デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- LOG_LEVEL（DEBUG|INFO|...）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視閾値）
- MONITOR_POLL_INTERVAL（監視ループのポーリング間隔（秒）; デフォルト 60。run_monitoring で利用）

データディレクトリ
- デフォルトで使用されるファイルは `data/` に置かれます。初回は `mkdir -p data` しておくと安全です。
- monitoring DB は init_monitoring_db() により必要なスキーマを作成します（冪等）。

---

## 使い方

基本的にモジュールはスクリプト経由で起動します。以下は主要な起動例です。

1) 監視ループを起動
- 説明: SystemMonitor を定期的に実行して monitoring DB に書き込み、必要に応じてリスクログや kill.flag を生成します。プロセス優先度を "high" に設定します。
- 実行:
  - MONITOR_POLL_INTERVAL を変更する例:
    - export MONITOR_POLL_INTERVAL=30
  - 実行:
    - python -m kabusys.run_monitoring
  - 備考:
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視は本番データを対象に想定）。

2) ExecutionEngine（取引エンジン）を起動
- 説明: ブローカークライアント（実/モック）を作成し、注文管理・リスク管理・リコンシリエーションを実行します。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite に記録します（本番 DB と完全に分離）。
- 実行:
  - KABUSYS_ENV=paper_trading を使う例:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 本番:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution

3) Paper Trading 検証レポート生成
- 説明: paper_trading の SQLite（デフォルト data/paper_trading.db）を読み、稼働率・注文成功率・レイテンシ等のサマリを標準出力に出すツールです。
- 実行例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または db 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

4) AI ニューススコアリング / レジーム判定（プログラムから呼び出す）
- 例（REPL やスクリプト内で DuckDB 接続を作って呼ぶ）:
  - from openai import OpenAI（または環境変数 OPENAI_API_KEY を設定）
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")
  - from kabusys.ai.news_nlp import score_news
  - written = score_news(conn, target_date, api_key="...")  # 書き込んだ銘柄数を返す
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key="...")

5) Streamlit ダッシュボード起動（監視用）
- 実行:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明: 監視 DB を読み取り専用で開いてダッシュボード表示します。MonitoringEngine を既に実行していないと DB が存在しない旨のエラーを表示します。

その他
- 設定値は Settings クラス経由で取得されます。.env/.env.local をプロジェクトルートに配置すると自動で読み込まれます（ただし、OS 環境変数が優先されます）。
- 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 注意事項 / 実装上のポイント

- データ分離: paper_trading は専用の SQLite（PAPER_TRADING_SQLITE_PATH）にデータを残し、本番 DB（SQLITE_PATH）とは物理的に分離されます。
- DB 初期化: run_monitoring / run_execution は起動時に init_monitoring_db() を呼び、必要なテーブルやマイグレーション（列追加）を冪等に実行します。
- フェイルセーフ: AI 呼び出しや外部 API 呼び出しは多数のエラーハンドリング（リトライやフォールバック）を行います。API キー未設定時は明示的に ValueError を投げる箇所があります。
- プロセス優先度: 起動スクリプトは set_process_priority("high") を呼びます。psutil による権限不足等は警告ログを出してスキップします。
- kill.flag: KillSwitch は flag ファイルを書き込むことで ExecutionEngine に停止シグナルを伝えます。Execution 側はこのフラグを参照して終了することが想定されています。

---

## ディレクトリ構成

概要的な構成（主要ファイルを抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数/.env 読み込みと Settings 定義
    - run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - ai/
      - __init__.py
      - news_nlp.py                — ニュース NLP（OpenAI）によるスコアリング
      - regime_detector.py         — マーケットレジーム判定
    - monitoring/
      - __init__.py
      - monitoring_db.py           — SQLite 用永続化レイヤ（テーブル作成・CRUD）
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py       — 各 Monitor を束ねるランナー
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他 execution 関連モジュール - broker / engine / repository 等)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - utils/
      - process_priority.py
      - __init__.py
    - (その他: data, strategy 等のパッケージが連携する想定)

注: 実運用では data/ 配下に DuckDB/SQLite のファイルを置きます（デフォルト: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）。

---

## よくある操作例 (まとめ)

- 監視起動:
  - export MONITOR_POLL_INTERVAL=60
  - python -m kabusys.run_monitoring

- 実行エンジン（ペーパー）起動:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

必要であれば、README に入れるべき追加のコマンド例（systemd ユニット、Dockerfile、テスト実行方法、CI 設定）や、各モジュールの API 使用例（関数シグネチャや戻り値の例）を追加で作成します。どの情報を優先して欲しいか教えてください。