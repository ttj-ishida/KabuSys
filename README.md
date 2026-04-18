KabuSys
=======

日本株向けの自動売買・研究プラットフォームの軽量実装です。  
シグナル生成、ポートフォリオ構築、発注（実行／ペーパートレード）、監視、AI を用いたニュース評価、研究用ファクター計算などのコンポーネントで構成されています。

この README はコードベース（src/kabusys）に基づいた概要、機能、セットアップ、使い方、ディレクトリ構成を日本語でまとめたドキュメントです。

プロジェクト概要
----------------
- 名称: KabuSys
- 目的: 日本株の自動売買システム（研究・ペーパートレード・本番を想定）
- 設計方針:
  - 環境変数 / .env による設定管理
  - DuckDB（分析）と SQLite（監視・発注ログ）を併用
  - 実行エンジンと監視エンジンを分離（run_execution / run_monitoring）
  - OpenAI を使ったニュースセンチメントや市場レジーム判定をサポート
  - フェイルセーフ（API失敗時のフォールバック、部分失敗で既存データ保護等）

主な機能一覧
--------------
- 実行エンジン（ExecutionEngine 起動スクリプト）
  - run_execution.py: 発注エンジンを起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使用して data/paper_trading.db に記録（本番 DB と分離）。
  - PID ファイル管理、停止フラグ（data/stop_requested.flag）による安全停止。

- 監視エンジン（Monitoring）
  - run_monitoring.py: SystemMonitor をポーリング。MONITOR_POLL_INTERVAL（秒）で間隔を変更可能（デフォルト: 60秒）。
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存チェック、データ鮮度チェック。
  - TradeMonitor / RiskMonitor / KillSwitch / Alert 管理（監視結果に応じた kill.flag 書き込み等）。
  - 監視データは SQLite（デフォルト data/monitoring.db）に永続化。

- ポートフォリオ構築（純粋関数群）
  - 候補銘柄選定、等重・スコア加重配分、ポジションサイズ計算（単元株丸め、集約キャップ処理）、セクター上限やレジーム乗数の適用。

- 研究用モジュール
  - ファクター計算（momentum/value/volatility 等）: duckdb 接続を受け取り SQL で計算。
  - 特徴量探索: 将来リターン計算、IC（Information Coefficient）計算、統計サマリー等。

- AI（OpenAI）統合
  - news_nlp: raw_news を集約して LLM（gpt-4o-mini など）でセンチメントを計算し ai_scores に格納。バッチ・リトライ・レスポンス検証を実装。
  - regime_detector: ETF(1321) の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime を判定・保存。

- ツール
  - paper_verification_report: ペーパートレード DB から稼働率・注文成功率・レイテンシ等の検証レポートを生成。

