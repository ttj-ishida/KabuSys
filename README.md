# KabuSys

KabuSys は日本株の自動売買／研究フレームワークです。シグナル生成・ポートフォリオ構築・発注管理・監視・研究ツール群を含むモジュール化されたコードベースを提供します。本リポジトリはローカル開発・ペーパートレード・本番運用を想定した設計になっています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提条件 / 依存関係
- セットアップ手順
- 実行方法（使い方）
- 主要設定項目（環境変数）
- ディレクトリ構成（主要ファイル説明）
- 運用メモ / よく使うファイル

---

プロジェクト概要
- 日本株自動売買システム（KabuSys）
- DuckDB を用いた研究／ファクター計算、SQLite による監視ログ保存、外部ブローカー API（kabuステーション）とのインタフェース、OpenAI を使ったニュース NLP / レジーム判定等を含む。
- 開発／ペーパートレード／本番（live）を環境切替可能。環境設定は .env ファイルまたは環境変数で管理。

主な機能一覧
- 実行エンジン起動スクリプト（run_execution）
  - 環境に応じて実際の BrokerClient / MockBrokerClient を切替（KABUSYS_ENV=paper_trading でペーパー用 DB に分離）。
  - RiskManager / OrderManager / ExecutionEngine の組立てと起動。
  - 停止フラグ（data/stop_requested.flag）検出で安全停止。
- 監視ポーリング（run_monitoring, MonitoringEngine）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期実行し、監視ログを SQLite に永続化。
  - KillSwitch による停止判定・flag 書き込み、AlertManager 経由の通知（LINE 等を想定）。
  - MONITOR_POLL_INTERVAL で間隔を調整可能。
- 監視 DB 層（monitoring.monitoring_db）
  - system_status, trade_logs, positions, risk_logs, dashboard などのテーブル作成・アップサート API。
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等重・スコア重み、ポジションサイズ計算（単元株・上限・スケール調整など）。
- 研究モジュール（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等ファクター計算、将来リターン、IC 計算、統計サマリー。DuckDB を用いた純粋関数群。
- AI モジュール（kabusys.ai）
  - news_nlp: OpenAI（gpt-4o-mini 等）でニュースをスコア化して ai_scores に保存。
  - regime_detector: ETF（1321）の MA とマクロニュースで市場レジームを判定し保存。
