KabuSys — 日本株自動売買システム
====================

このリポジトリは日本株向けの自動売買システムの一部実装です。ポートフォリオ構築、ポジションサイズ計算、監視（Monitoring）、発注実行（Execution）、リサーチ（ファクター計算）や AI を使ったニュースセンチメント評価などの機能を含みます。本 README はコードベース（src/kabusys 以下）を元に、導入・実行方法と主要コンポーネントの説明を日本語でまとめたものです。

概要
----
KabuSys は以下のような責務を持つモジュール群で構成されています。

- execution: 発注エンジン（実際の / ペーパートレードをサポート）
- monitoring: システム監視、リスク監視、Kill Switch、アラート連携
- portfolio: 候補選定、重み付け、ポジションサイズ計算、セクター制限等
- research: DuckDB を用いたファクター計算・特徴量解析
- ai: OpenAI を使ったニュース NLP（センチメント）、レジーム判定
- utils: ロギング設定・プロセス優先度設定などユーティリティ
- tools: 事後検証レポート生成などのユーティリティスクリプト

主な機能
--------
- 実行エンジン（ExecutionEngine）
  - 本番（live）／ペーパートレード（paper_trading）モードをサポート
  - Paper Trading 時は MockBrokerClient を使用し、専用の SQLite（data/paper_trading.db）に記録して本番 DB と分離
- 監視（Monitoring）
  - システムリソース（CPU・メモリ・ディスク）、データ鮮度、プロセス生存確認
  - トレード状況・滞留注文・約定異常チェック
  - リスク監視（ドローダウン、ポジション上限）と Kill Switch（data/kill.flag）
  - ログ永続化（SQLite）と分析用 DuckDB のサポート
- ポートフォリオ構築
  - シグナルのランク付け、等配分／スコア加重配分、リスクベース配分
  - セクター集中抑制、レジームに応じた投下資金乗数
  - 単元株丸め、aggregate cap によるスケーリング
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上で純粋関数的に実行）
  - 将来リターン計算、IC（スピアマン）や統計サマリー
- AI（OpenAI）
  - ニュースを銘柄ごとに集約し LLM（gpt-4o-mini）でセンチメントを算出して ai_scores に保存
  - マクロニュース + ETF MA 乖離から市場レジーム（bull/neutral/bear）を判定
  - API 呼び出しはリトライ・バックオフを備えフェイルセーフ（失敗時は中立扱い等）

セットアップ手順
----------------

1. リポジトリ取得
   - ソースは src/kabusys 以下に配置されています（パッケージとして実行可能）。

2. Python 環境
   - Python 3.9+ を推奨（プロジェクトの pyproject.toml に準拠してください）。
   - 仮想環境を作成して有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Linux/macOS)
     - .venv\Scripts\activate     (Windows)

3. 依存パッケージのインストール（最低限）
   - duckdb
   - psutil
   - openai (AI 機能を使う場合)
   - PyYAML（config 検証を YAML まで行いたい場合）
   例:
     pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合はそこからインストールしてください。）

4. 環境変数 / .env の準備
   - 初期の .env を対話式で作成するには:
     python -m kabusys.config_setup
   - 既存の .env を検証する:
     python -m kabusys.validate_config
     --strict オプションで警告もエラー扱いにできます。

   主な環境変数（代表例）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB、デフォルト: data/paper_trading.db)
   - OPENAI_API_KEY（AI 機能を使う場合）
   - LOG_LEVEL, LOG_DIR など

   自動 .env ロードはデフォルトで有効です。無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. ログディレクトリ
   - デフォルトは logs/。環境変数 LOG_DIR で変更可能。
   - ログは日次ローテートされ 30 日分保持されます。

使い方（主要スクリプト）
-----------------------

- 設定ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - 標準実行:
    python -m kabusys.run_execution
  - KABUSYS_ENV に基づき本番 or ペーパートレード用クライアントを選択します。
  - ペーパートレード時は PAPER_TRADING_SQLITE_PATH（またはデフォルト data/paper_trading.db）に履歴が記録され、本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中は data/execution.pid に PID が書かれます。

