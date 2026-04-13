# KabuSys

KabuSys は日本株の自動売買システムの骨格を提供する Python パッケージです。注文管理・発注エンジン、監視・アラート、ポートフォリオ構築、リサーチ（ファクター計算）、およびニュース NLP / レジーム判定（OpenAI を利用）などのコンポーネントを含みます。

---

## 主な特徴

- 実行エンジン（ExecutionEngine）
  - OrderManager / OrderRepository による注文作成・送信・状態同期
  - Reconciler による起動時の自動復旧（ブローカーとの突合）
  - RiskManager による執行時のリスク制御（最大ポジション比率、利用率、サーキットブレーカー等）

- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視ログは SQLite（monitoring.db）へ永続化（MonitoringDB）
  - LINE によるアラート通知（AlertManager）
  - kill.flag による ExecutionEngine 停止シグナル（KillSwitch）
  - Streamlit ベースの監視ダッシュボード

- ポートフォリオ構築
  - 候補選定、等配分・スコア加重配分、リスク調整（セクター上限、レジーム乗数）、ポジションサイズ決定（単元丸め、aggregate cap）

- リサーチ
  - DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン・IC 計算、ファクター統計サマリー

- AI（OpenAI）
  - ニュース記事のセンチメントスコア化（news_nlp.score_news）
  - マクロニュース + ETF MA を用いた市場レジーム判定（regime_detector.score_regime）
  - API 呼び出しはリトライ・フォールバック設計

- ツール
  - Paper Trading 検証レポート生成スクリプト
  - Monitoring DB 用 Streamlit ダッシュボード

---

## セットアップ手順

※ 以下は基本手順の例です。プロジェクトに requirements.txt があればそちらを利用してください。

1. Python（推奨 3.10 以上）を用意

2. 依存パッケージをインストール
   - 例:
     pip install duckdb psutil openai requests streamlit

3. データディレクトリを作成
   - 例:
     mkdir -p data

4. 環境変数を設定
   - 必須（実際に使用する機能に依存）:
     - JQUANTS_REFRESH_TOKEN（J-Quants API を使う場合）
     - KABU_API_PASSWORD（kabuステーション API）
     - OPENAI_API_KEY（ニュース/レジーム判定で OpenAI を使う場合）
   - オプション（デフォルト値あり）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
       - paper_trading の場合、MockBrokerClient を利用し paper DB（data/paper_trading.db）に記録
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定モード: instant | partial | never | reject、デフォルト: instant）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知）
     - PID_FILE_PATH（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（デフォルト: data/kill.flag）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を消す場合は "1"）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒）、デフォルト 60）

   - .env ファイルを使う場合はプロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（OS 環境変数を上書きしない挙動に注意）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

5. DuckDB のスキーマ（prices_daily / raw_financials / raw_news 等）およびデータは別途用意してください（research / ai モジュールは DuckDB のテーブルを前提とします）。

---

## 使い方

- 実行エンジンを起動（本番・ペーパー共通）
  - 環境変数で KABUSYS_ENV を切り替え
    - 本番: KABUSYS_ENV=live
    - ペーパー: KABUSYS_ENV=paper_trading
  - 実行:
    python -m kabusys.run_execution

  - 備考:
    - 起動時にプロセス優先度を "high" に設定し、データベース接続と初期化（監視テーブル）を行います。
    - paper_trading の場合は settings.paper_sqlite_path（デフォルト data/paper_trading.db）へ記録して本番 DB と分離されます。

- 監視ループを起動
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）。
  - 実行:
    python -m kabusys.run_monitoring

  - 監視で行われる処理:
    - SystemMonitor: CPU/メモリ/ディスク/プロセス生存チェック、データ鮮度
    - TradeMonitor: 滞留注文・約定異常価格チェック
    - RiskMonitor: ドローダウン・ポジション上限チェック
    - KillSwitch 評価 → 条件に合えば data/kill.flag を書き込む（ExecutionEngine 停止トリガー）
    - AlertManager による LINE 通知（設定済みの場合）

- Streamlit ダッシュボード（監視用）
  - 起動:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - 起動例:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  - 出力: 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、Pass/Fail 判定

- AI / リサーチ用関数（プログラムから呼び出す）
  - ニューススコア付与:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key=...)
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key=...)

---

## 環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- OPENAI_API_KEY
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE: instant | partial | never | reject
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

（必要に応じて .env/.env.local に定義してください）

---

## 注意事項 / 設計上のポイント

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。CWD に依存しない設計です。
- Monitoring は KABUSYS_ENV にかかわらず production 用の sqlite_path を使う設計（監視は常に本番 DB を参照）。
- Execution 起動時、プロセス優先度を "high" に設定しようとします（プラットフォーム依存。権限不足の場合は警告）。
- OpenAI API 呼び出しはリトライとフォールバック（失敗時は安全なデフォルト）を行います。
- Paper Trading（ペーパートレード）は本番 DB と完全分離するようになっています（デフォルトで data/paper_trading.db を使用）。
- kill.flag を書き込むと ExecutionEngine 側で検出して停止を試みる設計です（冪等）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数読み取り・設定クラス (Settings)
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - execution_engine.py
    - broker_factory.py
    - broker_api.py
    - order_record.py
    - order_record 等（発注関連のコア）
  - monitoring/
    - monitoring_db.py      — SQLite スキーマ・読み書き層（MonitoringDB）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

---

この README はコードベースに含まれるモジュールの概要と運用に必要な基本情報をまとめたものです。導入・本番運用時は監視設定（閾値）、LINE トークンや API キーの管理、DuckDB に投入する価格・財務データの準備、権限（プロセス優先度設定や PID 管理）を適切に設定してください。質問や補足があれば教えてください。