# KabuSys

日本株自動売買システムのサンプル実装。ポートフォリオ構築、発注管理、監視、AI を使ったニュースセンチメントやレジーム判定、Paper Trading 検証などの機能を含みます。

以下はこのリポジトリの README.md（日本語）です。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関する主要機能群をモジュール化したコードベースです。主な設計方針は「本番系コードと解析／検証系を分離」「外部 API 呼び出し時はフェイルセーフ」「DuckDB / SQLite を用いたローカルデータ分析と監視の組合せ」です。

主なコンポーネント：
- Execution（注文送信・状態管理・リコンシリエーション）
- Monitoring（システム状態、注文滞留、リスク監視、LINE 通知）
- Portfolio（候補選定、重み付け、ポジションサイズ計算、リスク調整）
- Research（ファクター計算、将来リターン、IC 計算）
- AI（ニュースセンチメント、レジーム判定 — OpenAI を利用）
- Tools（Paper Trading 検証レポートなど）

---

## 機能一覧

- システム監視（CPU／メモリ／ディスク、データ鮮度、プロセス生存監視）
- 注文監視（滞留注文・約定の価格異常検出）
- リスク監視（ドローダウン閾値・ポジション上限検出）と kill flag による自動停止シグナル発行
- LINE によるアラート送信（AlertManager）
- Execution エンジン起動スクリプト（paper_trading 時はモックブローカーと専用 DB を使用）
- Monitoring のポーリングプロセス起動スクリプト（環境変数で間隔変更可）
- Streamlit ベースの監視ダッシュボード（read-only）
- Paper Trading の検証レポート出力ツール（注文成功率、レイテンシ、稼働率など）
- ポートフォリオ構築ロジック（候補選定、重み計算、ポジションサイジング、セクター制約、レジーム乗数）
- リサーチ向けファクター計算（Momentum / Volatility / Value）
- AI モジュール：ニュース記事を LLM（gpt-4o-mini 等）でスコアリングして ai_scores に保存、マクロニュースを使った市場レジーム判定
- ユーティリティ：プロセス優先度・CPU アフィニティ設定、環境変数ローダー（.env 自動ロード）

---

## 前提（環境）

- Python 3.9+（型ヒント等の使用を想定）
- 必要なパッケージ（主なもの）
  - duckdb
  - psutil
  - requests
  - openai（OpenAI SDK）
  - streamlit（ダッシュボード用）
  - その他（標準ライブラリで賄える部分が多い）
- SQLite（Python 標準ライブラリで使用）

※ requirements.txt はリポジトリに含まれていない想定です。実行環境に合わせて pip install してください。

---

## セットアップ手順

1. リポジトリをクローン／チェックアウトします。

   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成（推奨）

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux / macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール

   例（最小限）:

   ```bash
   pip install duckdb psutil requests openai streamlit
   ```

4. 環境変数の設定

   プロジェクトルートに `.env` / `.env.local` を置くと自動ロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

   .env の例:

   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-...
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=
   SQLITE_PATH=data/monitoring.db
   DUCKDB_PATH=data/kabusys.duckdb
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   PAPER_FILL_MODE=instant
   LOG_LEVEL=INFO
   ```

   各環境変数の説明は下の「主な環境変数」を参照してください。

5. データディレクトリの作成（必要に応じて）

   ```bash
   mkdir -p data
   ```

---

## 主な環境変数（抜粋）

- KABUSYS_ENV: 起動環境。`development` | `paper_trading` | `live`（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI 呼び出しに必要
- PAPER_FILL_MODE: Paper Trading の約定モード（instant | partial | never | reject） デフォルト: instant
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite ファイル（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: 分析用 DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH: 各種ファイルパス（デフォルトは data 配下）

--- 

## 使い方（主なコマンド・起動方法）

- Monitoring（ポーリング監視）起動

  Monitoring は常に「本番用の sqlite_path」を用いて監視ログを記録します（KABUSYS_ENV の設定に依らず）。ポーリング間隔は環境変数で変更可能。

  ```bash
  # デフォルト間隔 60 秒
  python -m kabusys.run_monitoring

  # 例: 30 秒間隔に上書き
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

  停止はデフォルトでは Ctrl+C、もしくはプロジェクトルートの `data/stop_requested.flag` ファイルを作成しても停止します。

- Execution エンジン起動

  Execution は KABUSYS_ENV に応じて動作を切り替えます。`paper_trading` の場合は MockBrokerClient を使用し、Paper 用専用 DB（PAPER_TRADING_SQLITE_PATH）へ書き込みます。

  ```bash
  python -m kabusys.run_execution
  ```

  - 停止制御: `data/stop_requested.flag` を作成するとエンジンは停止します。
  - PID は `data/execution.pid`（デフォルト）に書き込まれます。

