# KabuSys — README

KabuSys は日本株の自動売買 / リサーチ / 監視を目的とした小規模なシステムです。  
このリポジトリは注文発行・実行エンジン、監視/アラート、ポートフォリオ構築、ファクター計算、LLM を用いたニュース解析などの機能を含みます。

目次
- プロジェクト概要
- 主な機能一覧
- 必要条件（依存）
- セットアップ手順
- 環境変数（主要）
- 使い方（実行例）
- ディレクトリ構成（主要ファイル説明）
- 運用上の注意

---

## プロジェクト概要
KabuSys は以下の要素で構成された自動売買支援システムです。
- ExecutionEngine: シグナルを受けて発注し、ブローカーとの同期・リコンシリエーションを行う。
- MonitoringEngine: システム状態・注文状態・リスク指標を定期チェックしログ・アラート発行や Kill Switch を管理する。
- Portfolio モジュール: 候補選定、重み計算、ポジションサイジング、セクター制約などの純粋関数群。
- Research モジュール: DuckDB を用いたファクター計算、将来リターン・IC 計算などの探索ツール。
- AI モジュール: OpenAI（gpt-4o-mini）を用いたニュースセンチメント分析や市場レジーム判定。
- 監視ダッシュボード: Streamlit ベースの簡易 UI（読み取り専用）。

設計方針の特徴:
- DuckDB/SQLite をローカルに使う（本番データと Paper Trading は分離可能）。
- LLM 呼び出しは失敗時にフォールバックする等、フェイルセーフ設計。
- 外部 API（ブローカーなど）は抽象化され、テスト用モックが使える。

---

## 主な機能一覧
- シグナル読み込み→Gate 検査→発注のフロー（ExecutionEngine）
- 起動時のリコンシリエーション（Reconciler）
- 注文状態管理、同期（OrderManager / OrderRepository）
- ポジションサイズ計算・セクターキャップ・レジーム乗数（portfolio パッケージ）
- ファクター計算（モメンタム・ボラティリティ・バリュー等）と探索ユーティリティ（research）
- ニュース記事を LLM に渡して銘柄別センチメントを算出し ai_scores に保存（ai.news_nlp）
- ETF + マクロニュースを組み合わせた市場レジーム判定（ai.regime_detector）
- 監視（CPU/メモリ/ディスク、データ鮮度、滞留注文、約定異常、ドローダウン等）とログ永続化（monitoring）
- LINE へのプッシュ通知（AlertManager）
- Streamlit による監視ダッシュボード（read-only）

---

## 必要条件（依存）
- Python 3.9+（コードは typing と一部新しい構文を使用）
- 必須パッケージ（主なもの）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード使用時）
- 標準ライブラリ: sqlite3, logging, datetime, pathlib 等

（プロジェクトに requirements.txt がない場合は上記パッケージを pip でインストールしてください）

例:
pip install duckdb psutil requests openai streamlit

---

## セットアップ手順
1. リポジトリのクローン（任意）
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows では .venv\Scripts\activate）
3. 必要なパッケージをインストール
   - pip install duckdb psutil requests openai streamlit
4. データディレクトリを作成
   - mkdir -p data
   - SQLite / DuckDB ファイル（デフォルト: data/monitoring.db, data/kabusys.duckdb）が必要になりますが、実行スクリプトが起動時に monitoring DB のテーブル作成を行います。
5. 環境変数を設定（.env ファイルをプロジェクトルートに置くことが可能）
   - 自動ロード機能: .env / .env.local をプロジェクトルートから自動読込（OS 環境変数を優先）。
   - 自動読み込みを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 主要な環境変数（抜粋）
- KABUSYS_ENV: 起動モード。 development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、モックブローカーを使用し paper_sqlite_path (default data/paper_trading.db) に記録
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須な機能がある場合）
- KABU_API_PASSWORD, KABU_API_BASE_URL: kabuステーション API 設定
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）で必須
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE 通知）
- SQLITE_PATH: 監視用 SQLite DB のパス（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB データベースファイル（デフォルト data/kabusys.duckdb）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant | partial | never | reject）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH: pid ファイル / kill flag のパス（デフォルト data/execution.pid, data/kill.flag）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

.env 例（プロジェクトルート）:
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
KABUSYS_ENV=paper_trading
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

---

## 使い方（実行例）

※ 実行はプロジェクトルートから、PYTHONPATH を src に通すか、パッケージとしてインストールして行ってください。簡易例は下記の通り。

