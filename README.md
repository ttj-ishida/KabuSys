KabuSys — 日本株自動売買システム (概要 README)
================================================

概要
----
KabuSys は日本株向けの自動売買システム／研究基盤です。本リポジトリには以下の主要コンポーネントが含まれます。

- ExecutionEngine: 発注・リスク管理・注文再突合せを行う実行部
- Monitoring: システム状態・注文状況・リスク監視と Kill Switch
- Research / AI: ファクター計算、特徴量探索、ニュース NLP（OpenAI を利用）
- Portfolio: 銘柄候補選定／重み付け／ポジションサイズ計算
- ユーティリティ: 設定ウィザード、設定検証、ログ設定、プロセス優先度調整 など

特徴（機能一覧）
----------------
- 実行（Execution）
  - 本番 / ペーパートレード（KABUSYS_ENV により切替）
  - BrokerClientFactory 経由でブローカー差し替え可能（paper_trading では MockBrokerClient）
  - リスク管理（ポジション上限、ドローダウン等）
  - 注文履歴の永続化（SQLite / duckDB 連携）

- 監視（Monitoring）
  - システム状態（CPU/メモリ/ディスク）、データ鮮度、Execution プロセスの生存監視
  - 注文の滞留・約定異常などの監視
  - Kill Switch（data/kill.flag）による ExecutionEngine 停止シグナル発行
  - 管理用ポーリングスクリプト（MONITOR_POLL_INTERVAL で間隔指定可）

- 研究（Research）
  - ファクター計算（モメンタム / バリュー / ボラティリティ 等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（OpenAI を利用）
  - ニュースのセンチメントスコアリング（news_nlp）
  - 市場レジーム判定（regime_detector）
  - API 呼び出しはリトライとフォールバックを備えた堅牢実装

- ツール類
  - .env 対話式ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 用検証レポート生成ツール（kabusys.tools.paper_verification_report）

必須 / 推奨依存パッケージ
-----------------------
（プロジェクトに requirements.txt は同梱されていない想定のため代表的な依存を列挙します）
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の構文チェックを行う場合）
- その他: sqlite3 は標準ライブラリ

セットアップ手順
----------------

1. リポジトリをクローンし仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - pip install duckdb psutil openai pyyaml
   - （必要に応じて他の依存を追加）

3. 環境変数の準備（.env）
   - 対話式ウィザードを使って .env を作成:
     - python -m kabusys.config_setup
   - あるいは .env を手動で配置（.env.example を参照して必要なキーを設定）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY を設定

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱う:
     - python -m kabusys.validate_config --strict

5. データディレクトリ / ログディレクトリ
   - デフォルトで data/ と logs/ を使用します。必要なら環境変数でパスを変更してください。
   - デフォルト DB パス:
     - DuckDB: data/kabusys.duckdb (環境変数 DUCKDB_PATH)
     - SQLite (monitoring): data/monitoring.db (環境変数 SQLITE_PATH)
     - Paper trading SQLite: data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)

基本的な使い方
--------------

- 実行エンジン（ExecutionEngine）起動
  - 本番／開発／ペーパートレードの切り替えは KABUSYS_ENV で指定
    - development, paper_trading, live
  - 起動コマンド:
    - python -m kabusys.run_execution
  - paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録されます。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒、デフォルト 60）
  - 監視は常に本番用の sqlite_path を使用（監視ログは本番 DB に保存）

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話式に作成・更新できます

- 設定検証
  - python -m kabusys.validate_config
  - config/*.yaml の存在・YAML パース（PyYAML 必須）や環境変数の妥当性をチェックします

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定する場合: --db PATH（デフォルトは PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- AI / 研究機能
  - Python API として利用:
    - ニューススコアリング: from kabusys.ai.news_nlp import score_news
      - score_news(conn, target_date, api_key=None)
    - レジーム判定: from kabusys.ai.regime_detector import score_regime
      - score_regime(conn, target_date, api_key=None)
    - 各種ファクター計算: from kabusys.research import calc_momentum, calc_volatility, calc_value, ...
  - OpenAI API キー（OPENAI_API_KEY）が必要。関数は api_key 引数経由でも与えられます。

運用上の注意点
---------------
- Kill Switch / Stop フラグ
  - Kill Switch は data/kill.flag を作成して ExecutionEngine に停止シグナルを送ります（KillSwitch クラス）。
  - run_monitoring/run_execution は data/stop_requested.flag を見てループを終了します。
  - ExecutionEngine の PID 管理ファイル: data/execution.pid（run_execution が使用）

- ロギング
  - ログはデフォルト logs/ ディレクトリに日次ローテーション（30日保持）で出力されます。
  - 環境変数 LOG_DIR, LOG_LEVEL で挙動を変更可能。

- DB
  - monitoring（system_status, trade_logs, positions, risk_logs, dashboard）は SQLite（defaults: data/monitoring.db）
  - DuckDB は分析用途（prices_daily, raw_financials, raw_news 等）で使用（defaults: data/kabusys.duckdb）
  - Paper trading は本番 DB と分離して data/paper_trading.db を使用（KABUSYS_ENV=paper_trading）

- 権限・プラットフォーム
  - プロセス優先度設定（psutil を利用）を行います。権限不足で設定に失敗する場合は警告が出ます。
  - CPU affinity 操作等はプラットフォームに依存するため失敗時はフォールバックします。

主な環境変数（抜粋）
-------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能利用時必須)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- KABUSYS_ENV (development / paper_trading / live) — default: development
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- MONITOR_POLL_INTERVAL (監視ポーリング間隔秒、default: 60)
- PAPER_FILL_MODE (instant/partial/never/reject) — paper_trading 時のモック約定挙動

ディレクトリ構成（主要ファイル）
----------------------------
以下はソースツリー（src/kabusys 配下）の要約です。実際のツリーはプロジェクトルート直下に src/ がある構成です。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境設定読み込み・Settings クラス
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - logging_setup.py            — ログ設定ユーティリティ
    - process_priority.py         — プロセス優先度・CPU affinity
  - monitoring/
    - monitoring_db.py            — SQLite 監視 DB 層
    - system_monitor.py
    - trade_monitor.py            — （存在、監視ロジック）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py            — （アラート送信ロジック等）
  - execution/                    — Execution 関連（Engine, BrokerFactory, OrderManager 等）
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
  - data/                         — （データ生成 / pipeline モジュール等: prices_daily など）
  - その他モジュール...

ライセンス / バージョン
---------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。
- ライセンスはリポジトリルートの LICENSE 等をご確認ください（本サンプルに LICENSE ファイルがない場合は別途付与してください）。

トラブルシューティング
---------------------
- .env が正しく読み込まれない / 自動ロードを無効にしたい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化します。
- PyYAML がないと config/*.yaml の内容検証がスキップされます（validate_config 警告）。
- OpenAI 呼び出しで 429 やネットワーク障害が発生しても、モジュールはリトライ＆フォールバックで安全に動作する設計です（ただし API キーは必須）。

補足
----
この README はコードベースの主要機能と運用方法の概観を示します。開発や運用の際は config/*.yaml や各モジュールの docstring・関数コメントも参照してください。必要であれば導入手順（systemd ユニットの例、Docker 化、詳細な運用手順）について別途ドキュメントを作成します。