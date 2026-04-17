# KabuSys

KabuSys は日本株自動売買システムのコアライブラリ群です。本リポジトリは戦略（ファクター計算）、ポートフォリオ構築、発注エンジン、監視・アラート、Paper Trading 用ツール、LLM を使ったニュース解析などのコンポーネントを含みます。

以下はこのコードベースの概要、機能、セットアップ方法、使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

- 日本株の自動売買プラットフォームのコア機能（研究、ポートフォリオ構築、注文管理、発注、監視）を提供する Python パッケージ群。
- DuckDB を用いた時系列データ/ファイナンスデータ処理、SQLite による監視ログ・注文ログ永続化。
- Paper Trading（モックブローカー）と本番（kabuステーション相当）を環境変数で切り替え可能。
- OpenAI を用いたニュースセンチメント解析や市場レジーム判定機能を備える（API キー必須）。
- 監視結果を LINE に通知する AlertManager、Streamlit ダッシュボードを提供。

---

## 主な機能一覧

- research
  - ファクター計算 (momentum, volatility, value)
  - 将来リターン計算、IC（情報係数）や統計サマリ
- portfolio
  - 候補選定、等金額 / スコア加重配分
  - ポジションサイズ計算（risk_based 等）、セクター上限適用、レジーム乗数
- execution
  - OrderManager / ExecutionEngine（発注ワークフロー）
  - Reconciler（再起動時のブローカー照合）
  - BrokerClientFactory による本番 / Paper Trading 切替
- monitoring
  - SystemMonitor（プロセス・CPU/メモリ/ディスク・データ鮮度）
  - TradeMonitor（滞留注文・約定価格異常検出）
  - RiskMonitor（ドローダウン・ポジション数監視）
  - KillSwitch（条件で stop フラグを書き、Engine を停止）
  - AlertManager（LINE Push による通知）
  - MonitoringEngine（各 Monitor の統合ポーリング）
  - Streamlit ダッシュボード（監視データ可視化）
- ai
  - news_nlp: raw_news を OpenAI に投げて銘柄単位のセンチメントを ai_scores テーブルへ登録
  - regime_detector: MA200 とマクロニュースセンチメントを合成して market_regime を記録
- tools
  - paper_verification_report: Paper Trading DB を解析して検証レポートを生成
- utils
  - プロセス優先度 / CPU affinity 設定ユーティリティ（psutil ベース）
- DB ヘルパー
  - monitoring_db: 監視用 SQLite スキーマ初期化・読み書きユーティリティ

---

## セットアップ手順（開発環境向け）

1. Python を用意
   - 推奨: Python 3.10+（typing の記法などを使用）
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - 本リポジトリには requirements.txt が含まれていないため、最低限以下をインストールしてください:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit
4. プロジェクトルートに .env を作成（任意）
   - config.py は自動でプロジェクトルートの `.env` と `.env.local` を読み込みます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - .env の例（必要に応じて設定）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development  # development | paper_trading | live
     - PAPER_FILL_MODE=instant  # instant | partial | never | reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - LOG_LEVEL=INFO
5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

注意: 一部の機能は外部 API（kabu API、J-Quants、OpenAI）やブローカーの実装に依存します。Paper Trading を使わない場合は本番ブローカーのクレデンシャルが必要です。

---

## 使い方

以下は主要なエントリポイントと実行例です。

1. 監視ループを起動（Monitoring）
   - デフォルトで MONITOR_POLL_INTERVAL=60 秒
   - 環境変数で上書き可: MONITOR_POLL_INTERVAL=30
   - 実行:
     - python -m kabusys.run_monitoring
   - 停止:
     - プロセスを Ctrl+C で停止する、またはプロジェクトルートの data/stop_requested.flag ファイルを作成するとループが検知して終了します。

2. ExecutionEngine 起動（発注エンジン）
   - Paper Trading 環境で動かす場合: KABUSYS_ENV=paper_trading
     - この場合 MockBrokerClient を使用し、デフォルトで data/paper_trading.db に分離して記録します。
     - PAPER_FILL_MODE により注文約定の挙動を設定できます（instant/partial/never/reject）。
   - 実行:
     - python -m kabusys.run_execution
   - 停止:
     - data/stop_requested.flag を作成するとスレッド内で検知して Engine.stop() が呼ばれます。

