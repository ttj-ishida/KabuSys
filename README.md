KabuSys — 日本株自動売買システム
==============================

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームです。  
主な機能は注文の実行エンジン、システム/取引の監視、ポートフォリオ構築、ファクター計算（研究）、およびニュースを用いた AI スコアリングです。  
設計方針として「本番とペーパートレードの分離」「ルックアヘッドバイアス回避」「フェイルセーフ（API失敗時は安全側で継続）」を重視しています。

主な特徴（機能一覧）
------------------
- Execution Engine
  - 実際のブローカークライアントまたは MockBrokerClient（ペーパートレード時）を使った発注処理
  - リスク管理（最大ポジション比率、利用率、回路遮断器など）
  - 注文管理・再整合（Reconciler）
  - 起動/停止は PID ファイル・フラグファイルで制御
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス稼働状況、データ鮮度監視
  - TradeMonitor：滞留注文・約定異常などの監視（trade_logs）
  - RiskMonitor：ドローダウン・ポジション上限監視、Kill Switch（条件で kill.flag を書き込み）
  - MonitoringEngine：各モニタを束ねたポーリングループ
- ポートフォリオ構築（純粋関数群）
  - 候補選定、等重/スコア重み、ポジションサイジング（単元丸め、aggregate cap のスケールダウン）
  - セクターキャップ、レジーム乗数（bull/neutral/bear）
- 研究（Research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ
  - DuckDB を用いた高速集計（prices_daily / raw_financials などを想定）
- AI モジュール
  - ニュースに対する LLM ベースのセンチメントスコアリング（OpenAI）
  - マクロニュース + ETF MA を組み合わせた市場レジーム判定（regime_detector）
  - API 呼び出しはリトライ/バックオフやレスポンスの厳密バリデーションあり
- ツール
  - 環境設定ウィザード（config_setup）で .env の初期作成・更新を対話式に実行
  - 設定検証 CLI（validate_config）で .env や config/*.yaml の不備チェック
  - Paper Trading 検証レポート生成 script（tools/paper_verification_report）

前提・依存
----------
- Python 3.9+（typing の表記や依存ライブラリを考慮して 3.9+ を想定）
- 主な Python パッケージ:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の中身検証を行いたい場合、任意）
- SQLite が標準で使用されます。データファイルは project_root/data 配下を想定。

セットアップ手順
---------------
1. リポジトリをクローンしてプロジェクトルートへ移動
   - 仮にソースは src/ 配下に配置されています。

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要ライブラリをインストール
   - pip install duckdb psutil openai
   - （任意）pip install pyyaml

   ※ requirements.txt がある場合はそちらを使用してください（本例コードベースに含まれていないため明示的に記載）。

4. ディレクトリ作成
   - data/ と logs/ を作成:
     - mkdir -p data logs

5. .env の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参考に）:
     - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - 主要な環境変数例:
       - KABUSYS_ENV=development|paper_trading|live
       - DUCKDB_PATH=data/kabusys.duckdb
       - SQLITE_PATH=data/monitoring.db
       - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db (ペーパートレード分離用)
       - LOG_LEVEL=INFO
       - OPENAI_API_KEY=（AI 機能を使う場合）

6. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

使い方（起動例）
----------------
- Execution Engine を起動（通常はサービス/systemd 等で起動）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に記録される（本番 DB と分離）
    - 起動前に data/stop_requested.flag があると起動をスキップ
    - PID ファイル: data/execution.pid（Settings.pid_file_path から上書き可能）

- Monitoring を起動（別プロセスで常駐）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - Monitoring は環境にかかわらず本番 sqlite_path を参照して監視情報を永続化します

- Kill Switch
  - KillSwitch は条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります
  - 必要に応じて kill.flag を手動で削除（Execution 起動前に自動クリア設定も可能; KILL_FLAG_CLEAR_ON_START）

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI モジュール（プログラムから呼び出す）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=...)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=...)

ログ
----
- 共通ロギング初期化: kabusys.utils.logging_setup.setup_logging(app_name=...) を各起動スクリプトで呼び出します。
- ログ出力先:
  - stdout（常に）
  - logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション、30日保持）
- LOG_DIR / LOG_LEVEL は環境変数で上書き可能

重要なファイル・フラグ
--------------------
- data/kill.flag — Kill Switch（Execution の停止要求）
- data/stop_requested.flag — run_* スクリプトのポーリングループ停止フラグ
- data/execution.pid — ExecutionEngine の PID ファイル（Settings.pid_file_path）
- data/monitoring.db — 監視用 SQLite（Settings.sqlite_path）
- data/paper_trading.db — ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）

ディレクトリ構成（主要ファイル）
-------------------------------
（src/kabusys 配下を想定）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数／設定読み込みロジック
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 起動前設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py            — ニュース NLP スコアリング
      - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
      - __init__.py
    - monitoring/
      - monitoring_db.py       — SQLite 永続化レイヤ
      - system_monitor.py
      - trade_monitor.py       — （省略したが取引監視ロジック）
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py       — （アラート送信ロジック、例: LINE）
    - execution/
      - execution_engine.py    — 実行エンジン本体
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - broker_factory.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - data/                     — 実行時生成想定（.gitignore 推奨）
    - logs/                     — ログ出力先（実行前に作成推奨）

注意事項 / 運用上のポイント
--------------------------
- KABUSYS_ENV（development / paper_trading / live）を正しく設定してください。live は本番であり慎重な取り扱いが必要です。
- .env は絶対に Git にコミットしないでください（config_setup.py のヘッダにも注意書きあり）。
- Paper Trading は本番 DB と完全分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI API 利用時は OPENAI_API_KEY を設定してください。API 呼び出しにはレート制限やコストが発生します。
- Monitoring は本番 sqlite（Settings.sqlite_path）を参照して稼働ログを永続化します。監視は起動環境に依らず本番 DB を見る設計です。
- プロセス優先度や CPU affinity の設定は utils/process_priority.py に抽象化されています（psutil を利用）。権限不足などで設定できない場合は警告が出ます。

開発 / テストのヒント
--------------------
- 単体関数群（portfolio/*、research/*）は副作用がなく DuckDB/引数を渡してテスト可能です。
- news_nlp や regime_detector の OpenAI 呼び出し部分は内部関数に分けられており、テスト時にモック差し替えが可能です（例: unittest.mock.patch）。
- validate_config は起動前のチェックに便利です。PyYAML が無い場合は YAML 内容検証をスキップします。

ライセンス・貢献
----------------
（この README にはライセンス情報・貢献ガイドは含めていません。プロジェクトに合わせて LICENSE ファイルや CONTRIBUTING を追加してください。）

以上が KabuSys の概要と基本的な使い方です。必要であれば、各モジュール（ExecutionEngine の詳細な起動手順、TradeMonitor の使い方、AI モジュールの具体的な API レスポンス仕様など）についてさらに詳細なドキュメントを作成します。どの部分をさらに展開しますか？