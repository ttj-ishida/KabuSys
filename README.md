# KabuSys

日本株自動売買システム（KabuSys）のコードベース README（日本語）です。  
このドキュメントはプロジェクト概要、主要機能、セットアップ手順、起動／利用方法、ディレクトリ構成をまとめたものです。

目次
- プロジェクト概要
- 機能一覧
- 前提・依存関係
- 環境変数（主要）
- セットアップ手順
- 実行方法（使い方）
- 重要ファイル・フラグの説明
- ディレクトリ構成（抜粋）
- 開発上の注意点

---

## プロジェクト概要
KabuSys は日本株の自動売買を目的としたシステムです。  
主な責務は次のとおりです。

- シグナルに基づく注文作成とブローカー API への発注（ExecutionEngine）
- 発注・約定の管理、再起動時のリコンシリエーション（Reconciler）
- 監視（Monitoring）：プロセス状態、リスク（ドローダウン・ポジション数）、注文滞留、データ鮮度等の定期チェック
- Paper Trading（検証）モードのサポート（本番 DB と分離）
- ポートフォリオ構築・ポジションサイジングのユーティリティ
- 研究用ファクター計算・特徴量探索モジュール（DuckDBを使用）
- ニュース NLP / 市場レジーム判定（OpenAI を用いた LLM スコアリング）
- レポート・可視化ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

---

## 機能一覧（主なコンポーネント）
- execution/
  - ExecutionEngine（エンジン起動・セッション実行）
  - BrokerClientFactory（実運用／モック切替）
  - OrderManager / OrderRepository（注文作成・DB 永続化）
  - Reconciler（起動時の注文・ポジション同期）
  - RiskManager（発注時のルール適用）
- monitoring/
  - SystemMonitor（CPU/メモリ/ディスク/プロセス/データ鮮度監視）
  - TradeMonitor（滞留注文・約定異常の検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（トリガー条件で停止フラグを作成）
  - AlertManager（LINE push による通知）
  - MonitoringEngine（複数モニタを束ねたポーリングループ）
  - streamlit_dashboard.py（監視ダッシュボード）
  - monitoring_db（SQLite ベースの永続化層）
- portfolio/
  - 候補選定、等重・スコア配分、ポジションサイズ計算、セクター制限、レジーム乗数等の純関数群
- research/
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC 計算、統計サマリ等
- ai/
  - news_nlp.score_news（ニュースを LLM でセンチメント化し ai_scores へ書込）
  - regime_detector.score_regime（ETF MA とマクロニュースを合成して market_regime 判定）
- tools/
  - paper_verification_report（Paper Trading データから検証レポート生成）
- utils/
  - process_priority（プロセス優先度 / CPU affinity 設定ユーティリティ）
- config.py
  - .env 自動読み込みロジック（.env / .env.local）、Settings クラス

---

## 前提・依存関係
必須（主な Python ライブラリ）：
- Python 3.8+（コードで型ヒント等を使用。運用環境に合わせて調整してください）
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボードを使う場合）
- sqlite3（標準ライブラリとして同梱）

（用途に応じて requirements.txt を作成し pip install してください）

例:
pip install duckdb psutil requests openai streamlit

---

## 主要な環境変数
（.env / .env.local をプロジェクトルートに置くことで自動ロードされます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）

必須（運用により必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

運用系 / 任意:
- KABUSYS_ENV — environment (development | paper_trading | live). デフォルト: development
  - paper_trading の場合、MockBrokerClient を用いて data/paper_trading.db に記録（本番 DB と分離）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時）
- PAPER_FILL_MODE — Paper Trading の約定モード（instant | partial | never | reject）デフォルト: instant
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite パス（デフォルト: data/paper_trading.db）
- SQLITE_PATH — monitoring 用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH, KILL_FLAG_PATH 等 — ファイルパスの上書き可能

---

## セットアップ手順（簡易）
1. リポジトリをクローン / 配置
2. 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) または .venv\Scripts\activate (Windows)
3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   （プロジェクトに requirements.txt を用意する場合は pip install -r requirements.txt）
4. .env をプロジェクトルートに作成（.env.example を参考に必須の環境変数を設定）
   - 例: KABUSYS_ENV=development, OPENAI_API_KEY=..., JQUANTS_REFRESH_TOKEN=..., KABU_API_PASSWORD=...
5. data ディレクトリ作成（DB を格納する場所）
   - mkdir -p data
6. DuckDB / SQLite の初期化は各スクリプトが必要に応じて行います（init_monitoring_db などが DB スキーマを作成します）

---

## 実行方法（使い方）

