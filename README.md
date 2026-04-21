# KabuSys — 日本株自動売買システム (README)

このリポジトリは、研究・ポートフォリオ構築・発注・監視を含む日本株自動売買システムのコアモジュール群です。  
以下はコードベースから抽出した概要、機能、セットアップ手順、使い方、ディレクトリ構成の説明です。

目次
- プロジェクト概要
- 機能一覧
- 前提条件
- セットアップ手順
- 実行方法（使い方）
- 環境変数（主なもの）
- 開発・運用の運用上の注意
- ディレクトリ構成（主要ファイルの説明）

────────────────────────
プロジェクト概要
────────────────────────
KabuSys は日本株向けの自動売買システムで、以下の主要コンポーネントを含みます:
- シグナル生成・ファクター計算（research）
- ポートフォリオ構築（portfolio）
- 発注・注文管理・リスク管理（execution）
- 監視・アラート・Kill Switch（monitoring）
- ニュース NLP（OpenAI）やレジーム判定（ai）
- 運用補助ツール（設定ウィザード、設定検証、検証レポート）

設計方針として、DuckDB / SQLite をデータ層に使い、外部 API 呼び出し（kabuステーション / J‑Quants / OpenAI 等）は明示的に扱います。Paper Trading 用に本番 DB と分離する仕組みがあります。

