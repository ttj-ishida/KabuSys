KabuSys — 日本株自動売買システム
================================

この README はリポジトリ内の主要スクリプト・モジュールを対象に、導入から実行までの手順と各機能の概要を日本語でまとめたものです。

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームです。以下の主要機能を含みます。

- ExecutionEngine：発注・注文管理・リスク管理の実行エンジン（本番/ペーパートレード対応）
- Monitoring：システム稼働状況・注文状態・リスク監視とアラート、Kill Switch（停止フラグ）
- AI 統合：OpenAI を使ったニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）
- Research：DuckDB を用いたファクター計算・特徴量解析
- Portfolio：銘柄選定、ウエイト算出、ポジションサイズ計算、リスク調整
- Tools：Paper Trading 用の検証レポート生成など補助スクリプト

主な機能一覧
--------------
- 実行環境（KABUSYS_ENV）切替
  - development / paper_trading / live
  - paper_trading では MockBroker を利用し、本番 DB と分離された data/paper_trading.db を使用
- 設定ウィザード（.env の対話的作成）: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config [--strict]
- 監視ループ起動: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を参照して監視テーブルを更新
- 実行エンジン起動: python -m kabusys.run_execution
  - 起動時に data/execution.pid を扱い、停止フラグ（data/stop_requested.flag）で安全停止
- AI モジュール
  - kabusys.ai.news_nlp.score_news: ニュースを LLM でスコアリングして ai_scores に書込
  - kabusys.ai.regime_detector.score_regime: ETF + マクロセンチメントを合成して市場レジーム判定
- 研究用モジュール
  - ファクター計算（momentum/volatility/value）や将来リターン・IC 計算
- ポートフォリオ構築
  - 銘柄選定、重み付け（等金額 / スコア重み）、ポジションサイズ計算（単元丸め・リスク制限）
- ツール
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

前提条件 / 推奨環境
-------------------
- Python 3.10+
- 推奨ライブラリ（最低限動かすのに必要なもの）
  - duckdb
  - psutil
  - openai （AI 機能を使う場合）
  - PyYAML（config 検証で YAML がある場合に推奨）
- ファイルシステムの書き込み権限（data/、logs/ ディレクトリ）

インストール（開発環境例）
------------------------
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML

3. パッケージを editable インストール（任意）
   - python -m pip install -e .

設定（.env の作成）
------------------
- 対話式ウィザードで .env を作成・更新:
  - python -m kabusys.config_setup
  - ウィザードは既存の .env を読み込み、Enter で既存値を保持できます。
- 自動ロード:
  - 起動時にプロジェクトルート（.git か pyproject.toml があるディレクトリ）を探して .env/.env.local を自動読み込みします。
  - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

重要な環境変数（主なもの）
--------------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須） — kabuステーション API パスワード
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、MockBroker と PAPER_TRADING_SQLITE_PATH が使われる
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（上書き可能）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動、デフォルト instant）
- OPENAI_API_KEY: OpenAI を用いる機能で必要
- DUCKDB_PATH: data/kabusys.duckdb（DuckDB ファイル）
- SQLITE_PATH: data/monitoring.db（監視用 SQLite）
- LOG_LEVEL: DEBUG|INFO|WARNING|...（ログレベル）
- LOG_DIR: ログ保存先（デフォルト logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（開発用。0 推奨）

設定検証
--------
- 起動前に設定チェックを行うことを推奨:
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱いで exit(1)

実行方法（主要スクリプト）
-------------------------
- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能
  - 停止: data/stop_requested.flag（ファイル作成）を配置するとループが終了
  - ログ: logs/monitoring.log（日次ローテーション）

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使い data/paper_trading.db に記録
  - 起動時に data/execution.pid を参照/作成
  - 停止: data/stop_requested.flag を作成すると安全に停止

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - DB は --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定可能

AI 関連
-------
- news_nlp（ニュースセンチメント）
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - 実行には OPENAI_API_KEY が必要（引数経由でも指定可）
  - 処理は DuckDB 上の raw_news/news_symbols を参照し ai_scores に書き込み
- regime_detector（市場レジーム判定）
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 指標とマクロニュースを組合せて market_regime テーブルに書き込む
- OpenAI 呼び出しはリトライ・フェイルセーフ処理を備えていますが、API キー・ネットワーク回復に注意してください

ログ・プロセス管理・フラグ
-------------------------
- ログ: logs/<app_name>.log（TimedRotatingFileHandler により日次ローテーション、30 日保持）
- PID / Stop フラグ:
  - data/execution.pid — 実行エンジンの PID（起動時に使用）
  - data/stop_requested.flag — 両ループ (execution/monitoring) の外部停止用フラグ
  - data/kill.flag — KillSwitch が書き込む停止用フラグ（実行エンジンに停止シグナルを発行）
- KillSwitch は RiskMonitor の判定（ドローダウン・ポジション上限）に基づき kill.flag を作成し、ExecutionEngine を停止させます
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動で kill.flag を削除します（本番では非推奨）

ディレクトリ構成（コードベースの主な部分）
---------------------------------------
- src/kabusys/
  - __init__.py — パッケージ定義（__version__ など）
  - config.py — 環境変数/.env の読み込み・Settings クラス
  - config_setup.py — .env 対話的ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化・DB 操作ラッパー
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス生存監視
    - trade_monitor.py — （注文周り監視）※詳細はコード参照
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — （アラート送信処理）※詳細はコード参照
  - execution/
    - execution_engine.py — 発注セッション実行ロジック（EngineConfig など）
    - broker_factory.py — Broker クライアント生成（Mock/実ブローカ選択）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 注文・リスク管理
  - portfolio/
    - portfolio_builder.py — 候補選定・スコア順ソート
    - position_sizing.py — 株数計算（単元丸め・スケール調整）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー計算（DuckDB SQL）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュースセンチメントの LLM スコアリング
    - regime_detector.py — 市場レジーム判定（ETF + LLM）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート出力
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定

注意事項 / トラブルシューティング
----------------------------------
- ディレクトリ権限: data/ と logs/ に書き込み権限が必要です。権限不足でログファイルや DB の作成に失敗することがあります。
- OpenAI: AI 機能を利用するには OPENAI_API_KEY が必須です。キーの漏洩に注意し、.env は絶対にリポジトリにコミットしないでください。
- Paper Trading 分離: KABUSYS_ENV=paper_trading を使うと paper_trading 用 DB に記録され、本番 DB と分離されます。試験時はこれを利用してください。
- ライブラリ互換: duckdb, psutil, openai などのバージョンによる差異で挙動が多少変わる可能性があります。validate_config や unit テストで挙動を確認してください。
- SQLite / DuckDB の接続はプロセス内で開いたまま使う設計です。外部からファイルを編集する場合はロック等に注意してください。

開発・拡張
-----------
- モジュールは比較的単機能に分かれており、テストしやすい設計になっています（多くの関数は副作用を持たない純粋関数として実装されています）。
- OpenAI 呼び出しはラップされているため、テスト時は該当関数をモックして外部依存を排除できます（コード内にモック推奨箇所のコメントあり）。

最後に
-----
この README はコードから推測できる範囲の説明をまとめたものです。各コンポーネントの詳細な設計・パラメータはソース内の docstring とコメントを参照してください。質問や追加記載が必要であれば教えてください。