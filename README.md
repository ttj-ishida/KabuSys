# KabuSys

日本株向け自動売買システムのコンポーネント群。戦略のポートフォリオ構築、ポジションサイジング、発注エンジン、監視（Monitoring）、ニュースの NLP によるスコアリング、検証ツールなどを含みます。

---

## プロジェクト概要

KabuSys は日本株自動売買のコアロジックと運用周辺機能（発注エンジン、監視、アラート、研究用ファクター計算、AI を用いたニュース集約評価など）をモジュール化して実装したコードベースです。  
主な設計方針：

- DuckDB / SQLite を用いたオンプレミスのデータ操作（prices_daily / raw_financials 等）
- Paper trading と本番環境の明確な分離（DB 分割）
- LLM（OpenAI）を用いたニュースセンチメントやレジーム判定（APIキー必須）
- フラグファイル・PID ファイルによるプロセス制御と監視連携
- フェイルセーフ重視（API失敗時は安全側にフォールバック）

---

## 機能一覧

- Execution（ExecutionEngine）
  - ブローカークライアント経由の発注、Order 管理、リコンシリエーション
  - Paper trading モード（MockBrokerClient）で本番 DB と分離して動作
  - リスク管理（ポジション上限、ドローダウン等）

- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、Execution プロセス存在、データ鮮度チェック
  - TradeMonitor：滞留注文チェック、約定価格異常チェック
  - RiskMonitor：ドローダウン／ポジション上限監視・アラート記録
  - KillSwitch：条件により停止フラグ（kill.flag）を書き込み、ExecutionEngine を停止させる
  - AlertManager：LINE Push による通知（トークン未設定時はログのみ）
  - Streamlit ダッシュボード（監視 DB を可視化）

- Portfolio（ポートフォリオ構築）
  - 候補選定、等重／スコア重み、セクター上限の適用、ポジションサイズ計算（単元丸め、aggregate cap）

- Research（研究用）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini）を用いたニュースのセンチメントスコアリング（ai_scores テーブルへ書込）
  - マクロニュース＋ETF MA200 を合成した市場レジーム判定（market_regime テーブルへ書込）

- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順

前提
- Python >= 3.10
- SQLite（標準ライブラリで可）
- DuckDB（Python パッケージ）
- pip が使える環境

推奨依存パッケージ（requirements の例）
- duckdb
- psutil
- requests
- openai
- streamlit

インストール例（仮想環境推奨）：
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

3. パッケージをプロジェクト直下で使う場合（開発用）
   - pip install -e .

環境変数 / .env
- プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数を上書きしません）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- 代表的な環境変数（.env に記載する例）
  - KABUSYS_ENV=development | paper_trading | live
  - JQUANTS_REFRESH_TOKEN=...
  - KABU_API_PASSWORD=...
  - OPENAI_API_KEY=...
  - LINE_CHANNEL_ACCESS_TOKEN=...
  - LINE_USER_ID=...
  - SQLITE_PATH=data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  - DUCKDB_PATH=data/kabusys.duckdb
  - LOG_LEVEL=INFO
  - PAPER_FILL_MODE=instant|partial|never|reject
  - MONITOR_POLL_INTERVAL=60  （監視ループの秒間隔）

データディレクトリ
- デフォルトで使用されるファイル群（プロジェクトルートの `data/` 下に置くことが想定）
  - data/monitoring.db（監視ログ SQLite、production で監視は本番 DB を使用）
  - data/paper_trading.db（paper_trading モード時の専用 DB）
  - data/kabusys.duckdb（DuckDB ファイル）
  - data/execution.pid（ExecutionEngine の PID）
  - data/stop_requested.flag（run_* スクリプトの停止フラグ検知）
  - data/kill.flag（KillSwitch が書き込む停止理由フラグ）

注意
- OpenAI を使う機能（ニュース NLP、レジーム判定）は `OPENAI_API_KEY` が必須です。
- Paper trading モードは `KABUSYS_ENV=paper_trading` とすることで本番 DB と完全分離した `PAPER_TRADING_SQLITE_PATH` を使用します。

---

## 使い方（主な実行方法）

パッケージが PYTHONPATH にある、あるいは `pip install -e .` している前提での実行例。

- ExecutionEngine を起動（本番／paper_trading は KABUSYS_ENV に依存）
  - KABUSYS_ENV=development python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行時に ExecutionEngine は data/execution.pid を書き、data/stop_requested.flag の有無を監視します。