────────────────────────
機能一覧
────────────────────────
- 設定ウィザード: .env を対話的に生成・更新（kabusys.config_setup）
- 設定検証: .env や config/*.yaml の不足・不整合を検出（kabusys.validate_config）
- 実行エンジン起動スクリプト: ExecutionEngine を起動（kabusys.run_execution）
  - KABUSYS_ENV=paper_trading で MockBroker を使用し paper_trading DB に記録
- 監視ループ起動スクリプト: SystemMonitor のポーリング実行（kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL でポーリング間隔上書き可能（デフォルト 60秒）
- 監視機能:
  - システム状態・データ鮮度監視（SystemMonitor）
  - 注文ログ監視（TradeMonitor）
  - ドローダウンやポジション上限監視（RiskMonitor）
  - Kill Switch（条件を満たすと data/kill.flag を書き込み）
  - 監視結果の永続化（SQLite: monitoring_db）
- ポートフォリオ関連:
  - 候補選定、等重/スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数
- 研究用モジュール:
  - ファクター（Momentum, Volatility, Value）計算（DuckDB）
  - 将来リターン、IC、統計サマリー
- AI 関連:
  - ニュースを OpenAI でスコア化して ai_scores に格納（kabusys.ai.news_nlp）
  - マクロニュース + ETF MA を使った市場レジーム判定（kabusys.ai.regime_detector）
- ユーティリティ:
  - 統一ログ設定（logs に日次ローテート）
  - プロセス優先度 / CPU affinity 設定
- 運用ツール:
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

────────────────────────
前提条件
────────────────────────
- Python 3.10 以上（型注釈で | 演算子を使用）
- SQLite（Python 標準ライブラリで利用）
- DuckDB（python-duckdb パッケージ）
- psutil（プロセス情報・優先度設定）
- openai（OpenAI API クライアント） — AI 機能を使う場合
- （任意）PyYAML（validate_config で config/*.yaml を検証する場合）

必要なパッケージの例:
pip install duckdb psutil openai pyyaml

────────────────────────
セットアップ手順
────────────────────────
1. リポジトリ取得
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai
   - （オプション）pip install pyyaml

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参照）
   - 自動ロード: デフォルトでプロジェクトルートの .env と .env.local を読み込みます。
     - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 警告を厳密に扱う場合は --strict を付ける

6. データディレクトリの作成
   - デフォルトで data/ と logs/ が使用されます。必要に応じて .env のパスを変更してください。

────────────────────────
使い方（実行例）
────────────────────────
- 監視ループの起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔の上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は monitoring 用 sqlite（Settings.sqlite_path）を使用します（環境に依らず本番 sqlite_path を参照します）。
  - 停止: スクリプト実行中に data/stop_requested.flag が作られるか、Ctrl+C（KeyboardInterrupt）

- 実行エンジン（ExecutionEngine）の起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定した場合:
    - MockBrokerClient を使用し、データは data/paper_trading.db（Settings.paper_sqlite_path）に保存されます。
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。
  - エンジンは data/execution.pid に PID を書きます（設定で変更可）。

- 設定検証（CLI）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 設定ウィザード
  - python -m kabusys.config_setup

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数: PAPER_TRADING_SQLITE_PATH でも DB パス指定可

- AI 機能（コードから呼び出す例）
  - OpenAI API キーを環境変数 OPENAI_API_KEY に設定するか、関数引数で渡す
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)

────────────────────────
主な環境変数
────────────────────────
（必須）
- JQUANTS_REFRESH_TOKEN — J‑Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

（運用・オプション）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY — OpenAI を使う場合に必要
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…）, ルートロガーは kabusys.utils.logging_setup で設定
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒（デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 本番での kill フラグ自動クリア（0/1、本番では 0 推奨）

詳細は kabusys.config.Settings を参照してください。

────────────────────────
運用上の注意
────────────────────────
- 本番環境（KABUSYS_ENV=live）では kill_flag の自動クリア KILL_FLAG_CLEAR_ON_START=1 は危険です（デフォルト 0 推奨）。
- run_monitoring は環境にかかわらず監視用 SQLite（デフォルト data/monitoring.db）を使用します。Execution（注文）とは DB を分離する運用も可能です（paper_trading）。
- ログ: logs/<app_name>.log に日次ローテーションで保存。ログディレクトリが作れない場合はコンソール出力のみになります。
- OpenAI 呼び出しは API 失敗時にリトライ実装がありますが、API レート制限等には注意してください。
- 実行中の停止指示は data/stop_requested.flag を作成することで行います（run_execution/run_monitoring はこのフラグを監視します）。Kill Switch 条件が満たされた場合は data/kill.flag が作成され、ExecutionEngine 停止等のトリガーになります。

────────────────────────
主要ディレクトリ / ファイル構成（抜粋）
────────────────────────
src/kabusys/
- __init__.py
  - パッケージ初期化（version 等）

- config.py
  - .env 自動ロード、Settings クラス（環境変数のラッパ）
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前チェック CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト（PID, stop flag, paper_trading 切替）

- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity 設定

- monitoring/
  - monitoring_db.py — SQLite テーブル初期化・永続化 API
  - system_monitor.py — システム状態・データ鮮度の監視
  - trade_monitor.py — (注文監視: ステール注文・約定異常等) — ファイルの一部
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の書き込み/評価
  - monitoring_engine.py — 各モニタのまとめ

- execution/ (発注関連)
  - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py など
  - ExecutionEngine, Order 管理, Broker クライアント抽象化（MockBroker サポート）

- research/
  - factor_research.py — Momentum / Volatility / Value などの計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - __init__.py — 主要 API のエクスポート

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・資金割当
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- ai/
  - news_nlp.py — raw_news を LLM で評価して ai_scores に書き込む
  - regime_detector.py — ETF MA + マクロニュースでレジーム判定

- tools/
  - paper_verification_report.py — Paper Trading の統計レポート生成

- data/ （実行時に使用することが多い）
  - stop_requested.flag, kill.flag, execution.pid などのフラグ / PID ファイルや DB（デフォルト path）

────────────────────────
補足・参考
────────────────────────
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を検出して行います。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- validate_config は PyYAML がない場合、config/*.yaml の内容検証をスキップします（警告を出す）。
- AI 関連は OpenAI の API 利用料が発生します。API キーと利用制限に注意してください。

────────────────────────
貢献・拡張
────────────────────────
- strategy / execution ロジックはモジュール設計で分離されているため、独自戦略・ブローカープラグイン・ポートフォリオ手法の追加が容易です。
- DuckDB を使った研究モジュールは SQL を拡張して新しいファクターや集計を追加できます。

以上がこのコードベースの README（日本語）です。必要であれば、実際の起動コマンド例や .env のサンプル（.env.example 相当）を追記できます。どの部分を優先して補足しますか？