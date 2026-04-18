README
=====

概要
----
KabuSys は日本株の自動売買に関わるユーティリティ群と実行基盤をまとめた Python パッケージです。  
主な機能は以下の通りです:

- ExecutionEngine（発注エンジン）の起動・運用（本番 / ペーパートレード対応）
- 監視（System / Trade / Risk）と Kill Switch による自動停止
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング、セクター制約）
- リサーチ（ファクター計算、将来リターン、IC 計算、統計サマリー）
- ニュース NLP による銘柄センチメント（OpenAI を用いたスコアリング）
- 各種ツール（ペーパー取引の検証レポート生成、設定ウィザード、設定検証）
- ロギング/プロセス優先度の統一設定ユーティリティ

主要な設計方針:
- DuckDB / SQLite による履歴・分析データの永続化
- 本番 DB とペーパートレード DB を明確に分離
- 重要な外部 API 呼び出し（OpenAI など）はリトライ・フェイルセーフ実装
- ルックアヘッドバイアス対策（日付参照の設計に注意）

機能一覧
--------
- run_execution: ExecutionEngine 起動（KABUSYS_ENV により本番 / paper_trading を切替）
  - paper_trading 時は MockBrokerClient を使用し、data/paper_trading.db に記録
- run_monitoring: SystemMonitor ポーリングループ（MONITOR_POLL_INTERVAL で間隔指定可）
  - システムリソース、プロセス生存、データ鮮度を監視し monitoring DB に記録
