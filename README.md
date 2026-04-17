# KabuSys

KabuSys は日本株向けの自動売買・リサーチ・監視基盤のコードベースです。  
本リポジトリはトレード実行エンジン、監視・アラート、ポートフォリオ構築、ファクター/リサーチ、AI（ニュース NLP / レジーム判定）などの主要コンポーネントを含みます。

以下はこのコードベースの README（日本語）です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - 実行エンジンの起動
  - 監視ループの起動
  - Streamlit ダッシュボード
  - Paper Trading 検証レポート
  - AI関連（ニューススコア / レジーム判定）
- 環境変数と設定
- 終了 / 停止制御
- ディレクトリ構成（主要ファイル一覧）
- 補足・注意点

---

プロジェクト概要
- 日本株自動売買システムの基盤モジュール群。
- ExecutionEngine による注文管理、OrderManager / Reconciler による復旧処理。
- Monitoring 系（SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch）による常時監視とアラート。
- Portfolio 構築（候補選定、重み付け、ポジションサイズ計算、セクター制限等）。
- Research 用に DuckDB 経由でファクター計算・特徴量探索のユーティリティを提供。
- AI モジュールは OpenAI（gpt-4o-mini 等）を利用してニュースセンチメント・マクロセンチメントを評価し、ai_scores / market_regime を更新。

機能一覧
- Execution:
  - 注文作成 / 同期 / 管理（OrderManager, OrderRepository）
  - Reconciler による再起動後の照合・復旧
  - Paper Trading モード（KABUSYS_ENV=paper_trading）で実環境と分離された DB と MockBroker を使用
- Monitoring:
  - システムリソース監視（CPU/メモリ/ディスク）
  - プロセス生存確認（PIDファイル）
  - 注文滞留 / 約定異常検出
  - ドローダウン / ポジション上限監視と kill.flag 発行
  - LINE へプッシュ通知（AlertManager）
  - streamlit ベースの監視ダッシュボード
- Portfolio:
  - 候補選定（スコア/ランク）
  - 等金額/スコア加重の重み計算
  - リスク調整（セクター制限・レジーム乗数）
  - ポジションサイズ計算（ロット丸め・aggregate cap）
- Research:
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI:
  - ニュース NLP による銘柄別センチメント（ai_scores へ書き込み）
  - レジーム判定（ETF ma200 とマクロニュースの LLM センチメント合成）
- ツール:
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
  - streamlit ダッシュボード（monitoring/streamlit_dashboard.py）

セットアップ手順（開発用）
1. Python 3.9+ を用意してください（コードは型アノテーションを使用）。
2. 仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）:
   - pip install duckdb psutil openai requests streamlit
   - （プロジェクトに requirements.txt がある場合はそれを使用してください）
4. 環境変数の設定:
   - ルートに .env / .env.local を作成できます（自動で読み込まれます）。
   - 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
5. データディレクトリ:
   - デフォルトの DB・PID・フラグファイルは data/ 配下に作成されます。必要に応じてディレクトリを作成してください:
     - mkdir -p data
6. 初回起動時、SQLite / DuckDB のテーブルは各モジュール（例: init_monitoring_db）が接続時に作成します。

主要環境変数（抜粋）
- KABUSYS_ENV: 開発/本番/ペーパートレードを示す。値: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使用する場合）
- PAPER_FILL_MODE: paper_trading 時の fill 挙動（instant | partial | never | reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite パス（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB パス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: 実行エンジン PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、既定 60 秒）

使い方（主要コマンド / 実行例）

- 実行エンジン（ExecutionEngine）起動
  - 目的: 発注・実行ロジックを開始する
  - コマンド例:
    - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、data/paper_trading.db に記録され、本番 DB と分離されます。
    - 起動時に data/stop_requested.flag があると起動をスキップします。
    - プロセス優先度を高く設定します（set_process_priority("high")）。

- 監視ループ（Monitoring）起動
  - 目的: システム監視・リスク監視・アラート・kill.flag 発行などを行う
  - コマンド例:
    - python -m kabusys.run_monitoring
  - 説明:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
    - 監視は本番 sqlite_path を参照（KABUSYS_ENV に関わらず本番 path を使用）。
    - 停止は data/stop_requested.flag を作ることで行えます（監視ループはこのフラグを検知して終了）。

