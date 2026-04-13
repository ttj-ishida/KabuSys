# KabuSys

日本株自動売買システム（ライブラリ / 実行ツール群）のリポジトリです。本ドキュメントはこのコードベースの概観、主要機能、セットアップと実行方法、ディレクトリ構成をまとめた README です。

注意: この README は src/kabusys 配下のコードを基に作成しています。実運用の前に .env の設定やテストを必ず行ってください。

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤です。主な役割は以下の通りです。

- 注文管理・ブローカーインタフェースを通じた発注（Execution Engine）
- ポジション構築（候補選定、配分、株数決定、セクター制約など）
- モニタリング（システム状態、注文の滞留・約定異常、リスク監視）
- 研究用ファクター計算・特徴量解析（DuckDB を用いる）
- ニュース NLP を使った銘柄センチメント評価や市場レジーム判定（OpenAI）
- Paper Trading 用の分離された DB / 検証レポート生成

設計方針の一部:
- DuckDB / SQLite をデータストアに使用
- 実行環境（KABUSYS_ENV）により paper_trading と live を分離
- LLM（OpenAI）呼び出しはフェイルセーフ化（失敗時にフォールバック）
- 外部依存は最小化（標準ライブラリ + 必要なライブラリのみ）

## 主な機能一覧

- Execution
  - OrderManager: 注文生成・送信・状態遷移の管理
  - Reconciler: 起動時の注文・ポジション照合（自動復旧）
  - Broker クライアントの抽象化（paper_trading 時は MockBroker を利用）

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度監視
  - TradeMonitor: 滞留注文、約定価格の異常検出
  - RiskMonitor: ドローダウン / 保有銘柄上限の監視とアラート
  - KillSwitch: 条件に応じて停止フラグを記述（ExecutionEngine 停止用）
  - AlertManager: LINE へのプッシュ通知（クールダウン管理）
  - Streamlit ダッシュボード（監視情報の可視化）

- Portfolio（銘柄選定・重み計算・サイズ決定）
  - 等金額 / スコア加重 / リスクベースのポジションサイズ決定
  - セクター集中制限・レジーム乗数の適用

- Research
  - ファクター計算（Momentum, Volatility, Value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI
  - news_nlp: raw_news を OpenAI でセンチメント評価して ai_scores に書込
  - regime_detector: ETF (1321) の MA200 とマクロニュースを合成して市場レジーム判定

- ツール
  - Paper Trading 検証レポート生成スクリプト
  - Streamlit ベースの監視ダッシュボード

## セットアップ手順

前提:
- Python 3.10+（typing の | や型注釈を利用）
- Git / OS 権限等

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 最低限の例:
     pip install duckdb openai psutil requests streamlit
   - 実際のプロジェクトでは requirements.txt がある場合はそれを使用してください:
     pip install -r requirements.txt

4. .env を準備
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（代表例）
     - JQUANTS_REFRESH_TOKEN — J-Quants API 利用時
     - KABU_API_PASSWORD — kabuステーション API
   - 任意 / 操作に必要な環境変数
     - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
     - KABUSYS_ENV — 起動環境 (development | paper_trading | live)（デフォルト: development）
     - PAPER_FILL_MODE — paper_trading の約定挙動 ("instant" | "partial" | "never" | "reject")（デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知を使う場合

5. データディレクトリを作成
   - mkdir -p data

（実行スクリプトが起動時に DB テーブルを初期化するため、特別な初期化手順は不要です）

## 使い方

以下は主要な実行例です。Python モジュールとして実行できます。

- Execution Engine を起動（通常/本番）
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading（実際の口座を使わずにテスト）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading はデフォルトで data/paper_trading.db を使用し、本番 DB と分離されます。

- Monitoring（ポーリング監視）を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - 無効な値（0以下や非整数）はデフォルト 60 秒へフォールバックします。
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視ログを書き込みます。

