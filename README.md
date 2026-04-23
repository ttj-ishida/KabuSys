KabuSys — 日本株自動売買システム
=============================

このリポジトリは日本株向けの自動売買システム（KabuSys）のコアライブラリ群です。  
戦略・ポートフォリオ構築、発注エンジン、監視、AI を使ったニュース解析、研究用ユーティリティなどを含んでいます。

概要
----
KabuSys は以下の主要コンポーネントを備えたモジュール構成のライブラリです。

- ExecutionEngine: 発注やオーダー管理、リスク管理を行う実行エンジン（本番 / ペーパートレード対応）。
- Monitoring: システム稼働状況、注文ログ、リスク指標をポーリングして記録・アラートや Kill Switch を管理。
- Portfolio モジュール: 候補選定・重み計算・ポジションサイズ算出・セクター制約適用など純粋関数群。
- Research: DuckDB を用いたファクター計算・将来リターン計算・IC 計算など研究用ユーティリティ。
- AI モジュール: OpenAI を用いたニュースのセンチメント分析と市場レジーム判定。
- Tools: ペーパートレード用の検証レポート生成スクリプト等の CLI ツール。
- 設定ユーティリティ: .env ウィザード（config_setup）と設定検証（validate_config）。
- 共通ユーティリティ: ロギング設定、プロセス優先度設定など。

主な機能一覧
-------------
- run_execution.py:
  - ExecutionEngine の起動スクリプト。
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient（ペーパートレード）を使用し、data/paper_trading.db に記録。
  - 停止判定は data/stop_requested.flag を監視。PID ファイル（data/execution.pid）を出力。
- run_monitoring.py:
  - SystemMonitor（監視）のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数で周期を変更可能（デフォルト 60 秒）。
  - 監視データは SQLite（data/monitoring.db）へ保存。Monitoring は環境にかかわらず本番 sqlite_path を使用。
- monitoring:
  - system_status / trade_logs / positions / risk_logs / dashboard テーブルを持つ永続化層（SQLite）。
  - RiskMonitor：ドローダウンやポジション数上限の監視とリスクログ。
  - KillSwitch：条件に応じて data/kill.flag を書き、ExecutionEngine に停止シグナルを送る。
  - MonitoringEngine：各 Monitor を束ねてポーリング・アラート処理。
- portfolio:
  - 候補選定、等配分・スコア配分、ポジションサイズ計算（リスクベース等）、セクター制限、レジーム乗数。
- research:
  - モメンタム / ボラティリティ / バリュー等のファクター計算。
  - 将来リターン・IC 計算・統計サマリなど。
- ai:
  - news_nlp.score_news: raw_news を集約して OpenAI に問い合わせ、銘柄ごとの ai_score を ai_scores テーブルに書き込む。
  - regime_detector.score_regime: ETF の MA 乖離とマクロニュースの LLM センチメントを合成して market_regime テーブルに書き込む。
  - OpenAI API（gpt-4o-mini）を使用。API キーは OPENAI_API_KEY を利用。
- tools/paper_verification_report.py:
  - ペーパートレード DB（data/paper_trading.db）から稼働率、注文成功率、レイテンシなどを集計し検証レポートを出力。

セットアップ手順
----------------
1. Python 環境
   - 推奨: Python 3.10+
   - 仮想環境を作る（例）:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージ（少なくとも以下が必要）
   - duckdb
   - psutil
   - openai
   - PyYAML（config の YAML 検証を行う場合）
   - 必要に応じて他の依存が生じる可能性があります。requirements.txt がない場合は手動でインストールしてください。
   例:
     pip install duckdb psutil openai PyYAML

3. .env の準備（環境変数）
   - 対話式ウィザードで .env を作成:
     python -m kabusys.config_setup
   - 必須環境変数（最小セット）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 重要な環境変数（例とデフォルト）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO
     - OPENAI_API_KEY: OpenAI を使う場合に必要

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合:
     python -m kabusys.validate_config --strict

5. データディレクトリの準備
   - scripts/ 起動時に自動作成されることが多いですが、手動で data/ や logs/ を作成しておくと安全です。
     mkdir -p data logs

使い方（起動例）
----------------
- ExecutionEngine を起動:
  - 本番 / 開発 / ペーパートレードは KABUSYS_ENV で切替（.env で設定）。
  - 起動:
    python -m kabusys.run_execution
  - ペーパートレードでは paper DB（PAPER_TRADING_SQLITE_PATH）にログが残ります。

