# KabuSys

日本株自動売買システムの軽量実装（ライブラリ / 実行スクリプト / 監視ツール群）。

このリポジトリはトレード実行エンジン、監視・アラート、ポートフォリオ構築ロジック、ファクター研究、ニュースNLP（OpenAI）連携などの主要コンポーネントを含みます。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコア部分をモジュール化したコードベースです。主要な設計方針は以下の通りです。

- 実行ロジック（ExecutionEngine / OrderManager / Reconciler）と監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）を分離
- SQLite（監視ログ等）と DuckDB（時系列・研究データ）を利用したデータ永続化
- Paper Trading 環境の分離（本番 DB と別ファイルに記録）
- OpenAI を用いたニュースセンチメント評価や市場レジーム判定の実装（フェイルセーフ設計）
- 単体関数ベースのポートフォリオ構築・リスク調整・ポジションサイズ計算（テスト容易）

---

## 主な機能一覧

- 実行エンジン起動スクリプト（run_execution）
  - Broker クライアントの生成（本番 / paper_trading の切替）
  - OrderManager / RiskManager / Reconciler 等の組み立てとセッション実行
  - Paper Trading は専用 SQLite（data/paper_trading.db 等）へ記録して本番と完全分離

- 監視ポーリング（run_monitoring / MonitoringEngine）
  - システム状態（CPU/Memory/Disk / プロセス生存）監視
  - 注文滞留・約定異常の検出
  - ドローダウン / ポジション上限の監視
  - kill.flag による ExecutionEngine 停止シグナル生成
  - LINE push によるアラート送信（AlertManager）

- データ層
  - monitoring_db: 監視用テーブル群（system_status / trade_logs / positions / risk_logs / dashboard）を初期化・操作する API

- ポートフォリオ構築（純関数）
  - 候補選定、等重・スコア重み付け、セクター制限、レジーム乗数、ポジションサイズ算出など

- 研究（research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ

- AI（OpenAI）連携
  - ニュース記事の銘柄別センチメント算出（news_nlp.score_news）
  - マクロニュース + ETF MA200 を使った市場レジーム判定（regime_detector.score_regime）
  - API 呼び出しは冪等性・リトライ・部分書き込みなどフェイルセーフ設計

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
  - Streamlit ダッシュボード（監視情報表示）

---

## 必要条件 / 依存関係

推奨 Python バージョン: 3.10+

主な Python パッケージ（例、requirements.txt を用意する場合の候補）:
- duckdb
- psutil
- requests
- openai
- streamlit

組み込み: sqlite3（標準ライブラリ）

※ 実際の requirements.txt は本リポジトリには含まれていないため、上記を pip 等でインストールしてください。

例:
pip install duckdb psutil requests openai streamlit

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動。

2. Python 環境を準備（仮想環境推奨）。
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール。
   pip install duckdb psutil requests openai streamlit

4. データディレクトリ作成（必要に応じて）。
   mkdir -p data

5. 環境変数（.env）を用意する。
   プロジェクトルートに `.env` または `.env.local` を置くことで自動読み込みされます（OSの環境変数が優先）。
   主な環境変数:
   - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
   - JQUANTS_REFRESH_TOKEN: （必須）
   - KABU_API_PASSWORD: （必須）
   - OPENAI_API_KEY: （AI 機能を使う場合）
   - SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
   - PID_FILE_PATH / KILL_FLAG_PATH / LOG_LEVEL 等（Settings クラス参照）

   例 (.env):
   KABUSYS_ENV=paper_trading
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=...
   JQUANTS_REFRESH_TOKEN=...

6. DB 初期化:
   - run_execution.py / run_monitoring.py の起動時に monitoring テーブルは自動で初期化されます（init_monitoring_db を呼び出すため冪等）。

---

## 使い方（主なコマンド）