- 運用ユーティリティ
  - config_setup: 対話式ウィザードで .env を生成・更新
  - validate_config: .env と config/*.yaml の検証 CLI
  - tools.paper_verification_report: ペーパートレード検証レポート生成

前提条件 / 依存関係
- Python 3.10 以上（PEP 604 の型記法などを利用）
- 外部パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 内容検証時に任意）
- SQLite は標準ライブラリで使用
- ネットワークアクセス: kabuステーション API（実運用時）、OpenAI API（AI モジュール）

参考インストール（例）
- 仮想環境を作成しアクティベート
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージをインストール
  - pip install duckdb psutil openai pyyaml

セットアップ手順
1. リポジトリをクローンして作業ディレクトリへ移動
2. Python 環境を準備（上記）
3. 環境変数の設定
   - 対話式で .env を作成: python -m kabusys.config_setup
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - 本番運用時は KABUSYS_ENV=live、開発・テストは development または paper_trading
4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱う
5. DB / data ディレクトリ
   - デフォルトの DB / データディレクトリは data/ 以下に作成されます
   - DuckDB: data/kabusys.duckdb（DUCKDB_PATH）
   - SQLite 監視 DB: data/monitoring.db（SQLITE_PATH）
   - Paper Trading 用（環境により別ファイル）: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
6. OpenAI を使う場合
   - OPENAI_API_KEY を .env に設定するか、score_news / score_regime 呼出時に明示的に渡す

使い方（主要コマンド）
- .env 作成（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 振る舞い
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading SQLite に分離して記録
    - 起動時に data/stop_requested.flag があると起動しない
    - 実行中は data/execution.pid に PID を書く（停止時に削除される想定）
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60 秒）
  - 監視は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用（監視データは本番 DB を想定）
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH 環境変数または --db で DB 指定可能
- AI モジュール（プログラムからの呼び出し）
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key=None)
  - score_regime は kabusys.ai.regime_detector.score_regime を使用
  - どちらも OPENAI_API_KEY の環境変数か api_key 引数を必須または渡す

主要設定項目（環境変数）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）
- PAPER_FILL_MODE: paper_trading 時のフィルモード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1 = 自動クリア、開発用）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動で .env を読み込まない（テスト用）

運用ファイル / フラグ
- data/kill.flag: KillSwitch が書き込む停止フラグ（ExecutionEngine が読み検知し停止）
- data/stop_requested.flag: run_execution / run_monitoring 起動ループが検知する停止フラグ（ユーザが手動で作成して停止）
- data/execution.pid: 実行エンジンの PID（SystemMonitor が存在確認）
- データベースファイル: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db

ディレクトリ構成（主要ファイルの説明）
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env 自動ロードロジック、Settings クラス（アプリ設定）
  - config_setup.py
    - .env を対話式に作成・更新するウィザード
  - validate_config.py
    - 起動前設定検証 CLI
  - run_execution.py
    - ExecutionEngine を構築して起動するエントリポイント
  - run_monitoring.py
    - SystemMonitor のポーリング起動スクリプト
  - utils/
    - process_priority.py
      - プラットフォームに依存しないプロセス優先度・CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py
      - SQLite テーブル作成 & MonitoringDB ラッパー（ログ書き込み API）
    - system_monitor.py
      - CPU / メモリ / ディスク / データ鮮度 / 実行プロセスの監視
    - trade_monitor.py
      - 注文滞留・約定異常価格の監視
    - risk_monitor.py
      - ドローダウン・ポジション上限監視とダッシュボード更新
    - kill_switch.py
      - kill.flag 書き込みロジック
    - monitoring_engine.py
      - 各 Monitor を束ねポーリング / アラート送信・KillSwitch 評価
    - alert_manager.py
      - （通知送信ロジック、コードベースに実装あり。LINE 等の通知を想定）
  - execution/
    - broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager, order_record など（発注・リスク管理・調整ロジック）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py（銘柄選定・重み・数量計算）
  - research/
    - factor_research.py, feature_exploration.py（ファクター計算・IC 等）
  - ai/
    - news_nlp.py（ニュースセンチメントの OpenAI 呼び出し・DB 書き込み）
    - regime_detector.py（マクロニュース + ETF MA によるレジーム判定）
  - tools/
    - paper_verification_report.py（ペーパートレード検証レポート生成）

運用メモ / 注意事項
- 自動 .env 読み込みはプロジェクトルート検出（.git または pyproject.toml）に基づく。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- monitoring は Settings.sqlite_path（通常 data/monitoring.db）を使用：監視ログは本番 DB を基本に想定。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使用し本番 DB とは完全分離。
- AI モジュールは OpenAI API 呼び出しに依存するため、API キーと呼び出し制限・コストに注意。
- KillSwitch はリスクイベント（例: ドローダウン閾値超過）で data/kill.flag を書き込み、ExecutionEngine が検知して停止する仕組み。
- データファイル（data/）は Git 管理対象外にすること（.env と同様に機密情報や履歴を含む可能性があるため）。

トラブルシューティング
- モジュールが YAML をパースできない、あるいは PyYAML がない場合、validate_config は該当検証をスキップして警告を出力します。PyYAML を入れると検証が厳密になります。
- psutil の一部機能（CPU affinity / priority）はプラットフォームや権限に依存して失敗することがあります。失敗時は警告を出力してスキップします。
- DuckDB / SQLite のバージョンによる executemany の挙動差異に注意（コード内に互換考慮のコメントあり）。

追加情報
- 各モジュールのドキュメントや設計メモはソースコード内の docstring / コメントで詳述されています。まずは config_setup → validate_config → run_monitoring / run_execution の順で動作確認することを推奨します。
- 研究目的であれば src/kabusys/research を参照し、DuckDB に prices_daily / raw_financials 等のテーブルをロードして実験してください。

もし README に追加したいコマンド例、依存関係の固定（requirements.txt）や CI/CD のセットアップなど要望があれば教えてください。README をそれに合わせて拡張します。