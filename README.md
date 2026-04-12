# KabuSys

日本株向け自動売買システムの一部（ライブラリ・ユーティリティ群）。  
このリポジトリには、監視／検証ツール、ポートフォリオ構築ロジック、研究用ファクタ計算、AI を使ったニューススコアリング、ExecutionEngine の起動補助などが含まれます。

以下はコードベースから抽出した README.md です。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。主要な責務は次の通りです。

- ExecutionEngine（発注・状態管理・リスク制御）の起動と補助
- 監視（プロセス・データ鮮度・注文状態・リスク）およびアラート送信（LINE）
- Paper Trading の検証レポート生成
- ポートフォリオ構築（候補選定、重み付け、株数計算、セクター制約）
- 研究用途のファクター計算（Momentum / Volatility / Value 等）
- AI（OpenAI）を用いたニュースセンチメント解析・市場レジーム判定
- DuckDB / SQLite を用いた価格・メタデータ/監視ログの永続化

設計のポイント：
- テストしやすい純関数群（DB参照なしのポートフォリオロジック等）
- ルックアヘッドバイアスを避ける実装（日時参照や SQL の制約）
- フェイルセーフ：外部 API 失敗時は安全側にフォールバックして継続

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine を起動（KABUSYS_ENV による Paper vs Live 切替）
  - Broker クライアント生成（paper_trading 時は MockBrokerClient を使用）
  - OrderRepository / OrderManager / RiskManager / Reconciler の組立て

- run_monitoring.py
  - SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔制御）
  - 監視ログは SQLite（data/monitoring.db のデフォルト）に保存

- monitoring パッケージ
  - SystemMonitor: CPU/メモリ/ディスク/プロセス/データ鮮度の監視
  - TradeMonitor: 注文の滞留・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視とダッシュボード更新
  - KillSwitch: フラグファイルによる ExecutionEngine 停止トリガ
  - AlertManager: LINE Push による一方向アラート送信
  - streamlit_dashboard: 監視ダッシュボード（Streamlit）

- tools/paper_verification_report.py
  - Paper Trading 用 DB から検証レポートを生成（稼働率・注文成功率・レイテンシ等）

- portfolio パッケージ
  - 銘柄選定（select_candidates）、重み付け（等配分・スコア加重）
  - セクターキャップ適用（apply_sector_cap）
  - ポジションサイジング（calc_position_sizes）

- research パッケージ
  - calc_momentum / calc_volatility / calc_value（DuckDB を使ったファクター計算）
  - calc_forward_returns / calc_ic / factor_summary（特徴量解析支援）

- ai パッケージ
  - news_nlp.score_news: raw_news を OpenAI でスコアリングして ai_scores に格納
  - regime_detector.score_regime: MA 乖離 + マクロセンチメントで日次レジーム判定

- utils
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティ

---

## セットアップ手順

前提:
- Python 3.9+（型ヒントの記法により 3.9 以降を想定）
- ソースツリーをプロジェクトルートに置き、`src` をパッケージルートとして利用する想定

1. リポジトリをクローン / 配置
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）
3. 依存パッケージをインストール（代表例）
   - pip install duckdb psutil requests openai streamlit
   - 必要に応じて他の依存（例えばテスト用のパッケージ）を追加

4. 環境変数／.env
   - プロジェクトはルートの `.env` / `.env.local` を自動ロードします（OS 環境変数が優先）。
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 重要な環境変数（例）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY（AI機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（監視アラート用）
     - SQLITE_PATH（監視DB、デフォルト: data/monitoring.db）
     - DUCKDB_PATH（時系列データ DB、デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の fill 動作: instant|partial|never|reject）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔 秒、デフォルト 60）
     - PID_FILE_PATH（Execution の PID 用ファイルパス、デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（kill.flag のパス、デフォルト: data/kill.flag）

5. データディレクトリ
   - デフォルトで `data/` 以下に DB・PID・フラグファイル等が配置されます。事前に作成しておくと権限等で問題が少ないです:
     - mkdir -p data

---

## 使い方

※本リポジトリを開発環境（`src` をパスに含める）として実行する例を示します。

- PYTHONPATH を通してモジュールを実行する（開発時）
  - PYTHONPATH=src python -m kabusys.run_monitoring
  - PYTHONPATH=src python -m kabusys.run_execution

