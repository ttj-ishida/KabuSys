KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視機能を備えた小規模なパッケージです。本リポジトリは次の機能群を含んでいます。

- 注文実行エンジン（ExecutionEngine）とブローカークライアントファクトリ（paper/live 切替）
- 監視コンポーネント（System / Trade / Risk モニタ、Kill Switch、アラート連携）
- ポートフォリオ構築（銘柄選定、重み計算、位置サイズ算出、セクター上限）
- リサーチ（ファクター計算、将来リターン、IC 計算、統計サマリー）
- AI ユーティリティ（ニュースセンチメント、レジーム判定：OpenAI を利用）
- ユーティリティ CLI：.env ウィザード、設定検証、Paper Trading レポート

主な特徴
--------
- 環境（development / paper_trading / live）の切替に応じた挙動（paper_trading は本番 DB と分離）
- DuckDB（分析用）と SQLite（監視 / 発注履歴）の併用設計
- kill.flag による外部からの安全停止（Kill Switch）
- OpenAI（gpt-4o-mini）を使ったニュース NLP と市場レジーム判定（API キー必須）
- 日次ログローテーション（logs/<app>.log）と標準化されたログ設定
- Pure function によるポートフォリオ構築 / リスク調整 / ポジションサイズ計算（単体テストしやすい）

前提（推奨）
-------------
- Python 3.10+
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証オプション）
- SQLite（標準ライブラリ）
- ネットワーク環境（本番で kabuステーション、J-Quants、OpenAI などと通信する場合）

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （オプション）pip install pyyaml

   （プロジェクトに requirements.txt が無い場合は上記パッケージを個別にインストールしてください）

4. .env（環境変数）を用意する
   - 対話式ウィザードで作成: python -m kabusys.config_setup
   - あるいは .env.example を参考に .env を手動作成
   - ウィザードは既存 .env を読み込み、対話的に編集して保存します

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります

主要な環境変数（一部）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- OPENAI_API_KEY — AI 機能利用時に必須
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視 DB デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB デフォルト: data/paper_trading.db
- LOG_LEVEL — デフォルト: INFO
- LOG_DIR — デフォルト: logs/
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — 監視 / 停止に関する設定
- PAPER_FILL_MODE — paper_trading の約定挙動（instant | partial | never | reject）

主な使い方
----------
- 環境設定（.env）を作る:
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（リアル or paper_trading は KABUSYS_ENV に従う）:
  - python -m kabusys.run_execution
  - paper_trading 環境では MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
  - 起動時に data/stop_requested.flag が存在すると起動を拒否

- Monitoring（SystemMonitor のポーリングループ）を起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒、デフォルト 60）
  - 監視は常に本番 sqlite_path（SQLITE_PATH）を使用します

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH

- AI 機能（ニューススコアリング／レジーム判定）:
  - OPENAI_API_KEY を設定後、プログラムから kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼ぶ
  - 例: score_news(conn, target_date, api_key=None) — api_key を省略すると環境変数 OPENAI_API_KEY が使われます

停止 / Kill Switch
------------------
- 外部から ExecutionEngine を停止するには data/kill.flag を作成します（KillSwitch が検出すると停止シグナルを出します）。
- KillSwitch は RiskMonitor 等の結果に基づき自動で data/kill.flag を書き込むことがあります。
- data/stop_requested.flag が存在すると run_execution/run_monitoring の起動ループ・スレッドは停止します。
- ExecutionEngine の PID は data/execution.pid に記録されます（起動時に使用）。

ログ
----
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一管理されます。
- デフォルトで logs/<app_name>.log に日次ローテーションでログが出力されます（30 日保持）。
- コンソール出力は stdout に出ます（cron/Task Scheduler での扱いを考慮）。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py             — 環境変数 / Settings 管理（.env 自動ロード機能含む）
- config_setup.py       — .env 対話式ウィザード（python -m kabusys.config_setup）
- validate_config.py    — 起動前チェック CLI（python -m kabusys.validate_config）
- run_execution.py      — ExecutionEngine 起動スクリプト
- run_monitoring.py     — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ
- ai/
  - news_nlp.py         — ニュースセンチメント（OpenAI でスコアリング）
  - regime_detector.py  — 市場レジーム判定（MA + マクロセンチメント合成）
- monitoring/
  - monitoring_db.py    — SQLite 用永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py   — システム状態・データ鮮度監視
  - trade_monitor.py    — （省略：注文監視ロジック）
  - risk_monitor.py     — ドローダウン / ポジション上限監視
  - kill_switch.py      — kill.flag 書き込みユーティリティ
  - monitoring_engine.py— 複数 Monitor を束ねるエンジン
  - alert_manager.py    — （省略：通知送信の抽象）
- execution/
  - broker_factory.py
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py — 銘柄選定・重み付け
  - position_sizing.py   — 発注株数計算（リスクベース / equal / score）
  - risk_adjustment.py   — セクター上限・レジーム乗数
- research/
  - factor_research.py   — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン / IC / 統計
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成ツール
- utils/
  - logging_setup.py     — ログ設定ユーティリティ
  - process_priority.py  — プロセス優先度 / CPU affinity 設定ユーティリティ

設計上の注意点 / 運用のヒント
----------------------------
- paper_trading 環境は本番 DB とは分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- AI（OpenAI）を利用する機能は API キーが必須で、呼び出しに失敗してもフェイルセーフで継続する設計ですが、本番ではレート制限やコストに注意してください。
- ログディレクトリ作成に失敗した場合はファイル出力が無効になりコンソール出力のみになります（警告が出ます）。
- kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START）は本番環境では 0（無効）を推奨します。
- データ鮮度（prices_daily 等の DuckDB テーブル）に依存する監視やレジーム判定は、必ずデータ更新パイプラインが正しく走ることを確認してください。

開発 / テスト
--------------
- 多くの関数は純粋関数（副作用無し）として実装されており、ユニットテストが書きやすくなっています（portfolio/*, research/* 等）。
- OpenAI／外部 API 呼び出し部はラッパー化してあり、テスト時はモックによる差し替えが可能です（モジュール内の _call_openai_api を patch する等）。

ライセンス / 著作権
-------------------
- 本 README にライセンス情報が無い場合はリポジトリに含まれる LICENSE ファイルを参照してください。

補足
----
- README に記載の内容はコードから抽出した要点です。実際の運用前に python -m kabusys.validate_config による検証を強く推奨します。
- 具体的な ExecutionEngine の設定や Broker クライアントの実装（kabuステーション連携など）は execution/* 内を参照してください。

お問い合わせ / 変更履歴
---------------------
- バージョン: 0.1.0 (パッケージ内 __version__ に基づく)

必要があれば README に実際のコマンド例・.env のテンプレート・起動手順のチェックリストなどを追加で作成します。どの項目を補足しますか？