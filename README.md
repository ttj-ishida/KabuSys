KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株自動売買システムの参照実装です。戦略の研究・ファクター計算・ポートフォリオ構築・発注実行（本番／ペーパートレード）・監視・アラート・AI を利用したニュースセンチメント評価など、運用に必要な主要コンポーネントを備えています。

主な特徴
--------
- ExecutionEngine（発注実行）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ペーパートレードでは MockBrokerClient を使用し、data/paper_trading.db に記録して本番 DB と完全分離
  - リスク管理・オーダー管理・再整合（reconciler）を内包
- Monitoring（監視）
  - システム状態（CPU/メモリ/ディスク）、Execution プロセスの稼働検知、注文ログの監視、リスク（ドローダウン、ポジション上限）監視
  - Kill Switch（data/kill.flag）による Execution 停止シグナル
  - 監視ログは SQLite（デフォルト data/monitoring.db）に永続化
- Portfolio（銘柄選定・配分・ポジションサイズ決定）
  - 候補選定、等金額/スコア加重、セクターキャップ、レジーム乗数、ポジションサイズ計算（lot 単位丸め・aggregate cap）
- Research（ファクター計算・特徴量解析）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI モジュール
  - ニュースのセンチメント評価（OpenAI API を利用、gpt-4o-mini を想定）
  - 市場レジーム判定（ETF MA + マクロニュースセンチメントの合成）
- ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート出力ツール

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ... （プロジェクトルートに移動）

2. Python 環境（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - 必須（ソースから読み取れる主な依存）: duckdb, psutil, openai
   - オプション: PyYAML（config/*.yaml 検証用）

   （注）requirements.txt がプロジェクトにない場合、手動で上記パッケージを入れてください。

4. 初期設定（.env 作成）
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に .env を作成して環境変数を設定してください。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - （OpenAI を使う場合）OPENAI_API_KEY

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

6. データディレクトリ作成
   - data/ および logs/ は自動作成される場合がありますが、権限などで失敗することがあるので必要なら手動作成してください。
   - デフォルト DB パス:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db

使い方
------
主要な実行スクリプトはモジュールとして起動します。

- ExecutionEngine を起動（本番 / paper_trading は KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 動作概要:
    - Settings を読み込み、適切な SQLite（paper_trading の場合は専用 DB）と DuckDB に接続
    - BrokerClientFactory によりブローカークライアントを生成（paper_trading では Mock）
    - Engine をスレッドで起動し、data/stop_requested.flag を監視して停止
    - PID ファイル: data/execution.pid（Settings.pid_file_path で変更可）

- Monitoring を起動（ポーリング監視）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（デフォルト 60）
  - 監視は本番 sqlite_path を使用してログを残します（KABUSYS_ENV に依らず本番 DB を参照）

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告があると exit(1) になります

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数がなければデフォルト data/paper_trading.db）

- AI / Research 関数の利用（ライブラリ関数として）
  - ニューススコア付与:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=...)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=...)
  - ファクター計算等（Research）:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank

運用上の注意
- Kill Switch:
  - Kill 条件発生時 (ドローダウン等) に data/kill.flag が書かれると、Execution 側で検出して停止します。
  - Settings.kill_flag_clear_on_start を 1 にする設定は本番では危険です（.env で調整）。
- ログ:
  - logs/<app_name>.log に日次ローテーションで保存（TimedRotatingFileHandler）。ログディレクトリは LOG_DIR で変更可能。
- プロセス優先度:
  - 起動スクリプトは起動時にプロセス優先度を "high" に設定しようと試みます（psutil に依存、失敗時は警告）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は起動時に必要なテーブルとカラムを作成し、既存 DB に対するマイグレーション（例: latency_ms, peak_value 追加）も行います。

主要環境変数（抜粋）
-------------------
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: Monitoring SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant/partial/never/reject）

ディレクトリ構成
----------------
（プロジェクトルート）
- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / 設定管理
    - config_setup.py           — .env ウィザード CLI
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py (想定)
    - execution/
      - execution_engine.py (想定)
      - order_manager.py (想定)
      - order_repository.py (想定)
      - broker_factory.py (想定)
      - reconciler.py (想定)
      - risk_manager.py (想定)
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - data/ (データ・DB ファイルを置く想定ディレクトリ)
- config/
  - *.yaml （system_config.yaml, strategy_config.yaml, 等のテンプレート）
- data/
  - monitoring.db (SQLite)
  - paper_trading.db (SQLite)
  - kabusys.duckdb (DuckDB)
  - kill.flag / stop_requested.flag / execution.pid などのフラグ・PID ファイル
- logs/
  - execution.log
  - monitoring.log
  - ...

追加情報 / 開発メモ
-----------------
- DuckDB を用いたファクター計算は大量データの高速集計に適しており、prices_daily / raw_financials 等のテーブルを参照します。
- AI モジュールは OpenAI API の利用を前提としており、API 呼び出しは失敗した場合にフォールバック（スコア 0.0 など）するフェイルセーフ実装が施されています。API 呼び出し部分はテスト時にモック可能です。
- テスト・CI のために KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると自動で .env を読み込む機能を無効化できます。
- run_monitoring は MONITORING 用テーブルに必ず書き込みます（Monitoring は KABUSYS_ENV に依存せず本番 sqlite_path を使用する実装になっています）。

問い合わせ・貢献
----------------
バグレポート、機能提案、プルリクエストは issue/PR を作成してください。README に記載のない運用手順やデプロイ方法（systemd / supervisor / コンテナ化など）を導入する場合は別途ドキュメントを作成してください。

以上。必要があれば、実行例・systemd ユニット例・.env.example のテンプレートやデプロイ手順を追加で作成します。