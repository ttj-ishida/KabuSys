# KabuSys

日本株向けの自動売買システム（プロトタイプ実装）。  
シグナルの発生から発注、監視、検証、リサーチ（ファクター計算）や AI を使ったニュースセンチメント評価までを含むモジュール群を提供します。

以下はこのリポジトリの主要な説明・セットアップ・使い方のまとめです。

---

## プロジェクト概要

KabuSys は以下の機能を備えたモジュール式の自動売買システムです。

- 注文生成 → 発注 → 状態管理（OrderManager / OrderRepository / ExecutionEngine）
- 再起動時のリコンシリエーション（Reconciler）
- リスク管理（RiskManager / RiskMonitor）
- 監視（SystemMonitor / TradeMonitor / MonitoringEngine）
- 監視結果の永続化（SQLite）および簡易ダッシュボード（Streamlit）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算、セクター制約）
- リサーチ（ファクター計算、IC計算、将来リターン計算）
- AI（OpenAI）を利用したニュースセンチメント評価（news_nlp）／市場レジーム判定（regime_detector）
- Paper trading モード（Mock ブローカー、実運用 DB と分離）
- 付帯ツール（Paper Trading 検証レポート生成など）

設計方針としては「モジュールごとに責務を分離」「ルックアヘッドバイアス回避」「フェイルセーフ（API失敗時のフォールバック）」を重視しています。

---

## 主な機能一覧

- Execution
  - 注文の作成・送信・同期（OrderManager, OrderRepository, ExecutionEngine）
  - 再起動時の自動復旧（Reconciler）
  - Risk 管理（RiskManager）
- Monitoring
  - システムリソース監視（CPU/MEM/DISK）、プロセス生存チェック（SystemMonitor）
  - 注文滞留・約定異常検出（TradeMonitor）
  - ドローダウン・ポジション上限検出と kill.flag による停止シグナル（RiskMonitor / KillSwitch）
  - アラート送信（LINE Push via AlertManager）
  - Streamlit ダッシュボード（streamlit_dashboard.py）
- Portfolio
  - 候補選定（select_candidates）
  - 重み計算（等金額 / スコア加重）
  - ポジションサイズ計算（risk_based / equal / score）
  - セクターキャップ適用、レジーム乗数
- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC、統計サマリー
- AI
  - ニュースを LLM でスコアリングして ai_scores に書き込み（news_nlp）
  - マクロニュース + ETF の MA 乖離で市場レジームを判定（regime_detector）
- Tools
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## システム要件（推奨）

- Python 3.10+
  - typing の PEP 604（X | Y） を使用しているため 3.10 以上が必要です
- 必要パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite は標準で利用可能

※ requirements.txt はリポジトリに含まれていないので、上記を適宜インストールしてください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

---

## 環境変数 / .env

このプロジェクトは .env ファイル（または環境変数）から設定を読み込みます。読み込みの優先度は OS 環境 > .env.local > .env です。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

重要な環境変数（抜粋）:

- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必要）
- PAPER_FILL_MODE: paper trading の約定挙動（instant / partial / never / reject）デフォルト: instant
- PAPER_TRADING_SQLITE_PATH: Paper trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db） — 監視は環境に関わらず本番 sqlite_path を使います
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: 実行プロセス PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60 秒）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

簡単な .env の例:
```
KABUSYS_ENV=paper_trading
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
```

---

## セットアップ手順

1. リポジトリをクローンしワークディレクトリへ移動
2. Python 仮想環境を作成・有効化
3. 必要パッケージをインストール（上記参照）
4. .env をプロジェクトルートに作成（.env.example がある場合は参照）
5. DuckDB / SQLite の初期データやテーブルは多くのモジュールが起動時に自動で初期化します（init_monitoring_db 等）

例:
```
git clone <repo>
cd repo
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
# .env を作成
```

---

## 実行 / 使い方

以下は代表的な起動方法です。実行はパッケージのモジュールとして行います。

- 監視ループを起動（Monitoring）
```
python -m kabusys.run_monitoring
# MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能
export MONITOR_POLL_INTERVAL=30
```
- ExecutionEngine を起動（注文処理）
```
python -m kabusys.run_execution
# KABUSYS_ENV=paper_trading を指定すると MockBroker を使用し、
# data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH） に記録します
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```

