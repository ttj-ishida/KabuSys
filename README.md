README
======

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。  
戦略・ポートフォリオ構築、注文発行（ExecutionEngine）、監視（Monitoring）、研究・ファクター計算、AI（ニュース NLP / レジーム判定）などのコンポーネントを含みます。  
このリポジトリはライブラリ／実行スクリプト群を提供し、ローカル開発、ペーパートレード、本番運用のいずれにも対応する設計になっています。

主な機能
--------
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレードを環境変数で切替。ペーパートレードでは MockBrokerClient を使用し、本番 DB と分離して data/paper_trading.db に記録。
  - リスク管理（RiskManager）、注文管理（OrderManager）、照合（Reconciler）を組み合わせて発注処理を行う。
- Monitoring（監視）
  - SystemMonitor：プロセス生存、CPU / メモリ / ディスク使用率、データ鮮度の監視。
  - TradeMonitor：滞留注文、約定価格の異常検出。
  - RiskMonitor：ドローダウン・ポジション上限の監視とアラート記録。
  - KillSwitch：リスクや上限トリガーで停止フラグを書き込み、ExecutionEngine に停止シグナルを送る。
  - MonitoringEngine：上記モニタを定期ポーリングしてアラートと Kill Switch 評価を行う。
- ポートフォリオ構築（純粋関数群）
  - 候補選定、等配分／スコア加重、ポジションサイズ計算（ロット丸め、上限制約、aggregate cap）、セクターキャップ適用、レジーム乗数。
- 研究／ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を使用、prices_daily / raw_financials テーブル参照）。
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー等。
- AI（OpenAI を利用）
  - news_nlp: ニュース記事を集約して LLM（gpt-4o-mini 等）でセンチメントを計算し ai_scores に書き込む。
  - regime_detector: ETF（1321）の MA とマクロニュースの LLM 評価を合成して市場レジーム（bull/neutral/bear）を判定し永続化。
  - API 呼び出しはリトライやバリデーションを備え、失敗時は安全側のフォールバックを行う。
- ユーティリティ
  - process priority / CPU affinity の設定（psutil ベース）。
  - .env 対話式ウィザード / 設定検証ツール。

