KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした Python パッケージです。  
主な機能は以下の通りです。

- 発注エンジン（ExecutionEngine）とその監視（Monitoring）
- ペーパートレード用の分離された DB を使った検証モード
- ポートフォリオ構築（候補選定、重み付け、リスク調整、ポジションサイズ計算）
- 価格・財務データを用いたファクター計算・特徴量解析（DuckDB ベース）
- ニュース NLP を使った銘柄センチメント評価（OpenAI API）
- 監視ログの永続化（SQLite）と監視エンジン、Kill Switch（フラグファイル）機構
- 各種ユーティリティ（設定ウィザード、設定検証、ペーパートレード検証レポート生成）

主な機能一覧
-------------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使用し data/paper_trading.db に記録。
  - run_monitoring.py: SystemMonitor のポーリングループを実行。MONITOR_POLL_INTERVAL で間隔を変更可能（デフォルト 60 秒）。
- 設定・検証
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 環境変数・config/*.yaml の事前検証 CLI
- ポートフォリオ構築
  - portfolio/ : 候補選定、スコア・等分配重み、ポジションサイズ計算、セクターキャップ、レジーム乗数
- 研究モジュール
  - research/ : ファクター計算（momentum/value/volatility）、将来リターン、IC 計算、統計サマリ
- AI（OpenAI）
  - ai/news_nlp.py: raw_news を集約し LLM で銘柄別センチメントを算出して ai_scores テーブルへ書き込む
  - ai/regime_detector.py: ETF の MA200 とマクロセンチメントを合成して市場レジーム判定し market_regime テーブルへ書き込む
- 監視
  - monitoring/: system/trade/risk の監視、MonitoringDB（SQLite）永続化、KillSwitch、アラート管理の統合
- ツール
  - tools/paper_verification_report.py: Paper Trading DB を解析して PASS/FAIL 判定を含む検証レポートを出力

セットアップ手順
----------------
1. リポジトリを取得
   - git clone ... （本 README はパッケージのルートに配置されていることを前提とします）

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 可能なら requirements.txt を用意しているはずなので:
     - pip install -r requirements.txt
   - 最小で必要となる主要パッケージ:
     - pip install duckdb psutil openai
   - optional:
     - pip install PyYAML  （validate_config による YAML 検証を行う場合）

4. 環境変数設定（.env）
   - 対話形式で .env を作成:
     - python -m kabusys.config_setup
   - 必須変数（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - OPENAI_API_KEY（AI 機能利用時）
   - デフォルト:
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - KILL_FLAG_CLEAR_ON_START=0

   注意:
   - .env.local が存在する場合は .env を上書きします（OS 環境変数を保護）。
   - .env は絶対に Git にコミットしないでください（機密情報を含むため）。

5. 設定検証
   - python -m kabusys.validate_config
   - 重大なエラーがあれば起動前に修正してください。
   - --strict オプションで警告を FAIL 扱いにできます。

6. 初回データディレクトリ作成（必要に応じて）
   - mkdir -p data logs

使い方（起動例）
----------------
- ExecutionEngine を起動
  - 通常:
    - python -m kabusys.run_execution
  - ペーパートレード:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - ペーパートレード時は settings.paper_sqlite_path（デフォルト data/paper_trading.db）に発注ログ等が書かれ、本番 DB と分離されます。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は MonitoringDB（settings.sqlite_path）に書き込みます。run_monitoring は環境にかかわらず本番 sqlite_path を使用します（監視データは本番 DB に格納）。

- 停止制御 / Kill Switch
  - 実行中のエンジンを停止させたい場合、data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送る仕組みがあります（KillSwitch）。
  - run_* スクリプトは data/stop_requested.flag を見て安全にループを抜けます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite ファイルパスを指定可能（優先度: --db > 環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト）。

- AI 機能（ニューススコアリング / レジーム判定）
  - ai/news_nlp.score_news(conn, target_date, api_key=None)
  - ai/regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（kabusys.config.Settings.duckdb_path）を受け取り DB のテーブルを更新します。OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡してください。

基本的な環境変数（主要）
-----------------------
- JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: execution 環境（development / paper_trading / live）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

ディレクトリ構成（主要ファイル）
-----------------------------
以下は主要モジュールの抜粋。プロジェクトルートに src/kabusys 配下が存在します。

- src/kabusys/
  - __init__.py                 — パッケージ定義（__version__ 等）
  - config.py                   — 環境変数読み込み・Settings クラス（.env 自動ロード機能含む）
  - config_setup.py             — 対話式 .env ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py          — 統一ログ設定（stdout + 日次ローテートファイル）
    - process_priority.py       — プロセス優先度 / CPU affinity 設定ユーティリティ
  - portfolio/
    - portfolio_builder.py      — 候補選定・重み計算
    - position_sizing.py        — 株数決定・丸め・キャップ
    - risk_adjustment.py        — セクター制限・レジーム乗数
  - research/
    - factor_research.py        — ファクター計算（momentum/value/volatility）
    - feature_exploration.py    — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py               — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py        — 市場レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py          — SQLite テーブル定義 & MonitoringDB ラッパー
    - system_monitor.py         — システム状態・データ鮮度監視
    - trade_monitor.py          — 発注 / 約定 / 滞留注文監視（実装参照）
    - risk_monitor.py           — ドローダウン・ポジション上限監視
    - kill_switch.py            — Kill Switch（flag ファイル書き込み）
    - monitoring_engine.py      — 監視エンジンの統合とポーリング
  - execution/                  — ExecutionEngine、OrderManager、BrokerFactory など（発注ロジック）
  - data/                       — データパイプライン・DuckDB スキーマ等（prices_daily / raw_financials 等）
  - monitoring/                 — 監視関連テーブルとロジック（上記）

運用上の注意
------------
- 本番（KABUSYS_ENV=live）での起動前に必ず python -m kabusys.validate_config を実行して設定を確認してください。
- .env に機密情報（API キー等）を含みます。Git 管理下に置かないでください。
- run_execution は起動時に data/stop_requested.flag の存在をチェックします。CI や運用スクリプトで安全に停止要求を出す場合は stop_requested.flag を作成してください（run_monitoring も同様にチェックします）。
- OpenAI API 呼び出しはコスト・レート制限があります。AI 機能を運用する際はキーの管理とコスト計算を行ってください。
- Monitoring は SQLite（settings.sqlite_path）に書き込みます。バックアップやログアーカイブポリシーを検討してください。

補足（開発者向け）
------------------
- logging の設定は kabusys.utils.logging_setup.setup_logging を通して統一されます。ログファイルはデフォルト logs/<app_name>.log に日次ローテートで出力されます。
- process_priority.set_process_priority を用いて起動時にプロセス優先度を高く設定します（権限不足等で失敗する場合は警告でスキップされます）。
- DB スキーマのマイグレーション処理は monitoring_db.init_monitoring_db 内で最低限の互換性を保つよう実装されています（例: 新カラム追加等）。

問題報告・貢献
--------------
バグ報告、改善提案、プルリクエストはリポジトリの issue / PR を利用してください。README にない操作や CLI があればドキュメントを更新していただけると助かります。

以上。必要であれば README に含めるサンプル .env のテンプレートや起動シナリオ（systemd service / docker-compose 例）も作成しますので指示ください。