- Monitoring を起動（監視ループ）
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL は秒単位。デフォルト 60 秒。0 以下や非整数はデフォルトにフォールバック。

- Streamlit ダッシュボード（監視 DB を可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - あるいはプロジェクトがパッケージ化されている場合、`--db` に DB パスを渡して起動可能。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 関連（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - `api_key` が None の場合は環境変数 OPENAI_API_KEY を参照
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（duckdb.connect(...)）を渡して使います。

停止方法
- run_execution / run_monitoring は `data/stop_requested.flag` の存在を検知して終了します。手動停止する場合はプロジェクトルートの `data/stop_requested.flag` を作成してください（内容は任意）。
- KillSwitch により `data/kill.flag` が書き込まれると ExecutionEngine 停止のトリガーになります（KillSwitch が条件を満たすと自動で書き込みます）。

ログ設定
- Settings.log_level（環境変数 LOG_LEVEL）でログレベルを制御します。実行スクリプト内で基本的に logging.basicConfig(level=logging.INFO) が設定されています。

---

## 主要設定（Settings API）

主な設定は `kabusys.config.Settings` で環境変数から取得されます。重要なプロパティ：

- env: KABUSYS_ENV（development / paper_trading / live）
- sqlite_path: SQLITE_PATH（monitoring DB）
- paper_sqlite_path: PAPER_TRADING_SQLITE_PATH
- duckdb_path: DUCKDB_PATH
- pid_file_path: PID_FILE_PATH
- kill_flag_path: KILL_FLAG_PATH
- paper_fill_mode: PAPER_FILL_MODE（instant / partial / never / reject）
- cpu_threshold_pct / memory_threshold_pct / disk_threshold_pct（監視閾値）
- line_channel_access_token / line_user_id（AlertManager 用）

Settings は自動で .env / .env.local を読み込みます（OS 環境変数は保護されます）。

---

## ディレクトリ構成

以下は主要なパッケージ階層（抜粋）：

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数・設定管理
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - run_monitoring.py              — SystemMonitor 起動スクリプト
    - tools/
      - paper_verification_report.py — Paper trading 検証レポート
    - portfolio/
      - portfolio_builder.py         — 候補選定・重み計算
      - position_sizing.py           — 株数決定・スケーリング
      - risk_adjustment.py           — セクター制限・レジーム乗数
    - research/
      - factor_research.py           — ファクター計算（momentum/value/vol）
      - feature_exploration.py       — 将来リターン・IC・統計
    - ai/
      - news_nlp.py                  — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py           — 市場レジーム判定（MA200 + LLM）
    - monitoring/
      - monitoring_db.py             — SQLite 監視 DB 層
      - system_monitor.py            — システム状態・データ鮮度監視
      - trade_monitor.py             — 注文滞留／約定異常監視
      - risk_monitor.py              — ドローダウン・ポジション監視
      - kill_switch.py               — kill.flag 制御ユーティリティ
      - alert_manager.py             — LINE 通知ラッパー
      - monitoring_engine.py         — Monitors を束ねる実行エンジン
      - streamlit_dashboard.py       — Streamlit ダッシュボード
    - execution/
      - order_manager.py
      - reconciler.py
      - order_repository.py
      - order_record.py
      - execution_engine.py
      - broker_factory.py
      - broker_api.py
    - monitoring/ (上記)
    - utils/
      - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
    - data/
      - （実行時に使用する SQLite / DuckDB / PID / flag ファイル等: data/*.db, data/*.flag）

---

## 運用上の注意・補足

- Paper trading: `KABUSYS_ENV=paper_trading` のときは本番用 SQLite を使用せず `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）を使用します。
- 自動読み込みされる .env はプロジェクトルート（.git または pyproject.toml がある階層）を基準に探索します。CI やテストで自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しはネットワークエラー・429・5xx に対してリトライやフォールバックが実装されていますが、API キー未設定時は ValueError を投げます（呼び出し側で取り扱ってください）。
- process_priority, cpu_affinity 関連の処理はプラットフォーム差分（Windows/Linux/macOS）を吸収する実装ですが、権限不足で設定できない場合は警告が出てスキップされます。
- monitoring_db には簡易的なマイグレーション処理があり、既存テーブルに新カラム（例: latency_ms / peak_value）がなければ追加されます。

---

必要であれば README にサンプル .env テンプレート、docker-compose による起動例、あるいは詳細な API 使用例（duckdb 接続の作り方、AI 関数の呼び出しサンプル）を追加できます。どの情報を優先して追記しますか？