README
======

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。
本リポジトリには、実行エンジン（ExecutionEngine）の起動スクリプト、監視（Monitoring）関連のコンポーネント、ポートフォリオ構築・ポジションサイジング・リスク調整の純粋関数群、リサーチ/ファクター計算、AI（ニュースセンチメント・レジーム判定）連携ユーティリティ、管理用ツールが含まれます。

主な特徴
--------
- 実行エンジン起動スクリプト（run_execution.py）
  - 本番 / ペーパートレードを環境変数で切替え（KABUSYS_ENV）
  - ペーパートレード時は MockBroker を用い、専用 SQLite に記録
- 監視プロセス（run_monitoring.py）
  - System / Trade / Risk の監視モジュールをポーリング
  - kill.flag による安全シャットダウン（Kill Switch）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
- モジュール化されたポートフォリオ構築
  - 候補選定、等金額/スコア加重、リスクベースのポジション決定
  - セクター上限・レジーム乗数の適用
- リサーチ機能（DuckDB を使ったファクター計算）
  - モメンタム、ボラティリティ、バリュー等の計算関数
- AI 統合
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント（ai.score_news）
  - マクロニュース + ETF MA による市場レジーム判定（ai.score_regime）
- 管理ツール
  - .env 対話型ウィザード（config_setup.py）
  - 起動前設定検証 CLI（validate_config.py）
  - ペーパートレード検証レポート生成ツール（tools/paper_verification_report.py）
- 汎用ユーティリティ
  - ロギング設定（logs 日次ローテーション）
  - プロセス優先度 / CPU affinity 設定
  - SQLite ベースの監視 DB ラッパー（監視ログ & ダッシュボード）

セットアップ
-----------
1. Python 環境
   - Python 3.9+ を推奨（プロジェクトがサポートするバージョンに合わせてください）
   - 仮想環境を作成してアクティベートすることを推奨します。

2. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai
   - PyYAML は設定ファイルの検証時に任意で使用します（validate_config.py で警告抑制）。

3. ディレクトリ作成（デフォルトを使用する場合）
   - data/ — SQLite や制御フラグ（kill.flag / stop_requested.flag / execution.pid）などを置く
   - logs/ — ログファイル出力
   例:
     mkdir -p data logs

4. .env の用意
   - 対話型ウィザードで作成:
       python -m kabusys.config_setup
   - もしくはプロジェクトルートに .env を配置（.env は絶対に Git にコミットしないこと）。
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV（development | paper_trading | live）
   - デフォルトの DB / ログパスは .env に記載可能（DUCKDB_PATH, SQLITE_PATH など）。

設定検証
--------
- 起動前に設定の整合性をチェック:
    python -m kabusys.validate_config
  - 警告もエラー扱いにする場合:
    python -m kabusys.validate_config --strict

使い方（実行例）
----------------

1. ExecutionEngine（注文実行）の起動
   - 本番 / ペーパーは KABUSYS_ENV で切替え（.env で設定）
   - 実行:
       python -m kabusys.run_execution
   - 注意:
     - ペーパートレード時は settings.is_paper が True になり、別 SQLite（PAPER_TRADING_SQLITE_PATH）を使用します。
     - 起動時に data/stop_requested.flag が存在すると起動を行いません。
     - 実行中に停止するには data/stop_requested.flag を作成するか、kill.flag を作成して監視側から止める運用も可能。

2. Monitoring（監視プロセス）の起動
   - 実行:
       python -m kabusys.run_monitoring
   - オプション:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定（デフォルト 60）
     - 監視は常に本番用 sqlite_path（settings.sqlite_path）を使用してログを残します。

3. ペーパートレード検証レポート生成
   - SQLite の paper_trading DB を対象にレポートを作成:
       python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB は data/paper_trading.db。--db でパス指定可能。

4. AI スコアリング / レジーム判定
   - Python から直接利用（例: REPL やスクリプト）:
       from kabusys.ai import score_news
       # duckdb_conn は DuckDB の接続オブジェクト、target_date は datetime.date
       score_news(duckdb_conn, target_date, api_key="sk-...")

       from kabusys.ai.regime_detector import score_regime
       score_regime(duckdb_conn, target_date, api_key="sk-...")
   - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を使用。

ロギング
--------
- setup_logging が全スクリプトで使用されます。
- デフォルト出力先:
  - コンソール（stdout）
  - ファイル: logs/<app_name>.log（日次ローテーション、30日保管）
- ログレベルは .env の LOG_LEVEL または引数で設定可能。

停止 / Kill Switch
-----------------
- 手動停止用フラグ:
  - data/stop_requested.flag — run_execution/run_monitoring スクリプトが検知して安全終了
  - data/kill.flag — KillSwitch によって書き込まれ、ExecutionEngine 停止を誘発
- 資金やドローダウンなどの条件で自動的に kill.flag を作成するよう設計されています（監視側で評価）。

環境変数一覧（主要）
--------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能を使う場合)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（例: INFO、DEBUG）
- MONITOR_POLL_INTERVAL（監視ポーリング秒。run_monitoring で使用）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（Settings 経由で利用）

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定管理
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py             — ニュース NLP（OpenAI）によるセンチメント
  - regime_detector.py      — レジーム判定
- monitoring/
  - monitoring_db.py        — SQLite 監視 DB ラッパー
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py
- execution/                — (Engine / OrderManager / BrokerFactory 等の実装が存在する想定)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

data/ と logs/
- data/                    — デフォルト DB / フラグ / pid ファイルを置く場所
  - monitoring.db           — デフォルト監視 DB（SQLITE_PATH）
  - paper_trading.db        — ペーパートレード DB（PAPER_TRADING_SQLITE_PATH）
  - kill.flag
  - stop_requested.flag
  - execution.pid
- logs/                    — ログファイル（日毎ローテート）

開発・運用上の注意
------------------
- .env は機密情報を含むため、絶対にリポジトリにコミットしないでください。
- KABUSYS_ENV=live では設定ミスが重大な実取引に繋がるため validate_config で事前検証を強く推奨します。
- OpenAI API 呼び出し部分は外部サービス依存です。コスト・レート制限に注意してください。
- DuckDB / SQLite のパスは運用要件に応じて適切に設定してください（バックアップやディスク容量の監視を推奨）。
- ロギングディレクトリ作成に失敗した場合はコンソール出力のみで継続されます（setup_logging 内でハンドリング）。

ライセンス・バージョン
----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現行: 0.1.0）。
- ライセンス情報はリポジトリルートの LICENSE を参照してください（存在しない場合はプロジェクトルールに従ってください）。

さらに詳しい運用や拡張
--------------------
- Execution/Monitoring の詳細な実装（発注フロー、ブローカー抽象、再実行/再送等）は execution パッケージ内を参照してください。
- DuckDB を使ったリサーチ処理は大量データ向けに最適化されています。データ投入パイプラインは data.pipeline 等の実装を参照してください。
- AI 関連はレジーム検出・ニューススコアリングの実験フェーズに合わせてパラメータ（モデル / バッチサイズ / トリム長）を調整可能です。

問い合わせ・貢献
----------------
バグ報告や機能追加の提案は Issue を立ててください。Pull Request は歓迎します。README には主要な使い方と注意点を記載しましたが、実環境へのデプロイ前に十分なテストを行ってください。