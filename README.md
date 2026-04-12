KabuSys — README
=================

概要
----
KabuSys は日本株自動売買（アルゴリズムトレーディング）を想定した小規模なフレームワークです。本リポジトリは以下の責務を持つモジュール群を含みます。

- 注文作成・送信・状態管理（Execution）
- 監視（Monitoring）：プロセス死活、データ鮮度、滞留注文、約定異常、ドローダウンなど
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 研究用ファクター計算・特徴量解析（Research）
- ニュースの NLP によるセンチメント評価・市場レジーム判定（AI）
- 各種 CLI / ツール（Paper Trading 検証レポート、Streamlit ダッシュボード 等）

主な設計方針
- DB は SQLite（監視用）と DuckDB（時系列/調査用）を利用
- Paper Trading と本番は DB を分離（安全な検証が可能）
- .env ファイルを読み込み、環境変数で挙動を制御
- LLM（OpenAI）を使う機能は APIキーで有効化（失敗時はフェイルセーフ動作）

機能一覧
--------
- Execution
  - OrderManager: 注文生成・送信・同期ロジック
  - Reconciler: 再起動時の注文・ポジション同期（ブローカー照合）
  - BrokerClientFactory による実運用 / モック切替（KABUSYS_ENV=paper_trading）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス生存・データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常検知
  - RiskMonitor: ドローダウン・ポジション数制限監視
  - KillSwitch: フラグファイルで ExecutionEngine に停止シグナルを送信
  - AlertManager: LINE Push による通知（クールダウンあり）
  - Streamlit ダッシュボード（簡易監視UI）
- Portfolio
  - 候補選定（スコア順）、等金額 / スコア重み配分、リスク調整（セクター制限・レジーム乗数）、ポジションサイズ計算（単元・資金制約考慮）
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB 経由）
  - 将来リターン計算、IC（Spearman）計算、ファクターサマリ
- AI
  - news_nlp: ニュース記事を OpenAI に送り銘柄別センチメントを ai_scores テーブルへ書込
  - regime_detector: ETF（1321）MA乖離 + マクロニュースセンチメントで日次レジーム判定
- Tools
  - paper_verification_report: Paper Trading DB から稼働率・成功率・レイテンシ等の検証レポートを生成

セットアップ手順
----------------
前提
- Python 3.10+（型ヒントや match ではなくとも、提示コードは 3.10+ を想定）
- 仮想環境の利用を推奨（venv / poetry 等）

例（venv）
1. リポジトリをクローンし作業ディレクトリへ移動
   - git clone ...
   - cd <repo>

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（代表的な依存）
   - pip install duckdb psutil requests openai streamlit

   ※ プロジェクトに requirements.txt/pyproject.toml がある場合はそれに従ってください。

4. 環境変数設定
   - プロジェクトルートに .env ファイルを置くと自動で読み込まれます（.env.local があれば優先して上書き）。
   - 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用）。

代表的な .env（例）
- KABUSYS_ENV=development|paper_trading|live
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- OPENAI_API_KEY=sk-...
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
- CPU_THRESHOLD_PCT=90.0
- MEMORY_THRESHOLD_PCT=85.0
- DISK_THRESHOLD_PCT=90.0

初期 DB 作成
- 多くの起動スクリプト（run_monitoring / run_execution）は起動時に monitoring テーブル群を自動作成します（init_monitoring_db が冪等に実行されます）。

使い方（主要コマンド・モジュール）
------------------------------

1) 実行エンジン（ExecutionEngine）起動
- 用途: 実際の発注処理を行うメインプロセス
- 本番 / Paper Trading の切替:
  - 本番: KABUSYS_ENV=live
  - Paper: KABUSYS_ENV=paper_trading（MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に記録）
- 起動:
  - python -m kabusys.run_execution
  - 例（Paper）: KABUSYS_ENV=paper_trading python -m kabusys.run_execution

2) 監視ループ（Monitoring）起動
- 用途: 定期的に System/Trade/Risk Monitor を実行し、DBへログ・アラート出力・KillSwitch 評価
- MONITOR_POLL_INTERVAL でポーリング間隔を上書き（秒、デフォルト 60）
- 起動:
  - python -m kabusys.run_monitoring
  - 環境変数例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

