# KabuSys

日本株自動売買システムのモジュール群（ライブラリ＋運用用スクリプト群）

このリポジトリは、マーケットデータ処理、ファクター計算、ポートフォリオ構築、発注エンジン、監視・アラート、AI ベースのニュース判定などを含む自動売買システムのコンポーネント群を提供します。各コンポーネントは独立性を保つよう設計され、運用環境（本番 / ペーパー取引 / 開発）に合わせた動作切替が可能です。

主な特徴
- DuckDB / SQLite を用いたデータ処理・永続化
- ファクター計算（Momentum / Volatility / Value 等）
- ポートフォリオ構築（候補選定、重み付け、株数決定、セクター制約）
- 発注/リコンシリエーション（ExecutionEngine 周辺、OrderManager、Reconciler）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）と Alert（LINE Push）
- ペーパー取引用の分離 DB と MockBroker 対応
- OpenAI（gpt-4o-mini）を用いたニュース NLP と市場レジーム判定
- 運用確認用レポート生成ツール（paper_verification_report）
- Streamlit ベースの監視ダッシュボード

---

## 機能一覧（抜粋）

- 設定・環境変数管理（kabusys.config.Settings）
  - .env / .env.local の自動読み込み（プロジェクトルートが検出できる場合）
  - KABUSYS_ENV（development / paper_trading / live）で動作切替
  - DB パス、PID / kill flag パス、監視閾値等の集中管理

- 実行系
  - run_execution.py: ExecutionEngine を起動（本番 / ペーパー判定でブローカークライアントを切替）
  - Reconciler: 起動時の注文・ポジション再照合

- 監視
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - MonitoringDB: SQLite に監視ログ・トレードログ・ポジション・リスクログ・ダッシュボードを永続化
  - AlertManager: LINE Messaging API による通知（クールダウン付き）
  - KillSwitch: 条件に応じて kill.flag を書き込み、ExecutionEngine 停止を指示

- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 等ウェイト / スコア重み（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクター制限・レジーム乗数（apply_sector_cap / calc_regime_multiplier）

- リサーチ
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 前方リターン計算、IC（Information Coefficient）や統計サマリー

- AI（OpenAI）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp.score_news）
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
  - LLM 呼び出しはリトライ・バックオフやレスポンス検証を含む堅牢な実装

- ツール
  - paper_verification_report: ペーパー取引 DB（data/paper_trading.db）から検証レポートを生成
  - Streamlit ダッシュボード（monitoring/streamlit_dashboard.py）

---

## 動作環境・依存関係（推奨）

- Python 3.10+
- 推奨パッケージ（pip インストール例は下記参照）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- OS: Linux / macOS / Windows（ただし process priority / cpu affinity 設定はプラットフォーム依存）

依存パッケージは実際のプロジェクトでは requirements.txt / pyproject.toml に定義してください。ここでは代表的なインストール例を示します:

venv 作成例
- python -m venv .venv
- source .venv/bin/activate  (Windows: .venv\Scripts\activate)

パッケージ例:
- pip install duckdb psutil requests openai streamlit

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化する
   - git clone <repo>
   - cd <repo>
   - python -m venv .venv
   - source .venv/bin/activate   (Windows は .venv\Scripts\activate)

2. 依存パッケージをインストールする
   - pip install duckdb psutil requests openai streamlit

3. 環境変数の準備
   - プロジェクトルートに .env または .env.local を配置することで環境を設定できます。
   - 自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
   - 必須例（.env.example を参考に作成してください）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...   (AI 機能を使う場合)
     - KABUSYS_ENV=development|paper_trading|live
     - PAPER_FILL_MODE=instant|partial|never|reject (paper_trading 用)
     - LINE_CHANNEL_ACCESS_TOKEN=... (LINE 通知を使う場合)
     - LINE_USER_ID=...
   - DB パスのデフォルト:
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

4. データディレクトリを作成する
   - mkdir -p data

5. 初回 DB 作成
   - run_monitoring や run_execution 実行時に init_monitoring_db() が呼ばれ、必要なテーブルが自動で作成されます。

注意:
- Settings クラスは起動時に環境変数を検証します。無効な値や欠損があると例外が発生するため、.env の内容を確認してください。

---

## 使い方（主要スクリプト）

- 監視ループを起動（SystemMonitor のポーリング）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更できます（デフォルト: 60）
  - python -m kabusys.run_monitoring
  - ログレベルはいまは basicConfig INFO 固定ですが、環境変数 LOG_LEVEL で検証値を制御する箇所あり（Settings.log_level）

