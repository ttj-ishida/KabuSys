README
======

概要
----
KabuSys は日本株自動売買のためのコンポーネント群を集めたリポジトリです。  
主要機能は以下のとおりです。

- 発注エンジン（ExecutionEngine）とそれを支えるリスク管理 / 注文管理 / 照合ロジック
- 監視サブシステム（System / Trade / Risk モニタ）と Kill Switch（停止フラグ）
- ポートフォリオ構築（銘柄選定・重み付け・株数計算・セクター制限）
- 研究用モジュール（ファクター計算、特徴量探索、IC 計算 等）
- AI 支援モジュール（ニュースセンチメント評価、レジーム判定） — OpenAI を利用
- 運用支援ツール（.env 設定ウィザード、設定検証、Paper Trading 検証レポート生成）

設計上のポイント
- .env / 環境変数で動作を切り替え（KABUSYS_ENV: development / paper_trading / live）
- Paper Trading 実行時は本番 DB と完全分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）
- 監視（monitoring）は環境にかかわらず本番 sqlite_path を参照してログを残す設計
- ログは標準出力（stdout）と日次ローテーションファイル（logs/*.log）に出力
- OpenAI 利用部分は API キー（OPENAI_API_KEY）を参照。失敗時はフォールバック動作

主な機能一覧
----------------
- 実行系
  - run_execution.py: ExecutionEngine を起動。Paper Trading 時は MockBroker を使用して data/paper_trading.db に記録。
  - ブローカー抽象化（BrokerClientFactory）・OrderManager・RiskManager・Reconciler 等を統合。

- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可、デフォルト 60 秒）。
  - MonitoringEngine: System/Trade/Risk Monitor を束ね、Kill Switch 評価やアラート通知を実行。
  - Kill Switch: data/kill.flag を書き込んで Execution を停止する仕組み。

- データ永続化
  - monitoring_db.py: SQLite に監視ログ（system_status, trade_logs, positions, risk_logs, dashboard）を永続化するレイヤ。

- ポートフォリオ構築
  - portfolio/*: 候補選定、等重／スコア重み、リスク調整（セクター上限・レジーム乗数）、株数決定（単元丸め・集計上限）

- 研究・分析
  - research/*: ファクター計算（momentum / volatility / value）、forward returns、IC、統計サマリ等（DuckDB を利用）

- AI（OpenAI）
  - ai/news_nlp.py: raw_news から銘柄ごとにニュースを集約して OpenAI でセンチメントスコアを算出し ai_scores に書き込み。
  - ai/regime_detector.py: ETF（1321）MA とマクロニュースの LLM 評価を合成して market_regime を判定。

- ツール
  - config_setup.py: 対話形式で .env を生成・更新するウィザード
  - validate_config.py: .env と config/*.yaml の妥当性チェック（--strict オプションあり）
  - tools/paper_verification_report.py: Paper Trading DB から検証レポートを生成

セットアップ手順
----------------
前提
- Python 3.10+（型の | 記法などを使用しています）
- 推奨パッケージ（最小限）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（validate_config で YAML の中身検証を行う場合）
- （任意）仮想環境を作成して依存を分離してください。

例: 仮想環境作成とパッケージインストール
- Unix/macOS:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install --upgrade pip
  - pip install duckdb psutil openai PyYAML

.env の準備
- 対話的に作成する（推奨）:
  - python -m kabusys.config_setup
- 手動で作成する場合は .env.example を参考に .env を用意し、以下は主な必須項目:
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用、デフォルト data/paper_trading.db）
  - OPENAI_API_KEY（AI 機能を使う場合）

設定検証
- python -m kabusys.validate_config
- --strict を付けると警告も失敗として exit(1) になります。

データディレクトリとログ
- デフォルトでは次のファイル／ディレクトリを使用します:
  - data/monitoring.db (SQLite)
  - data/paper_trading.db (Paper Trading 用 SQLite)
  - data/kabusys.duckdb (DuckDB)
  - data/execution.pid (Execution の PID 保存)
  - data/kill.flag (Kill Switch ファイル)
  - data/stop_requested.flag (起動中スクリプトの外部停止指示)
  - logs/<app_name>.log（ログファイル: 日次ローテーション）

使い方（実行例）
----------------

1) 設定ウィザード（.env 作成）
- python -m kabusys.config_setup

2) 設定検証
- python -m kabusys.validate_config
- 厳格モード: python -m kabusys.validate_config --strict

3) ExecutionEngine 起動（本番 / ペーパー）
- ローカルで直接実行:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、paper_trading.db に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 終了は stop flag (data/stop_requested.flag) の作成か、プロセスの終了で行います。

4) Monitoring 起動
- python -m kabusys.run_monitoring
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 監視は本番用 sqlite_path を参照してログを残します（環境にかかわらず）。

5) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- オプション --db で DB パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も利用可。

6) AI 機能の利用（プログラムから）
- OpenAI API キーを環境変数 OPENAI_API_KEY に設定。
- 例（ai.news_nlp をプログラムから使う）:
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key=None)  # api_key None → 環境変数参照

運用上の注意
- Kill Switch:
  - KillSwitch は RiskMonitor 等の判定で data/kill.flag を作成します。
  - ExecutionEngine は Settings.kill_flag_clear_on_start が 1 の場合、起動時に自動クリアする設定になりうるため本番では 0 を推奨します。
- 監視（monitoring）は本番 DB にアクセスする前提です。Paper Trading ケースでも監視側は本番 sqlite を参照する振る舞いがあります（設計上の決定）。
- ログディレクトリ作成に失敗した場合はコンソール出力のみになります（setup_logging が警告を出します）。
- プロセス優先度設定には psutil の権限が必要な場合があります。アクセス権限がないと警告を出してスキップします。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                  — 環境変数/設定管理（Settings クラス）
- config_setup.py            — .env 対話ウィザード
- validate_config.py         — 起動前設定検証 CLI
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — SystemMonitor ポーリング起動スクリプト

src/kabusys/execution/
- broker_factory.py
- execution_engine.py
- order_manager.py
- order_repository.py
- reconciler.py
- risk_manager.py

src/kabusys/monitoring/
- monitoring_db.py
- system_monitor.py
- trade_monitor.py
- risk_monitor.py
- kill_switch.py
- monitoring_engine.py
- alert_manager.py

src/kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py

src/kabusys/research/
- factor_research.py
- feature_exploration.py

src/kabusys/ai/
- news_nlp.py
- regime_detector.py

src/kabusys/tools/
- paper_verification_report.py

src/kabusys/utils/
- logging_setup.py
- process_priority.py

その他トップレベル
- config/                    — YAML 設定テンプレート（system_config.yaml, strategy_config.yaml 等）
- data/                      — デフォルトの DB / PID / flag ファイル配置場所
- logs/                      — デフォルトログ出力先（setup_logging により自動作成）

開発向けメモ
- DuckDB を使って研究用テーブル（prices_daily, raw_financials, raw_news, news_symbols 等）を管理します。
- research / ai モジュールは DuckDB 接続を受け取り純粋に SQL/Python で処理します（外部副作用を抑制）。
- unittest で外部 API をモックする設計を考慮しており、OpenAI 呼び出しを抽象化した private 関数をテストで差し替えられます。

トラブルシューティング
- MONITOR_POLL_INTERVAL を 0 や負数にすると警告が出てデフォルトにフォールバックします。
- プロセス優先度設定に失敗しても動作は続行します（警告ログ）。
- DB テーブルが不足している場合、init_monitoring_db が自動でテーブル・カラム追加を試みます（簡易マイグレーション）。

ライセンス / バージョン
- パッケージバージョン: kabusys.__version__ == "0.1.0"（src/kabusys/__init__.py）

以上。README の内容はコードベースの説明に基づいて作成しています。追加で「導入手順の自動スクリプト」「requirements.txt の生成」「運用手順（systemd / Supervisor 用ユニット例）」などが必要であれば追記します。