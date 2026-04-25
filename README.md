KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python ベースのシステムです。
主要機能（発注エンジン、監視エンジン、ポートフォリオ構築、ファクター計算、AI ベースのニュース解析 等）を含み、
DuckDB / SQLite をデータ格納に使用します。起動・設定は .env ベースで管理でき、対話式ウィザード・検証ツールが提供されています。

主な特徴
--------
- ExecutionEngine：実際の発注ロジック（paper_trading 環境ではモックブローカーで完全分離）
- Monitoring：システム稼働率・データ鮮度・取引ログ等のポーリング監視とアラート評価（Kill Switch を備える）
- Portfolio 建構成：候補選定、重み付け、ポジションサイズ計算、セクター上限やレジーム考慮
- Research：DuckDB 上でファクター（Momentum / Value / Volatility / Liquidity）や将来リターンの計算、IC 計算
- AI：OpenAI を使ったニュースのセンチメント評価や市場レジーム推定（API キー必要）
- ツール：Paper Trading 検証レポート生成スクリプト等
- ロギング：stdout + 日次ローテーションファイル（logs/）を標準で設定

必須環境変数（最低限）
-----------------------
- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
その他 / 推奨:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: AI 機能（news_nlp / regime_detector）を使う場合に必要
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（例: INFO、デフォルト: INFO）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の挙動）

セットアップ手順
----------------
1. Python 環境
   - 推奨: Python 3.10+（型ヒントや最新ライブラリを利用）
   - 仮想環境を作成して有効化:
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（主要依存）
   - duckdb
   - psutil
   - openai
   - PyYAML（任意だが config 検証であると便利）
   - （sqlite3 は標準ライブラリ）
   例:
     pip install duckdb psutil openai PyYAML

   ※ 実際の requirements.txt がある場合はそれを使用してください。

3. プロジェクトルートで .env を作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - 生成後、設定を検証:
     python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります

4. ディレクトリ確認 / 作成
   - data/ や logs/ は各スクリプトが起動時に自動作成しますが、
     必要なら手動で作成してパーミッションを確認してください。

5. （任意）OpenAI を使う場合:
   - 環境変数 OPENAI_API_KEY をセットするか、関数引数で渡します。

使い方（起動例）
----------------

- 監視ループを実行
  - 環境変数 MONITOR_POLL_INTERVAL で秒単位のポーリング間隔を設定可能（デフォルト 60 秒）。
  - run_monitoring は常に本番用の sqlite_path を使用（環境に依らず monitoring DB は同じファイルを参照）。
  実行:
    python -m kabusys.run_monitoring
  例（ポーリング間隔 30 秒）:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  停止方法:
    - data/stop_requested.flag を作成すると監視ループが検知して終了します（スクリプト内で定義）。
    - Ctrl+C（KeyboardInterrupt）でも終了します。

- ExecutionEngine（発注エンジン）を実行
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と完全分離）。
  実行:
    python -m kabusys.run_execution
  停止:
    - data/stop_requested.flag を作成するとエンジンが検知して停止します。
    - 実行時、data/execution.pid に PID を出力（設定により異なる）。

- Paper Trading 検証レポート生成
  - SQLite の paper_trading DB を読み、期間ごとの稼働率・成功率・レイテンシ等を集計してレポートを出力します。
  実行:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB 指定:
    --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

- 設定ウィザード / 検証
  - .env 生成:
    python -m kabusys.config_setup
  - 検証:
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

注意点と挙動
-------------
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数で間隔を上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバックします。
- Monitoring は「監視 DB（sqlite）」を環境にかかわらず本番 sqlite_path を使う実装箇所があるため、注意して設定してください（paper_trading でも monitoring.db を参照する設計です）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用 sqlite（PAPER_TRADING_SQLITE_PATH またはデフォルト data/paper_trading.db）を使用して本番 DB と分離します。
- Kill Switch:
  - risk_monitor と kill_switch により DRAWDOWN / POSITION_LIMIT 等で data/kill.flag を書き込み、ExecutionEngine を停止させる仕組みがあります。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアしますが、本番環境では 0 を推奨します。

ロギング
-------
- kabusys.utils.logging_setup.setup_logging を通じて統一的に設定されます。
- 出力先:
  - stdout（StreamHandler）
  - ファイル: logs/<app_name>.log（日次ローテーション、30 日保持）
- ログレベルは:
  - 引数 level > 環境変数 LOG_LEVEL > デフォルト INFO の順に決定されます

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数読み込み・Settings クラス
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 起動前チェック CLI
- run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
- run_execution.py         — ExecutionEngine 起動スクリプト

サブパッケージ（主要）
- ai/
  - news_nlp.py            — ニュースの LLM センチメント（ai_scores への書き込み）
  - regime_detector.py     — レジーム判定（MA + マクロセンチメントの合成）
- monitoring/
  - monitoring_db.py       — SQLite 用永続化層（schema 初期化、CRUD）
  - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py       — 取引ログ監視（滞留注文・異常約定の検出）
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — kill.flag の管理
  - monitoring_engine.py   — 各 Monitor を束ねるランナー
  - alert_manager.py       — （アラート送信実装想定）
- execution/
  - execution_engine.py    — 発注エンジン本体
  - broker_factory.py      — ブローカークライアント生成（実口座 / モック）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py   — 候補選定・重み付け
  - position_sizing.py     — 株数決定・集約キャップ処理
  - risk_adjustment.py     — セクターキャップ・レジーム乗数
- research/
  - factor_research.py     — モメンタム/ボラ/バリュー等の計算（DuckDB）
  - feature_exploration.py — IC / forward returns / 統計サマリ
- utils/
  - logging_setup.py       — 共通ロギング設定
  - process_priority.py    — プロセス優先度・CPU affinity 設定
- tools/
  - paper_verification_report.py — Paper Trading レポート生成

開発・拡張メモ
---------------
- DuckDB を用いた分析系関数は副作用を持たない設計（純粋関数）。prices_daily / raw_financials 等のテーブルを参照します。
- AI モジュールは OpenAI SDK（openai パッケージ）を利用。API の失敗に対してはフェイルセーフ（0.0 など）で継続動作する設計になっています。
- 設定検証（validate_config.py）は .env と config/*.yaml の存在と形式をチェックします。PyYAML がない場合は YAML の検証をスキップします。
- process_priority.set_process_priority() で起動直後に優先度を上げる実装があります。権限によっては設定できない場合があります（警告ログになるのみ）。

よくある操作コマンド（まとめ）
------------------------------
- .env 作成（対話式）:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視プロセス起動:
  python -m kabusys.run_monitoring

- 発注エンジン起動:
  python -m kabusys.run_execution

- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
------
この README は提供されたコードベースの要点をまとめたものです。詳細な設定例やデプロイ手順、運用手順（systemd/cron/コンテナ化等）は運用環境に合わせて追記してください。ご希望があれば運用向けのデプロイ手順や systemd unit 例、コンテナ Dockerfile のひな形も作成します。