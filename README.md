# KabuSys

日本株向けの自動売買 / 研究用ライブラリ（モジュール群のみのコードベース）
このリポジトリは、注文発行・実行管理、監視、ポートフォリオ構築、ファクター計算、
LLM を用いたニュースセンチメント評価などを含む自動売買システムのコア部分を提供します。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群で構成されています。

- 注文発行・状態管理（Execution）
  - ExecutionEngine、OrderManager、OrderRepository、Reconciler など
  - 本番 / ペーパー取引切替（KABUSYS_ENV）
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor、アラート送信（LINE）
  - 監視 DB（SQLite）への永続化と Streamlit ダッシュボード
  - Kill Switch による ExecutionEngine 停止シグナル
- ポートフォリオ構築（Portfolio）
  - 候補選定、重み計算、ポジションサイジング、セクターキャップ、レジーム乗数
- 研究（Research）
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value）
  - 特徴量探索（forward returns / IC / summary）
- AI（AI）
  - ニュース記事を LLM（OpenAI）でスコアリング（ai_scores へ保存）
  - マクロニュースを使った市場レジーム判定
- ユーティリティ
  - 環境変数読み込み、プロセス優先度設定など

---

## 主な機能一覧

- Execution
  - Order 作成→送信→状態遷移管理（DB 永続化、ブローカー API 統合）
  - 再起動時のリコンシリエーション（Reconciler）
  - Paper Trading モード（MockBroker を用い、ローカル DB に記録）
- Monitoring
  - CPU / メモリ / ディスクの監視、プロセス生存チェック
  - 注文の滞留・約定異常検出、ドローダウン監視
  - アラート（LINE API）送信とクールダウン管理
  - kill.flag による外部停止指示
  - Streamlit ダッシュボード（read-only で監視 DB を可視化）
- Research / Portfolio
  - DuckDB 上の価格・財務データに基づくファクター計算
  - 候補選定・重み付け・株数計算・セクター制限・レジーム調整
- AI 統合
  - OpenAI（gpt-4o-mini）を使用したニュースセンチメント（銘柄別）集約
  - マクロセンチメント + ETF MA200 乖離で市場レジーム判定
- CLI / スクリプト
  - run_execution、run_monitoring、tools.paper_verification_report、Streamlit ダッシュボード

---

## 要件（推奨）

- Python 3.9+
- 主な依存ライブラリ（一例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
  - （SQLite は標準ライブラリ）
- OS: Linux / macOS / Windows（process priority のサポート差異あり）

（プロジェクトの requirements.txt がある場合はそれを使用してください）

---

## 環境変数・設定

Settings クラスで参照している主な環境変数:

必須または動作に影響する主なキー
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI機能を使う場合）
- KABUSYS_ENV — 実行環境: `development` | `paper_trading` | `live`（デフォルト: development）
  - `paper_trading` の場合、MockBrokerClient を使い paper 用 DB に書き込む
- PAPER_FILL_MODE — Paper Trading の約定挙動: `instant` | `partial` | `never` | `reject`（デフォルト `instant`）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH — ExecutionEngine 用 PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を削除するか（"1"で有効）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（未設定なら通知は行わない）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

.env 読み込み
- プロジェクトルートの `.env` と `.env.local` を自動で読み込み（OS 環境変数優先）。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

---

## セットアップ手順（例）

1. リポジトリをクローン / checkout
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（requirements.txt がない場合は上記ライブラリを個別に）
   - pip install duckdb psutil requests openai streamlit
4. 環境変数を設定（.env を作成）
   - .env に必要なキーを記述（README に記載のキー参照）
   - 例:
     - KABUSYS_ENV=development
     - JQUANTS_REFRESH_TOKEN=xxx
     - KABU_API_PASSWORD=yyy
     - OPENAI_API_KEY=zzz
5. データディレクトリを作成
   - mkdir -p data
6. DuckDB / SQLite の初期テーブルは各スクリプト起動時に自動で作成・マイグレーションされます（init_monitoring_db 等）。

---

## 使い方（起動例）