- Streamlit 監視ダッシュボード
  - 起動方法:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明:
    - 読み取り専用で SQLite を開き、Overview / Positions / Orders / System を確認できます。

- Paper Trading 検証レポート
  - 使い方:
    - python -m kabusys.tools.paper_verification_report
    - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - DB デフォルト: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）

- AI 関連
  - ニュース NLP スコアリング:
    - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
    - 必要: OPENAI_API_KEY（引数でも渡せる）
    - DuckDB 接続（raw_news, news_symbols, ai_scores テーブル）を使います。
  - レジーム判定:
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - DuckDB の prices_daily / raw_news / market_regime を参照し、結果を market_regime テーブルへ書き込みます。
  - 注意:
    - API 呼び出しはリトライ・エラー処理を含みますが、APIキー未設定時は ValueError が発生します。
    - LLM 出力は JSON パース・検証して取り扱います。

終了・停止制御
- stop_requested.flag:
  - run_monitoring/run_execution はプロジェクトルート直下の data/stop_requested.flag（run モジュールで利用）を監視し、存在を検知すると安全に終了します。
- kill.flag:
  - KillSwitch（監視側）で条件を満たすと KILL_FLAG_PATH（デフォルト data/kill.flag）に理由を記載して書き込み、ExecutionEngine に停止シグナルを送ります。
- PID ファイル:
  - ExecutionEngine は起動時に pid ファイル（デフォルト data/execution.pid）を使用します。SystemMonitor はこの PID を確認してプロセスの生存を検出します。古い PID が残っていると stale PID と見なして削除・アラートします。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ初期化 & 永続化 API (MonitoringDB)
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文滞留 / 約定異常監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みロジック
    - alert_manager.py       — LINE push 通知
    - monitoring_engine.py   — 各 Monitor を束ねる
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py    (参照される実装ファイルあり)
    - execution_engine.py   (参照される実装ファイルあり)
    - broker_factory.py     (ブローカークライアント生成)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/  (runtime)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用デフォルト)
    - kabusys.duckdb (デフォルト)
    - execution.pid / kill.flag / stop_requested.flag など

補足・注意点
- Settings（config.py）はプロジェクトルート（.git または pyproject.toml を起点）から .env/.env.local を自動読み込みします。OS 環境変数が優先され、.env.local は上書き可能です。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- Paper Trading と Production の DB は分離されています（paper_trading モードで paper_sqlite_path を使用）。
- DuckDB は価格・財務データや raw_news を格納する用途で利用されます。AI / Research 処理は主に DuckDB を参照します。
- run_monitoring は MonitoringDB（SQLite）を必ず本番 sqlite_path で初期化します（環境に依らず本番 path を使用）。
- process priority / CPU affinity の設定はプラットフォーム依存で psutil を使用します。権限不足時は警告ログを出してスキップします。
- OpenAI API 呼び出しは rate limit / transient エラーに対し指数バックオフでリトライします。一部失敗時はフェイルセーフ（スコアを 0 にする等）で継続します。

サンプル .env（最小）
- .env.example なしの場合の参考:
  - JQUANTS_REFRESH_TOKEN=...
  - KABU_API_PASSWORD=...
  - OPENAI_API_KEY=...
  - KABUSYS_ENV=development
  - PAPER_FILL_MODE=instant
  - SQLITE_PATH=data/monitoring.db
  - DUCKDB_PATH=data/kabusys.duckdb
  - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  - PID_FILE_PATH=data/execution.pid
  - KILL_FLAG_PATH=data/kill.flag
  - LOG_LEVEL=INFO

最後に
- この README はコードを素早く理解してローカルで動かすためのガイドです。各モジュールの詳細な挙動は該当するソースコードの docstring / コメントに記載されています。必要に応じて各モジュール（monitoring/*.py, execution/*.py, ai/*.py, research/*.py）を参照してください。

お困りの点があれば、どの部分を詳しく知りたいか教えてください。設定例や具体的な起動スクリプトのテンプレートも作成できます。