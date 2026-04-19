KabuSys — 日本株自動売買システム
===============================

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリです。戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）および Paper Trading 検証ツールなどを含みます。設計方針として、ルックアヘッドバイアス回避、フェイルセーフ（API失敗時のデフォルト挙動）、および本番・ペーパー環境の明確な分離を重視しています。

主な機能
--------
- 環境設定ウィザード（.env 生成）: kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml）: kabusys.validate_config
- ExecutionEngine 起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading DB に書き込む
  - プロセス優先度を高く設定して動作
- Monitoring（監視）起動スクリプト: run_monitoring.py
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングし、kill.flag の生成やアラート送信を行う
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
- Paper Trading 検証レポート生成: kabusys.tools.paper_verification_report
- 研究用モジュール
  - ファクター計算: kabusys.research.calc_momentum / calc_volatility / calc_value
  - 特徴量探索・IC 計算等: kabusys.research
- ポートフォリオ構築ユーティリティ
  - 候補選定・重み計算・ポジションサイズ計算・セクターキャップ適用 など
- AI 支援モジュール（OpenAI）
  - ニュース NLP によるセンチメントスコアリング: kabusys.ai.news_nlp.score_news
  - 市場レジーム判定: kabusys.ai.regime_detector.score_regime
  - ※ OpenAI API キーが必要（OPENAI_API_KEY）

セットアップ手順
----------------

1. クローン / インストール
   - ソースをクローンして、仮想環境を作成して依存関係をインストールしてください（requirements.txt 等がある場合はそちらを使用）。

2. 環境変数 / .env の用意
   - 対話式ウィザードで .env を作成できます:
     - python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 主要な任意/設定変数とデフォルト:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
     - LOG_DIR: logs/
     - PID_FILE_PATH: data/execution.pid
     - KILL_FLAG_CLEAR_ON_START: 0（本番では 0 推奨）
     - MONITOR_POLL_INTERVAL: 環境変数でポーリング秒数上書き可能（デフォルト: 60）
     - OPENAI_API_KEY: OpenAI を使う場合に設定

   - 自動読み込み:
     - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を検出できれば .env を自動読み込みします。
     - .env.local を上書き読み込みできます。
     - テスト等で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

3. DB の準備
   - monitoring 用 SQLite（デフォルト data/monitoring.db）はアプリケーション起動時にテーブルを初期化します（init_monitoring_db）。
   - Paper Trading は settings.is_paper 判定により別 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します。
   - DuckDB（デフォルト data/kabusys.duckdb）は時系列価格等の分析用データを保持します。

4. ログディレクトリ
   - デフォルト logs/ に日次ローテーションでログが出力されます。LOG_DIR 環境変数で変更できます。

5. 追加パッケージ
   - 必須ライブラリ（使用機能により）: duckdb, psutil, openai（AI 機能）, PyYAML（config YAML 検証時にあると便利）

使い方（主要コマンド）
--------------------

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告も失敗扱いする strict モード:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 特徴:
    - 実行前に PID ファイル（data/execution.pid）を管理
    - 停止シグナルは data/stop_requested.flag（プロジェクトルート）で行える
    - Paper Trading 時は MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔秒数を上書き
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は本番 sqlite_path を常に参照（環境に依らず）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）
  - 出力: コンソールに検証サマリ（稼働率、注文成功率、レイテンシ等）と PASS/FAIL 判定

- AI 機能（手動呼び出し）
  - ニュースセンチメント付与:
    - 呼び出し例（コードから）: kabusys.ai.score_news(conn, target_date, api_key=...)
    - 環境変数 OPENAI_API_KEY を設定しておくと api_key を省略可能
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

挙動上の注意点 / 運用メモ
-----------------------
- Process 優先度: run_execution/run_monitoring は起動時に set_process_priority("high") を試みます（権限不足なら警告を出してスキップ）。
- Kill Switch:
  - monitoring の KillSwitch は RiskMonitor の結果等に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
  - 本番で KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアしてしまうため注意（デフォルトは 0 を推奨）。
- ファイルベースの停止:
  - プロジェクトルート data/stop_requested.flag の存在を run_execution/run_monitoring が監視しており、存在すれば安全に停止します。
- Paper Trading:
  - paper_trading 環境では発注処理はモック化され、本番 DB と完全に分離されます（PAPER_TRADING_SQLITE_PATH）。
- OpenAI 呼び出し:
  - rate limit / transient error に対してエクスポネンシャルバックオフでリトライしますが、最終的に失敗した場合は安全側の既定値（例: macro_sentiment=0.0）で継続します。

ディレクトリ構成（抜粋）
----------------------
src/ 以下の主要ファイル / モジュール:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数読み込み / Settings
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring 起動スクリプト

- src/kabusys/ai/
  - news_nlp.py                   — ニュースの LLM センチメント処理
  - regime_detector.py            — 市場レジーム判定

- src/kabusys/monitoring/
  - monitoring_db.py              — monitoring 用 SQLite 永続化層
  - system_monitor.py             — システム / データ鮮度監視
  - trade_monitor.py              — 注文監視（滞留注文 / 約定異常 など）
  - risk_monitor.py               — ドローダウン / ポジション上限監視
  - kill_switch.py                — kill.flag の生成・制御
  - monitoring_engine.py          — 各 Monitor のオーケストレーション
  - alert_manager.py              — （アラート送信ロジック: LINE など）

- src/kabusys/execution/
  - execution_engine.py           — 実行エンジン本体
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py

- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- src/kabusys/research/
  - factor_research.py             — ファクター計算
  - feature_exploration.py         — IC / 統計解析等

- src/kabusys/tools/
  - paper_verification_report.py   — Paper Trading レポート生成スクリプト

- src/kabusys/utils/
  - logging_setup.py               — ロギング設定ユーティリティ
  - process_priority.py            — プロセス優先度・CPU affinity ユーティリティ

サンプル .env（最小）
--------------------
# .env (例)
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
OPENAI_API_KEY=sk-...

依存関係
--------
- Python 3.9+（型アノテーションやライブラリ互換性に応じて調整してください）
- 推奨ライブラリ:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config YAML 検証用、なくても動作するが警告が出ます）

ライセンス / バージョン
-----------------------
パッケージのバージョンは src/kabusys/__init__.py の __version__ で管理されています（現状: 0.1.0）。

お問い合わせ / 開発補足
---------------------
- 設定・起動で問題が起きた場合は python -m kabusys.validate_config を実行して初期チェックを行ってください。
- ロギングは logs/<app_name>.log に日次ローテーションで出力されます（30 日分保持）。

以上がリポジトリの主要概要と導入・運用のためのガイドです。必要であれば、各モジュールの詳細な使用例や API リファレンス、運用チェックリストを別途追加します。