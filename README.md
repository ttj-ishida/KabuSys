README
=====

概要
----
KabuSys は日本株の自動売買およびそれに付随する分析・監視機能を提供するプロジェクトです。  
主な目的は以下の通りです。

- 戦略に基づいたポートフォリオ構築と発注ロジック（ExecutionEngine）
- 監視（System / Trade / Risk）のポーリングとアラート（Monitoring）
- Paper Trading 用の検証・レポート生成ツール
- DuckDB を使ったデータ分析・ファクター計算（Research）
- ニュースを用いた AI（OpenAI）によるスコアリング・レジーム判定

本リポジトリはライブラリとしての利用（プログラムからの呼び出し）と、起動スクリプトによる常駐運用の両方を想定しています。

主な機能
--------
- ExecutionEngine 起動（run_execution.py）
  - 本番／ペーパートレード両対応（KABUSYS_ENV に依存）
  - paper_trading 環境では MockBrokerClient を利用しデータを data/paper_trading.db に記録
  - PID ファイル管理（data/execution.pid）と停止フラグ監視（data/stop_requested.flag）
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - システム状態（CPU／メモリ／ディスク）、データ鮮度、発注ログなどを定期記録
  - Kill Switch（data/kill.flag）により ExecutionEngine の強制停止トリガ
  - RiskMonitor によるドローダウン／ポジション上限の監視、risk_logs への記録
- Portfolio コンポーネント（portfolio パッケージ）
  - 候補選定、重み計算、ポジションサイズ計算、セクターキャップ・レジーム補正
- Research（research パッケージ）
  - DuckDB を用いたファクター計算（モメンタム／ボラティリティ／バリュー）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ
- AI モジュール（ai パッケージ）
  - ニュースの NLP スコアリング（OpenAI を使用）: kabusys.ai.news_nlp.score_news
  - マーケットレジーム判定（OpenAI と ETF MA を組合せ）: kabusys.ai.regime_detector.score_regime
- ツール
  - 対話式 .env 作成ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

依存関係（主なもの）
-------------------
（プロジェクト内のすべての依存を列挙する requirements.txt は含まれていない想定です。必要に応じて pip 等でインストールしてください。）
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の構文検証を使う場合）
- （ロギングに標準 logging、SQLite3 は標準ライブラリ）

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai PyYAML

4. .env の作成（対話式）
   - python -m kabusys.config_setup
   - ウィザードで J-Quants トークンや Kabu API パスワード、環境（KABUSYS_ENV）などを設定します。
   - 作成後は python -m kabusys.validate_config で設定を検証してください。

5. データ・ログディレクトリ準備（通常は自動作成されますが事前に確認しておくと安全です）
   - data/（SQLite 等の既定パス）
   - logs/（ログ出力先、LOG_DIR 環境変数で変更可）

主な環境変数
-------------
（.env で設定する代表的なキー）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY（AI 機能を使う場合）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
- LOG_DIR（ログ出力先、デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START（0/1、起動時に kill.flag を自動クリアするか）
- MONITOR_POLL_INTERVAL（run_monitoring でポーリング間隔を秒で上書き可能）

注意: 自動 .env ロードはデフォルトで有効。無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

使い方（起動スクリプト）
------------------------

- ExecutionEngine を起動（常駐）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）と MockBrokerClient を使用
    - 実行中は data/execution.pid に PID を書きます
    - data/stop_requested.flag が存在すると起動しない／または実行中に検知して停止します

- Monitoring を起動（常駐ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）
  - 監視は常に（KABUSYS_ENV にかかわらず）本番用 sqlite_path を使用して monitoring DB に記録します
  - data/stop_requested.flag が存在するとループが終了します

- .env の作成・更新（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いで exit(1)

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで別 DB を指定可能（デフォルトは環境変数または data/paper_trading.db）

ログ・PID・フラグファイル
------------------------
- ログ:
  - デフォルト出力: stdout と logs/<app_name>.log（TimedRotatingFileHandler で日次ローテーション、30日保持）
  - LOG_DIR 環境変数で変更可能