- 実行エンジン起動（本番 / paper_trading は KABUSYS_ENV で切替）
  python -m kabusys.run_execution

  動作概要:
  - プロセス優先度を "high" に設定（可能な場合）
  - SQLite / DuckDB に接続
  - BrokerClient を作成（paper_trading では MockBrokerClient を使い、paper DB に記録）
  - ExecutionEngine を組み立てて run_session() を実行

- 監視ポーリングを開始
  python -m kabusys.run_monitoring

  環境変数でポーリング間隔を上書き:
  MONITOR_POLL_INTERVAL=30  （秒、デフォルト 60）

  監視は monitoring DB（Settings.sqlite_path）を使用します（環境にかかわらず本番 sqlite_path を使用する実装）。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション:
  --from, --to: YYYY-MM-DD
  --db: DB パス（デフォルトは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db）

- Streamlit ダッシュボード起動（監視用）
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI 関数（Python から直接呼び出す）
  - ニューススコア付け:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="sk-...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="sk-...")

  ※ OpenAI API キーは api_key 引数、もしくは環境変数 OPENAI_API_KEY を利用。

---

## 主要な設定項目（Settings に定義されているもの）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信用）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE（instant | partial | never | reject）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH / 各種閾値（CPU/MEM/DISK）
- KABUSYS_ENV（development | paper_trading | live）

設定は .env/.env.local または OS 環境変数で与えられます。プロジェクトルートの探索は git または pyproject.toml を基準に行われ、自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py  — 環境変数 / 設定管理
- run_execution.py  — ExecutionEngine 起動スクリプト
- run_monitoring.py — Monitoring ポーリングスクリプト

パッケージ別:
- ai/
  - news_nlp.py         — ニュースセンチメント（OpenAI）
  - regime_detector.py  — 市場レジーム判定（OpenAI + MA200）
- monitoring/
  - monitoring_db.py    — SQLite 監視 DB 層（初期化 / CRUD）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - alert_manager.py
  - kill_switch.py
  - streamlit_dashboard.py
- execution/
  - reconciler.py
  - order_manager.py
  - (その他 broker / engine / order_repository 等の実装箇所)
- portfolio/
  - portfolio_builder.py
  - risk_adjustment.py
  - position_sizing.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py

ドキュメント / 設計リファレンス（コード内コメントに多数あり）：
- PortfolioConstruction.md / StrategyModel.md 等（プロジェクト参照があるがこのコードベース内に未同梱の場合あり）

---

## 運用上の注意 / 補足

- Paper Trading: KABUSYS_ENV=paper_trading のとき、ブローカークライアントはモックを使い paper_trading 用 SQLite に記録します。本番 DB と完全に分離されます。
- 監視（Monitoring）コンポーネントは monitoring DB（Settings.sqlite_path）を使います。run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計です。
- OpenAI の呼び出しはリトライ・バックオフを実装していますが、API キーやコストに注意してください。API が無い場合は AI 機能は使えません（score_* 関数は例外を投げるかフェイルセーフで 0 を返す実装が混在します）。
- PID ファイル / kill.flag を利用して ExecutionEngine の状態管理や外部停止命令を行います。kill.flag の書き込みは冪等で、既に存在する場合は追記しません。
- streamlit ダッシュボードは監視 DB を読み取り専用で開くことを推奨します（起動時に read-only URI を使用）。

---

## 開発 / テスト

- 各モジュールは純粋関数 (portfolio, research など) と状態を持つクラス（monitoring_db, MonitoringDB 等）に分離されており、ユニットテストを書きやすい構造になっています。
- OpenAI 呼び出し部分は _call_openai_api のような個別関数でラップされており、テスト時に patch / mock 可能です。
- DB に対する影響を限定的にするため、paper_trading 用 DB を別にしておくことを推奨します。

---

必要があれば README に以下を追加できます:
- 実際の requirements.txt（依存固定版）
- CI / テスト実行方法（pytest など）
- 詳しい設計ドキュメント参照（PortfolioConstruction.md / StrategyModel.md 等）のリンクや要約

ご希望があれば上記の追記（依存関係の pin、サンプル .env.example、簡易運用手順など）を作成します。