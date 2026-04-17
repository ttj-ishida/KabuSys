# KabuSys — README

このリポジトリは日本株向けの自動売買システム「KabuSys」の一部実装です。  
本書はコードベースから読み取れる設計方針や利用方法をまとめた README です。

注意: 実行には各種外部ライブラリ（duckdb, psutil, requests, openai, streamlit など）および API キーが必要です。テストやローカル検証用途のコードも含まれます。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（起動例・コマンド）
- 主な環境変数
- 停止・フラグ操作
- ディレクトリ構成（主要ファイル一覧）
- 補足（注意点）

---

プロジェクト概要
- KabuSys は日本株の自動売買フレームワークのコンポーネント群です。
- 監視（Monitoring）、発注実行（Execution）、ポートフォリオ構築、リサーチ（ファクター計算 / 特徴量探索）、AI（ニュース NLP / レジーム判定）などをモジュール化しています。
- 永続化に SQLite（監視 / paper trading 用）と DuckDB（時系列価格・リサーチ用）を使用します。
- OpenAI を使ったニュースセンチメント評価やレジーム判定のロジックを含みます（API キー必須）。

---

機能一覧
- 監視
  - SystemMonitor: CPU・メモリ・ディスク・Execution プロセス存在・株価データ鮮度を監視しログ化
  - TradeMonitor: 注文滞留・約定異常価格を検出しログ化
  - RiskMonitor: ドローダウン・ポジション上限の監視とリスクログ記録
  - MonitoringEngine: 上記 Monitor を束ねてポーリング、KillSwitch と AlertManager を統合
  - AlertManager: LINE Messaging API での通知（クールダウン管理）
  - Streamlit ベースの簡易ダッシュボード（read-only）
- 実行（Execution）
  - ExecutionEngine 起動スクリプト（run_execution.py）。paper_trading モードでは MockBroker 使用・DB 分離
  - OrderManager / Reconciler / RiskManager / OrderRepository 等による発注制御と再同期機能
- ポートフォリオ構築
  - 候補選定、重み計算（等重・スコア重み）、セクターキャップ、レジーム乗数、ポジションサイズ計算（単元株丸め等）
- リサーチ
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン・IC・統計サマリ等
- AI
  - news_nlp: raw_news をまとめて OpenAI に送信し銘柄ごとの ai_score を生成・書き込み
  - regime_detector: MA200 乖離 + マクロニュースの LLM センチメントを合成して market_regime を算出
- ツール
  - paper_verification_report: Paper Trading の検証レポートを生成（命令ラインから実行）

---

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン／配置
2. 仮想環境を作成して有効化（例: python -m venv .venv && source .venv/bin/activate）
3. 必要なパッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit
   - 実際の requirements.txt がある場合はそちらを使用してください
4. data ディレクトリを作成（初回起動で自動作成されることもありますが手動で用意しておくと安全です）
   - mkdir -p data
5. 環境変数を設定
   - .env / .env.local をプロジェクトルートに置くことで自動ロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（機能により必須なものが異なります）
   - OpenAI を使う機能を利用する場合は OPENAI_API_KEY を設定
6. DB 初期化
   - monitoring 用の SQLite（デフォルト: data/monitoring.db）は実行時に init_monitoring_db() により作成されます
   - DuckDB（デフォルト: data/kabusys.duckdb）はアプリ側で使用します。既存の prices_daily / raw_financials テーブルが必要

---

使い方（よく使うコマンド例）

- 監視ループを起動
  - 実行: python -m kabusys.run_monitoring
  - 補足:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60）
    - run_monitoring は Monitoring 用 DB として settings.sqlite_path（デフォルト data/monitoring.db）を使用（KABUSYS_ENV に関係なく本番 sqlite_path を使用する実装になっています）
    - 停止はプロジェクトルートの data/stop_requested.flag ファイルを作成することで検知して終了

- 実行エンジン（ExecutionEngine）を起動
  - 実行: python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient が使用され、paper_trading 用 DB（デフォルト data/paper_trading.db）に完全分離して記録されます
    - 停止検知: project_root/data/stop_requested.flag を確認して安全に停止します
    - 起動時に kill.flag の存在チェックを行い、存在すれば起動せず終了します

- Paper Trading 検証レポートを生成
  - 実行: python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: --db で SQLite ファイルを指定（デフォルト env / data/paper_trading.db）

