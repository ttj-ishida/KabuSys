# KabuSys

KabuSys は日本株向けの自動売買／リサーチ／監視プラットフォームのコアライブラリです。本リポジトリは取引実行エンジン、監視（Monitoring）、ポートフォリオ構築、ファクター計算、ニュース NLP（OpenAI を利用したセンチメント評価）などの主要コンポーネントを含みます。

以下はコードベースに基づく README.md（日本語）です。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- 注文発行・状態管理・再同期を行う Execution エンジン
- システム稼働状況・注文滞留・リスク（ドローダウン・ポジション上限）を監視する Monitoring
- ポートフォリオ構築（銘柄選定・重み計算・ポジションサイズ決定）
- DuckDB を用いたファクター計算・リサーチユーティリティ
- OpenAI を利用したニュースセンチメント評価（AI モジュール）
- Paper Trading 用の検証レポート生成ツール
- Streamlit ベースの監視ダッシュボード

設計方針の特徴：
- 可能な限り副作用を抑えた純粋関数群（ポートフォリオ／リサーチ）
- DB（SQLite / DuckDB）は明示的に接続して利用
- OpenAI API 呼び出しは失敗耐性（リトライ・フォールバック）を備える
- 環境変数 / .env による設定管理

---

## 主な機能一覧

- Execution
  - 注文の作成／送信／同期／再突合（Reconciler）
  - Paper trading モード（MockBroker を使用し paper DB に分離）
  - リスク管理（RiskManager）統合
- Monitoring
  - SystemMonitor: プロセス生存、CPU/メモリ/ディスク、データ鮮度チェック
  - TradeMonitor: 注文滞留（stale）・約定価格異常検知
  - RiskMonitor: ドローダウン／ポジション上限の監視とアラート
  - KillSwitch: 条件に応じた停止フラグ（data/kill.flag）出力
  - AlertManager: LINE Push によるアラート通知（オプション）
  - Streamlit ダッシュボード（read-only 接続）
- Research / Data
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）計算
- AI
  - news_nlp: ニュース記事を OpenAI でスコアリングして ai_scores に保存
  - regime_detector: ETF（1321）MA200 とマクロニュースを組み合わせた市場レジーム判定
- Tools
  - paper_verification_report: Paper Trading の検証レポート生成（期間指定可）

---

## 必要条件（推奨）

- Python 3.10+
- pip
- 必要パッケージ（例）:
  - duckdb
  - openai
  - psutil
  - requests
  - streamlit (ダッシュボード利用時)
- SQLite（標準ライブラリ sqlite3 を使用）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai psutil requests streamlit
```

（プロジェクトに requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローンして作業環境を準備する
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb openai psutil requests streamlit
   ```

2. 環境変数 / .env を準備する
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - PAPER_FILL_MODE (instant | partial | never | reject) — デフォルト: instant
     - PAPER_TRADING_SQLITE_PATH — Paper 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - PID_FILE_PATH, KILL_FLAG_PATH など
     - LOG_LEVEL（DEBUG/INFO/...）

   例 .env（最小）
   ```
   KABUSYS_ENV=development
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-...
   ```

3. データディレクトリを作成する
   ```bash
   mkdir -p data
   ```

4. DuckDB / SQLite の初期テーブルについて
   - Monitoring 用 SQLite は起動時に自動でテーブルを作成します（init_monitoring_db）。明示的な初期化は不要です。
   - DuckDB には prices_daily や raw_financials / raw_news といったテーブルが必要です（データ投入は別途実施）。

---

## 使い方（主要エントリポイント）

※ モジュールはパッケージとして実行可能です（python -m kabusys.<module>）。

1. 監視ループを起動（Monitoring）
   - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
   - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用します（監視 DB は本番 DB を想定）。
   ```bash
   python -m kabusys.run_monitoring
   # または
   MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   ```

2. 実行エンジンを起動（Execution Engine）
   - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録されます。
   ```bash
   python -m kabusys.run_execution
   # Paper trading の例
   KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   ```