- 実行エンジン（ExecutionEngine）を起動
  - KABUSYS_ENV により本番 / paper_trading が切り替わる
    - paper_trading の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます
  - python -m kabusys.run_execution

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは読み取り専用モードで SQLite DB を開きます（存在しない場合はエラー表示）

- AI 機能（プログラム内呼び出し）
  - ニューススコア:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)

- リサーチ / ポートフォリオ関数（ライブラリ利用）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

---

## 主要設定（環境変数とデフォルト）

重要な環境変数（代表）
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使用する際に必須）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject (デフォルト "instant")
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で使用）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

Settings クラスは不正値検出時に ValueError を投げます。PAPER_FILL_MODE 等は許容値が限定されています。

---

## ディレクトリ構成（src/kabusys 以下、主なファイル説明）

- src/kabusys/__init__.py
  - パッケージメタデータ（__version__ 等）

- src/kabusys/config.py
  - 環境変数読み込み・Settings クラス（.env 自動読み込み、必須チェック、各種パス・閾値）

- src/kabusys/run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 対応）

- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 時は MockBroker を利用し DB を分離）

- src/kabusys/monitoring/
  - monitoring_db.py: SQLite スキーマ初期化・CRUD ユーティリティ（MonitoringDB）
  - system_monitor.py: システム状態・データ鮮度チェック
  - trade_monitor.py: 注文滞留・約定異常チェック
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag の管理（Execution 停止）
  - alert_manager.py: LINE へのアラート送信
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py: Streamlit ベースの監視ダッシュボード

- src/kabusys/execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine 等（発注管理、再同期、リスク管理、ExecutionEngine）

- src/kabusys/portfolio/
  - portfolio_builder.py: 候補選定、重み計算
  - position_sizing.py: 株数・スケーリング・lot 調整
  - risk_adjustment.py: セクター上限、レジーム乗数
  - __init__.py: API エクスポート

- src/kabusys/research/
  - factor_research.py: Momentum / Volatility / Value ファクター計算（DuckDB を利用）
  - feature_exploration.py: 将来リターン、IC、統計サマリー

- src/kabusys/ai/
  - news_nlp.py: raw_news -> OpenAI による銘柄別ニューススコア集約・書き込み
  - regime_detector.py: マクロ記事 + ETF MA200 乖離から市場レジーム算出・DB 書き込み

- src/kabusys/tools/
  - paper_verification_report.py: Paper Trading DB から検証レポート生成ツール

- src/kabusys/utils/
  - process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティ

（上記は抜粋です。実際のファイル一覧はソースツリーを参照してください。）

---

## 運用メモ / 注意点

- 自動ロードされる .env はプロジェクトルート（.git または pyproject.toml を基準）から読み込まれます。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_execution は起動時に paper_trading なら別 DB を使用するため本番 DB と完全に分離可能です。ペーパー運用時の挙動（PAPER_FILL_MODE）を必ず確認してください。
- run_monitoring は MonitoringDB を常に本番 sqlite_path に対して初期化します（監視ログは本番用 DB を使う設計）。
- AI（OpenAI）を利用する機能は API キーが必要です。API 呼び出しはレート制限や 5xx を考慮したリトライロジックがありますが、API キーの漏洩に注意してください。
- PID ファイル（デフォルト data/execution.pid）と kill.flag（data/kill.flag）はプロセス間での稼働監視に利用します。実運用時は filesystem の権限やプロセス管理方式（systemd 等）と整合させてください。
- Streamlit ダッシュボードは読み取り専用で DB を開きます。運用環境では MonitoringEngine を先に起動してデータを投入してください。

---

## 追加情報 / 開発者向け

- テスト: 各モジュールは外部依存（OpenAI / ブローカー API 等）を抽象化しているため、unit tests ではモック可能です（例: _call_openai_api のパッチなど）。
- マイグレーション: monitoring_db.init_monitoring_db は冪等でテーブルを作成し、既存の列追加（ALTER TABLE）も処理します。
- ロギング: 各モジュールは標準 logging を使っています。必要に応じて起動時に logging 設定を上書きしてください。

---

以上がこのコードベースの概要・セットアップ・使用法・ディレクトリ構成です。README の内容や実行方法について追加で明記してほしい点（例: CI 設定、詳細な env.example、Docker サンプルなど）があれば教えてください。