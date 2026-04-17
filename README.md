KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買/リサーチ基盤の一部を実装したコードベースです。本リポジトリには以下のような機能群が含まれます。

- 実行エンジン起動スクリプト（ExecutionEngine）
- 監視用ポーリングループ（Monitoring）
- Paper Trading 用の分離 DB / 検証レポート
- ポートフォリオ構築・ポジションサイジング・リスク調整ロジック（純粋関数）
- ファクター計算・特徴量探索（Research）
- ニュース NLP / レジーム判定（OpenAI を利用）
- 環境設定ウィザード・検証ツール

主な特徴
--------
- 環境分離: KABUSYS_ENV による environment（development / paper_trading / live）
  - paper_trading 時は発注はモックに切替え、data/paper_trading.db を用いることで本番 DB と分離
- 監視: system / trade / risk 監視コンポーネントを束ねた MonitoringEngine
- Kill Switch: 条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止
- DuckDB を用いたリサーチ用データ処理（prices_daily / raw_financials 等）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント / マクロ判定（リトライ・検証実装済）
- .env ウィザード（対話式）と設定検証 CLI（YAML の存在確認は PyYAML に依存）

準備（セットアップ）
--------------------

1. Python 環境の準備
   - Python 3.9+ を推奨
   - 仮想環境を作成して activate してください。

2. 依存パッケージのインストール
   - 主な依存例:
     - duckdb
     - psutil
     - openai
     - PyYAML（optional: config/*.yaml の文法チェック用）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. プロジェクトルートの配置
   - リポジトリをクローンし、ルートに .env/.env.local を配置します（.env の自動読み込み機能あり）。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. 環境変数 (.env)
   - 対話式ウィザードで .env を作成できます（.env は絶対に git にコミットしないでください）:
     - python -m kabusys.config_setup
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な設定例:
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant|partial|never|reject
     - OPENAI_API_KEY=...
     - LOG_LEVEL=INFO
   - 自動ロードの振る舞い:
     - OS 環境 > .env.local > .env の優先順位で読み込み（既存 OS 環境変数は保護されます）
     - テストなどで自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証
   - 作成後に検証:
     - python -m kabusys.validate_config
     - 警告も FAIL にする: python -m kabusys.validate_config --strict

使い方（起動・実行）
-------------------

- 実行エンジン（ExecutionEngine）をデーモン的に起動:
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用して data/paper_trading.db に記録します（本番 DB と完全分離）。
    - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
    - 実行中に data/stop_requested.flag を作るとエンジンは停止を試みます。
    - 実行中は data/execution.pid が作成されます。

- 監視ポーリングループ起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - Monitoring は環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用します。
  - 監視は system / trade / risk をチェックし、KillSwitch などの判断を行います。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を使うか、環境変数 PAPER_TRADING_SQLITE_PATH を設定してください（デフォルト: data/paper_trading.db）。

- AI / レジーム判定・ニューススコア（ライブラリ API）
  - ニューススコアリング（ai.news_nlp.score_news）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)  # api_key を省略すると OPENAI_API_KEY を参照
  - レジーム判定（ai.regime_detector.score_regime）:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)
  - どちらも OpenAI API を使用し、API キーは引数または環境変数 OPENAI_API_KEY で指定します。

重要なファイル / フラグ
--------------------
- data/kill.flag — Kill Switch による停止フラグ
- data/stop_requested.flag — 開発用停止フラグ（run_* スクリプトで検出）
- data/execution.pid — ExecutionEngine の PID 管理
- data/monitoring.db — 監視用 SQLite（Settings.sqlite_path）
- data/paper_trading.db — Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）
- data/kabusys.duckdb — DuckDB（Settings.duckdb_path）

設定（Settings）
---------------
- Settings クラス（kabusys.config.Settings）が環境変数を読み取ります。主なプロパティ:
  - env / is_live / is_paper / is_dev
  - duckdb_path / sqlite_path / paper_sqlite_path
  - paper_fill_mode（instant|partial|never|reject）
  - pid_file_path / kill_flag_path / KILL_FLAG_CLEAR_ON_START
  - CPU / メモリ / ディスク閾値（監視用）

ディレクトリ構成（主要部分）
---------------------------

src/
  kabusys/
    __init__.py
    config.py                     — 環境変数・.env ロードロジック
    config_setup.py               — 対話式 .env ウィザード
    validate_config.py            — 設定検証 CLI
    run_execution.py              — ExecutionEngine 起動スクリプト
    run_monitoring.py             — Monitoring 起動スクリプト

    ai/
      __init__.py
      news_nlp.py                 — ニュース NLP スコアリング（OpenAI）
      regime_detector.py         — 市場レジーム判定（OpenAI）

    monitoring/
      monitoring_db.py            — SQLite の永続化層（system_status / trade_logs / risk_logs / positions / dashboard）
      system_monitor.py          — システム監視（CPU/メモリ/ディスク/データ鮮度/PID）
      trade_monitor.py           — 注文滞留・約定異常の監視
      risk_monitor.py            — ドローダウン・ポジション上限監視
      kill_switch.py             — kill.flag 書き込み・管理
      monitoring_engine.py       — 各 Monitor を束ねるエンジン
      alert_manager.py           — （アラート管理、実装はコード参照）

    portfolio/
      portfolio_builder.py        — 候補抽出・配分（等配分 / スコア配分）
      position_sizing.py         — 株数決定・集約キャップ処理
      risk_adjustment.py         — セクターキャップ・レジーム乗数
      __init__.py

    research/
      factor_research.py         — Momentum / Volatility / Value の計算（DuckDB）
      feature_exploration.py     — 将来リターン・IC・統計サマリ
      __init__.py

    tools/
      paper_verification_report.py — Paper Trading の PASS/FAIL レポート
      __init__.py

    utils/
      process_priority.py        — プロセス優先度・CPU affinity 設定ユーティリティ
      __init__.py

補足 / 実運用における注意点
-------------------------
- .env を含む個人情報・キー類は決してリポジトリにコミットしないでください。
- 本番環境（KABUSYS_ENV=live）では LINE 通知や Kill Switch 設定などを慎重に確認してください（validate_config で追加チェックあり）。
- OpenAI を用いる機能は API の呼び出し回数・料金に注意し、API キーの権限・レート制限に留意してください。
- psutil でプロセス優先度や CPU affinity を変更する際は権限不足で失敗する場合がありますが、その場合は警告ログを出してスキップします。

開発・拡張
----------
- DuckDB を利用したリサーチ関数はテスト用に独立しており、prices_daily / raw_financials テーブルだけを参照します。外部 API には依存しません（副作用なし）。
- AI 呼び出し部分はリトライ・バリデーション実装済みで、テストでは _call_openai_api をモックできます。
- 監視ログのスキーマ変更は monitoring_db.init_monitoring_db に集約されています。マイグレーションの追加はここに記述してください。

ライセンス・バージョン
----------------------
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリのルートにある LICENSE を参照してください（存在しない場合はプロジェクトポリシーに従ってください）。

問い合わせ / 開発時のヒント
-------------------------
- 設定周りで問題があればまず python -m kabusys.validate_config を実行してください。
- .env の自動読み込みはプロジェクトルートを .git または pyproject.toml を基準に探索します。パッケージ配布後も CWD に依存しない設計です。

以上がリポジトリの概要・導入手順・利用方法の要点です。その他、個別モジュールの詳細や API 仕様は各モジュールの docstring を参照してください。