前提 / 依存
------------
- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
- 任意（YAML 検証）
  - PyYAML（validate_config が config/*.yaml のパース検証を行う場合）
- SQLite3（標準ライブラリ）、その他ライブラリは requirements.txt があればそちらを利用してください。

セットアップ手順
---------------
1. リポジトリをクローンしてワークディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存インストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai
   - （PyYAML を使う場合）pip install pyyaml

   ※ プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください。

4. .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードに従って J-Quants トークン、kabu API パスワード、データベースパス、KABUSYS_ENV などを設定してください。
   - 生成される .env は絶対に Git にコミットしないでください。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も fail 扱いになります（exit code 1）。

使い方（主要スクリプト）
-----------------------

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - デフォルト（KABUSYS_ENV に従う）:
    - python -m kabusys.run_execution
  - ペーパートレード（環境変数指定例）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - この場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB とは分離されます。
  - 起動時にプロセス優先度を "high" に設定します（psutil を使用）。
  - 実行中はデフォルトで data/execution.pid に PID を書く想定です（Settings.pid_file_path）。

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で変更可能（秒、デフォルト 60）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを記録します。

- 停止／フラグ
  - 実行スクリプトは data/stop_requested.flag（プロジェクトルートの data ディレクトリ）を監視しており、存在すると安全にループを抜けます。手動で停止要求を出すにはこのファイルを作成します（内容は任意）。
  - KillSwitch は data/kill.flag を書き込み、ExecutionEngine 側で受けて動作を停止するトリガーとして使用します（Settings.kill_flag_path の値を使用）。
  - KILL_FLAG_CLEAR_ON_START=1 を設定していると起動時に kill.flag を自動クリアする挙動を許可します（本番では 0 推奨）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数を上書き）
  - 検証基準（README 内定義）
    - 稼働率（uptime） >= 99.0%
    - 注文成立率 >= 90.0%
    - 送信率 >= 95.0%
    - P95 レイテンシ <= 200 ms
  - レポートは標準出力に出力されます。

主要環境変数（抜粋）
-------------------
- 必須（少なくとも設定が必要）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作環境
  - KABUSYS_ENV (default "development")
    - "development" / "paper_trading" / "live"

- データベース / ファイルパス
  - DUCKDB_PATH (default "data/kabusys.duckdb")
  - SQLITE_PATH (default "data/monitoring.db") — 監視 DB（monitoring）
  - PAPER_TRADING_SQLITE_PATH (default "data/paper_trading.db")
  - PID_FILE_PATH (default "data/execution.pid")
  - KILL_FLAG_PATH (default "data/kill.flag")

- Paper トレード
  - PAPER_FILL_MODE (default "instant") — 有効値: instant | partial | never | reject

- ログ / 閾値
  - LOG_LEVEL (default "INFO")
  - CPU_THRESHOLD_PCT (default 90.0)
  - MEMORY_THRESHOLD_PCT (default 85.0)
  - DISK_THRESHOLD_PCT (default 90.0)

- 監視間隔
  - MONITOR_POLL_INTERVAL (default 60 秒) — run_monitoring のポーリング間隔を秒で指定

- OpenAI
  - OPENAI_API_KEY — news_nlp / regime_detector の API 呼び出しに使用

データ / ファイル
-----------------
- data/
  - kabusys.duckdb（DuckDB、分析用）
  - monitoring.db（SQLite、監視ログ）
  - paper_trading.db（SQLite、ペーパートレード用）
  - execution.pid（ExecutionEngine の PID）
  - stop_requested.flag（実行ループ停止用のフラグファイル）
  - kill.flag（KillSwitch による強制停止シグナル）

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys をルートとした構成の抜粋）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env の読み込みと Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 単体のポーリング起動スクリプト
  - utils/
    - process_priority.py     — psutil を使った優先度 / CPU affinity ユーティリティ
  - execution/                — 発注関連（OrderManager, ExecutionEngine, BrokerFactory, 等）
  - monitoring/
    - monitoring_db.py        — SQLite ベースの監視 DB 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        — （アラート送信管理、未完や詳細はコード参照）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング
    - regime_detector.py      — 市場レジーム判定
  - tools/
    - paper_verification_report.py

設計上のポイント / 注意点
------------------------
- .env 自動ロード:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に .env / .env.local を自動読み込みします。自動ロードを抑制するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- データ鮮度チェック:
  - SystemMonitor は DuckDB 上の prices_daily テーブルの最終日時を見てデータ鮮度を判定します（許容差: _FRESHNESS_DAYS = 3 日）。
- ペーパートレードの完全分離:
  - KABUSYS_ENV=paper_trading のときは paper_sqlite_path を使用し、本番 monitoring.db / orders DB と分離するよう設計されています。
- AI 呼び出し:
  - OpenAI API を利用する機能は API キー（OPENAI_API_KEY）が必要です。API 呼び出しにはリトライやレスポンスバリデーションが組み込まれており、失敗時は安全なデフォルトでフォールバックします（例: macro_sentiment=0.0）。
- 実運用上の注意:
  - KABUSYS_ENV=live の場合は LINE トークン等の通知設定を必ず確認してください。validate_config は live のときに特別な警告を出します。
  - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨します（自動で kill.flag を消すと危険）。

開発者向け
----------
- テスト実行やモジュール呼び出しは個々の関数（例: kabusys.ai.news_nlp.score_news、kabusys.ai.regime_detector.score_regime、kabusys.research.calc_momentum 等）を直接インポートして使うことができます。
- DuckDB のスキーマ（prices_daily / raw_financials / raw_news など）に依存するため、研究・AI 機能をローカルで試す場合はサンプルデータでテーブルを作成してください。
- モジュール単体の動作確認用に MonitoringEngine.run_once() を使って一回だけ監視処理を実行できます（テスト用に便利）。

ライセンス / バージョン
-----------------------
- バージョンは kabusys.__version__ = "0.1.0"（コード参照）
- ライセンス情報が別途ある場合はプロジェクトルートの LICENSE 等を参照してください。

お問い合わせ
------------
バグ報告や機能提案はリポジトリの issue にお願いします。初期セットアップや .env 周りで不明点があれば README を更新するためのリクエストを送ってください。

以上。README の補足や特定のセクション（例: ExecutionEngine の詳細な起動オプション、Broker の設定、DB マイグレーション方法）を追記したい場合は指示をください。