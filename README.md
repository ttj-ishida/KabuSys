# KabuSys

日本株向け自動売買プラットフォーム（ライブラリ/ツール群）の README。  
この README はリポジトリ内のソースコードをもとに作成しています。

概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援するモジュール群です。  
主な目的は以下です：

- 戦略の研究（ファクター計算・特徴量探索）
- ポートフォリオ構築（銘柄選定・重み付け・ポジションサイズ計算）
- ExecutionEngine による発注管理とリコンシリエーション
- 監視システム（プロセス・リスク・注文滞留・アラート）
- Paper Trading 用の検証ツール・レポート生成
- ニュースの NLP によるセンチメント評価や市場レジーム判定（OpenAI 利用）

設計方針として、DuckDB / SQLite を使ったローカルデータ処理、外部 API 呼び出し（kabuステーション / OpenAI 等）は抽象化しており、Paper Trading モードで本番 DB と分離できます。

---

## 主な機能一覧

- research/
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- portfolio/
  - 候補選定（スコア順）
  - 等金額／スコア加重／リスクベースの重み・株数計算
  - セクターキャップの適用、レジーム乗数
- execution/
  - OrderManager / ExecutionEngine（発注・注文状態管理）
  - Reconciler（再起動後の同期）、OrderRepository（SQLite）
- monitoring/
  - SystemMonitor / TradeMonitor / RiskMonitor（定期ポーリング）
  - MonitoringDB（SQLite 用テーブル初期化・永続化）
  - KillSwitch（異常時の停止フラグ生成）
  - AlertManager（LINE Push で通知）
  - Streamlit ダッシュボード（監視データ可視化）
- ai/
  - news_nlp: OpenAI によるニュースセンチメント評価（ai_scores へ書込）
  - regime_detector: MA200 + マクロセンチメントで市場レジーム判定
- tools/
  - paper_verification_report: Paper Trading の検証レポート生成

---

## セットアップ手順（開発環境）

以下はソースをチェックアウトしてローカルで動かす最小手順例です。

1. リポジトリをクローン / ソースを配置

2. Python 仮想環境（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール（例）
   - pip install duckdb psutil openai requests streamlit
   - 追加でテストや開発で必要なパッケージがあれば適宜インストールしてください。

   注: requirements.txt はリポジトリに含まれていない想定なので、上記の主要依存をインストールしてください。

4. 環境変数 / .env
   - 必須（実行に必須の環境変数は実行パスに依存します）
     - JQUANTS_REFRESH_TOKEN（J-Quants API を使う場合）
     - KABU_API_PASSWORD（kabuステーション API を使う場合）
   - OpenAI を使う機能を実行する場合:
     - OPENAI_API_KEY
   - LINE 通知を使う場合（任意）:
     - LINE_CHANNEL_ACCESS_TOKEN
     - LINE_USER_ID
   - その他（デフォルトがあるもの）
     - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - DUCKDB_PATH（DuckDB ファイル、デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）

   自動でプロジェクトルートの `.env` と `.env.local` を読み込みます（.git または pyproject.toml をプロジェクトルートとして検出）。自動ロードを無効化するには:
   - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データディレクトリ
   - data/ フォルダは実行時に自動生成されることが多いですが、必要に応じて作成してください。
   - PID / flag ファイル等はデフォルトで data/ 以下を使用します。

---

## 使い方（主要コマンド・実行例）

ソースツリーのまま実行する前提での呼び出し例です。パッケージをインストール後、プロジェクトルートで実行してください。

- 実行エンジン（ExecutionEngine）の起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に記録して本番 DB と分離します。
    - プロセス優先度を「high」に設定し、pid ファイルを書きます。
    - data/stop_requested.flag があると起動をキャンセル／停止します。

- 監視ループ（SystemMonitor）の起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（デフォルト 60 秒）
  - 監視は monitoring.db（Settings.sqlite_path）へ記録します（Monitoring は環境にかかわらず本番 sqlite_path を使用）

- Streamlit ダッシュボード（読み取り専用）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードから positions / orders / system status / dashboard を確認できます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH より優先）
  - レポートはシステム稼働率、注文成功率、送信率、レイテンシ等を集計して PASS/FAIL を判定します。