1) ExecutionEngine を起動（本番 or paper_trading）
- paper_trading モード例（モックブローカーを使用）
  PYTHONPATH=src KABUSYS_ENV=paper_trading python src/kabusys/run_execution.py

- live / development（実際のブローカー接続を行う実装がある場合）
  PYTHONPATH=src KABUSYS_ENV=live python src/kabusys/run_execution.py

- 実行前: 必要な環境変数（KABU_API_PASSWORD 等）がセットされていることを確認してください。

2) MonitoringEngine を起動（常時ポーリング）
- ポーリング間隔を変える:
  MONITOR_POLL_INTERVAL=30 PYTHONPATH=src python src/kabusys/run_monitoring.py

- 監視は常に本番用の sqlite_path を参照します（KABUSYS_ENV に関わらず監視 DB は production sqlite_path が使われます）。

3) Streamlit ダッシュボード（読み取り専用）
- 起動:
  PYTHONPATH=src streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4) AI 関連
- ニューススコア算出（スクリプト化されている関数を使う場合）:
  - OPENAI_API_KEY を設定して、kabusys.ai.score_news(conn, target_date) を呼ぶ
- レジーム判定:
  - OPENAI_API_KEY を設定して、kabusys.ai.regime_detector.score_regime(conn, target_date) を呼ぶ

5) モジュール単体の利用（研究・テスト）
- research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic などは DuckDB 接続を渡して使用します。

---

## 主要スクリプト／起動ポイント
- src/kabusys/run_execution.py — ExecutionEngine の起動スクリプト
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用（paper_trading DB に記録）
- src/kabusys/run_monitoring.py — SystemMonitor のポーリング起動スクリプト
  - MONITOR_POLL_INTERVAL でポーリング間隔上書き可能（デフォルト 60 秒）
- src/kabusys/monitoring/streamlit_dashboard.py — Streamlit ベースのダッシュボード（起動は streamlit run）

---

## ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py (パッケージ定義, バージョン)
  - config.py — 環境変数 / Settings 管理（.env 自動読込ロジック含む）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - execution/
    - execution_engine.py — ExecutionEngine（発注フロー、push/drain 等）
    - order_manager.py — OrderManager（状態遷移・送信ロジック）
    - order_repository.py — SQLite ベースの永続化（このリポジトリに実装あり）
    - reconciler.py — 起動時のリコンシリエーション
    - risk_manager.py — 発注前 Gate 検査・レート制限など（設定含む）
    - broker_api.py / broker_factory.py — ブローカー抽象・ファクトリ
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化・永続化用 API
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 注文滞留/約定異常監視
    - risk_monitor.py — ドローダウン/ポジション数監視
    - monitoring_engine.py — 各モニタのポーリング統括
    - alert_manager.py — LINE 通知ラッパー
    - kill_switch.py — kill.flag 書き込みロジック
    - streamlit_dashboard.py — ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定・スコアソート
    - position_sizing.py — 数量決定ロジック（lot/aggregate cap 等）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム/ボラ/バリュー計算
    - feature_exploration.py — 将来リターン・IC・サマリー等
  - ai/
    - news_nlp.py — OpenAI によるニュースセンチメント集計 & ai_scores 書込み
    - regime_detector.py — ETF MA とマクロニュースでレジーム判定
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 運用上の注意
- Paper Trading: KABUSYS_ENV=paper_trading に切り替えると紙上での分離が行われ、取引記録は paper_trading_sqlite_path に保存されます。本番 DB を汚さないために有効です。
- Kill Switch: KillSwitch は monitoring 側の評価条件（ドローダウン超過等）で data/kill.flag を書き込みます。ExecutionEngine は起動時やループ内でこのフラグを確認し停止します。必要に応じて起動時にフラグ削除（clear）を行ってください（Settings.kill_flag_clear_on_start で制御可能）。
- PID 管理: ExecutionEngine は起動時に PID ファイルを書き、SystemMonitor はその PID の有無でプロセス稼働判定を行います。stale PID は検出されたら削除されます。
- LLM 使用時の API キー: OPENAI_API_KEY が必須。API のレート制限やエラーに対しては指数バックオフを実装していますが、コスト・レート制限には注意してください。
- DB マイグレーション: monitoring_db.init_monitoring_db は冪等でテーブルを作成します。既存 DB にカラムがない場合の簡易マイグレーション処理も含まれます（例: dashboard.peak_value 追加）。

---

もし README の補足（例: environment の具体的な .env.example、requirements.txt の自動生成、運用チェックリスト、デプロイ手順）を追加したい場合は、必要な項目を教えてください。