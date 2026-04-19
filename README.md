README
=====

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を行う小規模なフレームワークです。  
主な目的は以下をサポートすることです:

- 戦略の研究（ファクター計算・特徴量解析）
- ポートフォリオ構築（候補選定・ウェイト計算・ポジションサイズ決定）
- 実行エンジン（paper/live 切替、発注・リスク管理・約定ログ）
- 監視（システム稼働状況・注文状態・リスクの定期チェック）
- AI（ニュースセンチメント・レジーム判定）を用いた補助機能
- Paper Trading の検証レポート生成

主な設計方針として「テスト容易性」「ルックアヘッドの回避（日時依存を直接参照しない）」「フェイルセーフ（API失敗時の安全フォールバック）」が守られています。

機能一覧
--------
- 設定管理
  - .env / .env.local からの自動読み込み（プロジェクトルートを基準）
  - config_setup.py による対話式 .env 作成ウィザード
  - validate_config.py による起動前チェック

- 実行エンジン
  - run_execution.py で起動
  - KABUSYS_ENV に応じて paper_trading（MockBrokerClient）/ live（実ブローカ）を切替
  - PaperTrading は本番 DB と分離（デフォルト: data/paper_trading.db）
  - プロセス優先度を high に設定（可能な場合）

- 監視
  - run_monitoring.py によるポーリングループ
  - system / trade / risk の各モニタを組み合わせた MonitoringEngine
  - kill.flag による ExecutionEngine 停止（KillSwitch）
  - stop_requested.flag による安全停止（外部からの即時停止）

- ポートフォリオ構築（純粋関数群）
  - 候補選定、等金額／スコア加重配分、リスク調整（セクターキャップ・レジーム乗数）
  - 株数決定（リスクベース／等分／スコア基準）、単元株丸め、aggregate cap

- リサーチ
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン計算、IC（スピアマンランク相関）、統計サマリー

- AI 統合（OpenAI）
  - ニュースを LLM でスコアリングして ai_scores に格納（news_nlp）
  - マクロニュース + ETF MA を使ったレジーム判定（regime_detector）
  - リトライや出力バリデーションを備えた堅牢な実装

- ツール
  - paper_verification_report: Paper Trading DB を用いた検証レポート生成

前提条件
--------
- Python 3.10+（コードは型アノテーションを使用）
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai (AI 機能利用時)
  - PyYAML（config YAML の検証を行う場合）
- Git/プロジェクトルート（.git または pyproject.toml がある場所）にて実行推奨

セットアップ手順
----------------
1. リポジトリをクローンしてプロジェクトルートへ移動:

   - 例: git clone ... && cd <project>

2. Python 仮想環境を作成して有効化:

   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係をインストール:

   - pip install duckdb psutil openai PyYAML
   - （requirements.txt があればそれを使う）

4. .env を作成（対話ウィザード）:

   - python -m kabusys.config_setup
   - ウィザードは .env を生成します。生成後は必ず .env を Git にコミットしないでください。

5. 設定検証（任意）:

   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6. （任意）データディレクトリの作成:

   - デフォルトでは data/ 下に DB・PID・フラグ等を作成します。必要に応じてパーミッションを確認してください。

環境変数（主なもの）
-------------------
- JQUANTS_REFRESH_TOKEN（必須） — J-Quants API 用
- KABU_API_PASSWORD（必須） — kabuステーション API パスワード
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
  - paper_trading: MockBrokerClient を使用し data/paper_trading.db に記録
  - live: 実際のブローカ API を使用（注意して設定を確認してください）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

使い方
------
起動スクリプト
- 実行エンジン（ExecutionEngine）起動:
  - python -m kabusys.run_execution
  - 起動時に data/execution.pid が書かれ、内部スレッドでエンジンが動きます。
  - _STOP_FLAG（data/stop_requested.flag）が存在すると起動を行わず終了します。

- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（デフォルト 60）。
  - 監視は monitoring DB（Settings.sqlite_path）へログを残します。Monitoring は実行環境にかかわらず本番 sqlite_path を使用する設計です。