- Streamlit 監視ダッシュボード

  監視 DB を read-only で開く Streamlit アプリ。

  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート（ツール）

  データベース（paper_trading.db）から指定期間の検証レポートを出力します。

  ```bash
  # デフォルト DB を使用
  python -m kabusys.tools.paper_verification_report

  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # DB パスを指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 機能（ニューススコア / レジーム判定）

  これらは Python API として提供されています。例:

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  # OpenAI API キーは OPENAI_API_KEY 環境変数、または引数で渡す
  num_written = score_news(conn, target_date=date(2026, 4, 11), api_key=None)
  score_regime(conn, target_date=date(2026, 4, 11), api_key=None)
  ```

  OpenAI キーが未設定の場合は例外が発生します。

---

## 重要ファイル・フラグ

- data/stop_requested.flag: run_monitoring / run_execution が監視している停止フラグ（存在すると安全に停止）
- data/kill.flag: KillSwitch（リスク閾値超過）による Execution 停止シグナル
- data/execution.pid: ExecutionEngine の PID を保存（SystemMonitor がプロセス存在チェックに利用）

---

## ディレクトリ構成

リポジトリは `src/kabusys` パッケージ配下に主要モジュールを持ちます（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス：環境変数読み込み・検証・デフォルト管理
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading 時は専用 DB）
  - tools/
    - paper_verification_report.py : Paper Trading 検証レポート生成 CLI
  - monitoring/
    - monitoring_db.py : SQLite を使った永続化（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py : CPU/メモリ/ディスク・データ鮮度・プロセス監視
    - trade_monitor.py : 注文滞留 / 約定異常検出
    - risk_monitor.py : ドローダウン・ポジション上限監視
    - kill_switch.py : kill.flag 制御
    - alert_manager.py : LINE 通知送信（クールダウン管理）
    - monitoring_engine.py : 複数モニタの束ね（テスト用 run_once / 実行用 run）
    - streamlit_dashboard.py : Streamlit ダッシュボード
  - execution/
    - order_manager.py : OrderManager（Order 作成 / 発注制御）
    - reconciler.py : 起動時のリコンシリエーション（注文照合・ポジション差分）
    - （その他：broker_factory, execution_engine, order_repository などが想定される）
  - portfolio/
    - portfolio_builder.py : 候補選定・重み計算（等金額・スコア重み）
    - position_sizing.py : 株数計算（risk_based / equal / score）
    - risk_adjustment.py : セクター制約・レジーム乗数
  - research/
    - factor_research.py : Momentum/Volatility/Value ファクター計算（DuckDB 使用）
    - feature_exploration.py : 将来リターン計算・IC / 統計サマリ
  - ai/
    - news_nlp.py : raw_news を LLM でスコアリングし ai_scores に書き込む
    - regime_detector.py : ETF MA200 乖離とマクロニュースを合成してレジーム判定
  - utils/
    - process_priority.py : プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 実践的な注意点・運用メモ

- Monitoring は監視ログを SQLite（settings.sqlite_path） に書き込みます。開発環境でも本番 DB パスを参照する設計の箇所がありますので注意してください（run_execution は KABUSYS_ENV=paper_trading の場合専用 DB を使用します）。
- OpenAI 呼び出しを行うモジュールは API エラー時にリトライやフォールバックを行いますが、API キーの設定は必須です（テスト時はモック化推奨）。
- .env の自動読み込みはプロジェクトルートを .git または pyproject.toml を基準に探索して行われます。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- process priority / cpu affinity の設定は psutil に依存し、権限やプラットフォームによっては効果が無い／警告が出ます。
- データ鮮度チェックや監視は UTC ベースで処理している箇所と JST を意図的に用いる箇所が混在します。時間窓に関する仕様は各モジュールの docstring を参照してください（news_nlp.calc_news_window など）。

---

## トラブルシューティング

- DuckDB / SQLite が開けない:
  - パス指定が正しいか、ファイルアクセス権限を確認してください。
  - streamlit で read-only 開く場合は URI に `?mode=ro` を付与しています。

- OpenAI 呼び出しエラー:
  - OPENAI_API_KEY が有効か確認。API のレート制限や一時的なネットワークエラーはリトライによりフォールバックしますが、キー未設定は例外になります。

- PID ファイル・stale PID:
  - SystemMonitor は `data/execution.pid` を参照してプロセス存在を確認します。PID ファイルの破損（非整数など）は自動で削除され、リスクログに記録されます。

---

README はここまでです。各モジュールの内部仕様やアルゴリズム（ポートフォリオ構築の詳細、ファクター定義、AI プロンプト設計など）はソースコード内の docstring とコメントを参照してください。必要ならば、個別モジュールごとの詳細ドキュメント（関数シグネチャ、使用例、入出力の型仕様など）も作成します。ご希望があれば教えてください。