3) Streamlit ダッシュボード（監視 UI）
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 監視用 SQLite を読み取り専用で開きます（既存 DB が必要）

4) Paper Trading 検証レポート
- 用途: paper_trading DB から運用検証用レポート（稼働率・成功率・レイテンシ等）を出力
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

5) AI 関連（ニュースセンチメント / レジーム判定）
- OpenAI API キー（OPENAI_API_KEY）が必要
- 呼び出しは programmatic（score_news / score_regime）で使用
- 失敗時は安全にフォールバック（スコア = 0 等）する設計

主要設定（Settings）
-------------------
設定は kabusys.config.Settings 経由で環境変数から取得されます。主なキー:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能で必要)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (AlertManager)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト data/paper_trading.db)
- PAPER_FILL_MODE (instant | partial | never | reject)
- PID_FILE_PATH / KILL_FLAG_PATH
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL

注意点 / 運用メモ
----------------
- Paper Trading は本番 DB と明確に分離されます（settings.is_paper による切替）。
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計（run_monitoring 内の挙動）。
- MONITOR_POLL_INTERVAL が 0 以下や不正な値の場合はデフォルト 60 秒にフォールバックします。
- KillSwitch は設定された kill.flag を書き込み、ExecutionEngine 側で存在を検知して停止させる想定です。kill.flag が既存のときは上書きしません（冪等）。
- .env の読み込み順: OS 環境変数 > .env.local > .env。プロジェクトルートは .git または pyproject.toml を探索して決定します。
- 自動 .env ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

ディレクトリ構成
----------------
（src/kabusys 配下の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / Settings
  - run_monitoring.py                — SystemMonitor のポーリングループ起動
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py   — Paper Trading レポート生成
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュース NLP（OpenAI 連携）
    - regime_detector.py             — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - __init__.py
    - monitoring_db.py               — SQLite 永続化層（テーブル作成 / CRUD ユーティリティ）
    - system_monitor.py              — システム / データ鮮度監視
    - trade_monitor.py               — 滞留注文 / 約定異常監視
    - risk_monitor.py                — ドローダウン・ポジション監視
    - kill_switch.py                 — kill.flag 書き込みロジック
    - alert_manager.py               — LINE push 通知（クールダウン）
    - monitoring_engine.py           — 各 Monitor をまとめる実行ループ
    - streamlit_dashboard.py         — Streamlit 監視ダッシュボード
  - execution/
    - reconciler.py                  — 起動時リコンシリエーション（同期）
    - order_manager.py               — 注文ステートマシン外向け API
    - (その他 broker / order_repository 等が想定)
  - portfolio/
    - __init__.py
    - portfolio_builder.py           — 候補選定・重み付け
    - position_sizing.py             — 株数算出（単元・リスク・キャッシュ制約）
    - risk_adjustment.py             — セクターキャップ・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py             — Momentum / Volatility / Value 等
    - feature_exploration.py         — 将来リターン / IC / summary
  - utils/
    - __init__.py
    - process_priority.py            — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/ (想定されるデータディレクトリ)
    - monitoring.db (SQLite)
    - paper_trading.db (SQLite)
    - kabusys.duckdb (DuckDB)

開発者向けヒント
-----------------
- process_priority.set_process_priority("high") により起動直後に優先度を上げますが、権限不足で失敗する場合は警告ログになります。
- DuckDB 接続を渡して純粋関数群（research / ai）が SQL と Python を併用して分析を行います。テスト用には小さな DuckDB を作って実験できます。
- OpenAI や外部 API を使う関数はテスト時に内部の API 呼び出し関数を patch して置き換えるよう設計されています（例: _call_openai_api を patch）。

ライセンス / 責任
-----------------
（この README にライセンス条項は含めていません。必要に応じて LICENSE ファイルを追加してください。）

問い合わせ
----------
不明点や改善提案があれば Issue を立ててください。

以上。