- AI 関連（ニュース NLP / レジーム判定）
  - Python API 経由で利用（OpenAI API キー必須）
  - 例（REPL / スクリプト）:
    - from kabusys.ai import score_news
      - score_news(conn, target_date, api_key="...")  — raw_news を解析して ai_scores を更新
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key="...")  — market_regime を更新
  - OpenAI API 呼び出しはリトライ・バリデーション等のフェイルセーフ実装済み

- 監視データベース初期化
  - init_monitoring_db(conn) を呼ぶと SQLite の監視テーブルが作成（冪等）

注意事項:
- KABUSYS_ENV の有効値: development, paper_trading, live
- run_monitoring は Monitoring 用 DB (sqlite_path) を用いるため、監視は常に本番監視 DB を参照します（環境に依存しない）
- 実行中に data/stop_requested.flag を配置することでループを終了できます
- ExecutionEngine を強制停止するために data/kill.flag を KillSwitch が作成することがあります。起動時に kill flag をクリアする設定もあります（Settings.kill_flag_clear_on_start）

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須になる箇所あり）
- KABU_API_PASSWORD — kabuステーション API 用（必須になる箇所あり）
- OPENAI_API_KEY — OpenAI を使う機能で必須
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager（LINE）用（任意）
- KABUSYS_ENV — execution / 設定の切替（development | paper_trading | live）
- SQLITE_PATH — 監視 DB（default: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイル（default: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（default: data/paper_trading.db）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

---

## ディレクトリ構成（概要）

以下は主要ファイルと簡単な説明です（src/kabusys 配下）。

- __init__.py
  - パッケージのメタ情報（__version__ 等）
- config.py
  - 環境変数の読み込み、自動 .env ロード、Settings クラス
- run_execution.py
  - ExecutionEngine 起動スクリプト（スレッドで実行、stop flag 監視）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成 CLI
- portfolio/
  - portfolio_builder.py — 候補選定、等配分・スコア配分計算
  - position_sizing.py — 株数・リスク制約の計算
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — 将来リターン、IC、統計サマリ 等
- ai/
  - news_nlp.py — raw_news を OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py — MA200 + マクロセンチメントで market_regime を判定
- monitoring/
  - monitoring_db.py — SQLite テーブル作成、MonitoringDB クラス（読み書き API）
  - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度の監視
  - trade_monitor.py — 注文滞留・約定異常の検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の作成 / 管理
  - alert_manager.py — LINE 通知の実装（クールダウン有）
  - monitoring_engine.py — 各 Monitor をまとめてポーリングするエンジン
  - streamlit_dashboard.py — Streamlit による監視 UI
- execution/
  - order_manager.py — Order State Machine の外向き API
  - reconciler.py — 再起動時の発注・ポジション同期
  - その他、broker_factory 等の実装が存在する想定
- utils/
  - process_priority.py — プロセス優先度 / CPU-affinity 設定ユーティリティ
- data/
  - （実行時に生成される）monitoring.db、kabusys.duckdb、paper_trading.db、pid/flag ファイルなど

---

## 運用上の注意・ベストプラクティス

- Paper Trading と本番 DB は完全に分離する設計です。KABUSYS_ENV=paper_trading を使うと paper_trading 用 DB に記録されます。
- .env に本番の認証情報を平文で置く際はアクセス制御に注意してください（.env を Git にコミットしない）。
- OpenAI API 呼び出しはコストがかかるため、本番ではキューやバッチ実行の頻度を制御してください。
- Monitoring のポーリングはデフォルト 60 秒です。環境に応じて MONITOR_POLL_INTERVAL を調整してください。
- PID / flag 管理によりプロセス間通信（停止指示など）を行っています。flag ファイルを手動で操作する場合は影響を理解して行ってください。

---

## 参考：よく使うコマンドまとめ

- 開発用仮想環境の準備
  - python3 -m venv .venv && source .venv/bin/activate
- 依存ライブラリのインストール（例）
  - pip install duckdb psutil openai requests streamlit
- ExecutionEngine 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - python -m kabusys.run_monitoring
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードベースの注釈に基づいて作成しました。さらに詳細な API ドキュメントや設計資料（PortfolioConstruction.md、StrategyModel.md 等）があればそれを参照してください。必要であれば README にサンプル .env.example、起動フローチャート、より詳細なコマンドオプション一覧などを追加します。