# KabuSys

KabuSys は日本株向けの自動売買・研究・監視フレームワークです。  
このリポジトリには発注実行・監視エンジン、ポートフォリオ構築ロジック、ファクター計算、LLM を利用したニュース NLP / レジーム判定、検証ツールなどが含まれます。

以下はこのコードベースの概要、機能、セットアップおよび使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

- 自動売買 ExecutionEngine（発注管理、リスク管理、リコンシリエーション）を含む実運用コンポーネント
- 監視（System / Trade / Risk）コンポーネントと永続化（SQLite）・アラート（LINE）
- ポートフォリオ構築（候補選択・重み付け・ポジションサイズ計算・セクター制限・レジーム補正）
- 研究用モジュール（DuckDB を用いたファクター計算、特徴量分析）
- AI モジュール（OpenAI を使ったニュースセンチメント評価・市場レジーム判定）
- 運用支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

設計方針の一部：
- DuckDB を分析用 DB、SQLite を運用ログ/監視用 DB に利用
- 環境変数 / .env による設定管理（自動ロード機能あり）
- 本番 / PaperTrading を明確に分離（paper_trading の場合は専用 SQLite を使用）
- OpenAI API 呼び出しはリトライ・バックオフを備えフォールバックに優しい実装

---

## 主な機能一覧

- Execution
  - 注文作成、送信、ブローカーとの同期（Reconciler）
  - リスク管理（Position 上限、ドローダウン等）
  - Paper Trading モード（MockBroker を利用し専用 DB に記録）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス状態、データ鮮度監視
  - TradeMonitor：滞留注文、約定価格異常検出
  - RiskMonitor：ドローダウン、ポジション上限監視、ダッシュボード更新
  - MonitoringEngine：上記を束ねてポーリング、KillSwitch による Execution 停止フラグ出力
  - AlertManager：LINE を使ったプッシュ通知（クールダウン管理）
  - Streamlit ダッシュボード（監視 DB を可視化）
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC 計算、統計サマリー
- AI
  - news_nlp: OpenAI（gpt-4o-mini）を使った銘柄単位ニュースセンチメント -> ai_scores テーブル
  - regime_detector: MA200 とマクロニュースセンチメントを合成して market_regime を決定
- Tools
  - paper_verification_report: Paper Trading DB から稼働率・成功率・レイテンシ等の検証レポートを生成

---

## セットアップ手順

前提：
- Python 3.9+（コードは typing の新記法等を使用）
- DuckDB, SQLite が使える環境
- ネットワーク接続（LINE / OpenAI を使う場合）

1. リポジトリをクローン
   - git clone <リポジトリURL>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil requests streamlit openai
   - （実行環境やテストに応じて追加パッケージが必要になる場合があります）

4. data ディレクトリ（デフォルト DB / PID / フラグファイル用）を作成
   - mkdir -p data

5. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須設定（運用に必要な例）:
     - JQUANTS_REFRESH_TOKEN (必要に応じて)
     - KABU_API_PASSWORD — kabu ステーション API のパスワード
     - OPENAI_API_KEY — OpenAI を使う場合必須
   - 主なオプション設定（デフォルト値は括弧内）:
     - KABUSYS_ENV (development | paper_trading | live) — (development)
     - LOG_LEVEL (INFO) — ログレベル
     - DUCKDB_PATH (data/kabusys.duckdb)
     - SQLITE_PATH (data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
     - PAPER_FILL_MODE (instant | partial | never | reject) — paper_trading の約定挙動（instant）
     - PID_FILE_PATH (data/execution.pid)
     - KILL_FLAG_PATH (data/kill.flag)
     - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒, default 60）

6. 初回実行
   - 監視・実行スクリプトは起動時に必要な DB テーブルを作成（冪等）します。

---

## 使い方（主要な実行例）

- 監視ループ起動（SystemMonitor のデーモン）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可（デフォルト 60 秒）。
  - python -m kabusys.run_monitoring
  - 実行内容：プロセス優先度を high に設定 → monitoring DB (設定された sqlite_path) に接続 → SystemMonitor のポーリング

- 実行エンジン起動（ExecutionEngine）
  - KABUSYS_ENV により実行挙動が変わる:
    - paper_trading: MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録。実運用 DB と分離。
    - live: 本番ブローカーを想定。
  - python -m kabusys.run_execution
  - 実行内容：プロセス優先度を high に設定 → broker クライアント作成 → 各コンポーネントを組み立て ExecutionEngine.run_session()

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を使うか環境変数 PAPER_TRADING_SQLITE_PATH を指定

- Streamlit ダッシュボード（監視 DB を可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - readonly モードで SQLite を開きます（起動前に MonitoringEngine で DB が作成されている必要あり）

- AI 関連
  - news_nlp.score_news / regime_detector.score_regime は OpenAI API キー (OPENAI_API_KEY) を必要とします。関数は DuckDB 接続を受け取って操作します（コード内呼び出し／スケジュール実行向け）。
  - これらは自動で再試行・バックオフを行いますが、API キーは必須です。

- Kill Switch
  - KillSwitch は監視結果に基づき `data/kill.flag` を書き込みます。ExecutionEngine はこのフラグを見て停止する設計になっています（起動時にクリーンアップ設定がある場合は削除可）。

---

## 環境変数（主な一覧・説明）

- 必須（実行内容による）:
  - KABU_API_PASSWORD — kabu ステーション API パスワード
  - JQUANTS_REFRESH_TOKEN — J-Quants 等を利用する機能で必要
  - OPENAI_API_KEY — news_nlp / regime_detector を使う場合

- 主要オプション:
  - KABUSYS_ENV: development | paper_trading | live (default: development)
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
  - DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（monitoring）パス（default: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（default: data/paper_trading.db）
  - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定モード）
  - PID_FILE_PATH: ExecutionEngine が PID を書き込むファイル（default: data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（default: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: "1" にすると ExecutionEngine 起動時に kill.flag を自動クリア
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60、0 以下は無効）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" で .env 自動読み込みを無効化

.env に記載する例（簡易）
- KABU_API_PASSWORD=secret
- OPENAI_API_KEY=sk-...
- KABUSYS_ENV=paper_trading
- PAPER_FILL_MODE=instant
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db

注意: .env パーサは export KEY=val, コメント、シングル/ダブルクォート、エスケープ等に対応しています。

---

## トラブルシューティングのヒント

- PID/kill flag
  - PID ファイルが残っていると SystemMonitor は stale PID を検出して削除することがあります。運用開始時に kill.flag を残さない場合は KILL_FLAG_CLEAR_ON_START を確認してください。
- OpenAI 呼び出しが失敗する場合
  - OPENAI_API_KEY を設定し、ネットワーク・料金上限を確認してください。リトライはある程度自動で行われますが、API のレート制限やアカウント制約に依存します。
- DuckDB / SQLite ファイル
  - デフォルトパスは data 以下です。適切なファイル権限を設定してください（読み書き権限）。
- streamlit が DB を開けない場合
  - MonitoringEngine を先に起動して監視 DB を作成しておくか、手動で monitoring.db を作成してください。streamlit は read-only uri モードで接続します。

---

## 主要モジュール一覧（短い説明）

- kabusys.config: 環境変数と .env ロード、Settings クラス
- kabusys.execution: BrokerFactory, ExecutionEngine, OrderManager, Reconciler, OrderRepository（発注・同期関連）
- kabusys.monitoring: SystemMonitor / TradeMonitor / RiskMonitor / MonitoringDB / MonitoringEngine / AlertManager / KillSwitch / Streamlit ダッシュボード
- kabusys.portfolio: 銘柄選定・重み付け・ポジションサイズ計算・リスク調整
- kabusys.research: ファクター計算、特徴量探索（IC 等）
- kabusys.ai: news_nlp（ニュース NLP）、regime_detector（市場レジーム判定）
- kabusys.tools: paper_verification_report（Paper Trading の検証レポート）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- run_monitoring.py                — SystemMonitor ポーリング起動スクリプト
- run_execution.py                 — ExecutionEngine 起動スクリプト
- tools/
  - __init__.py
  - paper_verification_report.py    — Paper Trading 検証レポート
- monitoring/
  - __init__.py
  - monitoring_db.py                — SQLite 永続化層（テーブル作成・CRUD）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - alert_manager.py
  - kill_switch.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - reconciler.py
  - (他: broker_factory, execution_engine, order_repository 等)
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
  - news_nlp.py
  - regime_detector.py
  - __init__.py
- utils/
  - process_priority.py

（実際のファイルは src/kabusys/ 以下に複数あります。ここでは主要ファイルを抜粋しています。）

---

## 開発メモ / 注意点

- 設計は「本番 DB と Paper Trading DB を分離」する方針です。paper_trading モードでは専用 SQLite（PAPER_TRADING_SQLITE_PATH）が使われます。
- 環境の自動読み込みは `.git` または `pyproject.toml` の存在からプロジェクトルートを探索します。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してロードを制御できます。
- Process 優先度の切り替え（high/normal/low）は psutil を使い、プラットフォーム差分を吸収します。権限がない場合は警告を出してスキップします。
- AI 系の処理は外部 API を呼ぶため「部分失敗 = その銘柄だけスキップ」するように設計されています（部分的な書き換えによる安全性確保）。

---

この README はコード内のモジュール docstring / コメントを元に作成しています。各モジュールの詳細な使い方や API は該当ファイルの docstring を参照してください。必要であれば実行例や .env.example のテンプレートを追加で作成します。どの情報を重点的に追記したいか教えてください。