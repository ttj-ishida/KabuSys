# KabuSys

KabuSys は日本株向けの自動売買 / 研究 / 監視を目的とした内部ライブラリ群です。  
このリポジトリには、取引エンジン、監視・アラート、ポートフォリオ構築、ファクター計算、ニュース NLP（OpenAI）連携などの機能が含まれます。

以下はコードベースから読み取れる主要情報をまとめた README です。

---

## プロジェクト概要

- 目的: 日本株の自動売買システム（KabuSys）のコアロジック群および運用支援ツールを提供する。
- 主なコンポーネント:
  - ExecutionEngine（発注・リスク管理・リコンシリエーション）
  - Monitoring（プロセス・注文・リスク監視、LINE 通知、kill flag）
  - Portfolio（銘柄選定・重み計算・ポジションサイズ算出）
  - Research（ファクター計算・将来リターン・IC 計算）
  - AI（ニュース NLP による銘柄センチメント、レジーム判定）
  - Tools（Paper Trading 検証レポート、Streamlit ダッシュボード起動スクリプト）

- データ永続化: SQLite（監視 / paper trading 用）と DuckDB（時系列価格・財務データ等の分析用）を併用。

---

## 機能一覧

- Execution
  - ブローカクライアント抽象化（実ブローカ / モックの切替）
  - OrderManager: 注文作成・重複排除・状態同期
  - Reconciler: 再起動時の注文・ポジション同期
  - RiskManager: 発注制限・利用率等の管理（設定に応じた判定）

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク、プロセス監視、データ鮮度チェック
  - TradeMonitor: 滞留注文検出、約定異常価格検出
  - RiskMonitor: ドローダウン/ポジション数監視（ダッシュボード更新・risk_logs 登録）
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - AlertManager: LINE Messaging API でのプッシュ通知（クールダウン管理）
  - MonitoringEngine: 上記を統合してポーリング実行
  - Streamlit ダッシュボード: 監視 DB を読み取り Web UI 表示

- Portfolio
  - 候補選定（スコア順ソート）
  - 重み計算（等分 / スコア加重）
  - セクターキャップ適用（既存保有を考慮）
  - ポジションサイズ計算（リスクベース / 等配分 / スコア配分、単元株丸め、aggregate cap）

- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB SQL ベース）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計要約

- AI
  - news_nlp.score_news: OpenAI を利用したニュースセンチメント計算 → ai_scores テーブルへ書込
  - regime_detector.score_regime: マクロニュース + ETF ma200 を合成して市場レジーム（bull/neutral/bear）判定・登録

- Tools
  - paper_verification_report: Paper Trading DB から検証レポート生成（稼働率・成功率・レイテンシ等）
  - streamlit_dashboard.py: 監視データの可視化（Streamlit）

---

## セットアップ手順

以下は開発 / 運用環境の一般的なセットアップ手順です（環境に応じて適宜調整してください）。

1. Python 環境
   - Python 3.10+ を推奨
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 代表的な依存:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit (ダッシュボード利用時)
   - 例:
     - pip install duckdb psutil openai requests streamlit

   （プロジェクトに requirements.txt がある場合はそれを使用してください。）

3. データディレクトリ作成
   - デフォルト DB / フラグ用に `data/` を作成:
     - mkdir -p data

4. 環境変数 / .env
   - 必須（運用モードにより変わる）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 推奨 / よく使う:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - OPENAI_API_KEY (AI 機能利用時)
     - SQLITE_PATH （監視 DB、デフォルト: data/monitoring.db）
     - DUCKDB_PATH （分析 DB、デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH（paper_trading モード用 DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE (instant | partial | never | reject) — paper trading の約定モード
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知利用時）
     - LOG_LEVEL（INFO など）
     - MONITOR_POLL_INTERVAL（監視のポーリング間隔秒 数、デフォルト 60）
   - .env の自動読み込み:
     - プロジェクトルートに `.env` / `.env.local` があれば自動で読み込まれます（ただし OS 環境変数が優先）。
     - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

5. DB 初期化
   - Monitoring 用 DB はスクリプト実行時に init_monitoring_db() によりテーブル作成（冪等）されます。
   - DuckDB 側は必要なテーブル（prices_daily / raw_financials / raw_news 等）を別途用意してください。

---

## 使い方

### 実行コンポーネント