- Streamlit ダッシュボード（監視画面）
  - 実行:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 補足: dashboard は read-only（監視 DB を read-only URI で開く）

- AI モジュールの利用（スコア算出 / レジーム判定）
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続および OPENAI_API_KEY が必要
  - 直接 Python から呼び出す、または専用のバッチ呼び出しラッパを作成して実行してください

---

主な環境変数（一部）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須利用時）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須利用時）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の注文執行モード（instant | partial | never | reject） デフォルト: instant
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒） デフォルト: 60
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込むフラグパス（デフォルト data/kill.flag）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動読み込みを無効化

（Settings クラスで使える設定は src/kabusys/config.py を参照してください）

---

停止・フラグ操作
- stop_requested.flag
  - run_monitoring / run_execution はプロジェクトルート data/stop_requested.flag の存在を監視してループ終了または Engine 停止を実行します。
  - 管理スクリプトや CI から停止を指示したいときはこのファイルを作成します。
- kill.flag
  - KillSwitch（監視側）が条件を満たした場合に KILL_FLAG_PATH（デフォルト data/kill.flag）へ理由を書き込み、ExecutionEngine に停止シグナルを送ります（Execution 側は起動時や監視で kill.flag をチェックして停止する設計）。
- PID ファイル
  - ExecutionEngine は起動時に PID を data/execution.pid に書く設計です（設定により上書き可能）。system monitor はこの PID ファイルを見てプロセス存否をチェックします。

---

ディレクトリ構成（抜粋・主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                          — 環境変数 / Settings 管理（.env 自動ロード含む）
  - run_execution.py                    — ExecutionEngine 起動スクリプト
  - run_monitoring.py                   — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py      — Paper Trading の検証レポート生成 CLI
  - monitoring/
    - monitoring_db.py                  — monitoring DB schema + MonitoringDB ラッパ
    - system_monitor.py                 — システム状態・データ鮮度監視
    - trade_monitor.py                  — 注文滞留 / 約定異常監視
    - risk_monitor.py                   — ドローダウン / ポジション上限監視
    - monitoring_engine.py              — Monitor を束ねるエンジン
    - alert_manager.py                  — LINE 通知ラッパ
    - kill_switch.py                     — kill.flag 書き込みユーティリティ
    - streamlit_dashboard.py            — streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py
    - order_record.py
    - execution_engine.py (部分的に参照されている設計)
    - broker_factory.py / broker_api.py (ブローカー抽象)
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py              — 候補選定・重み計算
    - position_sizing.py                — 株数計算 / 単元丸め / aggregate cap
    - risk_adjustment.py                 — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py                — mom / vol / value の計算（DuckDB）
    - feature_exploration.py            — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py                       — OpenAI を使ったニュースセンチメント + ai_scores 書込
    - regime_detector.py                — MA200 + マクロセンチメント合成でレジーム判定
  - utils/
    - process_priority.py               — psutil を用いた優先度 / CPU affinity 設定
  - data/ (実行時に利用されることが多いディレクトリ)
    - monitoring.db (SQLite)
    - paper_trading.db (SQLite)
    - kabusys.duckdb (DuckDB)
    - execution.pid
    - stop_requested.flag
    - kill.flag

---

補足・注意点
- process priority / CPU affinity の設定は psutil を利用しています。権限不足や未対応 OS の場合は警告が出てスキップされます。
- .env ファイルの自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。CWD に依存しないように __file__ の親を辿る実装です。
- monitoring の init は冪等（既存テーブルがあっても安全）。必要なカラムが足りなければマイグレーション的に追加する処理もあります。
- OpenAI を利用する機能はコストとレートリミットに注意。news_nlp / regime_detector はリトライ・バックオフを実装していますが、API キーと利用制限を事前に確認してください。
- Paper Trading モードでは本番 DB と完全分離されるよう実装されています（run_execution が PAPER_TRADING_SQLITE_PATH を使用）。
- DuckDB の SQL は prices_daily / raw_financials 等のテーブル構造に依存します。リサーチ機能を使う際は事前に該当テーブルを準備してください。

---

問い合わせ・拡張
- コードはファンクション単位でコメント・設計方針が豊富に書かれているため、各モジュールの docstring を参照してください。
- 実稼働前に十分なテストと安全弁（手動停止フラグ、フェイルセーフのログ化、通知）が実装されているかを確認してください。

以上。README の内容を元に実行環境を用意し、必要に応じて .env.example を作成して環境変数を設定してください。