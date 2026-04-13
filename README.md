KabuSys — 日本株自動売買システム
==============================

概要
----
KabuSys は日本株向けの自動売買システムのコードベースです。発注・リスク管理・監視・ポートフォリオ構築・リサーチ・ニュース NLP（OpenAI）を含むモジュール群を提供します。設計方針として「本番 DB と paper_trading の分離」「ルックアヘッドバイアス回避」「LLM 呼び出しはフェイルセーフ化」などを重視しています。

主な機能
--------
- ExecutionEngine（発注エンジン）
  - ブローカークライアント（本番 / モック）を切り替え可能
  - OrderManager / Reconciler による状態管理・再同期
  - RiskManager による投資上限・サーキットブレーカー等
- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態・データ鮮度監視
  - TradeMonitor: 注文滞留・約定価格異常検知
  - RiskMonitor: ドローダウン / ポジション上限監視
  - KillSwitch: 条件成立で ExecutionEngine 停止用フラグを出力
  - AlertManager: LINE によるプッシュ通知（オプション）
  - Streamlit ダッシュボード（監視ビュー）
- Portfolio construction
  - 候補選定（score / rank）、等金額・スコア重み配分、ポジションサイズ計算（単元株丸め）
  - セクター集中・レジーム乗数の適用
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 特徴量探索（将来リターン計算、IC 計算、統計サマリー）
  - DuckDB を使った高速な時系列計算
- AI（OpenAI 連携）
  - news_nlp: ニュースを集約して LLM により銘柄ごとのセンチメントを算出、ai_scores テーブルへ書き込み
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM 評価を合成して市場レジームを判定
- ツール
  - paper_verification_report: Paper Trading DB から検証レポートを生成

前提・依存
----------
- Python 3.9+（型アノテーション・pathlib 等を使用）
- 必須パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード起動時）
- SQLite（組み込み）
- ネットワークアクセス（LINE / OpenAI / ブローカー API を使う場合）

インストール・セットアップ
------------------------
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用）
4. データディレクトリを作成
   - mkdir -p data
   - デフォルトで使用する DB ファイル:
     - SQLite (監視): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - DuckDB: data/kabusys.duckdb

環境変数（主なもの）
-------------------
設定は環境変数またはプロジェクトルートの .env / .env.local から読み込まれます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。主なキー:

- 必須（実運用時）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- OpenAI
  - OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
- 実行モード
  - KABUSYS_ENV — 環境 (development | paper_trading | live)（デフォルト: development）
    - paper_trading の場合は MockBrokerClient を使用し paper DB を用います
- データ・ファイル位置
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視用、デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用、デフォルト: data/paper_trading.db)
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)
- その他
  - PAPER_FILL_MODE: paper_trading の Fill 動作 ("instant" | "partial" | "never" | "reject")（デフォルト: instant）
  - LOG_LEVEL: ログレベル（DEBUG|INFO|...）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

基本的な使い方
--------------

1. ExecutionEngine（発注エンジン）を起動
   - 本番 / 開発 / paper_trading の挙動は KABUSYS_ENV に依存します。
   - 例（本番/開発）:
     - python -m kabusys.run_execution
   - 例（Paper Trading）:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     - この場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。

2. Monitoring（監視ループ）を起動
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書きできます（例: MONITOR_POLL_INTERVAL=30）。
   - 監視用 DB（SQLITE_PATH）に system_status / trade_logs / risk_logs / positions / dashboard などのテーブルを自動で作成します。

3. Streamlit ダッシュボード（監視）
   - 起動:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 監視 DB を読み取り専用で開き、Overview/Positions/Orders/System タブを表示します。

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11
   - デフォルト DB は data/paper_trading.db。期間フィルタは YYYY-MM-DD。

5. AI 機能
   - ニューススコアリング:
     - kabusys.ai.score_news を用いて DuckDB 内の raw_news から ai_scores へ書き込みます。呼び出し時に OPENAI_API_KEY を設定してください。
   - レジーム判定:
     - kabusys.ai.regime_detector.score_regime を呼び出し、market_regime テーブルへ書き込みます。

運用上の注意
-----------
- process_priority の設定:
  - 起動スクリプトは最初にプロセス優先度を "high" に設定しようとします（権限不足時は警告ログ）。
- PID / kill.flag:
  - ExecutionEngine の再起動 / 止めるために PID ファイル、kill.flag を利用します。必要に応じて設定ファイルでパスを変更してください。
- DB の分離:
  - paper_trading を指定すると paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と完全に分離されます。
- OpenAI 呼び出し:
  - ネットワークエラー・429・5xx はリトライロジックあり。失敗してもフェイルセーフ（デフォルトの値で継続）を採用しています。
- DuckDB:
  - リサーチや AI は DuckDB 接続を前提に設計されています。prices_daily / raw_financials / raw_news 等のテーブルを準備してください。

ディレクトリ構成（主要ファイル）
--------------------------------
（src/kabusys 配下）

- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード機構含む）
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

- execution/
  - order_manager.py
  - reconciler.py
  - order_repository.py (実装の続きがある想定)
  - execution_engine.py (エンジン本体)
  - broker_factory.py (Broker クライアント生成)
  - broker_api.py (ブローカープロトコル定義)
  - order_record.py

- monitoring/
  - monitoring_db.py — SQLite スキーマ定義・読み書きラッパ
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py

- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数決定・単元丸め・aggregate cap
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — Momentum / Volatility / Value 計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリ

- ai/
  - news_nlp.py — ニュースの LLM ベース評価・ai_scores 書き込み
  - regime_detector.py — 市場レジーム判定（ETF MA + マクロ NLP）
- data/ (想定)
  - kabusys.duckdb (DuckDB ファイル)
  - monitoring.db (監視 SQLite)
  - paper_trading.db (Paper Trading SQLite)

サンプル .env（例）
------------------
以下は参考例です。実際の値は .env または実環境の環境変数で設定してください。

- JQUANTS_REFRESH_TOKEN=your_jquants_token_here
- KABU_API_PASSWORD=your_kabu_password_here
- OPENAI_API_KEY=sk-...
- KABUSYS_ENV=development
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- PAPER_FILL_MODE=instant
- LOG_LEVEL=INFO

トラブルシューティング
----------------------
- DB に接続できない / ファイルが見つからない:
  - data ディレクトリとファイルパーミッションを確認してください。streamlit は read-only モードでも開くため URI を読み取り専用で指定します。
- OpenAI 呼び出し失敗:
  - OPENAI_API_KEY を確認。API レート制限やネットワークエラーはリトライされますが、ログを確認して対処してください。
- プロセス優先度の設定に失敗する場合:
  - 権限不足やプラットフォーム非対応の警告がログに出ますが、処理は継続します。
- kill.flag の誤発動を防ぎたい場合:
  - Settings.kill_flag_clear_on_start を使って起動時にフラグをクリアする挙動を調整してください。

貢献・拡張
----------
- ブローカークライアントの追加（BrokerAPIProtocol 実装）
- position sizing の lot_size を銘柄別に拡張
- ダッシュボードの可視化追加（Streamlit）
- テスト・CI の追加（mock OpenAI / mock DB）

ライセンス
----------
プロジェクトに付随する LICENSE を参照してください。

以上が README の概要です。ドキュメントや実行例・環境固有の設定（ブローカー情報・APIキー等）について追記が必要であれば、対象箇所を指定してください。