3. Paper Trading 検証レポート
   ```bash
   # デフォルト DB を使う場合
   python -m kabusys.tools.paper_verification_report

   # 期間指定例
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

   # DB 指定例
   python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
   ```

4. Streamlit ダッシュボード（監視用）
   - 起動方法（read-only 接続推奨）
   ```bash
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```

5. AI 機能（ニューススコアリング / レジーム判定）
   - OpenAI API キー（OPENAI_API_KEY）を環境変数に設定してください。
   - 例（ニューススコアリングの関数を呼ぶスクリプト／バッチから利用）:
     - kabusys.ai.news_nlp.score_news(conn, target_date, api_key)
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key)

---

## 環境変数の抜粋（重要なもの）

- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（default: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（default: data/kabusys.duckdb）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、default: 60）
- PAPER_FILL_MODE: paper trading の約定挙動（instant/partial/never/reject）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行制御用パス
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

注意: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化できます（テスト等で便利）。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要モジュールと簡単な説明です（コードベースから抜粋）。

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / .env の読み込みと Settings クラス
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 対応）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - monitoring/
    - monitoring_db.py — SQLite ベースの永続化層（テーブル作成・CRUD）
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・PID チェック
    - trade_monitor.py — 注文滞留・約定価格異常の検知
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — 停止フラグ生成ロジック
    - alert_manager.py — LINE Push による通知
    - monitoring_engine.py — 各 Monitor をまとめるエンジン
    - streamlit_dashboard.py — Dashboard（Streamlit）
  - execution/
    - reconciler.py — 再起動時の注文／ポジション同期
    - order_manager.py — 注文状態管理の外向き API（OrderManager）
    - （他の execution 関連ファイルは本リストでは省略）
  - portfolio/
    - portfolio_builder.py — 候補銘柄選定・重み計算
    - position_sizing.py — 発注株数決定・単元丸め・キャップ調整
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI で銘柄別スコア生成）
    - regime_detector.py — 市場レジーム判定（MA200 + マクロニュース）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/ (想定)
    - DuckDB / SQLite のデータファイル（デフォルトは data/ 以下）

（上記は実ファイルの一部を抜粋しています。完全な構成はリポジトリのツリーを参照してください）

---

## 運用上の注意点 / 補足

- Monitoring は production の sqlite_path を使用するため、監視 DB のアクセス権やバックアップ運用を考慮してください。
- ExecutionEngine は KABUSYS_ENV により paper_trading（完全分離）／live の動作を切り替えます。Paper モードでは paper_trading DB に書き込まれるため本番資金管理は不要です。
- OpenAI を使う機能は API キー管理とコストに注意してください。API 呼び出しはバッチ化・リトライ・失敗時のフォールバックが実装されていますが、運用時はレート制限やコスト監視が必要です。
- process_priority.set_process_priority を使っています。psutil による権限不足で操作に失敗する場合があるため、実運用での権限設定を確認してください。
- streamlit ダッシュボードは SQLite を read-only モード（URI + mode=ro）で開くようにしています。運用時は監視プロセスと同一 DB の排他に注意してください。

---

## さらに詳しく / 開発時ヒント

- 設定読み込みは config.Settings を通して行ってください。Settings は型チェックとバリデーションを含みます。
- MonitoringDB.init_monitoring_db は冪等なテーブル作成と簡単なマイグレーション（カラム追加）を行います。新しいテーブルやカラムを追加する場合はマイグレーション処理の追加を検討してください。
- AI 関連の OpenAI 呼び出しはテストしやすいように _call_openai_api を抽象化してあり、ユニットテストでは patch して挙動を模擬できます。
- DuckDB を使用したファクター計算関数は接続オブジェクトを受け取り純粋に SQL / Python ロジックで計算します。外部 API 呼び出しは行いません。

---

この README はリポジトリ内のソース（src/kabusys 以下）を参照して作成しています。実際の運用／導入時はプロジェクト固有の README やデプロイ手順（systemd / supervisor / containerization）を追加してください。必要であれば起動スクリプト例や systemd ユニットファイル、docker-compose 構成のテンプレートも作成できます。ご希望があれば追記します。