3. Paper Trading 検証レポート
   - data/paper_trading.db を対象にパフォーマンス／安定性指標を出力します。
   - 実行例:
     - python -m kabusys.tools.paper_verification_report
     - 期間指定:
       - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB パス指定:
       - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

4. Streamlit ダッシュボード（監視ビュー）
   - 起動例:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ダッシュボードは監視用 SQLite DB（読み取り専用推奨）を可視化します。

5. AI 関連（ニューススコア、レジーム判定）
   - OpenAI API キー（OPENAI_API_KEY）が必要です。
   - モジュール関数を直接呼ぶ（スクリプトや REPL で利用）:
     - from kabusys.ai.news_nlp import score_news
       - score_news(conn, target_date, api_key=...)
     - from kabusys.ai.regime_detector import score_regime
       - score_regime(conn, target_date, api_key=...)
   - 注意: これらは DuckDB 接続を受け取ります（prices_daily / raw_news 等のテーブルが前提）。

6. 設定（Settings）
   - 環境変数で設定を行います（config.Settings 参照）。主なキーとデフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - SQLITE_PATH — デフォルト data/monitoring.db
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH — デフォルト data/paper_trading.db
     - PAPER_FILL_MODE — デフォルト instant（valid: instant|partial|never|reject）
     - PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEM/DISK 閾値 等
   - .env / .env.local は自動ロードされます（既存 OS 環境変数は保護される）。

7. 停止制御 / Kill Switch
   - KillSwitch は監視結果に基づき data/kill.flag を書き込み、ExecutionEngine に停止信号を送ります。
   - KillSwitch は閾値超過時に冪等的にファイルを書きます（既存の場合は再書き込みしません）。
   - ExecutionEngine 側は stop フラグや PID ファイルの監視を行います。

---

## よく使う環境変数（抜粋）

- KABUSYS_ENV (development | paper_trading | live) — 実行環境
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒）
- SQLITE_PATH — 監視 DB（monitoring.db）パス（デフォルト data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 専用 SQLite（分離）
- PAPER_FILL_MODE — Paper Trading の約定モード（instant/partial/never/reject）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで必須）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD — 外部 API 認証情報
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager（LINE）で通知する場合に必要

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理（.env 自動ロード）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py — SQLite スキーマ初期化 & 監視 DB 操作クラス
    - system_monitor.py — CPU/メモリ/ディスク、PID、データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - alert_manager.py — LINE Push 通知ラッパー
    - monitoring_engine.py — 各 Monitor をまとめるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py, order_repository.py, reconciler.py, execution_engine.py 等（発注ロジック）
    - broker_factory.py — Broker クライアント生成（paper_trading 切替）
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 発注株数計算、制約適用
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value 計算
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py — raw_news → OpenAI でセンチメント → ai_scores 書込
    - regime_detector.py — MA200 + マクロセンチメントで market_regime 判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成

※上記は主要モジュール抜粋です。実運用では execution 側のブローカー実装や DB マスタデータ（prices_daily、raw_financials、raw_news 等）の準備が必要です。

---

## 運用上の注意点 / ベストプラクティス

- Paper Trading を利用すると本番ブローカーや口座に影響を与えず動作確認できます（KABUSYS_ENV=paper_trading）。
- OpenAI を使用する機能は API コストとレート制限に注意してください。score_news / score_regime は内部でリトライやバッチ処理、スコアクリップを実装していますが、運用時は API キー管理と利用量の監視が必要です。
- Monitoring のログやデータベースは /data 以下に作られます。バックアップや権限管理を忘れずに。
- PID / stop flag / kill flag によるプロセス管理はファイルベースです。コンテナ運用やシステムサービス化する場合はその環境に合わせた適応が必要です。
- config.Settings は .env の自動ロードを行います。CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って外部環境の影響を避けてください。

---

もし README に追加したい具体的な実行例（例えば ExecutionEngine の詳細オプション、Broker 実装の使い方、テスト用のサンプルデータ生成スクリプト等）があれば教えてください。必要に応じて README を拡張します。