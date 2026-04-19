README
=====

概要
----
KabuSys は日本株向けの自動売買 / 研究プラットフォームです。  
戦略の研究・ファクター計算、ポートフォリオ構築、注文発行（本番 / ペーパートレード両対応）、およびシステム監視・アラート・Kill Switch 機構を備えています。AI（OpenAI）を用いたニュースセンチメントや市場レジーム判定機能も含まれます。

主な設計方針
- ルックアヘッドバイアスを避ける実装（datetime.today()等を直接参照しない設計）
- 本番 DB とペーパートレード DB の分離
- フェイルセーフ：API 失敗時はフォールバックして継続
- モジュール化されテストしやすい純粋関数群（ポートフォリオ構築・リスク計算等）

特徴一覧
--------
- 実行エンジン（ExecutionEngine）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカー抽象化（MockBrokerClient / 実ブローカー）
  - リスク管理・オーダーマネージャ・再整合（Reconciler）
- 監視コンポーネント
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視結果は SQLite に永続化（monitoring.db）
  - Kill Switch（条件により data/kill.flag を書き込み Execution を停止）
- データ基盤 / 研究ツール
  - DuckDB ベースのファクター計算（momentum, volatility, value 等）
  - 特徴量探索・IC 計算・将来リターン計算
- AI 機能
  - ニュースを LLM（OpenAI）でスコアリングし ai_scores に書き込み
  - マクロニュース + ETF MA による市場レジーム判定
- ペーパートレード検証
  - レポート生成スクリプト（tools/paper_verification_report.py）
- 補助ユーティリティ
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - 統一的なログ設定ユーティリティ、プロセス優先度設定

前提（推奨）
-------------
- Python 3.10+
- 必須ライブラリ（pip インストール）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
- 任意:
  - PyYAML（config/*.yaml のパース検証を行う場合）

セットアップ手順
----------------

1. リポジトリをクローン / チェックアウト
   - プロジェクトルートに移動してください（.git または pyproject.toml を含むディレクトリ）。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate   （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 必要に応じて requirements.txt があれば利用してください。無ければ最低限:
     - pip install duckdb psutil
     - （OpenAI 機能を使う場合）pip install openai
     - （YAML 検証をしたい場合）pip install pyyaml

4. 環境変数 (.env) の作成
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参考にしてください）。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - PAPER_FILL_MODE（ペーパートレード時の約定挙動: instant | partial | never | reject）
     - LOG_LEVEL（例: INFO）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにするには --strict を付与

起動・使い方
------------

1. 監視ループを起動（SystemMonitor）
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
   - 監視は常に本番 sqlite_path を参照（環境に依らず monitoring DB は本番パスを使用する旨に注意）。

2. 実行エンジンを起動（ExecutionEngine）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録して本番 DB と分離します。
   - 実行はバックグラウンドスレッドで行われ、data/execution.pid に PID が出力されます。
   - 停止は data/stop_requested.flag または Kill Switch による data/kill.flag により行います。

3. .env の Kill Switch/Stop フラグ
   - Kill Switch (data/kill.flag) は Monitoring が条件を満たした場合に書き込まれます（ExecutionEngine は起動時にオプションでクリアできます）。
   - 停止フラグ (data/stop_requested.flag) を置くと run_execution/run_monitoring はループを終了します。

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB は data/paper_trading.db。--db で別パス指定可能。

5. AI 機能
   - ニューススコアリング: kabusys.ai.score_news を呼び出す（OpenAI API キーが必要）。
   - レジーム判定: kabusys.ai.regime_detector.score_regime を呼び出す（同じく API キーが必要）。
   - 実行スクリプトで呼び出す際は OPENAI_API_KEY を設定してください。

ログ・DB・ファイルパス（デフォルト）
-----------------------------------
- ログディレクトリ: logs/（app_name により logs/execution.log などに出力）
- DuckDB: data/kabusys.duckdb
- SQLite (監視): data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db
- 実行 PID: data/execution.pid
- Kill Flag: data/kill.flag
- Stop Flag: data/stop_requested.flag

ディレクトリ構成（抜粋）
-----------------------
プロジェクトの主要なモジュール構成（src/kabusys 配下）:

- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
- run_execution.py         — ExecutionEngine 起動スクリプト
- config.py                — 環境変数 / 設定読み込みロジック
- config_setup.py          — .env 生成ウィザード
- validate_config.py       — 設定検証 CLI

- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ

- monitoring/
  - monitoring_db.py       — SQLite 永続化層
  - system_monitor.py      — システム状態・データ鮮度監視
  - trade_monitor.py       — （発注ログ監視: コードベースに存在）
  - risk_monitor.py        — ドローダウン / ポジション制限監視
  - kill_switch.py         — kill.flag 管理
  - monitoring_engine.py   — 各モニタを束ねるエンジン
  - alert_manager.py       — （アラート送信管理: コードベースに存在）

- execution/
  - execution_engine.py    — ExecutionEngine（発注セッション制御）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py      — ブローカークライアント生成（Mock / 実ブローカー切替）

- portfolio/
  - portfolio_builder.py   — 銘柄選定・スコアソート
  - position_sizing.py     — 株数計算・資金配分ロジック
  - risk_adjustment.py     — セクター制限・レジーム乗数

- research/
  - factor_research.py     — Momentum / Volatility / Value 等ファクター計算
  - feature_exploration.py — 将来リターン計算・IC 計算・統計サマリ

- ai/
  - news_nlp.py            — ニュースセンチメント（OpenAI）
  - regime_detector.py     — マクロ + MA によるレジーム判定

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート

注意事項 / 運用上のヒント
------------------------
- KABUSYS_ENV を "live" に設定する前に、必ず validate_config を実行して設定を確認してください。--strict モードでは警告も失敗扱いになります。
- 本番運用時は KILL_FLAG_CLEAR_ON_START は 0 を推奨（自動クリアを無効にする）。
- AI 機能は API コストとレイテンシが発生します。OpenAI のレート制限や課金に注意してください。
- ログディレクトリ作成に失敗した場合、ログはコンソール出力のみになります。systemd / supervisor 等で実行する場合はログ周りを適切に設定してください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状: 0.1.0）。

問い合わせ / 開発
-----------------
- 開発者向け: ソースはモジュールごとに分離され、ユニットテストを実装しやすい設計になっています。CI での静的解析・型チェック（mypy）・テストの導入を推奨します。

以上。必要であれば、README に含める具体的な .env.example や systemd ユニット、Docker 化手順、より詳しい運用手順を追加で作成します。どの情報を優先して追加しますか？