### Execution Engine（発注エンジン）の起動
- 本番モード / 開発 / paper_trading は KABUSYS_ENV により切り替え
- 実行:
  - python -m kabusys.run_execution
- 特記事項:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録します（本番 DB と完全分離）。
  - 実行中は data/execution.pid が作成される（Settings.pid_file_path）。run_execution は stop フラグ（data/stop_requested.flag）があると停止します。
  - 起動時に process priority を "high" に設定しようとします（psutil によりプラットフォーム差異を吸収）。

### Monitoring（監視ループ）の起動
- 実行:
  - python -m kabusys.run_monitoring
- 設定:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
- 監視内容:
  - SystemMonitor（CPU/メモリ/ディスク・プロセス・データ鮮度）
  - TradeMonitor（滞留注文、約定異常）
  - RiskMonitor（ドローダウン・ポジション上限）
  - KillSwitch 評価 → 必要時 data/kill.flag を書き込む
  - LINE へ通知する場合は AlertManager（LINE トークン/ユーザー設定）を渡すこと

### Paper Trading 検証レポート
- コマンドライン:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH（優先）または環境変数 PAPER_TRADING_SQLITE_PATH を使用
- 出力:
  - 稼働率・注文成功率・送信率・レイテンシ等のサマリ（PASS/FAIL 判定）

### 監視ダッシュボード（Streamlit）
- 実行:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - ダッシュボードは監視用 SQLite を読み取り専用で開き、Overview / Positions / Orders / System タブを表示します。

### AI モジュール（ニュース NLP / レジーム判定）
- ニューススコア付与:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続（prices_daily, raw_news, news_symbols, ai_scores 等）を渡して実行
  - OPENAI_API_KEY または引数 api_key が必要
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA とマクロニュースを合成して market_regime テーブルへ書き込む

---

## 重要ファイル・フラグの説明
- data/stop_requested.flag
  - run_execution.py / run_monitoring.py が監視する停止フラグ。存在するとエンジン／監視ループが終了します。
- data/kill.flag
  - KillSwitch が条件に合致したときに書き込むファイル。ExecutionEngine 側で検出して停止する運用に使う想定。
- data/execution.pid（デフォルト）
  - 実行中の ExecutionEngine の PID を記録。SystemMonitor はこの PID をチェックしてプロセスの生存を確認します。
- data/monitoring.db（デフォルト）
  - 監視ログの SQLite DB。monitoring_db.init_monitoring_db() によってスキーマが作成される。
- data/paper_trading.db（paper_trading 用）
  - Paper Trading 用の SQLite DB（本番 DB と分離）

---

## ディレクトリ構成（抜粋）
以下はこのリポジトリに含まれる主要なファイル・モジュールのツリー（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - utils/
    - __init__.py
    - process_priority.py
  - monitoring/
    - __init__.py
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - (OrderManager, Reconciler, ExecutionEngine, BrokerFactory, OrderRepository 等)
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
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/ （実行時に生成される想定）
    - monitoring.db
    - paper_trading.db
    - kabusys.duckdb
    - stop_requested.flag / kill.flag / execution.pid

（実際のリポジトリでは execution 以下にさらに多数のモジュールが含まれます）

---

## 開発上の注意点 / 運用上の注意
- .env 自動読み込み
  - config.py はプロジェクトルート（.git または pyproject.toml がある場所）を起点に .env/.env.local を自動読み込みします。自動読み込みを止めるには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading と本番 DB は分離
  - KABUSYS_ENV=paper_trading を設定すると paper_trading 用 SQLite（data/paper_trading.db がデフォルト）を使用します。本番 DB を誤って上書きしないよう注意してください。
- Kill Switch / Stop フラグ
  - kill.flag（緊急停止）と stop_requested.flag（ユーザー要求停止）はファイル存在で制御されます。運用手順を明確にして誤発火を防いでください。
- OpenAI 呼び出しのフェイルセーフ
  - AI モジュールは API 失敗時にフェイルセーフ（0.0 等）で継続するよう設計されていますが、API キーやレート制限に注意してください。
- DB マイグレーション
  - monitoring_db.init_monitoring_db() はスキーマ作成と簡単なマイグレーション（カラム追加）を行いますが、複雑な移行が必要な場合は別途管理を検討してください。
- プロセス優先度設定
  - set_process_priority() は psutil を使用して優先度を変更します。権限不足で失敗することがあり、その場合はログに警告が出ます。

---

必要であれば、README に含める具体的な例（.env.example のテンプレート、requirements.txt、運用 runbook、systemd / supervisor 用の単純なユニットファイル例など）を追加で作成できます。どの内容を追加したいか教えてください。