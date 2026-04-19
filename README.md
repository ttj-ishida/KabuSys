KabuSys
=======

日本株向け自動売買システムのコアライブラリ / 実行スクリプト群です。  
このリポジトリには、発注エンジン、監視・アラート、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などの主要コンポーネントを含みます。

主な特徴
--------
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアント分離（BrokerClientFactory）
  - 注文管理・リスク管理・照合（OrderManager / RiskManager / Reconciler）
- Monitoring（監視サブシステム）
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / プロセス監視
  - TradeMonitor / RiskMonitor: 注文滞留・約定異常・ドローダウン / ポジション上限監視
  - Kill Switch: 条件成立時に data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine: 各 Monitor を定期実行しアラートを発行
- Portfolio Construction
  - 候補選定、等重・スコア重み、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイジング（単元丸め・集約キャップ）
- Research / Feature 工具
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
- AI モジュール
  - news_nlp: OpenAI を使ったニュースセンチメント（銘柄別）スコア化 → ai_scores テーブルへ書き込み
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM センチメントを合成して日次レジーム判定（bull/neutral/bear）
- ユーティリティ
  - ログ設定ユーティリティ（stdout + 日次ローテートファイル）
  - プロセス優先度・CPU affinity 設定（Windows / POSIX 対応）
  - .env ウィザードと設定検証 CLI
- ツール
  - Paper Trading 検証レポート生成スクリプト（paper_verification_report）

動作環境（推奨）
---------------
- Python 3.10 以上（型記法に | を使用しているため）
- 主な Python パッケージ（最低限）:
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config/*.yaml の検証に使用）
- ログ・データディレクトリ: logs/, data/（スクリプトが自動で作成しますが、適切な権限を確認してください）

セットアップ手順
----------------
1. リポジトリをクローン
   - 例: git clone <repo> && cd <repo>

2. 仮想環境を作成して有効化（任意だが推奨）
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 依存パッケージをインストール（requirements ファイルがない場合は主要パッケージを個別に）
   - pip install duckdb psutil openai
   - 任意: pip install pyyaml

4. 環境変数（.env）の作成
   - 対話式ウィザードで .env を生成:
     - PYTHONPATH=src python -m kabusys.config_setup
   - 重要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
     - KABU_API_PASSWORD（kabuステーション API 用）
   - その他:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能利用時に必要）
     - LOG_LEVEL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID 等

5. 設定検証（推奨）
   - PYTHONPATH=src python -m kabusys.validate_config
   - --strict をつけると警告も exit(1) 扱いになります

使い方（主要コマンド）
---------------------
※ パッケージをインストールしていない開発ツリーから実行する場合は PYTHONPATH=src を指定してください。

- .env ウィザード（対話式）
  - PYTHONPATH=src python -m kabusys.config_setup

- 設定検証
  - PYTHONPATH=src python -m kabusys.validate_config
  - 厳格モード: PYTHONPATH=src python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番 / ペーパー共通スクリプト）
  - PYTHONPATH=src python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag がある場合は起動せず終了
    - 停止シグナルは data/stop_requested.flag を作成することで送る

- Monitoring を起動（ポーリング）
  - PYTHONPATH=src python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔秒を上書き（デフォルト 60）
  - 監視は Settings.sqlite_path を本番 DB として常に使用（環境に依らず）

- Paper Trading 検証レポート生成
  - PYTHONPATH=src python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11

- AI 機能（プログラムから呼び出す）
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続を受け取り日付を指定して実行します。
  - 例（スクリプト内で）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, date(2026, 4, 10), api_key="...")

運用上の注意
-------------
- KABUSYS_ENV の意味:
  - development: 発注無効の開発用（デフォルト）
  - paper_trading: ペーパートレード（MockBrokerClient） — 発注ロジックを検証できます
  - live: 本番発注
- ペーパートレードは本番データベースと分離（PAPER_TRADING_SQLITE_PATH）
- Kill Switch:
  - RiskMonitor 等が条件を満たすと KillSwitch が data/kill.flag を書き込み、ExecutionEngine 側で検出して停止します
  - 本番では KILL_FLAG_CLEAR_ON_START を 0（クリアしない）にすることを推奨
- ログ:
  - デフォルトは logs/<app_name>.log（TimedRotatingFileHandler、日次ローテート、30日保持）と stdout
  - LOG_DIR, LOG_LEVEL でカスタマイズ可能
- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を呼びます（権限不足で失敗した場合は警告が出ます）

ディレクトリ構成（主要ファイル）
--------------------------------
（package ルートは src/kabusys）  
以下は主要モジュールの一覧（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / .env 自動読み込み / Settings
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - utils/
    - logging_setup.py         — 統一ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py         — SQLite 永続化（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py        — システムヘルスチェック / データ鮮度
    - risk_monitor.py          — ドローダウン / ポジション上限監視
    - kill_switch.py           — kill.flag 書き込み
    - monitoring_engine.py     — 各 Monitor を束ねる
    - alert_manager.py         — （アラート管理 — 省略ファイルあり）
    - trade_monitor.py         — （注文監視 — 参照箇所あり）
  - execution/
    - execution_engine.py      — 実行エンジン本体（EngineConfig 等）
    - broker_factory.py        — BrokerClientFactory
    - order_manager.py         — 発注管理
    - order_repository.py      — 注文永続化
    - reconciler.py            — 注文照合
    - risk_manager.py          — リスク管理（RiskConfig 等）
  - portfolio/
    - portfolio_builder.py     — 候補選定 / 重み計算
    - position_sizing.py       — 株数決定 / 集約キャップ
    - risk_adjustment.py       — セクター上限 / レジーム乗数
  - research/
    - factor_research.py       — Momentum / Volatility / Value 計算
    - feature_exploration.py   — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI 連携）
    - regime_detector.py       — レジーム判定（MA200 + マクロセンチメント）
  - data/                      — デフォルトの DB / フラグ等（実行時に生成される）
    - monitoring.db (SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (DUCKDB_PATH)
    - kill.flag / stop_requested.flag / execution.pid

開発者向けメモ
---------------
- テスト / CI:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化できます（テストで便利）
- DuckDB 接続は各リサーチ・AI モジュールへ明示的に渡す設計です（副作用を避ける）
- OpenAI 呼び出しまわりはリトライロジックやレスポンスバリデーションを実装済み（429・ネットワーク断・5xx に対応）
- DB マイグレーション（monitoring_db.init_monitoring_db）は idempotent（既存列チェック・ALTER を行う）

ライセンス / バージョン
-----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス情報はリポジトリルートの LICENSE を参照してください（本 README 提供コードには明示されていません）。

問い合わせ / 貢献
-----------------
- バグ報告や機能提案は Issue を立ててください。プルリク歓迎です。README の追加や改善、テストカバレッジ向上やドキュメント化の貢献も助かります。

以上が本コードベースの概要と利用手順です。実際の運用時は KABUSYS_ENV や各種閾値・API キーの取り扱いに十分注意してください。必要であれば各モジュールの詳細ドキュメント（関数引数・返り値・副作用）を別途生成します。