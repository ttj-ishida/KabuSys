# KabuSys

日本株自動売買システムの一部（ライブラリ＋運用ツール群）。  
本リポジトリは、シグナル → ポートフォリオ構築 → 発注（ExecutionEngine）、
および稼働監視（MonitoringEngine）／検証ツール／リサーチ／AI 補助モジュールを含みます。

## 概要
- Execution: Broker 経由で注文を作成・送信・同期する実行エンジン（本番 / paper_trading モード対応）。
- Monitoring: システム状態、注文滞留、ドローダウン等をポーリングしてログ・アラートを出す監視機能（SQLite に永続化）。
- Tools: Paper Trading 向けの検証レポート生成や Streamlit ベースの監視ダッシュボード。
- Research / AI: DuckDB を利用したファクター計算、将来リターン・IC 計算、ニュースの LLM スコアリング・レジーム判定など。

設計上のポイント:
- 設定は環境変数 / .env（自動ロード）で管理（kabusys.config）。
- paper_trading は本番 DB と分離され、MockBroker を用いた検証が可能。
- DuckDB により歴史価格・財務データ等のバッチ解析を高速に実行。
- OpenAI（gpt-4o-mini）を用いたニュース NLP / レジーム判定機能を搭載（API キー必須）。

## 主な機能一覧
- Execution:
  - OrderManager: 注文生成・送信・状態同期・Duplicate 防止
  - Reconciler: 再起動時の注文・ポジション照合による自動復旧
  - RiskManager: 発注前のリスクチェック（最大ポジション比率等）
- Monitoring:
  - SystemMonitor: CPU/Memory/Disk、Execution プロセス存在チェック、データ鮮度チェック
  - TradeMonitor: 注文滞留・約定価格異常検出
  - RiskMonitor: ドローダウン検出、ポジション上限監視
  - KillSwitch / AlertManager: 異常時の停止フラグ書き込み・LINE 通知
  - MonitoringEngine: 各 Monitor を束ねたポーリングループ
  - Streamlit ダッシュボード（読み取り専用）
- Tools:
  - paper_verification_report: Paper Trading DB から期間指定で検証レポートを生成
- Research / Portfolio:
  - ファクター計算（momentum/volatility/value）
  - forward return / IC / 統計サマリ
  - ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算）
- AI:
  - news_nlp.score_news: ニュース記事を LLM でスコア化して ai_scores に格納
  - regime_detector.score_regime: マクロニュース + ETF ma200 乖離で市場レジーム判定

## 要件（主な Python パッケージ）
- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード利用時)
- その他（テスト/環境により）: sqlite3 は標準ライブラリ

インストール例:
pip install duckdb psutil requests openai streamlit

## セットアップ手順（ローカル開発 / 運用向け）
1. リポジトリをチェックアウト
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate
3. 依存パッケージをインストール
   - pip install -r requirements.txt  # なければ個別インストール（上記参照）
4. 環境変数を準備
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動でロードされます（自動ロードを抑制するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
   - 例（.env）:
     - KABUSYS_ENV=development|paper_trading|live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant|partial|never|reject
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL=60
     - LOG_LEVEL=INFO
5. データディレクトリ準備
   - data/ 配下に duckdb / sqlite ファイルを配置（初回は空ファイルでも OK）。
   - MonitoringDB の初期化は実行スクリプトが行います（init_monitoring_db）。

注意:
- paper_trading モード（KABUSYS_ENV=paper_trading）の場合、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）へ分離して記録します。
- Monitoring は常に本番用 sqlite_path（Settings.sqlite_path）を使う仕様です。

## 使い方（主要な起動 / 実行コマンド）
- ExecutionEngine を起動（実行エンジン）
  - KABUSYS_ENV を適切に設定した上で:
    - python -m kabusys.run_execution
  - 特記事項: 起動時にプロセス優先度を high に設定します。paper_trading モードでは MockBroker を利用します。

- Monitoring（ポーリング監視）を起動
  - MONITOR_POLL_INTERVAL を変更してポーリング間隔を上書き可能（秒。デフォルト 60）。
    - export MONITOR_POLL_INTERVAL=30
  - 起動:
    - python -m kabusys.run_monitoring

- Streamlit ダッシュボード（読み取り専用）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI / レジーム判定・ニューススコアリング（ライブラリ API）
  - Python から直接呼び出し（例）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # duckdb_conn は duckdb.connect(...)
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

- Research / Factor 計算（ライブラリ API）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - calc_momentum(duckdb_conn, date_obj)

## 主要な環境変数（要点）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の動作）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行プロセス管理用ファイルパス
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- LOG_LEVEL: DEBUG/INFO/...

詳細は kabusys.config.Settings のプロパティ実装を参照してください。

## 運用上の注意
- MonitoringEngine は監視ログを SQLite に保存します。init_monitoring_db() は冪等な初期化・簡易マイグレーション（カラム追加）を行います。
- Execution 起動時に PID ファイルを書き、SystemMonitor はその PID の存否で Execution プロセスの健全性をチェックします。KillSwitch がトリガーされると KILL_FLAG を書き込み Execution 停止を促します。
- OpenAI など外部 API 呼び出しはリトライ・フォールバック（失敗時は安全側の既定値）を組み込んでありますが、API キー管理とレート制限には注意してください。
- paper_trading は本番 DB と完全に分離することを意図しています。検証時に誤って本番 DB を上書きしないようパスを確認してください。

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / .env 読み込み・Settings
  - run_execution.py  — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - monitoring/
    - __init__.py
    - monitoring_db.py   — SQLite 永続化層 + MonitoringDB クラス
    - system_monitor.py   — システム・データ鮮度監視
    - trade_monitor.py    — 注文滞留 / 約定異常監視
    - risk_monitor.py     — ドローダウン / ポジション上限監視
    - kill_switch.py      — 停止フラグ書き込みユーティリティ
    - alert_manager.py    — LINE Push 通知
    - monitoring_engine.py— 各 Monitor を束ねる実行エンジン
    - streamlit_dashboard.py — Streamlit UI（read-only）
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py (一部実装参照)
    - ... (Broker 関連インターフェース等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py        — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — マーケットレジーム判定（OpenAI）
    - __init__.py
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py

（上記は本リポジトリの主要モジュールのみ抜粋）

## 開発 / テストに関して
- 多くの機能は外部依存（ブローカー API、OpenAI、DuckDB）に依存するため、ユニットテストではモックが必須です。コード内でも _call_openai_api 等は置き換え可能に設計されています（テスト用 patch 想定）。
- スクリプトは __main__ エントリを提供しているため、python -m kabusys.<module> で実行できます。

---

不明点や追加してほしい README の節（例: 詳しい .env.example、運用チェックリスト、デプロイ手順など）があれば教えてください。必要に応じて .env.example のテンプレートも作成します。