KabuSys — 日本株自動売買システム
=================================

このリポジトリは「KabuSys」という日本株向けの自動売買 / 研究基盤です。
コードは小さなモジュール群に分割されており、トレード実行、監視、ポートフォリオ構築、研究（ファクター計算）、およびニュースNLP/レジーム判定（OpenAI 利用）といった機能を含みます。

主な特長
--------
- ExecutionEngine（発注エンジン）と Monitoring（監視）を分離して運用可能
- Paper Trading（ペーパートレード）モードをサポート（本番 DB と完全分離）
- DuckDB を用いた研究・ファクター計算（prices_daily / raw_financials 等）
- ニュースの LLM（OpenAI）によるセンチメントスコアリング（ai.news_nlp）
- レジーム判定（ai.regime_detector）と市場センチメントの統合
- 監視（system / trade / risk）の自動ロギング（SQLite）と Kill Switch
- ログはコンソール出力＋日次ローテートファイル（logs/*.log）

機能一覧
--------
- 環境設定ウィザード: python -m kabusys.config_setup（.env ファイル生成）
- 設定検証 CLI: python -m kabusys.validate_config （--strict で警告も FAIL 扱い）
- 発注実行スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し data/paper_trading.db に記録
  - 起動時にプロセス優先度を "high" に設定
  - stop フラグ（data/stop_requested.flag）を検知して安全に停止
- 監視スクリプト: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視ログは常に本番 sqlite_path（data/monitoring.db デフォルト）へ書き込む
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- 研究モジュール:
  - ファクター計算: kabusys.research.calc_momentum / calc_volatility / calc_value
  - 特徴量探索（forward returns / IC / summary 等）
- ポートフォリオ構築:
  - 銘柄選定・重み付け・サイズ計算・セクター制約適用等
- AI 関連:
  - kabusys.ai.score_news（ニュース → ai_scores）
  - kabusys.ai.regime_detector（レジーム判定 → market_regime）
  - OpenAI API（gpt-4o-mini）を利用（OPENAI_API_KEY が必要）

前提・依存
-----------
主に以下のパッケージを想定しています（環境に合わせてインストールしてください）:
- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config 検証時に YAML のパースを行う場合）
- sqlite3（標準ライブラリ）

設定（.env / 環境変数）
---------------------
主要な環境変数（抜粋）:

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 時の DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant|partial|never|reject（paper_trading の挙動）
- OPENAI_API_KEY（ai.score_news / score_regime を使う場合に必要）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（運用時の通知設定）
- PID_FILE_PATH（実行エンジンの pid ファイル path）
- KILL_FLAG_PATH（Kill Switch 用 flag path）
- KILL_FLAG_CLEAR_ON_START（1 にすると起動時に kill.flag を自動クリア）

.env を作成するには（推奨）
- python -m kabusys.config_setup を実行すると対話式ウィザードで .env を生成できます。
- 生成後、python -m kabusys.validate_config で設定を検証してください。

セットアップ手順
--------------
1. リポジトリをクローン / プロジェクトルートへ移動
2. Python 仮想環境の作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install -r requirements.txt
     （requirements.txt がない場合は duckdb, psutil, openai, pyyaml などを個別にインストール）
4. 環境変数を設定
   - python -m kabusys.config_setup で .env を生成（もしくは手動で .env を作成）
5. 設定検証
   - python -m kabusys.validate_config
   - 問題がなければ OK が表示される。--strict を付けると警告も FAIL 扱い
6. データディレクトリを作る（必要に応じて）
   - mkdir -p data logs

基本的な使い方
--------------
- 発注エンジン（ExecutionEngine）を起動
  - 本番 / 開発 / paper_trading は KABUSYS_ENV によって変わる
  - 起動:
    - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、専用の paper_trading DB（PAPER_TRADING_SQLITE_PATH）に記録し、MockBrokerClient を使用
    - 起動時に data/stop_requested.flag が存在すると起動をキャンセル
    - 停止は data/stop_requested.flag を作成するか、kill.flag による Kill Switch で停止

- 監視プロセスを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更するには環境変数 MONITOR_POLL_INTERVAL（秒）を設定
    - 例: export MONITOR_POLL_INTERVAL=30

- Paper Trading 検証レポートを出力
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを指定可能（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）

- AI（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定しておく
  - 呼び出しはライブラリ関数として利用できます（例: kabusys.ai.score_news）

停止・Kill シグナル
------------------
- data/stop_requested.flag: run_execution / run_monitoring の両方で監視される停止フラグ
- data/kill.flag: KillSwitch により書き込まれ、ExecutionEngine に停止指示を送る（監視コンポーネントが条件を満たしたとき）
- ExecutionEngine の PID は data/execution.pid（デフォルト）に書き込まれる

ログ
----
- ログはデフォルトで stdout（コンソール）と logs/<app_name>.log に出力されます
- ログの設定は kabusys.utils.logging_setup.setup_logging で行われる
- ログディレクトリは LOG_DIR 環境変数で上書き可能（デフォルト logs/）

よく使うコマンドまとめ
---------------------
- .env を対話的に作る
  - python -m kabusys.config_setup
- 設定チェック
  - python -m kabusys.validate_config
- Execution を起動
  - python -m kabusys.run_execution
- Monitoring を起動
  - python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

ディレクトリ構成（抜粋）
-----------------------
以下は主要ファイル/ディレクトリのツリー（src/kabusys 配下の抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                 # 環境変数・Settings 管理（.env 自動ロード含む）
    - config_setup.py           # .env 対話ウィザード
    - validate_config.py        # 設定検証 CLI
    - run_execution.py          # ExecutionEngine 起動スクリプト
    - run_monitoring.py         # Monitoring 起動スクリプト
    - ai/
      - news_nlp.py             # ニュース NLP（OpenAI） → ai_scores 書き込み
      - regime_detector.py      # レジーム判定（MA + マクロセンチメント）
      - __init__.py
    - monitoring/
      - monitoring_db.py        # SQLite 用の永続化層 / MonitoringDB
      - system_monitor.py       # システム状態・データ鮮度監視
      - trade_monitor.py        # (省略) トレード監視ロジック
      - risk_monitor.py         # ドローダウン・ポジション上限監視
      - kill_switch.py          # KillSwitch 実装
      - monitoring_engine.py    # 各 Monitor を束ねる実行エンジン
      - alert_manager.py        # (省略) 通知連携
    - portfolio/
      - portfolio_builder.py    # 候補選定・重み付け
      - position_sizing.py      # 株数決定・スケーリング
      - risk_adjustment.py      # セクターキャップ・レジーム乗数
      - __init__.py
    - research/
      - factor_research.py      # momentum / volatility / value 等の計算
      - feature_exploration.py  # forward returns / IC / summary 等
      - __init__.py
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py        # ログ設定ユーティリティ
      - process_priority.py     # プロセス優先度・CPU affinity
      - __init__.py
    - monitoring/ (上記)
    - portfolio/ (上記)
    - research/ (上記)
    - ai/ (上記)
    - tools/ (上記)

（注）ここに掲載していないモジュール（execution.*、data.*、strategy.* 等）は本リポジトリの他ファイルで実装されています。必要に応じてプロジェクト全体のツリーを参照してください。

設計上の注意点・運用メモ
----------------------
- 監視（monitoring）は KABUSYS_ENV にかかわらず常に本番 sqlite_path を使用する設計です（監視ログは一元管理）。
- Paper Trading は本番データと厳密に分離するように設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI を利用する処理は API 呼び出しの失敗に対してフォールバック（0.0 スコア等）し、全体が止まらないようにしています。ただし API キーは必須です（該当機能を使う場合）。
- ログディレクトリ作成に失敗した場合はファイル出力がスキップされ、コンソールのみで動作します。
- プロセス優先度設定は OS によって成功しないことがあります（権限や未サポート OS）。失敗時は警告を出してスキップします。

トラブルシューティング
----------------------
- .env の設定が不明瞭な場合:
  - python -m kabusys.config_setup（再実行）→ python -m kabusys.validate_config でチェック
- DB ファイルがない / パスが異なる:
  - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を確認、必要なら作成
- OpenAI 呼び出しで失敗:
  - OPENAI_API_KEY を確認、API レートやネットワーク・リトライのログを参照

ライセンス・貢献
----------------
- 本リポジトリのライセンス情報はプロジェクトルートの LICENSE ファイルを参照してください（ここには含まれていません）。
- バグ修正・機能追加はプルリクエストで受け付けます。単体テストや静的解析の追加も歓迎します。

最後に
------
この README はコードベースの主要部分（実行・監視・研究・AI・ポートフォリオ）の利用開始に必要な情報をまとめたものです。詳細実装や追加のユーティリティはソース内の docstring / コメントを参照してください。必要であれば README に追記を加えますので、どの点をより詳しく書いてほしいか教えてください。