- run_monitoring.py
  - 監視ループを起動します。MONITOR_POLL_INTERVAL 環境変数でポーリング秒数を上書きできます（デフォルト 60 秒）。
  - 例: MONITOR_POLL_INTERVAL=30 PYTHONPATH=src python -m kabusys.run_monitoring

- run_execution.py
  - ExecutionEngine を起動します。KABUSYS_ENV が `paper_trading` の場合、paper 用の SQLite を使い、MockBrokerClient による記録が `data/paper_trading.db` に残ります。
  - 例: KABUSYS_ENV=paper_trading PYTHONPATH=src python -m kabusys.run_execution

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 起動後、ブラウザ上でポートフォリオ値・ポジション・注文・システム状態を確認できます。

- AI 機能（news_nlp / regime_detector）
  - OPENAI_API_KEY が必要です。API キーを環境変数または関数引数で渡します（score_news / score_regime）。
  - AI 呼び出しは外部 API の失敗に対してフォールバックするよう設計されています（失敗時はスコアを 0 にする等）。

- 設定の注意
  - Settings クラスに各種設定の取得ロジックがまとめられています。環境変数を用いて挙動を制御してください。
  - KABUSYS_ENV（development / paper_trading / live）により DB の使い分けや broker の選択が行われます。

---

## 主要な環境変数（抜粋とデフォルト）

- KABUSYS_ENV = development | paper_trading | live（デフォルト: development）
- SQLITE_PATH = data/monitoring.db
- DUCKDB_PATH = data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH = data/paper_trading.db
- PAPER_FILL_MODE = instant | partial | never | reject（デフォルト: instant）
- PID_FILE_PATH = data/execution.pid
- KILL_FLAG_PATH = data/kill.flag
- MONITOR_POLL_INTERVAL = 60
- OPENAI_API_KEY = (OpenAI API key for ai modules)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID = (for AlertManager)

例 .env（最小）
```
KABUSYS_ENV=development
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
OPENAI_API_KEY=sk-...
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
```

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数読み込み / Settings
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

パッケージ（サブディレクトリ）
- ai/
  - news_nlp.py — ニュースの LLM スコアリング
  - regime_detector.py — 市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite 監視ログの永続化層（テーブル初期化・CRUD）
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py — 注文滞留 / 約定価格異常検出
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — フラグファイルによる停止シグナル
  - alert_manager.py — LINE push 通知
  - monitoring_engine.py — 各モニタを束ねるループ実行器
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - reconciler.py — 起動時リコンシリエーション
  - order_manager.py — 発注の高レベル API
  - order_repository.py, order_record.py, broker_factory など（発注周り）
- portfolio/
  - portfolio_builder.py — 候補選定、重み計算
  - position_sizing.py — 株数決定・スケーリング
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value factor 計算
  - feature_exploration.py — 将来リターン / IC / 統計まとめ
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- utils/
  - process_priority.py — 優先度 / CPU affinity ユーティリティ
- data/ (推奨)
  - monitoring.db (SQLite)
  - kabusys.duckdb (DuckDB)
  - paper_trading.db (Paper Trading 用 SQLite)
  - execution.pid
  - kill.flag

（実際のファイル一覧はソースツリーを参照してください）

---

## 運用上の注意・ベストプラクティス

- Paper Trading と Live の DB は分離してください（Settings がデフォルトで分離）。
- run_execution.py / run_monitoring.py は起動直後にプロセス優先度を High に設定しようとします。権限がないと警告が出ますが処理は継続します。
- kill.flag により ExecutionEngine を安全に停止できます。KillSwitch は監視結果に応じてこのフラグを作成します。
- AI（OpenAI）呼び出しは外部 API であるためレート制限・料金に注意してください。環境変数 OPENAI_API_KEY の管理を適切に。
- LINE アラートを有効にするには LINE の Channel Access Token とユーザ ID を設定してください。
- DuckDB / prices_daily に必要なデータがないと research / ai の一部機能は期待通り動作しません。データ投入を確認してください。

---

## 貢献・拡張ポイント（考慮済みの TODO 等）

- 銘柄ごとの lot_size をマスタに持たせる（現在は固定単元で丸め）
- price のフォールバックロジック（前日終値等）を追加して price が欠損するケースを改善
- ExecutionEngine の永続化戦略（トランザクション・クラッシュ再開）強化
- AI レスポンスのより厳格な検証・フォールバックの拡張

---

この README はソース内の docstring / コメントをもとに作成しています。実際の運用前に設定（環境変数・DB パス・API キー）を確認してください。質問や追記してほしい項目があれば教えてください。