- Monitoring（監視）起動
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path を使用します（環境にかかわらず監視 DB は本番 DB を参照）。
  - stop フラグ data/stop_requested.flag を置くことでループを停止できます。

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD  --to YYYY-MM-DD  --db PATH
  環境変数 PAPER_TRADING_SQLITE_PATH を指定して DB パスを渡すことも可能。

- AI 関連（プログラムから呼ぶ）
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key=None)
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key=None)
  - どちらも OpenAI API キーは引数 or 環境変数 OPENAI_API_KEY を参照します。未設定時は ValueError を送出します。

停止 / Kill Switch
-----------------
- Monitoring の Kill Switch は RiskMonitor 等のチェック結果により data/kill.flag を書き、その存在が ExecutionEngine 停止のトリガーになります。
- 手動で停止したい場合は data/stop_requested.flag を作成してください（監視 / 実行プロセスはいずれもこれを見て終了します）。
- kill.flag を削除する場合は単にファイルを削除してください（自動クリアを許可する設定 KILL_FLAG_CLEAR_ON_START=1 を有効にすることも可能ですが、本番では 0 を推奨）。

設定・運用上の注意
-----------------
- KABUSYS_ENV は development / paper_trading / live のいずれかを指定してください。live 設定は本番運用になります。LINE 通知等の設定漏れは本番で重大な問題になります。
- Paper Trading モードでは本番口座とは DB を分離して記録します（PAPER_TRADING_SQLITE_PATH）。
- AI API 呼び出し（OpenAI）はエラー時にフォールバックする設計ですが、API キーの漏洩に注意してください。.env は絶対に Git にコミットしないでください。
- ログディレクトリに書き込み権限がない場合、ファイル出力はスキップされコンソールのみの出力になります（警告が出ます）。
- process_priority 設定には psutil が必要です。必要な権限がないと設定に失敗する場合がありますが、警告を出してスキップします。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
  __init__.py
  config.py                 # 環境変数 / .env 自動ロード・Settings
  config_setup.py           # .env 対話式ウィザード
  validate_config.py        # 設定検証 CLI
  run_execution.py          # ExecutionEngine 起動スクリプト
  run_monitoring.py         # SystemMonitor ポーリング起動スクリプト

  utils/
    logging_setup.py        # ロギング初期化ユーティリティ
    process_priority.py     # プロセス優先度・CPU affinity 設定
    __init__.py

  monitoring/
    monitoring_db.py        # SQLite 永続化層（テーブル作成・CRUD）
    system_monitor.py       # システム監視
    trade_monitor.py        # (該当コード内) トレード監視
    risk_monitor.py         # ドローダウン・ポジション上限監視
    kill_switch.py          # kill.flag / stop フラグ管理
    monitoring_engine.py    # 各 Monitor を束ねる

  execution/
    (実行エンジン・ブローカー関連コンポーネント)

  portfolio/
    portfolio_builder.py    # 候補選定・重み化
    position_sizing.py      # 株数決定・スケーリング
    risk_adjustment.py      # セクター上限・レジーム乗数
    __init__.py

  research/
    factor_research.py      # Momentum/Volatility/Value 等のファクター計算
    feature_exploration.py  # 将来リターン / IC / 統計サマリ
    __init__.py

  ai/
    news_nlp.py             # ニュース NLP スコアリング（OpenAI）
    regime_detector.py      # 市場レジーム判定（MA + マクロ NLP）
    __init__.py

  tools/
    paper_verification_report.py  # Paper Trading 検証レポート
    __init__.py

付録：よく使うコマンドまとめ
----------------------------
- .env 作成（ウィザード）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Execution 起動
  python -m kabusys.run_execution

- Monitoring 起動
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- AI 関数を直接呼ぶ（Python REPL 等で）
  from kabusys.ai.news_nlp import score_news
  score_news(duckdb_conn, date(2026,4,10), api_key="sk-...")

最後に
-------
本 README はコード（src/kabusys/*.py）の実装内容に基づき要点をまとめたものです。実運用前には必ず python -m kabusys.validate_config で設定を検証し、テスト環境（paper_trading）での動作確認を行ってください。必要であれば README に追記したい項目（例：更に詳しい設定例、systemd / Supervisor のサンプル unit、CI/CD の手順など）を教えてください。