- 設定管理
  - config_setup.py: .env を対話式に生成/更新するウィザード。
  - validate_config.py: .env と config/*.yaml の基本的な整合性チェック（--strict オプションあり）。

環境変数（主なもの）
--------------------
必須（実行前に設定が必要）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な任意 / デフォルト
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード時の専用 DB）
- LOG_LEVEL: INFO 等
- LOG_DIR: logs/
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）で必要
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定モード）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）

重要なフラグファイル / パス
- data/kill.flag: KillSwitch が書き込むことで ExecutionEngine に停止シグナルを与える
- data/stop_requested.flag: 実行スクリプトが外部停止要求として監視するフラグ（存在するとループを抜ける）
- data/execution.pid: 実行エンジンの PID ファイル（run_execution で使用）
- logs/<app>.log: 日次ローテーションで出力されるログ（デフォルト logs/）

セットアップ手順
----------------
※ 以下は一般的な手順案。実プロジェクトでは requirements.txt / Poetry 等に合わせてください。

1. リポジトリをクローン
   - git clone <リポジトリ>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai
   - （開発用に）pip install PyYAML

   注: 実際の依存関係はプロジェクトの requirements / pyproject を確認してください。

4. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成してプロジェクトルートに置く（.env は Git にコミットしないこと）。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります:
     - python -m kabusys.validate_config --strict

6. 必要なディレクトリの作成（通常は logging/setup が自動で作成）
   - mkdir -p data logs

使い方（起動・主要コマンド）
-------------------------

基本的にはモジュールとして起動します（プロジェクトのルートを CWD にして実行）。

- 実行エンジン起動（本番 / ペーパートレード）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に結果を記録します。

- 監視エンジン起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
  - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使って記録します。

- .env の作成 / 更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - オプション: --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI / 研究モジュールの利用（ライブラリ呼び出し）
  - OpenAI 機能を使うには OPENAI_API_KEY を設定
  - 例（ニューススコア）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

ログ / トラブルシュート
-----------------------
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリ作成権限を確認してください。
- ログレベルは LOG_LEVEL 環境変数で変更可能（DEBUG/INFO/...）。
- PyYAML がインストールされていない場合、validate_config は YAML の内容検証をスキップします（警告）。
- DuckDB / SQLite のパスは環境変数で上書き可能。親ディレクトリが存在しない場合は警告となりますが、多くのコードは起動時にディレクトリを作成します。
- PID / フラグファイル（data/*.pid / data/*.flag）はプロセス制御に使用します。不要なフラグが残っていると起動や動作に影響するため、起動前に確認してください（KILL_FLAG_CLEAR_ON_START 設定に注意）。

ディレクトリ構成（主なファイル）
--------------------------------
以下は src/kabusys 以下の主要なモジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / Settings 管理
  - config_setup.py                -- 対話式 .env 作成ウィザード
  - validate_config.py             -- 設定検証 CLI
  - run_execution.py               -- ExecutionEngine 起動スクリプト
  - run_monitoring.py              -- SystemMonitor ポーリングループ起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py                  -- ニュースを LLM で評価して ai_scores に書込
    - regime_detector.py           -- マーケットレジーム判定

  - monitoring/
    - monitoring_db.py             -- SQLite テーブル作成 / DB 永続化層
    - system_monitor.py            -- CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - risk_monitor.py              -- ドローダウン / ポジション上限モニタ
    - trade_monitor.py             -- （発注ログ監視: 未掲示の箇所あり）
    - kill_switch.py               -- kill.flag の生成 / 評価
    - monitoring_engine.py         -- 各 Monitor を束ねる実行ループ
    - alert_manager.py             -- （アラート送信の管理: 実装参照）

  - execution/
    - broker_factory.py            -- ブローカクライアントの生成（実/モック）
    - execution_engine.py          -- 発注エンジン本体
    - order_manager.py             -- 注文管理
    - order_repository.py          -- DB への注文永続化
    - reconciler.py                -- 注文状態整合処理
    - risk_manager.py              -- リスク制御ロジック

  - portfolio/
    - portfolio_builder.py         -- 候補選定・重み計算
    - position_sizing.py           -- 株数決定・資金割当
    - risk_adjustment.py           -- セクター制限・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py           -- momentum/value/volatility 等ファクター計算
    - feature_exploration.py       -- 将来リターン・IC・統計サマリー
    - __init__.py

  - data/
    - pipeline.py                  -- prices_daily 等データ取得パイプライン（参照あり）
    - stats.py                     -- zscore_normalize 等ユーティリティ（参照あり）

  - utils/
    - logging_setup.py             -- 共通ログ設定ユーティリティ
    - process_priority.py          -- プロセス優先度 / CPU affinity 設定
    - __init__.py

  - tools/
    - paper_verification_report.py -- ペーパートレード検証レポート
    - __init__.py

補足・運用上の注意
------------------
- 本プロジェクトは本番口座での発注機能を持ちます。KABUSYS_ENV=live 設定時は必ず設定と権限を慎重に確認してください（validate_config の live チェックを活用）。
- Kill Switch（data/kill.flag）や停止フラグ（data/stop_requested.flag）は誤操作で本番停止を招く可能性があるため、運用手順を整備してください。KILL_FLAG_CLEAR_ON_START は本番環境では 0 を推奨します。
- OpenAI API を利用する機能は API 利用コストとレイテンシを伴います。API Key の管理、リトライ動作、レスポンス検証（JSON モード）などの実装は行われていますが、実運用での監視を推奨します。
- DuckDB / SQLite のスキーママイグレーションは簡易的な手法を採用しています。運用時はバックアップをとってからバージョン更新を行ってください。

最後に
------
この README はソースコードの注釈・実装に基づいた概要ドキュメントです。各モジュールの詳細実装や API（関数引数・戻り値）については該当ファイルの docstring / ソースを参照してください。必要であれば各コンポーネント（ExecutionEngine、MonitoringEngine、AI 処理など）の詳細ドキュメントや運用手順書を追加で作成できます。