README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤です。本リポジトリは以下の主要機能を含むモジュール群で構成されています。

- 発注・実行エンジン（ExecutionEngine）
- 監視・アラート基盤（Monitoring）
- ポートフォリオ構築・ポジションサイジング（portfolio）
- リサーチ（ファクター計算・特徴量解析）
- AI を使ったニュースセンチメント / レジーム判定（OpenAI）
- 設定ウィザード・検証ツール、運用用ユーティリティ類

設計方針のハイレベル要点：
- 本番用とペーパートレードは DB を分離（KABUSYS_ENV により切替）
- .env による環境変数管理（config_setup による対話的作成）
- ログは統一的に設定（Console + 日次ローテート）
- 外部 API（OpenAI 等）はキーを環境変数で渡す設計
- ルックアヘッドバイアス防止を意識した設計（date.today() へ依存しない等）

主な機能一覧
--------------
- Execution
  - 実際のブローカークライアントまたは MockBrokerClient（paper_trading）を用いた発注処理
  - RiskManager / OrderManager / Reconciler 等のコンポーネントで堅牢化
- Monitoring
  - SystemMonitor：CPU・メモリ・ディスク・プロセス生存チェック、データ鮮度チェック
  - TradeMonitor：注文ログ・滞留注文・約定異常検出（ソース内に実装）
  - RiskMonitor：ドローダウン・ポジション数監視、kill.flag 書き込み
  - MonitoringEngine：ポーリングループで各モニタを呼び出しアラート・KillSwitch 評価
  - SQLite に監視ログ永続化（monitoring_db.init_monitoring_db）
- Portfolio
  - 候補選定、等金額/スコア加重配分、リスクベースのポジション算出
  - セクター集中制限、レジーム乗数
- Research
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）などの解析ユーティリティ
- AI
  - news_nlp.score_news：OpenAI を使ってニュースを銘柄毎にセンチメントスコア化し ai_scores に保存
  - regime_detector.score_regime：ETF（1321）MA 乖離とマクロニュースセンチメントを合成してレジーム判定
- Tools
  - paper_verification_report：Paper Trading の履歴を集計し PASS/FAIL 判定を出力
- 設定管理
  - config_setup.py：対話式 .env ウィザード
  - validate_config.py：起動前の環境変数 / config/*.yaml 検証

前提 / 要件
------------
最低限の実行に必要な環境（例）
- Python 3.9+（型注釈にオプションの union 型を使用しているため 3.10 推奨）
- パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- SQLite（標準ライブラリ）
- ネットワークアクセス（OpenAI を使う場合）
注：pyproject.toml / requirements.txt がある場合はそれに従ってください（本スニペットでは未提示）。

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （必要に応じて他のパッケージも追加）

3. .env の作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で .env を作成
   - 重要: .env は秘密情報を含むため絶対に Git にコミットしないでください

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱い（exit 1）

5. DB 初期化
   - 監視用 SQLite は実行時に自動でテーブル作成されます（monitoring_db.init_monitoring_db）
   - DuckDB ファイルは必要に応じて prices_daily 等のテーブルを投入してください（データ準備は別途）

環境変数（主なもの）
--------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db） — Monitoring 用
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START（1 にすると起動時に kill.flag を自動クリア。production では 0 推奨）
- KABUSYS_DISABLE_AUTO_ENV_LOAD（1 にすると自動で .env を読み込まない）

実行方法 / 使い方
------------------

起動スクリプト（モジュール実行）
- ExecutionEngine（注文実行）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading 用 DB に記録
    - 実行中は data/execution.pid を作成
    - data/stop_requested.flag / data/kill.flag を監視して安全停止
- Monitoring（システム監視ループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60）
  - 監視は常に settings.sqlite_path（本番監視 DB）を使用する
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを指定可能（PAPER_TRADING_SQLITE_PATH 環境変数も使用可）

AI / リサーチ関係（プログラム API）
- news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB の接続オブジェクトを渡し、指定日分のニュースを OpenAI で評価して ai_scores に書き込む
  - api_key を None にすると環境変数 OPENAI_API_KEY を参照
- regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA 乖離 + マクロニュース で市場レジーム判定して market_regime テーブルに書き込む

運用上のファイル / フラグ
- data/execution.pid — ExecutionEngine の PID 管理用（起動時に設定）
- data/stop_requested.flag — 監視/実行ループ用の停止フラグ（存在するとループ終了）
- data/kill.flag — KillSwitch が書き込む停止フラグ（ExecutionEngine 停止トリガー）
- デフォルトの DB / ログパスは .env でカスタマイズ可能

ロギング
--------
- setup_logging(app_name="...") を全スクリプトで使用
- stdout（StreamHandler） + 日次ローテートファイル（logs/<app_name>.log）に出力
- LOG_DIR / LOG_LEVEL 環境変数で挙動制御

監視・Kill Switch の基本挙動
----------------------------
- RiskMonitor がドローダウン／ポジション上限を検出すると risk_logs に記録し、KillSwitch が条件を満たせば data/kill.flag を作成
- MonitoringEngine は各種アラート条件を評価し AlertManager を通じて通知（実装に依存）
- kill.flag は既に存在する場合は再書き込みせず冪等性あり。clear() で削除可能（起動時の自動クリアは設定で制御）

ディレクトリ構成（主要ファイル）
---------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings クラス（.env 自動ロード機能あり）
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 起動前検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト

modules/
- execution/               — 発注・実行関連（Engine, OrderManager, BrokerFactory 等）
- monitoring/
  - monitoring_db.py       — SQLite テーブル初期化 / 永続化 API
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py
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
- utils/
  - logging_setup.py
  - process_priority.py

tools/
- tools/paper_verification_report.py

ドキュメント参照先
-----------------
- PortfolioConstruction.md, StrategyModel.md 等（コード中に参照があるがこのリポジトリで同梱されていれば参照）
- .env.example（存在する場合）を参照して環境変数を準備してください

運用上の注意
------------
- .env に含む機密情報は漏洩しないよう管理（Git へコミットしない）
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨
- OpenAI 等の外部 API 呼び出しは費用・レート制限に注意
- ログディレクトリ作成やプロセス優先度設定で権限不足が発生する可能性がある（警告ログが出るが稼働は継続）

トラブルシュート（よくある問題）
--------------------------------
- .env が自動読み込みされない場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認
  - プロジェクトルートが .git または pyproject.toml を含むか確認（自動検出のため）
- OpenAI 呼び出しで失敗する場合:
  - OPENAI_API_KEY の有無、ネットワーク、レートリミットを確認
- 監視ループが停止しない場合:
  - data/stop_requested.flag を作成して停止を試す
  - 実行中の PID は data/execution.pid を確認

付記
----
本 README はソース内の docstring / コメントを基に自動生成された要約です。内部実装の詳細は各モジュールの docstring を参照してください。プロジェクトに付属する追加ドキュメント（md ファイル等）があればそちらも併せて参照してください。