- PID ファイル:
  - ExecutionEngine: data/execution.pid（Settings.pid_file_path で変更可能）
- 停止フラグ:
  - data/stop_requested.flag: run_execution / run_monitoring のポーリングループを停止させるために使用
  - data/kill.flag: Kill Switch によって書き込まれると、ExecutionEngine に停止を促す（Execution 側で kill.flag を検知して停止する仕組みがある）

プログラマブル API の利用例
--------------------------
（ライブラリとして呼び出す場合の簡単な例）

- AI ニューススコアリングを直接呼ぶ（DuckDB 接続を渡す）
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect("data/kabusys.duckdb")
  - score_news(conn, target_date=date(2026,4,10), api_key="sk-...")

- ポートフォリオ関係ユーティリティ
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - candidates = select_candidates(signals)
  - weights = calc_equal_weights(candidates)
  - sizes = calc_position_sizes(weights, candidates, ...)

- Research / Factor 計算
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - conn = duckdb.connect("data/kabusys.duckdb")
  - results = calc_momentum(conn, target_date=date.today())

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュールと役割の抜粋です。

- kabusys/
  - __init__.py               — パッケージ定義（バージョン等）
  - config.py                 — 環境変数 / Settings 管理（自動 .env 読み込みロジック含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - utils/
    - logging_setup.py        — ロギング設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - portfolio/
    - portfolio_builder.py    — 候補選定 / 重み計算
    - position_sizing.py      — 株数計算・制約適用
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py  — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — マーケットレジーム判定（OpenAI + ETF MA）
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ / 永続化層
    - system_monitor.py       — システム監視（CPU / メモリ / データ鮮度）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - trade_monitor.py        — （発注ログの監視・整合性チェック等）※本リードミーでは要旨のみ
    - monitoring_engine.py    — 各 monitor を束ねるループ
    - kill_switch.py          — kill.flag の生成・管理
    - alert_manager.py        — （通知の抽象化; LINE 等へ送信）
  - execution/
    - execution_engine.py     — ExecutionEngine 実体（起動・セッション管理）
    - broker_factory.py       — BrokerClient（本番/Mock）生成
    - order_repository.py     — DB 操作（orders/trade_logs 等）
    - order_manager.py        — 発注管理ロジック
    - reconciler.py           — ブローカーとリポジトリの整合
    - risk_manager.py         — 発注前のリスクチェック
  - monitoring/monitoring_db.py — 監視 DB のスキーマと API

運用上の注意
------------
- 本番環境（KABUSYS_ENV=live）では設定ミスが重大な被害につながるため validate_config の出力を必ず確認してください。
- KILL_FLAG_CLEAR_ON_START=1 を本番で設定するのは危険です（kill.flag が誤ってクリアされる可能性があるため推奨されません）。
- AI（OpenAI）関連機能は API キー・コスト・レスポンスの信頼性を考慮して運用してください。API エラー時にはフェイルセーフでスコアを 0.0 にフォールバックする等の保護がありますが、期待通りの動作をするとは限りません。
- ログ・DB のバックアップとディスク容量管理を行ってください（ログは日毎ローテートしますが保存数は環境に応じて調整してください）。

ライセンス / 貢献
-----------------
（ここには実際のプロジェクトのライセンスや貢献ガイドラインを記載してください。README のテンプレート的な注意）

附録: よく使うコマンド例
-----------------------
- .env 作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 起動（開発）
  - KABUSYS_ENV=development python -m kabusys.run_execution

- Execution 起動（ペーパートレード）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Monitoring 起動（デフォルト 60秒）
  - python -m kabusys.run_monitoring

- Monitoring 起動（30秒ポーリング）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート（過去期間指定）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

問題報告・問い合わせ
--------------------
不具合や改善案は issue を立ててください。README の補足やサンプル設定などがあればプルリクエスト歓迎します。