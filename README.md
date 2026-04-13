README
======

概要
----
KabuSys は日本株の自動売買システム向けに設計された Python パッケージです。
主要機能は以下のとおりです:

- 実取引 / Paper Trading 用の ExecutionEngine 起動
- 実行状態・注文・リスクの監視とアラート（LINE 経由のプッシュ）
- 監視データの永続化（SQLite）および分析用 DuckDB 連携
- ポートフォリオ構築・銘柄選定・株数決定ロジック（純粋関数群）
- 研究用ファクター計算・特徴量探索（DuckDB を用いたバッチ処理）
- ニュースを LLM でスコア化する AI モジュール（OpenAI）
- Paper Trading 検証レポート生成ツール（コマンドライン）
- Streamlit ベースの監視ダッシュボード

設計上のポイント
- Settings は環境変数 / .env(.local) から読み込み（自動ロードを無効化可能）
- Paper Trading は本番 DB と分離（デフォルト: data/paper_trading.db）
- 監視は常に本番の sqlite_path を利用（KABUSYS_ENV に依存しない）
- 外部 API 呼び出し（OpenAI 等）はフェイルセーフ/リトライ処理あり

機能一覧
--------
主な機能（モジュール単位）

- 起動スクリプト
  - kabusys.run_execution: ExecutionEngine を起動（KABUSYS_ENV に応じて MockBroker使用）
  - kabusys.run_monitoring: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可）
- 監視関連
  - monitoring.monitoring_db: SQLite テーブル初期化 / CRUD ラッパー
  - monitoring.system_monitor: CPU/メモリ/ディスク・プロセス・データ鮮度チェック
  - monitoring.trade_monitor: 注文滞留 / 約定異常検出
  - monitoring.risk_monitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - monitoring.kill_switch: 条件に応じて kill.flag を書き込み ExecutionEngine を停止
  - monitoring.alert_manager: LINE Push API で通知（cooldown 制御あり）
  - monitoring.monitoring_engine: 上記モニタを束ねたポーリングエンジン
  - monitoring.streamlit_dashboard: Streamlit による監視 GUI
- 実行・注文管理
  - execution.order_manager, order_repository, reconciler: 発注・同期・リコンシリエーション
- ポートフォリオ構築
  - portfolio.portfolio_builder: 候補選定・重み計算（等配分・スコア加重）
  - portfolio.position_sizing: 株数決定（risk_based / equal / score）
  - portfolio.risk_adjustment: セクター上限・レジーム乗数計算
- 研究（Research）
  - research.factor_research: Momentum / Volatility / Value ファクター計算（DuckDB）
  - research.feature_exploration: 将来リターン、IC、統計サマリ等
- AI（LLM）
  - ai.news_nlp: raw_news をまとめて OpenAI に投げ、銘柄ごとのセンチメントを ai_scores に書込
  - ai.regime_detector: ETF (1321) の MA200 とマクロニュース LLM を合成して市場レジームを判定
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポートを生成（期間指定可）

セットアップ手順
----------------
前提: Python 3.10 以上を推奨（型注釈の union 表記などを使用）

1. リポジトリをクローン
   - git clone <repo_url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - 代表的な依存例:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit

   ※ requirements.txt があればそれを使用してください:
     - pip install -r requirements.txt

4. 環境変数設定
   - プロジェクトルートに .env/.env.local を置くと自動的に読み込まれます（既存 OS 環境変数は保護）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（未設定なら送信スキップ）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading DB（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒（デフォルト: 60）
- PAPER_FILL_MODE: paper_trading の約定モード（instant | partial | never | reject）

使い方
------
起動スクリプト（例）

- ExecutionEngine を起動（通常/ペーパーは KABUSYS_ENV で切替）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - python -m kabusys.run_execution  （デフォルト KABUSYS_ENV=development）

  説明:
  - paper_trading モードでは MockBrokerClient を使い、Paper DB（data/paper_trading.db）へ記録します。
  - 起動時に PID ファイル（Settings.pid_file_path、デフォルト data/execution.pid）を書きます。

- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート（コマンドライン）
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: --db PATH で SQLite パスを指定（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

- AI 機能（プログラムから呼び出し）
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数に渡すか環境変数 OPENAI_API_KEY を利用

その他の注意点
- Settings は自動的に .env / .env.local をロードします（OS の環境変数は保護）。
- paper_trading の DB は本番 DB とは物理的に分離されるように設計されています（デフォルト値で分離済み）。
- プロセス優先度設定（set_process_priority）は権限により失敗する場合がありますが、失敗時はログに落ちてスキップします。
- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）は KillSwitch によって作成され、ExecutionEngine 側がこれを検知して停止する設計です。Execution 起動時に KILL_FLAG_CLEAR_ON_START を 1 にすると起動時にフラグを削除します。

ディレクトリ構成（主要ファイル）
-----------------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数 / .env ロードと Settings クラス
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 用分離処理あり）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

サブパッケージ（抜粋）
- monitoring/
  - monitoring_db.py       — SQLite テーブル初期化と MonitoringDB クラス
  - system_monitor.py      — システム状態・データ鮮度チェック
  - trade_monitor.py       — 注文滞留・約定異常チェック
  - risk_monitor.py        — ドローダウン / ポジション上限監視
  - kill_switch.py         — kill.flag の管理
  - alert_manager.py       — LINE 通知
  - monitoring_engine.py   — 各 Monitor をまとめる
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - (broker_factory, execution_engine など：発注・実行ロジック)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py     — Momentum/Volatility/Value 等のファクター計算
  - feature_exploration.py — 将来リターン / IC / 統計
- ai/
  - news_nlp.py            — ニュースを LLM でスコアリングして ai_scores に書込
  - regime_detector.py     — MA200 とマクロセンチメントで市場レジーム判定
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
- utils/
  - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
- portfolio/__init__.py, research/__init__.py, monitoring/__init__.py, ai/__init__.py などで公開 API を整理

サンプル .env（最小例）
---------------------
# KABUSYS 環境
KABUSYS_ENV=development

# API トークン（必須）
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password

# OpenAI（AI機能使用時）
OPENAI_API_KEY=sk-...

# DB パス（任意）
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

よくある質問 / トラブルシュート
------------------------------
- .env が読み込まれない:
  - プロジェクトルートの判定は .git または pyproject.toml を基準にしています。配布後にこれらが存在しない場合は自動ロードされません。手動で環境変数を設定するか KABUSYS_DISABLE_AUTO_ENV_LOAD を使って挙動を制御してください。

- OpenAI 呼び出しが失敗する:
  - ネットワーク/429/5xx は内部でリトライします。API キー未設定の場合は例外となるのでキーを確認してください。

- Monitoring が意図せず停止する:
  - run_monitoring は KeyboardInterrupt で終了します。kill.flag の書き込みは ExecutionEngine 側の停止トリガーです（監視側は flag を書くだけ）。

貢献・拡張
----------
- DuckDB や SQLite に格納されるスキーマは monitoring_db.init_monitoring_db で管理されます。スキーマ変更時はマイグレーション処理の追加を検討してください。
- AI モジュールのモデル切替やプロンプトチューニングは news_nlp / regime_detector 内の定数で調整できます。
- ポートフォリオロジック（position_sizing 等）は純粋関数ベースで分かりやすく設計されているため、テストと差し替えが容易です。

ライセンス
---------
（ここにライセンス記載）

問い合わせ
----------
（プロジェクト固有の連絡手段や issue 提出先を記載してください）