- Streamlit ダッシュボード（監視可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開きます。MonitoringEngine を先に起動してデータを作成してください。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- AI / レジーム判定などの呼び出し（ライブラリ利用）
  - news_nlp（ニュース NLP スコアリング）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)  # api_key が None の場合は OPENAI_API_KEY を参照
  - regime_detector:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（duckdb.connect(...).connect() で得られる接続）を受け取ります。

- その他のユーティリティ
  - プロセス優先度設定: start-up スクリプト類は起動時に set_process_priority("high") を呼びます（psutil を使用）。権限不足などで失敗しても警告ログを出すだけです。

### 環境変数（主なもの）

- KABUSYS_ENV: 起動環境（development, paper_trading, live）デフォルト "development"
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB パス（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動 ("instant"|"partial"|"never"|"reject")
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
- OPENAI_API_KEY: OpenAI を使う機能の API キー
- JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD: 外部 API 用の認証情報
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE 通知）用

## ディレクトリ構成

（src/kabusys 配下の主要ファイル・モジュールの要約）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数読み込み / Settings
  - run_monitoring.py              — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート生成 CLI
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント取得（OpenAI）
    - regime_detector.py            — 市場レジーム判定（MA200 + マクロニュース + LLM）
  - monitoring/
    - __init__.py
    - monitoring_db.py              — SQLite 監視ログ永続化層（テーブル初期化含む）
    - system_monitor.py             — システム状態・データ鮮度監視
    - trade_monitor.py              — 注文滞留・約定異常監視
    - risk_monitor.py               — ドローダウン / ポジション上限監視
    - kill_switch.py                — 停止フラグファイル管理
    - alert_manager.py              — LINE への通知送信
    - monitoring_engine.py          — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py        — Streamlit ダッシュボード
  - portfolio/
    - __init__.py
    - portfolio_builder.py          — 候補選定・重み計算
    - position_sizing.py            — 発注株数/リスク制御
    - risk_adjustment.py            — セクターキャップ / レジーム乗数
  - research/
    - __init__.py
    - factor_research.py            — Momentum / Volatility / Value 等の計算
    - feature_exploration.py        — 将来リターン, IC, 統計サマリ等
  - execution/
    - order_manager.py              — 注文状態マシン外向き API
    - reconciler.py                 — 起動時の自動リコンシリエーション
    - (その他 broker / engine / order_repository 等の実装が存在)
  - utils/
    - __init__.py
    - process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ

> 注: 一部のモジュール（例えば data/ 以下や execution 内の broker 実装等）は本 README の元となる抜粋に含まれていない可能性があります。実行時には該当モジュールが揃っているか確認してください。

## 運用上のポイント / 注意事項

- Paper Trading と Live は DB を分離して運用すること（Settings により paper_trading は data/paper_trading.db を使用）。
- Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path（監視 DB）を使用します。監視ログは本番 DB に対して行われます。
- OpenAI 等の外部 API キーは環境変数で管理してください。API 呼び出しはリトライ・フォールバック実装がありますが、API 制限やコストには注意してください。
- process priority / CPU affinity の設定はプラットフォーム依存です。必要な権限がない場合はログに警告が出てスキップされます。
- kill.flag を使った強制停止機構があります（KillSwitch）。ExecutionEngine 起動時に kill_flag をクリアする動作は Settings.kill_flag_clear_on_start により制御できます。

## 開発・テスト

- unit test や CI の設定は含めていませんが、各モジュールは可能な限り副作用を排除した純粋関数を採用しており、ユニットテストが書きやすく設計されています（例: portfolio の関数群、research の計算関数など）。
- OpenAI や外部 API 呼び出し部分はテスト時にモック可能（モジュール内の _call_openai_api 等を patch する設計）。

---

さらに詳しい設計資料（PortfolioConstruction.md / StrategyModel.md 等）や運用手順書がある場合は、それらを参照してください。追加で README に入れたい具体的なコマンドや運用フローがあれば教えてください。