- ExecutionEngine を起動（本番 / 開発 / paper_trading 切替は KABUSYS_ENV）:
  - デフォルト（モジュール実行）:
    - python -m kabusys.run_execution
  - Paper trading で実行（例）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 注意: paper_trading の場合、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に発注ログが記録され、本番 DB と分離されます。

- Monitoring（ポーリングループ）を起動:
  - MONITOR_POLL_INTERVAL で監視間隔(秒)を上書き可能（デフォルト 60秒）
  - python -m kabusys.run_monitoring
  - 例: export MONITOR_POLL_INTERVAL=30; python -m kabusys.run_monitoring
  - 監視は Settings に関係なく本番 sqlite_path（SQLITE_PATH）を参照してログを記録します。

- Streamlit ダッシュボード（監視データの可視化）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 既存の monitoring DB を読み取り専用で開きます（存在しない場合はエラー）。

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡してニューススコアを ai_scores テーブルへ書き込む
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - マクロ + MA200 でレジームを判定し market_regime テーブルへ書き込む

---

## 開発上の注意 / 実装上の振る舞い

- .env のパースは柔軟に実装（export プレフィックス、クォート、コメント対応）。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行うため、CWD に依存しません。
- run_monitoring は監視 DB に必ず production sqlite_path を使います（環境に関係なく）。
- run_execution は KABUSYS_ENV=paper_trading の時、paper DB（paper_sqlite_path）に切替。
- OpenAI の呼び出しは堅牢性を重視（リトライ、JSON パース復元、失敗時はフェイルセーフ）。
- process priority / CPU affinity はプラットフォーム差を吸収して設定しようと試みますが、権限不足時は無視されログ出力します。
- DuckDB の executemany はバージョン差で空リストが問題になるため、空チェックを行ってから executemany しています。

---

## ディレクトリ構成

主要ファイル／モジュールの概観:

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / 設定管理
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py — Paper Trading の検証レポート生成 CLI
    - monitoring/
      - __init__.py
      - monitoring_db.py           — monitoring DB スキーマ + DB ラッパ
      - system_monitor.py          — CPU/メモリ/ディスク/データ鮮度監視
      - trade_monitor.py           — 注文滞留 / 約定異常監視
      - risk_monitor.py            — ドローダウン・ポジション上限監視
      - kill_switch.py             — kill.flag 制御
      - alert_manager.py           — LINE 通知ラッパ
      - monitoring_engine.py       — 各 Monitor を束ねるエンジン
      - streamlit_dashboard.py     — Streamlit ダッシュボード
    - execution/
      - order_manager.py
      - order_repository.py
      - execution_engine.py
      - reconciler.py
      - broker_factory.py
      - (その他注文・ブローカー関連)
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
      - news_nlp.py                — ニュースセンチメント生成（OpenAI）
      - regime_detector.py         — 市場レジーム判定（OpenAI + MA200）
      - __init__.py
    - utils/
      - process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ
      - __init__.py

---

## よくある運用パターン

- 開発 / テスト:
  - KABUSYS_ENV=development を使用。OpenAI を使わない場合は OPENAI_API_KEY を空にする。
  - ペーパー取引・解析は paper_trading を使って実データと分離。
- 本番運用:
  - KABUSYS_ENV=live、十分な権限のプロセスで run_execution/run_monitoring を起動。
  - LINE 通知・Kill Switch を有効にして安全弁を構成。
  - 監視は run_monitoring が常駐、Streamlit は読み取り専用で運用。

---

## 追加情報 / 開発者向けメモ

- tests や CI がある場合、Settings の自動 .env 読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI API 呼び出し部分はテスト容易性のため内部呼び出し関数を patch して差し替え可能に作っています（unittest.mock.patch を利用）。
- DuckDB のスキーマやテーブルは research / ai の前提になります。必要に応じて初期データをロードしてください。

---

必要に応じて README に追記します。運用手順（systemd ユニット、コンテナ化、ログローテーション等）や依存関係リストを追加したい場合は使用環境情報を教えてください。