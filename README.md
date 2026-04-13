# KabuSys

KabuSys は日本株向けの自動売買システム（プロトタイプ）です。本リポジトリは、発注・リスク管理・監視・バックテスト／リサーチ用ユーティリティや、ニュース NLP を用いた AI 推論などを含むモジュール群で構成されています。

主な設計方針：
- プロダクション志向の安全性（リコンシリエーション、フェイルセーフ、冪等性）を重視
- DuckDB / SQLite をデータ基盤に利用（pricing / financials / monitoring）
- Paper Trading（検証用 DB 分離）を明確にサポート
- 外部 API（kabuステーション、J-Quants、OpenAI）との連携を想定

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 環境変数（主な設定）
- 使い方（起動コマンド例）
- ディレクトリ構成（概要）

---

プロジェクト概要
- 自動売買エンジン（ExecutionEngine）とその周辺コンポーネント（OrderManager / RiskManager / Reconciler）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / AlertManager）
- ポートフォリオ構築ユーティリティ（銘柄選定、重み計算、ポジションサイズ計算、セクター制限）
- 研究用モジュール（ファクター計算、将来リターン、IC 計算等）
- AI コンポーネント（ニュース NLP によるセンチメントスコアリング、レジーム判定）
- 運用支援ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード）

---

機能一覧（抜粋）
- Execution:
  - ブローカー抽象化（実ブローカー / MockBroker 切替：KABUSYS_ENV=paper_trading）
  - 注文の2相永続化・エラーハンドリング・重複防止
  - 起動時リコンシリエーション（OrderSent の同期、ポジション差分検出）
- Monitoring:
  - システム資源監視（CPU / メモリ / ディスク）
  - データ鮮度チェック（DuckDB の prices_daily 最終日検査）
  - 注文滞留チェック、約定異常価格検出
  - ドローダウン・ポジション上限監視と kill.flag による強制停止シグナル
  - LINE 経由のプッシュ通知（AlertManager）
  - Streamlit ダッシュボード（read-only）
- Portfolio:
  - 候補選定、等金額・スコア重み配分、リスクベースの株数計算
  - セクター集中制限、レジーム乗数
- Research:
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を直接参照）
  - 特徴量の統計サマリ、IC (Spearman) 計算
- AI:
  - ニュースの銘柄別センチメントスコア化（OpenAI を用いた LLM 呼び出し）
  - マクロニュース + ETF MA200 を用いた市場レジーム判定
- Tools:
  - paper_verification_report: Paper Trading DB の検証レポート生成
  - streamlit_dashboard: 監視 DB の可視化

---

セットアップ手順（開発 / 実行環境準備）
1. Python（3.10 以上推奨）を準備
2. リポジトリをクローン
   - git clone <repo-url>
3. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
4. 必要パッケージをインストール（pip で直接指定例）
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）
5. 環境変数を設定
   - プロジェクトルートに .env / .env.local を置くと自動読み込みされます（既存 OS 環境変数は保護）
   - 重要な変数例（下記「環境変数」節参照）
6. データ準備
   - monitoring SQLite DB は起動時に自動で初期化されます（schema 作成・マイグレーション）
   - DuckDB（data/kabusys.duckdb）はファクター計算や prices_daily 等のテーブルが必要（外部 ETL で投入）
   - Paper Trading を利用する場合、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用
7. 実行権限やポート設定等が OS により必要な場合があります（psutil による優先度設定など）

---

主な環境変数（要約）
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live (default: development)
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL (default: INFO)
- API トークン / ブローカー
  - JQUANTS_REFRESH_TOKEN（必須: J-Quants 用）
  - KABU_API_PASSWORD（必須: kabuステーション API 用）
  - OPENAI_API_KEY（AI モジュールで必要）
- DB パス
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (monitoring 用, default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper trading 用, default: data/paper_trading.db)
- Paper Trading モード
  - PAPER_FILL_MODE: instant | partial | never | reject (default: instant)
- 監視 / 実行制御
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START: "1" で実行時に kill.flag をクリア
  - MONITOR_POLL_INTERVAL: 監視ループ間隔（秒, default: 60）
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- 自動 .env ロードを抑止したい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例 (.env の抜粋)
    KABUSYS_ENV=development
    OPENAI_API_KEY=sk-...
    KABU_API_PASSWORD=...
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db
    PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

---

使い方（主要コマンド例）

- ExecutionEngine（注文エンジン）を起動
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使用され、data/paper_trading.db に書き込まれます。

- Monitoring（ポーリング監視）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（例: MONITOR_POLL_INTERVAL=30）

- Streamlit ダッシュボード（監視 DB を可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート（コマンドライン）
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11
  - --db を省略すると環境変数 PAPER_TRADING_SQLITE_PATH またはデフォルトを使用

- AI スコア / レジーム判定（プログラム呼び出し例）
  - Python REPL / スクリプトから呼び出し:
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026,4,10), api_key="sk-...")

    同様に kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

注記:
- Monitoring の初回起動では monitoring DB（SQLite）のテーブルが自動作成されます。
- DuckDB のデータ（prices_daily, raw_financials, raw_news 等）は外部 ETL（スクレイピング / CSV インポート 等）で整備する必要があります。

---

ディレクトリ構成（主要ファイルの説明）
- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動読み込み）
  - run_execution.py — ExecutionEngine 起動スクリプト（プロセス優先度設定・DB 接続・組立て）
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - execution/
    - order_manager.py — 注文管理の外向き API（create/send/sync）
    - reconciler.py — 起動時の再同期ロジック
    - (その他 execution 関連モジュールは本リポジトリの一部)
  - monitoring/
    - monitoring_db.py — SQLite を用いた監視 DB の読み書き層（schema 初期化含む）
    - system_monitor.py — システム監視（CPU/メモリ/ディスク/プロセス/データ鮮度）
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 書き込み（ExecutionEngine 停止シグナル）
    - alert_manager.py — LINE によるプッシュ通知（クールダウン付き）
    - monitoring_engine.py — 各 Monitor を束ねてポーリングするエンジン
    - streamlit_dashboard.py — Streamlit による監視ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数算出・制限・丸め処理
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — raw_news を LLM で処理して ai_scores に書き込む
    - regime_detector.py — ETF MA + マクロニュースでレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - monitoring.db / paper_trading.db / kabusys.duckdb — （data ディレクトリに配置する想定の DB）

（上記に示したファイルは代表的なもので、実際のコードベースにはさらに詳細なモジュールが含まれます）

---

運用上の注意
- Paper Trading モードは実ブローカーとは独立しており、DB も分離されます（実運用での誤発注を防ぐ設計）。
- OpenAI 等の API キーは外部に漏れないよう管理してください。
- process priority / cpu affinity の設定は OS 権限に依存します。権限不足時は警告をログに出してスキップします。
- DuckDB 上のデータ（prices_daily 等）は結果の信頼性に直結します。正確で十分な過去データを準備してください。
- kill.flag による強制停止は冪等に実装されていますが、運用ポリシーを定めた上で使用してください。

---

開発に貢献するには
- まずはローカルで unit テスト / flake8 等を実行し、コードスタイルを統一してください（テストフレームワークはプロジェクトに依存します）。
- 重大な変更は設計意図（冪等性、フェイルオープンなど）を意識した PR をお願いします。

---

以上。セットアップや実行で不明点があれば、実行環境や設定ファイル、発生しているエラーのログを添えて質問してください。