停止と Kill Switch
- 外部から即時停止（監視ループ / 実行エンジンの終了）:
  - stop: プロジェクトルートの data/stop_requested.flag ファイルを作ると run_execution / run_monitoring はループを抜けます（run_execution は flag 検知で engine.stop()）。
- 安全停止（ポートフォリオリスクに起因する停止）:
  - KillSwitch が条件を満たすと data/kill.flag を作成し、ExecutionEngine を停止シグナルで止めます。
  - KILL_FLAG_CLEAR_ON_START=1 にしていると起動時に自動で kill.flag を削除します（本番では 0 推奨）。

ログ
- ログはデフォルトで logs/ ディレクトリに日次ローテーションで出力されます（logs/<app_name>.log）。
- setup_logging(app_name="execution" or "monitoring") が各スクリプトで呼ばれます。
- LOG_LEVEL 環境変数でログの詳細度を調整できます。

Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - DB は --db または環境変数 PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）で指定
  - 稼働率・注文成功率・レイテンシ等を集計して PASS/FAIL 判定を出力します

AI 機能（ニューススコアリング / レジーム判定）
- OpenAI API キー（OPENAI_API_KEY）を設定して利用します。
- モジュール関数:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- これらは DuckDB 接続（duckdb.connect(...) の戻り値）を受け取り、ai_scores / market_regime テーブルへ書き込みます。
- API の失敗時もフォールバック処理を行うためシステムは堅牢です。

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py              — 環境変数読み込み・Settings 定義（.env 自動ロードロジック含む）
- config_setup.py        — .env 対話式ウィザード
- validate_config.py     — 起動前設定検証ツール
- run_execution.py       — ExecutionEngine 起動スクリプト
- run_monitoring.py      — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ（主要）
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - （発注・リスク管理・発注履歴管理の実装）
- monitoring/
  - system_monitor.py        — システム/データ鮮度監視
  - trade_monitor.py         — 注文滞留・約定異常検出（ファイル中で参照あり）
  - risk_monitor.py          — ドローダウン・ポジション上限監視
  - monitoring_db.py         — SQLite テーブル定義・読み書きラッパ
  - kill_switch.py           — kill.flag の作成/管理
  - monitoring_engine.py     — 各 Monitor のポーリング統括
  - alert_manager.py         — アラート送信（LINE 等）※実装参照
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - （候補選定、重み付け、ポジション量計算、セクター制限等）
- research/
  - factor_research.py       — ファクター計算（momentum/value/volatility）
  - feature_exploration.py   — 将来リターン・IC・統計サマリ
- ai/
  - news_nlp.py              — ニュース NLP スコアリング（OpenAI 利用）
  - regime_detector.py       — レジーム判定（MA + マクロ NLP）
- tools/
  - paper_verification_report.py — Paper Trading レポート出力ツール
- utils/
  - logging_setup.py         — 共通ログ設定
  - process_priority.py      — プロセス優先度/CPU affinity 設定ユーティリティ

補足・運用上の注意
-----------------
- .env は機密情報を含むため絶対にリポジトリへコミットしないでください。
- 本番（KABUSYS_ENV=live）では kill.flag の自動クリア設定（KILL_FLAG_CLEAR_ON_START）は 0 を推奨します。
- OpenAI 用 API キーは適切なレート制限とコスト管理のもとで運用してください。
- DuckDB / SQLite のパスは環境変数で変更できます。運用時は永続ストレージ上に配置してください。
- プロセス優先度や CPU affinity の設定はプラットフォームによって異なり、権限不足で失敗する可能性があります（警告が出ますが処理は継続します）。

ライセンス / バージョン
----------------------
- パッケージバージョン: src/kabusys/__version__ = "0.1.0"
- ライセンス情報はプロジェクトルートの LICENSE を参照してください（存在する場合）。

以上。必要に応じて README にコマンド例や運用手順（systemd / supervisor の Unit ファイル例、バックアップ方針、DB 初期化スクリプト等）を追加できます。どの情報を優先して追記したいか教えてください。