- Paper Trading 検証レポートを生成
```
# 期間指定例
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を直接指定する場合
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

- Streamlit ダッシュボードを起動（監視 DB を読み取り専用で表示）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- AI スコアリング / レジーム判定（例、コードから直接呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=...)
  - regime_detector.score_regime(conn, target_date, api_key=...)
  - これらは OPENAI_API_KEY が必要（引数で渡すことも可）

注意点:
- Monitoring は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。環境に関わらず本番監視 DB を参照する設計になっています。
- ExecutionEngine は KABUSYS_ENV が paper_trading の場合、paper_sqlite_path を使って DB を分離します（本番 DB とは完全に分離）。

---

## プロセス優先度 / kill flag

- 起動スクリプト（run_monitoring/run_execution）は起動時に set_process_priority("high") を呼び出し、プロセス優先度を上げます（platform に依存、権限が無い場合はスキップされます）。
- kill.flag（Settings.kill_flag_path）は KillSwitch により書かれ、ExecutionEngine 側で読み取ることで外部からの安全停止シグナルとして機能します。起動時に KILL_FLAG_CLEAR_ON_START を 1 にしておくと自動でクリアできます（設定による）。

---

## Paper Trading（模擬取引）

- KABUSYS_ENV=paper_trading に設定すると、MockBrokerClient を使用して発注はモック実行され、Paper trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）に記録されます。
- PAPER_FILL_MODE によって約定挙動（instant/partial/never/reject）を変更できます。

---

## ログ / 監視出力

- logging.basicConfig(level=INFO) ベースで起動します。LOG_LEVEL を設定すれば Settings.log_level で制御されます（起動スクリプトで使用可）。
- MonitoringDB（SQLite）には system_status / trade_logs / positions / risk_logs / dashboard のテーブルが作成されます。
- MonitoringEngine は各モニタ結果に応じて AlertManager を通じて LINE へ通知できます（設定された channel token と user id が必要）。

---

## 主要ファイル・ディレクトリ構成

以下は src/kabusys 以下の主要な構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings
  - run_monitoring.py        — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — monitoring 用 SQLite 永続化層（init / MonitoringDB）
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度 / PID チェック
    - trade_monitor.py       — 注文滞留・約定異常検出
    - risk_monitor.py        — DD / position limit 監視（KillSwitch と連携）
    - kill_switch.py         — kill.flag 書込みロジック
    - alert_manager.py       — LINE Push 通知
    - monitoring_engine.py   — 各 Monitor を束ねる
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - ... (broker_factory, execution_engine, order_repository 等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py     — momentum/volatility/value 等
    - feature_exploration.py — forward returns / IC / summary
  - ai/
    - news_nlp.py            — ニュースセンチメント評価（OpenAI）
    - regime_detector.py     — レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

（上記は代表的なファイルの抜粋です。詳しい実装は各ファイル内の docstring / コメントを参照してください。）

---

## 開発・テスト時の注意点

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト中に自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- DuckDB のクエリは prices_daily / raw_financials / raw_news 等のテーブルに依存します。AI / research 機能を使うには事前にこれらのデータをロードしてください。
- OpenAI 呼び出しは外部 API に依存するため、テスト時は _call_openai_api をモックする設計になっています（コード内にコメントあり）。
- SQLite / DuckDB に対するマイグレーションは起動時に簡易対応されています（例: 列追加のチェックと ALTER）。

---

## FAQ / よくある操作

- 監視のポーリング間隔を変更したい
  - 環境変数 MONITOR_POLL_INTERVAL を秒数で設定（例: 30）

- Paper trading の DB を指定したい
  - env: PAPER_TRADING_SQLITE_PATH または --db オプションで指定

- Streamlit が DB をロックする？
  - streamlit_dashboard は読み取り専用 URI を使って開きます: sqlite3.connect(Path(...).resolve().as_uri() + "?mode=ro", uri=True)

---

この README はコードベースの主要点をまとめたものです。各機能の詳細やパラメータは該当モジュール（src/kabusys 以下の各ファイル）の docstring を参照してください。必要であれば、インストール用の requirements.txt やデプロイ手順、運用手順（systemd ユニットや監視構成）を別途作成できます。