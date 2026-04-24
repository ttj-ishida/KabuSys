README
======

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした小規模なフレームワークです。
主な役割は以下の通りです。
- 発注実行エンジン（ExecutionEngine）とその監視（Monitoring）
- ペーパートレード用の分離 DB と Mock ブローカーサポート
- ファクター計算・特徴量探索（DuckDB を使った分析）
- ニュースを使った LLM ベースのセンチメント評価（OpenAI を利用）
- ポートフォリオ構築・ポジションサイズ算出ロジック
- 監視ログ（SQLite）とアラート / Kill Switch の仕組み

主要な設計方針
- 本番とペーパートレードは DB を分離（KABUSYS_ENV により切替）
- DuckDB を分析用に利用、SQLite を監視 / トレードログ用に利用
- LLM 呼び出しはフェイルセーフ（失敗してもプロセスが停止しない）
- 自動化しやすい CLI（.env 作成ウィザード・設定検証・レポート生成 等）

機能一覧
--------
- 実行エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBroker を利用し、data/paper_trading.db に書込
  - プロセス優先度設定、PID ファイル管理、停止フラグ監視を実装
- 監視ループ起動スクリプト: run_monitoring.py
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリング
  - MONITOR_POLL_INTERVAL によるポーリング間隔変更（デフォルト 60 秒）
  - 停止フラグファイルを検出して安全停止
- 環境設定ウィザード: config_setup.py
  - 対話的に .env を生成 / 更新
- 設定検証 CLI: validate_config.py
  - .env や config/*.yaml（任意）の整合性チェック
- Paper Trading 検証レポート: tools/paper_verification_report.py
  - paper_trading DB を解析して稼働率・成功率・レイテンシ等をレポート出力
- AI 関連:
  - ai.news_nlp: ニュースを OpenAI でセンチメント評価して ai_scores に書き込む
  - ai.regime_detector: ETF (1321) の MA とマクロニュースを使って市場レジーム判定
- 研究 / ファクター:
  - research.factor_research: momentum / volatility / value ファクター計算
  - research.feature_exploration: 将来リターン計算、IC 計算、統計サマリ等
- ポートフォリオ:
  - portfolio.portfolio_builder: 候補選定・重み計算（等金額/スコア重み）
  - portfolio.position_sizing: 株数算出（risk_based / equal / score）
  - portfolio.risk_adjustment: セクター上限・レジーム乗数
- ユーティリティ:
  - utils.logging_setup: 統一ロギング設定（コンソール + 日次ローテートファイル）
  - utils.process_priority: プロセス優先度 / CPU affinity 設定
- 監視永続化:
  - monitoring.monitoring_db: SQLite 用テーブル定義と読み書きラッパー
  - monitoring.kill_switch: data/kill.flag による停止要求発行ロジック
  - monitoring.risk_monitor / system_monitor: ドローダウン・プロセス死活・データ鮮度監視

セットアップ手順
--------------
前提
- Python 3.10 以上（型注釈で | を使用しているため）
- system パッケージ: sqlite3 は標準、外部パッケージは下記をインストールしてください。

推奨手順（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS) または .venv\Scripts\activate (Windows)

2. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - validate_config の YAML 検証を使う場合: pip install PyYAML
   - その他ユーティリティは標準ライブラリを利用

   （プロジェクトに pyproject.toml / requirements.txt があればそちらからインストールしてください）

3. パッケージの参照方法
   - 開発中はプロジェクトルート（src がある階層）で PYTHONPATH を設定するか、
     pip install -e .（パッケージ化されている場合）を使用してください。
   - 例: export PYTHONPATH=$(pwd)/src

4. .env の作成
   - python -m kabusys.config_setup を実行して対話式ウィザードで .env を生成
   - または .env.example を参考に手動で .env を作成してください

5. 設定確認
   - python -m kabusys.validate_config
   - --strict オプションで警告もエラー扱いにできます

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: execution モード（development / paper_trading / live）。デフォルト development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（ai.* を利用する場合）
- LOG_LEVEL / LOG_DIR: ログレベル・ログ保存ディレクトリ
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60）

使い方
------
基本的なコマンド
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB (PAPER_TRADING_SQLITE_PATH) を使い、
      MockBrokerClient を利用して発注をシミュレート（本番 DB と分離される）
    - プロセス優先度が "high" に設定されます（set_process_priority）
    - 停止は data/stop_requested.flag（プロジェクトルート下）や data/kill.flag による制御

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は本番 sqlite_path を使用（環境にかかわらず同じ監視 DB を参照）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

AI / LLM 関連
- ai.news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡し、指定日 (date) に該当するニュースウィンドウを評価して ai_scores を更新
  - OPENAI_API_KEY が必要（api_key 引数でも指定可能）
- ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF の MA とマクロニュースを使って market_regime テーブルへ書込み

停止フラグ / Kill Switch
- デーモン的な運用では data/stop_requested.flag（run_execution / run_monitoring が監視）を作ると
  プロセスは安全に停止します。
- monitoring の KillSwitch は条件（ドローダウンやポジション上限）を満たすと data/kill.flag を書き、
  ExecutionEngine に停止を促します。KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動クリアしますが、
  本番では 0 を推奨します。

ログ
- デフォルトでは logs/<app_name>.log に日次ローテーションで出力されます（30日保持）。
- LOG_DIR 環境変数で保存先を変更できます。ログレベルは LOG_LEVEL。

ディレクトリ構成
----------------
以下は src/kabusys 以下の主要ファイル / モジュール構成（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings クラス（自動 .env ロード機能含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py      — 市場レジーム判定（LLM + MA）
  - research/
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — 将来リターン / IC / 統計
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py        (参照あり — ロジックファイル)
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py        (参照あり)
  - execution/
    - execution_engine.py    (参照あり)
    - order_manager.py       (参照あり)
    - order_repository.py    (参照あり)
    - broker_factory.py      (参照あり)
    - reconciler.py          (参照あり)
    - risk_manager.py        (参照あり)
  - data/                    — 実行時生成される各種 DB / flag / pid 置き場（プロジェクトルートの data/）
  - utils/
    - logging_setup.py
    - process_priority.py
  - research / data / other modules...
  - その他: DuckDB/SQLite を操作するモジュールやツール群

補足・運用ノウハウ
-----------------
- 本番運用では KABUSYS_ENV=live とし、LINE 通知などのアラート設定を確実に行ってください。
- validate_config の出力で WARNINGS が出る場合は必ず内容を確認してください。--strict モードを CI に組み込むと良いです。
- LLM を使う処理は API コストとレイテンシが発生します。頻度やバッチサイズ（news_nlp._BATCH_SIZE）を運用に合わせて調整してください。
- logs ディレクトリ / data ディレクトリはコンテナやサーバで永続化（ボリューム）することを推奨します。
- 単体テストや CI を追加する場合、環境変数の自動ロードを無効化するために KABUSYS_DISABLE_AUTO_ENV_LOAD を使うことができます。

ライセンス / 貢献
-----------------
- この README はコードベースの抜粋に基づくドキュメントです。実運用に移す際はセキュリティ（API キー管理）とテストを十分行ってください。
- 変更や機能追加は PR ベースで管理してください（本リポジトリの CONTRIBUTING.md 等に従ってください）。

以上。必要なら「インストール用 requirements.txt の候補」や「.env の例」を追加で作成します。必要なら教えてください。