- Monitoring を起動:
  - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は monitoring DB（SQLITE_PATH）へ記録します。Monitoring は環境にかかわらず本番 sqlite_path を使用する点に注意。

- .env の作成/更新:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで別 DB を指定可能:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（プログラムから呼ぶ場合）
  - OPENAI_API_KEY を設定してください。
  - 例:
    from kabusys.ai import score_news
    score_news(conn=duckdb_conn, target_date=date(2026,4,10))

運用 / 制御ファイル
-------------------
- data/stop_requested.flag:
  - run_execution.py / run_monitoring.py がこれを検知するとメインループを停止します（外部でのシャットダウンに使用）。
- data/kill.flag:
  - KillSwitch が書き込むファイル。ExecutionEngine に強制停止を促す用途（Kill Switch）。
- data/execution.pid:
  - run_execution が PID を出力するファイル（プロセス管理用）。

設定重要事項
-------------
- KABUSYS_ENV:
  - development, paper_trading, live のいずれか。
  - live 設定ではアラートや Kill Switch の扱いが厳しくなるため注意して設定してください。
- PAPER_FILL_MODE:
  - ペーパートレード時のモック約定挙動（instant, partial, never, reject）。
- KILL_FLAG_CLEAR_ON_START:
  - 起動時に kill.flag を自動で消すかどうか（本番での自動クリアは危険なためデフォルトは 0）。

ロギングとプロセス優先度
------------------------
- 共通ユーティリティ kabusys.utils.logging_setup.setup_logging を全スクリプトで呼び出し、stdout と日次ローテートのファイルログを設定します（logs/<app_name>.log）。
- run_* スクリプトは起動時に kabusys.utils.process_priority.set_process_priority("high") を呼んでプロセス優先度を上げる設計です（すべての OS/環境で成功するとは限りません）。

ディレクトリ構成（主なファイル/モジュール）
----------------------------------------
src/
  kabusys/
    __init__.py
    config.py                 # 環境変数・設定管理、自動 .env ロード
    config_setup.py           # 対話式 .env 作成ウィザード
    validate_config.py        # 設定検証 CLI
    run_execution.py          # ExecutionEngine 起動スクリプト
    run_monitoring.py         # SystemMonitor 起動スクリプト

    ai/
      __init__.py
      news_nlp.py             # ニュース NLP による銘柄別センチメント
      regime_detector.py      # 市場レジーム判定

    monitoring/
      monitoring_db.py        # SQLite 監視 DB レイヤ
      system_monitor.py       # システム状態監視
      trade_monitor.py        # （関連ファイル）注文監視（コードベースに依存）
      risk_monitor.py         # ドローダウン・ポジション監視
      kill_switch.py          # Kill Switch（flag 書込み）
      monitoring_engine.py    # 各 Monitor を束ねる

    portfolio/
      portfolio_builder.py    # 候補選定・重み計算
      position_sizing.py      # 銘柄ごとの株数決定
      risk_adjustment.py      # セクター制約・レジーム乗数
      __init__.py

    research/
      factor_research.py      # ファクター計算
      feature_exploration.py  # IC・将来リターン等
      __init__.py

    tools/
      __init__.py
      paper_verification_report.py

    utils/
      __init__.py
      logging_setup.py        # ログ設定ユーティリティ
      process_priority.py     # プロセス優先度・CPU affinity

注意事項 / 運用上のヒント
-------------------------
- データベースファイル（DuckDB / SQLite）はデフォルトで data/ 以下に配置されます。運用時は永続ストレージに置いてください。
- Monitoring は sqlite_path を環境にかかわらず本番 DB を参照するため、テスト実行時は注意（ペーパートレードと分離したければ環境変数でパスを調整）。
- OpenAI を利用する機能は API キーが必須。エラー時はフェイルセーフでスコアをスキップまたは中立値で継続する実装になっていますが、API 利用に伴うコストとレート制限を考慮してください。
- 設定変更後は python -m kabusys.validate_config でチェックすることを推奨します。

ライセンス / バージョン
-----------------------
パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください。

最後に
------
この README はコードベースの主要な使い方と構成を簡潔にまとめたものです。運用時は各モジュールのドキュメント（ソース内の docstring）を参照してください。追加で README の補足（環境ごとのデプロイ手順や systemd/cron 用の起動例等）が必要であればお知らせください。