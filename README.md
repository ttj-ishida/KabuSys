KabuSys — 自動売買システム（README）
=================================

概要
----
KabuSys は日本株自動売買のための内部ライブラリ群および運用ツール群です。本リポジトリはシグナル生成・ポートフォリオ構築・発注管理・監視・レポート・LLM を用いたニュース評価など、実運用を想定したコンポーネントを含みます。各モジュールは可能な限り副作用を避け、テストしやすい純粋関数 / 明示的な DB / 接続注入設計を採用しています。

主な特徴
--------
- 実行エンジン起動スクリプト（run_execution）
  - KABUSYS_ENV による運用モード切替（development / paper_trading / live）
  - paper_trading モード時は MockBroker と専用 SQLite DB を使用して本番 DB と分離
  - リスク管理（最大ポジション比率・利用率・ドローダウン等）
  - 起動時のリコンシリエーション（Reconciler）で注文・ポジションを同期

- 監視/アラート（monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor による定期チェック
  - LINE による通知 (AlertManager)
  - kill.flag を書き込むことで ExecutionEngine 停止をトリガする KillSwitch
  - SQLite に監視ログを永続化（monitoring_db）
  - Streamlit ダッシュボードで運用状況を可視化

- ポートフォリオ構築（portfolio）
  - 候補選定、等金額／スコア加重配分、ポジションサイズ計算（単元株丸め、aggregate cap）
  - セクター集中制限、レジームに応じた乗数調整

- 研究 / ファクター計算（research）
  - モメンタム・ボラティリティ・バリューなどのファクター算出（DuckDB 経由）
  - 将来リターン、IC（Spearman）計算、統計サマリー

- LLM を利用した AI 機能（ai）
  - ニュースのセンチメントを OpenAI（gpt-4o-mini）で評価して ai_scores に格納
  - マクロニュース + ETF MA200 比で市場レジーム判定（regime_detector）

- ユーティリティ
  - process の優先度設定 / CPU affinity（psutil 経由）
  - .env 自動読み込み（Settings クラス）

前提条件
--------
- Python 3.9+（型アノテーションに Path | None 等を使っています）
- SQLite（組み込み）
- 推奨依存パッケージ（必要に応じてインストール）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)

セットアップ
-----------
1. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt / pyproject.toml があれば pip install -e . や pip install -r requirements.txt を推奨）

3. パッケージとして利用する場合（推奨）
   - リポジトリルートで: pip install -e .

   あるいは PYTHONPATH に src を追加して直接モジュールを実行しても動作します。

環境変数 / 設定
----------------
Settings クラスは .env/.env.local（プロジェクトルート）や環境変数から設定を読み込みます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定できます。

主な環境変数（一部）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading では発注は MockBroker、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant | partial | never | reject）
- PID_FILE_PATH: ExecutionEngine 用 pid ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで利用）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等: 必須の外部 API キー

簡単な .env 例
---------------
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb

使い方（主要スクリプト）
-----------------------

- 監視モード（SystemMonitor の単体ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト 60 秒）
  - 監視は監視用 SQLite（Settings.sqlite_path）に書き込みます。monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用します。

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、ブローカーは MockBroker になり data/paper_trading.db に記録されます（本番 DB と完全分離）
  - 起動時に PID ファイルを書き、再起動時は Reconciler による復旧処理を行います

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で SQLite パスを指定可能（デフォルトは env もしくは data/paper_trading.db）
  - 稼働率 / 注文成功率 / 送信率 / P95 レイテンシ 等を算出して PASS/FAIL 判定を出力します

- Streamlit ダッシュボード（監視可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ブラウザで CPU/Memory/Disk、ポジション、最近の注文、リスクログ、ダッシュボード集計を確認できます
  - DB を読み取り専用で開くため、MonitoringEngine が稼働中であることが望ましいです

- AI 機能の実行例（ライブラリ API）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

注意事項 / 運用上のポイント
-------------------------
- .env 自動読み込み: プロジェクトルート（.git または pyproject.toml を起点）を探索して .env / .env.local を読み込みます。OS 環境変数は保護されます。
- MONITOR_POLL_INTERVAL は 1 秒以上の正整数を期待します。不正な値はデフォルト（60 秒）にフォールバックします。
- process の優先度設定（psutil）や CPU affinity の設定は権限によって失敗する可能性があります。失敗時は警告ログが出力され処理は継続します。
- OpenAI 連携:
  - OPENAI_API_KEY が必要です。AI モジュールは失敗時にフェイルセーフ（多くの場合 0.0 やスキップ）を行いますが、API キー未設定時は明示的に例外を投げる関数もあります。
  - API 呼び出しはリトライ／バックオフを備えていますが、呼び出し回数やコストに注意してください。
- paper_trading モードはあくまで検証用です。本番の注文フローや金銭的リスクが発生しないよう別 DB に分離されています。
- monitoring_db は起動時に簡単なマイグレーション（カラム追加など）を行います。既存 DB の互換性に注意してください。

ディレクトリ構成（主要ファイル）
----------------------------
（src/kabusys 以下）
- __init__.py
- config.py                          — 環境変数 / Settings
- run_monitoring.py                  — SystemMonitor ポーリング起動スクリプト
- run_execution.py                   — ExecutionEngine 起動スクリプト

- ai/
  - news_nlp.py                       — ニュース NLP（OpenAI）によるスコア付け
  - regime_detector.py                — レジーム判定（MA200 + マクロセンチメント）
- monitoring/
  - monitoring_db.py                  — SQLite 永続化層（テーブル作成・CRUD）
  - system_monitor.py                 — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py                  — 注文滞留・約定異常監視
  - risk_monitor.py                   — ドローダウン・ポジション上限監視
  - kill_switch.py                     — kill.flag による停止トリガ
  - alert_manager.py                  — LINE Push 通知
  - monitoring_engine.py              — 各モニターを束ねる
  - streamlit_dashboard.py            — Streamlit ダッシュボード
- portfolio/
  - portfolio_builder.py              — 候補選定・重み計算
  - position_sizing.py                — 株数決定・aggregate cap
  - risk_adjustment.py                — セクター上限・レジーム乗数
- research/
  - factor_research.py                — ファクター計算（momentum/value/volatility）
  - feature_exploration.py            — 将来リターン・IC・統計
- execution/
  - reconciler.py                     — 起動時リコンシリエーション
  - order_manager.py                  — 発注ワークフロー制御（state machine）
  - （その他: broker_factory, order_repository, order_record 等は実装に依存）
- tools/
  - paper_verification_report.py      — Paper Trading 検証レポート生成スクリプト
- utils/
  - process_priority.py               — プロセス優先度 / CPU affinity ユーティリティ

開発・テスト
------------
- 単体で動く関数は DB や外部 API にアクセスしないように設計されています（DuckDB の接続注入等）。
- テスト時は .env の自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部分は内部で _call_openai_api を分離しているため、テストでは unittest.mock.patch などで差し替え可能です。

最後に
------
この README はコードベースの主要機能と起動方法をまとめたものです。詳細な設計やアルゴリズムの背景はソース内の docstring / コメント（PortfolioConstruction.md / StrategyModel.md 参照箇所）を参照してください。運用前に必ずテスト環境（paper_trading）で十分な検証を行ってください。