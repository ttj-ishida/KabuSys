README
=====

概要
----
KabuSys は日本株向けの自動売買システム（プロトタイプ）です。  
戦略の研究用ファクター計算やポートフォリオ構築、発注実行エンジン、システム監視・アラート、LLM を使ったニュースセンチメント／市場レジーム判定などの主要コンポーネントを含みます。

主な機能
--------
- 実行エンジン（ExecutionEngine）
  - ブローカー抽象化（本番 / ペーパートレード切替）
  - 注文管理・リスク管理・リコンサイル
- 監視（Monitoring）
  - システム状態（CPU/メモリ/ディスク）ログ記録
  - データ鮮度チェック、プロセス生存確認
  - トレードログ・リスクログの永続化（SQLite）
  - Kill Switch（条件を満たしたらエンジン停止フラグを書き込む）
- ポートフォリオ構築
  - 候補選定、重み計算、セクターキャップ、ポジションサイズ計算
- リサーチ
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン、IC 計算、統計サマリ
- AI（OpenAI）統合
  - ニュースのセンチメント付与（ai_scores へ保存）
  - マクロニュースと ETF を使った市場レジーム判定
- ツール
  - Paper Trading 向け検証レポート生成スクリプト
- 設定支援
  - .env 対話式ウィザード（config_setup）
  - 起動前設定検証（validate_config）
- ロギング / プロセス優先度ユーティリティ

動作環境 / 必要条件
-------------------
- Python 3.10 以上（型アノテーションの union 演算子などを使用）
- 推奨インストールパッケージ（例）:
  - duckdb
  - psutil
  - openai
  - pyyaml（config 検証で YAML をパースする場合に必要）
  - （標準ライブラリの sqlite3 等は不要）
- 実行に必要な外部サービス:
  - kabuステーション API（本番発注時）
  - OpenAI API（ニュース NLP / レジーム判定を使う場合）

セットアップ手順
----------------
1. リポジトリをクローンし、作業ディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - 実際の要件はプロジェクトに requirements.txt があればそちらを利用してください。

4. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants / kabuステーション / DB パスなど主要変数を生成します。
   - 生成後、次のコマンドで設定検証を行ってください:
     - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります。

重要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用トークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、MockBrokerClient が使用され DB は data/paper_trading.db に分離される
- DUCKDB_PATH — DuckDB（分析用）のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（monitoring.db）のパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード時の専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI 呼び出しに必要（news_nlp / regime_detector）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

データ・ログファイル
--------------------
- デフォルト DB / ファイル:
  - data/kabusys.duckdb (DuckDB)
  - data/monitoring.db (監視ログ用 SQLite)
  - data/paper_trading.db (ペーパートレード用 SQLite)
  - logs/<app_name>.log （ログファイル、setup_logging により作成）
  - data/execution.pid（ExecutionEngine の PID ファイル）
  - data/kill.flag（Kill Switch 用フラグ）
  - data/stop_requested.flag（外部からループ停止を指示するためのフラグ）
- run_monitoring は KABUSYS_ENV に関係なく sqlite_path（本番監視 DB）を使用します。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使い本番 DB と分離します。

使い方（主要コマンド）
--------------------
- .env の作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
  - 起動中に data/stop_requested.flag を作成すると起動を抑止 / 停止判定を行います（ファイル存在を監視）。
  - Kill Switch（監視が条件に達した際に data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります）。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 停止要求: data/stop_requested.flag を作成すると監視ループは終了します。

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB の指定:
    - --db オプション、もしくは環境変数 PAPER_TRADING_SQLITE_PATH を使用

- AI モジュール（プログラムから呼び出す）
  - ニューススコア付与:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
    - api_key が None の場合は環境変数 OPENAI_API_KEY を参照
  - レジーム判定:
    - from kabusys.ai import regime_detector
    - regime_detector.score_regime(duckdb_conn, target_date, api_key=None)

停止・強制停止の仕組み
---------------------
- stop_requested.flag: run_monitoring と run_execution はこのファイルの存在を監視し、存在時は安全に停止します（外部からの停止要求用）。
- kill.flag: Monitoring の KillSwitch がリスクトリガーを検出した際に書き込みます。ExecutionEngine は起動時や稼働中に kill.flag を検出すると停止します。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動でクリアしますが、本番では 0 を推奨します。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings 管理、.env 自動ロード
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 起動前設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py            — ニュースの LLM スコアリング
  - regime_detector.py     — 市場レジーム判定（ETF + LLM）
- monitoring/
  - monitoring_db.py       — SQLite スキーマ / 永続化層
  - system_monitor.py      — システム状態・データ鮮度監視
  - trade_monitor.py       — （トレード監視：滞留注文／約定異常検出）
  - risk_monitor.py        — ドローダウン／ポジション数監視
  - kill_switch.py         — kill.flag 書き込みロジック
  - monitoring_engine.py   — 各 Monitor をまとめるループ
  - alert_manager.py       — （アラート送信管理（LINE 等））
- portfolio/
  - portfolio_builder.py   — 候補選定・重み付け
  - position_sizing.py     — 株数決定・資金配分
  - risk_adjustment.py     — セクターキャップ・レジーム乗数
- research/
  - factor_research.py     — ファクター計算（momentum/value/vol）
  - feature_exploration.py — IC / forward returns / summary
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成
- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity 設定

補足 / 運用上の注意
-------------------
- run_monitoring は監視用 DB（SQLITE_PATH）を使用します。監視は環境に依らず本番用 sqlite_path を参照する設計です（監視対象は常に本番 DB を想定）。
- run_execution は KABUSYS_ENV=paper_trading の場合に PAPER_TRADING_SQLITE_PATH を使用し、本番と注文履歴を分離します。
- OpenAI を利用する機能は API 呼び出しの失敗に対してフェイルセーフ（スコア 0 やスキップ）を実装していますが、API キーの設定と利用上限には注意してください。
- ログは setup_logging を通じてコンソール（stdout）と logs/<app>.log に出力されます。ログディレクトリは自動作成されますが、権限エラーが起きた場合はファイル出力が無効化されコンソールのみになります。
- 本リポジトリには本番環境での金銭授受を行うコード（発注実行処理）が含まれているため、本番稼働前に設定・リスクパラメータを十分検討してください。

開発・寄稿
----------
- テストや開発は KABUSYS_ENV=development を使用してください。ペーパートレードは paper_trading を利用して注文処理を切り分けられます。
- バグ修正・機能追加は pull request を通して行ってください。重大な変更はドキュメントと設定検証ツールの更新をお願いします。

以上

（この README はコードベースのソースから生成した概要と操作手順をまとめたものです。詳細な設計や運用ルールは各モジュールの docstring を参照してください。）