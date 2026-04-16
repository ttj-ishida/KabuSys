# KabuSys

日本株自動売買システムのコードベース（モジュール群の抜粋）。この README は開発者向けにプロジェクト概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

概要
---
KabuSys は日本株の自動売買を支援するシステムで、主なコンポーネントは以下です。

- Execution (ExecutionEngine / OrderManager 等): 発注・注文状態管理・リコンシリエーション
- Monitoring: システム健全性・注文滞留・リスク監視、LINE 通知、Streamlit ダッシュボード
- Portfolio: 銘柄選定、重み付け、ポジションサイズ計算、セクター上限・レジーム調整
- Research: ファクター計算、将来リターン計算、IC 計測などのリサーチ用ユーティリティ
- AI: OpenAI を使ったニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）
- Tools: Paper Trading の検証レポート生成スクリプト等
- Utils / Config: 環境設定読み込み、プロセス優先度設定などユーティリティ

設計上のポイント
- DuckDB を利用したオンメモリ／分析向けテーブル（prices_daily 等）
- SQLite を監視ログや Paper Trading 用 DB に使用
- Paper Trading（KABUSYS_ENV=paper_trading）時は MockBroker を使い DB を分離
- OpenAI 呼び出しは失敗時に保守的にフォールバック（例: スコア 0.0）する等のフェイルセーフを実装
- 自動で `.env` / `.env.local` を読み込み（必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）

主要機能一覧
---
- Execution
  - 発注フロー（OrderManager / OrderRepository）
  - ブローカー同期・再起動後リコンシリエーション（Reconciler）
  - RiskManager による発注時のリスクチェック
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセス存否チェック
  - TradeMonitor: 注文滞留・約定価格異常検出
  - RiskMonitor: ドローダウン・保有数上限の監視、ダッシュボード更新
  - KillSwitch: 条件を満たすと `data/kill.flag` を書き込み ExecutionEngine 停止シグナルを発行
  - AlertManager: LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボードで監視データを可視化
- Portfolio
  - シグナル候補選定、等重・スコア重み付け
  - リスク調整（セクター上限、レジーム乗数）
  - 発注株数計算（単元丸め、aggregate cap, cost buffer）
- Research & AI
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン、IC、統計サマリー
  - ニュース NLP による銘柄別センチメント取得（OpenAI）
  - マクロニュース + ETF MA200 を合成した市場レジーム判定（OpenAI）
- Tools
  - paper_verification_report: Paper Trading の検証レポートを生成（CLI）

セットアップ手順
---
前提
- Python 3.10 以上を推奨（typing の表記等から）
- 必要依存パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード実行時）
- 仮想環境作成（推奨）
  - python -m venv .venv
  - source .venv/bin/activate (Windows: .venv\Scripts\activate)

インストール例
1. リポジトリをクローンし、プロジェクトルートへ移動
2. 依存をインストール
   - pip install -r requirements.txt
   - （requirements.txt が無い場合は上記ライブラリを個別にインストール）

環境変数 / .env
- プロジェクトは .env / .env.local を自動で読み込みます（OS 環境変数優先）。
- 例として設定が必要（最低限）な環境変数:
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - OPENAI_API_KEY (AI 機能を使うなら必須)
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（LINE 通知を使う場合）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用の DB、デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject、デフォルト: instant）
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト: 60）
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など（Monitoring 設定）
- 簡易の .env 例:
  - KABUSYS_ENV=paper_trading
  - OPENAI_API_KEY=sk-...
  - JQUANTS_REFRESH_TOKEN=...
  - KABU_API_PASSWORD=...

DB 初期化
- 監視テーブル等は run_monitoring/run_execution 起動時に自動作成される（init_monitoring_db を通じて冪等で作成）。
- DuckDB のスキーマ（prices_daily, raw_news, raw_financials 等）は別途データパイプラインで投入する想定。

使い方（起動／コマンド）
---
起動スクリプト
- ExecutionEngine（本番 / paper_trading を含む）
  - python -m kabusys.run_execution
  - 動作: Settings に応じて本番ブローカー or MockBroker を選択。paper_trading では PAPER_TRADING_SQLITE_PATH に記録。
  - 起動前に `data/kill.flag` が存在すると起動を中止する。Execution 側は `data/execution.pid` を書き、stop フラグ等を監視する。