- 監視ループ（SystemMonitor 単体スクリプト）
  - 実行:
    - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、1 以上、デフォルト 60）
  - 挙動:
    - Monitoring は KABUSYS_ENV の値にかかわらず本番 sqlite_path を使用して監視ログを書きます。
    - data/stop_requested.flag の存在でループを抜けて終了します。

- 実行エンジン（ExecutionEngine 起動スクリプト）
  - 実行:
    - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合はモックブローカー（MockBrokerClient）を使用し、専用の paper_trading DB（PAPER_TRADING_SQLITE_PATH）へ記録して本番 DB と分離されます。
    - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します。
    - 実行中は `data/execution.pid` を作成します。stale PID の検出・削除機能あり。

### ツール

- Paper Trading 検証レポート
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB 指定:
      - --db PATH（省略時は PAPER_TRADING_SQLITE_PATH 環境変数 → data/paper_trading.db）
  - 出力: 稼働率・注文成功率・送信率・P95 レイテンシ等を標準出力に表示

- Streamlit 監視ダッシュボード
  - 実行:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明: 監視 DB を読み取りダッシュボードを表示。監視エンジン起動後にアクセスすること。

### ライブラリ関数の利用例（コード内 API）

- AI スコアリング:
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key=...)
- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key=...)
- Research（ファクター等）:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
- Portfolio（重み・サイズ計算）:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes

---

## 主要ファイル / ディレクトリ構成

以下は src/kabusys 以下の主要モジュールと役割の概略です。

- src/kabusys/
  - __init__.py — パッケージ情報
  - config.py — 環境変数 / 設定の読み込み・検証ロジック（.env 自動ロードの挙動を含む）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
- src/kabusys/monitoring/
  - monitoring_db.py — SQLite に対する永続化レイヤ（テーブル初期化・CRUD）
  - system_monitor.py — システムリソース・データ鮮度・プロセス監視
  - trade_monitor.py — 注文滞留・約定異常のチェック
  - risk_monitor.py — ドローダウン / ポジション上限等の監視
  - kill_switch.py — kill.flag 書き込みロジック（Execution 停止トリガ）
  - alert_manager.py — LINE 通知ラッパー（クールダウン管理）
  - monitoring_engine.py — 上記を束ねるポーリングエンジン
  - streamlit_dashboard.py — Streamlit UI（監視 DB 読み取り）
- src/kabusys/execution/
  - order_manager.py — 発注 API を用いた注文作成 / 管理
  - reconciler.py — 起動時の注文/ポジション照合
  - （他に broker_factory, execution_engine, order_repository, risk_manager などが存在する想定）
- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数決定・丸め・aggregate cap 処理
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- src/kabusys/research/
  - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリ等
- src/kabusys/ai/
  - news_nlp.py — OpenAI を使ったニュースセンチメント集約 / ai_scores 書込処理
  - regime_detector.py — マクロ記事 + ETF MA でレジーム判定、market_regime 登録
- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- src/kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

その他、DuckDB / SQLite のスキーマやツールの細かい仕様は各モジュールの docstring を参照してください。

---

## 運用上の注意 / ヒント

- 環境分離:
  - paper_trading モードでは paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離するよう設計されています。運用時は環境変数 KABUSYS_ENV を適切に設定してください。
- .env の自動ロード:
  - config.py はプロジェクトルート（.git または pyproject.toml を探索）を基準に .env / .env.local を自動ロードします。
  - 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時等）。
- フラグ / PID ファイル:
  - data/stop_requested.flag や data/kill.flag、data/execution.pid 等を利用してプロセス制御を行います。運用時にはこれらのファイル管理に注意してください。
- OpenAI API:
  - AI 機能は OPENAI_API_KEY が必要です。API 呼び出しはレート制限やネットワーク障害を考慮してリトライやフェイルセーフが実装されていますが、コスト・レート制限に注意してください。
- 権限:
  - process priority の設定や cpu_affinity 設定は OS 権限に依存します。アクセス拒否が発生した場合は警告を出してスキップします。

---

必要であれば、この README に以下の追加情報を追記できます:
- requirements.txt の推奨内容
- .env.example の完全なサンプル
- 詳しい API リファレンス（各関数の引数・戻り値一覧）
- 運用 runbook（起動順序・監視手順・トラブルシュート）

ご希望があれば追記します。