- monitoring_engine: System/Trade/Risk モニタを束ねたポーリングエンジン（テスト用 API あり）
- KillSwitch: ドローダウンやポジション上限で kill.flag を書き込み ExecutionEngine を停止
- MonitoringDB: SQLite を用いた監視ログ永続化層（system_status/trade_logs/positions/...）
- portfolio モジュール: 候補選定、重み計算、sizing、セクターキャップ、レジーム乗数など
- research モジュール: momentum/value/volatility 等ファクター、forward return、IC、統計
- ai.news_nlp: raw_news を OpenAI に送り銘柄別センチメントを ai_scores に書き込み
- ai.regime_detector: ETF＋マクロ記事から市場レジーム（bull/neutral/bear）判定
- tools.paper_verification_report: ペートレード DB から検証レポートを標準出力で生成
- config_setup: .env を対話式に生成・更新するウィザード
- validate_config: .env と config/*.yaml の起動前チェック CLI

セットアップ手順
----------------
前提
- Python 3.10+（typing の | 演算子を利用しています）
- SQLite（標準ライブラリ）
- OS により追加のシステムパッケージが必要になる場合があります（例: psutil のビルド要件）

依存パッケージ（一例）
- duckdb
- psutil
- openai
- PyYAML（config YAML 検証用、任意）

インストール（開発用）
1. リポジトリルートに移動（この README はパッケージが src/ 配下にある前提）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb psutil openai PyYAML
   - （必要に応じて他の依存を追加して下さい）
4. 開発モードでインストール（任意）
   - pip install -e .

.env の準備
1. 対話式ウィザードで .env を作成
   - PYTHONPATH=src python -m kabusys.config_setup
   - または python -m kabusys.config_setup（パッケージをインストール済みの場合）
2. ウィザードの後に設定を検証
   - PYTHONPATH=src python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN：J-Quants API 用（必須）
- KABU_API_PASSWORD：kabuステーション API パスワード（必須）
- KABUSYS_ENV：実行環境（development | paper_trading | live）。デフォルト: development
- OPENAI_API_KEY：OpenAI API キー（ai モジュール利用時）
- DUCKDB_PATH：DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH：SQLite 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH：ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL：ログレベル（DEBUG/INFO/...、デフォルト INFO）
- MONITOR_POLL_INTERVAL：run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE（paper_trading 時の約定モード: instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START：Execution 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

基本的な使い方
--------------
環境が正しく設定され、パッケージが import 可能な状態で以下を実行できます。  
（開発中は PYTHONPATH=src を付与するか pip install -e . を行ってください）

1) ExecutionEngine を起動（本番/ペーパーを切り替え）
- 本番（KABUSYS_ENV=live）
  - KABUSYS_ENV=live python -m kabusys.run_execution
- ペーパートレード（KABUSYS_ENV=paper_trading）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - ペーパートレード時は data/paper_trading.db に記録され本番 DB とは分離されます

停止方法:
- data/stop_requested.flag を作成すると run_execution の監視ループが検知して安全に停止します
- KillSwitch（監視側）が条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止します

2) 監視ループを起動
- MONITOR_POLL_INTERVAL 秒ごとにポーリング（デフォルト 60 秒）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 監視は常に本番の sqlite_path（Settings.sqlite_path）を使用してログを書きます
- 監視停止: data/stop_requested.flag を作成すると監視ループが終了します

3) 設定ウィザード / 検証
- PYTHONPATH=src python -m kabusys.config_setup
- PYTHONPATH=src python -m kabusys.validate_config [--strict]

4) Paper Trading 検証レポート
- PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

5) ライブラリとしての利用（リサーチ・ポートフォリオ等）
- 例: DuckDB 接続を作成してファクター計算を呼び出す
  - from kabusys.research import calc_momentum
  - calc_momentum(duckdb_conn, target_date)

注意点 / 運用メモ
- run_execution は起動時にプロセス優先度を "high" に設定しようとします（psutil を使用）。権限がない場合は警告が出ますが処理は継続します。
- ログは logs/<app_name>.log に日次ローテーションで保存されます（logs ディレクトリが作成できない場合はコンソール出力のみになります）。
- Monitoring は環境に関わらず Settings.sqlite_path（本番用監視 DB）を使用します。ペーパートレード DB と監視 DB は目的別に分けて運用してください。
- OpenAI API 呼び出しを行う ai モジュールは API キーが必須です。API 呼び出しはリトライとフェイルセーフ実装が入っていますが、API 利用料やレート制限に注意してください。
- .env は絶対に Git にコミットしないでください（config_setup のヘッダにもその旨が記載されています）。

ディレクトリ構成（抜粋）
-------------------
src/
  kabusys/
    __init__.py
    config.py                     # 環境変数・Settings 管理（.env 自動ロード機能あり）
    config_setup.py               # .env 対話ウィザード
    validate_config.py            # 起動前検証 CLI
    run_execution.py              # ExecutionEngine 起動スクリプト
    run_monitoring.py             # SystemMonitor ポーリング起動スクリプト

    utils/
      __init__.py
      logging_setup.py            # ログ設定ユーティリティ
      process_priority.py         # プロセス優先度 / CPU affinity 設定

    monitoring/
      monitoring_db.py            # SQLite 永続化層
      system_monitor.py           # システム / データ鮮度監視
      trade_monitor.py            # （trade 監視ロジック）
      risk_monitor.py             # ドローダウン / ポジション数監視
      kill_switch.py              # kill.flag 管理
      monitoring_engine.py        # 複合ポーリングエンジン
      alert_manager.py            #（LINE など通知用マネージャ）

    execution/
      execution_engine.py         # ExecutionEngine 本体
      order_manager.py
      order_repository.py
      reconciler.py
      risk_manager.py
      broker_factory.py

    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
      __init__.py

    research/
      factor_research.py
      feature_exploration.py
      __init__.py

    ai/
      news_nlp.py                 # ニュース NLP スコアリング（OpenAI）
      regime_detector.py          # レジーム判定（ETF + マクロニュース）
      __init__.py

    data/                         # 実行時に生成される（例: data/monitoring.db, data/kabusys.duckdb, flags）
    logs/                         # ログファイル（デフォルト）

その他ツール
------------
- paper_verification_report: ペーパートレード DB を解析して PASS/FAIL 判定を行うレポートツール
  - 実行例: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

ライセンス・貢献
----------------
（このリポジトリにライセンス情報がない場合は適切なライセンスファイルを追加してください。）

フィードバックやバグ報告は Issue にてお願いします。

付録: よく使うコマンド（開発時）
-----------------------------
- 開発用インストール:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install -e .[dev]  # extras を用意している場合
- .env 作成:
  - PYTHONPATH=src python -m kabusys.config_setup
- 設定検証:
  - PYTHONPATH=src python -m kabusys.validate_config --strict
- Execution 起動（ペーパートレード）:
  - PYTHONPATH=src KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Monitoring 起動（間隔 30 秒）:
  - PYTHONPATH=src MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper レポート:
  - PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上。README の不明点や追記したい項目（例: 詳細な設定例、Docker 化、CI 設定など）があれば指示してください。