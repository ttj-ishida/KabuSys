README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買 / リサーチ / モニタリング用ライブラリ群です。本リポジトリは発注エンジン、監視・アラート、ポートフォリオ構築、ファクター・リサーチ、LLM を使ったニュース解析などをモジュール化して提供します。実行スクリプトはローカル開発・ペーパートレード・本番を想定した設定をサポートします。

主な特徴
--------
- ExecutionEngine（発注エンジン）と監視（Monitoring）を分離した実行スクリプト
- Paper Trading（モックブローカー）対応（本番 DB と分離）
- 監視ログを SQLite に永続化（system_status / trade_logs / risk_logs / positions / dashboard）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- ファクター計算（Momentum / Volatility / Value 等）とリサーチユーティリティ
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント / レジーム判定（API キー必須）
- 簡易的な .env ウィザード（対話式）、設定検証 CLI、レポート生成ツール

必須依存関係（例）
-----------------
以下は主要な依存パッケージです。プロジェクトに合わせて requirements.txt を作成してください。

- Python 3.10+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config ファイル検証を行う場合、任意）

セットアップ手順
----------------

1. リポジトリをクローン・チェックアウト
   - 通常の Python パッケージとして扱えるように src 配下を PYTHONPATH に含めるか、pip install -e . でインストールしてください。

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - これにより .env が生成されます。必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を入力してください。

5. 設定検証
   - python -m kabusys.validate_config
   - オプション --strict を付けると警告も失敗扱いになります。

主要な環境変数
---------------
（.env に設定する主なキー）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (instant | partial | never | reject) — ペーパートレードの約定挙動
- OPENAI_API_KEY (AI 機能を使う場合)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- LOG_DIR (ログ保存先、デフォルト: logs/)
- KILL_FLAG_CLEAR_ON_START (0/1) — 本番での自動クリアは注意

使い方（起動スクリプト）
-----------------------

- 環境準備後、まず .env を作成・検証してください（上記参照）。

1. 監視ループ起動（Monitoring）
   - python -m kabusys.run_monitoring
   - 補足:
     - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
     - 監視は Settings.sqlite_path（通常 data/monitoring.db）を使用します（監視 DB は本番環境も同じパスを参照します）。
     - 停止させるにはプロジェクトルートの data/stop_requested.flag を作成（または既存ファイル）してください。スクリプトはこのファイルの存在を検知してループを抜けます。

2. 発注エンジン起動（ExecutionEngine）
   - python -m kabusys.run_execution
   - 補足:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、デフォルトで data/paper_trading.db を使います（本番 DB と完全分離）。
     - エンジンは実行中に PID ファイル（data/execution.pid）を作成します。
     - 停止させるには data/stop_requested.flag を作成するか、モニタリング側の KillSwitch が条件を満たした場合 data/kill.flag が書き込まれ、ExecutionEngine に停止指示が送られます。

3. 設定検証（CLI）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit 1）扱いになります。

4. .env 作成ウィザード
   - python -m kabusys.config_setup

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     - --from YYYY-MM-DD, --to YYYY-MM-DD
     - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数またはデフォルトを上書き）

ログ
---
- ログはデフォルトで stdout と logs/<app_name>.log に出力されます（TimedRotatingFileHandler、日次ローテーション、30 日保持）。
- setup_logging(app_name=...) でアプリ名を指定します（例: "monitoring", "execution"）。
- LOG_DIR 環境変数でログ保存先を変更できます。

停止 / Kill スイッチの挙動
-------------------------
- run_monitoring/run_execution はプロジェクトルートの data/stop_requested.flag をチェックして安全に終了します（運用者が作成することで停止）。
- KillSwitch（監視ロジック）は条件（ドローダウン、ポジション上限等）に応じて data/kill.flag を作成し、ExecutionEngine 側で検出するとエンジン停止処理を実行します。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動クリアしますが、本番では 0 を推奨します。

AI 機能（ニュース NLP / レジーム判定）
-----------------------------------
- ニュース NLP: kabusys.ai.news_nlp.score_news() — raw_news / news_symbols テーブルを参照して ai_scores を更新します。
- レジーム判定: kabusys.ai.regime_detector.score_regime() — ETF 1321 の MA とマクロニュースを組み合わせて market_regime を更新します。
- どちらも OpenAI API キー（OPENAI_API_KEY）が必要です。API 呼び出しはリトライ・フォールバック実装を含みますが、API キーが未設定だと例外になります。

ディレクトリ構成（抜粋）
-----------------------
以下は src/kabusys 以下の主要ファイル・パッケージ（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動ロード・Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py       — 共通ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化・永続化 API
    - system_monitor.py      — システム状態 / データ鮮度監視
    - trade_monitor.py       — （取引監視ロジック。ファイル参照）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - monitoring_engine.py   — 複数 Monitor を束ねる実行器
    - alert_manager.py       — （アラート送信ロジック。ファイル参照）
  - execution/
    - execution_engine.py    — ExecutionEngine 本体（起動は run_execution）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - data/                    — デフォルトの DB・PID・フラグファイル置き場（運用時に作成される）

（注）上のツリーは主要ファイルを抜粋したものです。細かなユーティリティや未記載のモジュールも含まれます。

サンプル .env（最小例）
---------------------
以下は最小限の例（機密情報は実運用時に適切に管理してください）。

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

よくある運用フロー
------------------
1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. 監視プロセスを起動（python -m kabusys.run_monitoring）
4. 発注エンジンを起動（python -m kabusys.run_execution）
5. 必要に応じて Paper Trading レポート（python -m kabusys.tools.paper_verification_report）
6. 異常検知 → モニタが kill.flag を書き込み → エンジンが停止

注意事項 / 運用上の注意
---------------------
- .env は機密を含むため絶対にリポジトリにコミットしないでください。
- KABUSYS_ENV=live の設定時は特に設定値（API トークン、Kill Switch 設定、ログレベル等）を十分に確認してください。validate_config は live 時に追加警告を出します。
- OpenAI 等の外部 API を利用する機能はコスト・レイテンシの影響を受けます。API キーと利用ポリシーに注意してください。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します（setup_logging の設計）。

貢献 / 拡張
------------
- 新しいブローカーの追加は execution/broker_factory.py を拡張してください。
- 戦略やファクターは research/* に追加、ポートフォリオ構築は portfolio/* を拡張してください。
- 監視ルールやアラート送信は monitoring/* の各モジュールを修正・追加してください。

ライセンス
----------
（プロジェクトのライセンス情報をここに記載してください。省略されている場合はリポジトリの LICENSE を参照してください。）

問い合わせ
----------
実装や利用に関する質問がある場合は、プロジェクトの issue または担当者へ連絡してください。

以上。README はプロジェクトのコード構成・運用フローに対応する概要をまとめたものです。必要であれば、導入手順や運用手順（systemd / supervisor 用のユニットファイル例、CI/CD スクリプト、requirements.txt 生成など）を追記します。