- Monitoring（定期ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒指定可能（デフォルト: 60）
  - Monitoring は常に Settings.sqlite_path（本番監視 DB）を使用する点に注意

Tools
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH (PAPER_TRADING_SQLITE_PATH より優先)
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

Streamlit ダッシュボード
- 実行:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- read-only で SQLite を開き、Positions / Orders / System / Overview を表示

AI / Research 呼び出し
- AI 機能（news_nlp.score_news, regime_detector.score_regime）は DuckDB 接続と API キーを与えて呼び出す。API キーは引数で渡すか環境変数 OPENAI_API_KEY を使用します。
- Research 関数（calc_momentum 等）は DuckDB 接続を受け取り純粋関数として実行できます。

運用上の注意
- paper_trading モードは本番ブローカーとデータを完全分離するため、テスト時はこちらを利用してください。
- KillSwitch はリスクルール（ドローダウンや保有数上限） に基づき `data/kill.flag` を書き込み、Execution を安全に停止させます。KillSwitch は冪等で書き込みを行います。
- Monitoring はプロセス優先度を上げる処理（set_process_priority("high")）を行います。権限が無い場合は警告を出してスキップします。
- OpenAI 呼び出しはリトライやクリッピングなど保護ロジックを実装していますが、API 利用時のコストやレート制限には注意してください。

ディレクトリ構成（概要）
---
- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数の読み込み・検証、.env 自動ロード機能
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント（KABUSYS_ENV に応じて動作）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - execution/
    - order_manager.py, order_repository.py, execution_engine.py, reconciler.py, risk_manager.py, broker_factory.py, broker_api.py, order_record.py, ...
    - 発注フロー、ブラウザクライアント抽象、Reconciler 等
  - monitoring/
    - monitoring_db.py : SQLite による永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py, alert_manager.py, streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
    - 銘柄選定、重み計算、サイズ決定、セクター/レジーム調整
  - research/
    - factor_research.py, feature_exploration.py
    - ファクター計算、将来リターン、IC、統計要約
  - ai/
    - news_nlp.py : ニュースを OpenAI でセンチメント化し ai_scores テーブルへ書き込む
    - regime_detector.py : ETF MA200 とマクロセンチメントを合成して market_regime を判定
  - tools/
    - paper_verification_report.py : Paper Trading 用レポート生成 CLI
  - utils/
    - process_priority.py : プロセス優先度・CPU affinity 設定ユーティリティ

ファイル / データフォルダ（ランタイムで使用）
- data/
  - monitoring.db（デフォルト SQLITE_PATH）
  - kabusys.duckdb（デフォルト DUCKDB_PATH）
  - paper_trading.db（paper_trading 用 DB）
  - execution.pid（ExecutionEngine の PID）
  - kill.flag（KillSwitch が書き込む停止フラグ）
  - stop_requested.flag（run_* スクリプトでループ停止確認に使用）

よく使う環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン
- KABU_API_PASSWORD: kabu API のパスワード
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH
- MONITOR_POLL_INTERVAL: 監視ループ間隔（秒）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant | partial | never | reject）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用

開発メモ / 注意点
- DuckDB 関連クエリは prices_daily / raw_financials / raw_news 等のテーブルを前提としています（データパイプラインで事前投入）。
- Monitoring の init_monitoring_db() は起動時に冪等でテーブルとマイグレーション（欠けているカラムの追加）を行います。
- OpenAI 呼び出しはネットワークや rate limit で失敗する可能性があるため、外部 API の失敗時にはロギングして安全側にフォールバックします。

サンプル実行例
---
- 開発（Paper Trading）で Execution を起動:
  - export KABUSYS_ENV=paper_trading
  - export OPENAI_API_KEY=sk-...
  - python -m kabusys.run_execution

- 監視プロセスを起動（デフォルト 60 秒間隔）:
  - python -m kabusys.run_monitoring
  - あるいは MONITOR_POLL_INTERVAL を変更:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

サポート / 拡張
---
- DuckDB テーブルの準備・更新用データパイプラインは別途用意する想定です。
- Broker 抽象（broker_api.py）を実装すれば別ブローカーへの対応が可能です。
- 将来的な拡張候補：銘柄別 lot_size 対応、より高度なリスク制御、バックテスト用エンジンの追加。

---

README の補足や追加したいセクション（CI、テスト、デプロイ手順など）があれば教えてください。必要に応じて .env.example のテンプレートや requirements.txt の推奨内容も作成できます。