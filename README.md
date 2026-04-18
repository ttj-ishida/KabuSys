README
======

概要
----
KabuSys は日本株向けの自動売買 / 研究プラットフォームです。本リポジトリは取引実行エンジン、監視（Monitoring）、ファクター・リサーチ、ポートフォリオ構築、AI ベースのニュース解析などのコンポーネント群を含んでいます。設計思想としては「本番データと検証用を分離」「ルックアヘッドバイアス排除」「外部 API 呼び出しは明示的に制御」「障害に対するフェイルセーフ」を重視しています。

主な機能
---------
- Execution（発注エンジン）
  - Broker クライアントの抽象化（paper_trading モードでは MockBroker を使用）
  - OrderManager / OrderRepository / RiskManager / Reconciler を組み合わせて発注セッションを実行
  - 起動時に PID ファイルを作成し、停止フラグで安全に終了可能

- Monitoring（監視）
  - SystemMonitor：CPU / メモリ / ディスク / プロセス生存確認、データ鮮度チェック
  - TradeMonitor：滞留注文・異常約定価格の検出
  - RiskMonitor：ドローダウン・ポジション上限監視（ダッシュボード更新・イベント記録）
  - KillSwitch：重大アラート発生時に data/kill.flag を書き込み ExecutionEngine 停止をトリガ
  - MonitoringEngine：上記モニタを束ねて定期ポーリング・アラート発行

- Portfolio（ポートフォリオ構築）
  - 候補選定・スコア順ソート
  - 等金額 / スコア加重の重み計算
  - セクター制約の適用、レジーム乗数
  - 銘柄ごとの発注株数計算（ロット丸め、リスクベース配分、総合キャップ）

- Research（研究）
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
  - DuckDB を用いた高速な時系列集計

- AI（ニュース NLP / レジーム判定）
  - raw_news をまとめて OpenAI（gpt-4o-mini 等）でセンチメント評価 → ai_scores へ保存
  - ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して market_regime を判定
  - API 呼出しはリトライ・バイパス等のフェイルセーフ実装あり

- ツール
  - .env 生成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）

セットアップ手順
----------------
前提:
- Python 3.10+（typing 機能や型アノテーションに依存）
- SQLite（標準ライブラリ）
- 環境によっては管理者権限が必要（プロセス優先度設定等）

1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必須（代表例）:
     - duckdb
     - psutil
     - openai
   - 任意:
     - PyYAML（config/*.yaml の検証を有効化する場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt があれば pip install -r requirements.txt を利用してください）

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに .env を作成（.env.example を参考にする）

5. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

主な環境変数（要設定）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
  - paper_trading: MockBroker を使用し data/paper_trading.db を利用（本番 DB と分離）
  - live: 本番モード（注意して設定）
- OPENAI_API_KEY（AI 機能を使う場合）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/…）
- PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知を使う場合）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアする場合は 1、注意）

使い方
------
主要コマンド（モジュール実行）

- ExecutionEngine を起動（実際のトレードまたは paper_trading）
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV により broker クライアントが切り替わる
    - paper_trading の場合は paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
    - 起動前に data/stop_requested.flag があれば起動しない

- Monitoring（監視ループ）を起動
  - MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（デフォルト 60 秒）
  - python -m kabusys.run_monitoring
  - 注意:
    - Monitoring は環境にかかわらず Settings.sqlite_path（本番監視 DB）を使用します

- 設定ウィザード（.env の生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/db.sqlite

制御ファイル（フラグ・PID）
- data/execution.pid : ExecutionEngine の PID（実行中に作成）
- data/stop_requested.flag : 強制停止用フラグ（存在を検知すると起動をキャンセル、稼働中は停止処理）
  - run_execution と run_monitoring の両方で使用され、存在するとループを抜けます
- data/kill.flag : KillSwitch が書き込むフラグ（重大なリスクが検出されたときに ExecutionEngine を停止させる目的）
  - KillSwitch は monitoring 内の判定によって書き込まれます
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリア（本番では 0 を推奨）

注意点 / 運用メモ
- Monitoring は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。paper_trading でも本番監視 DB を参照するため、DB パスの取り扱いに注意してください。
- ExecutionEngine は paper_trading の場合 paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離します。
- OpenAI など外部 API を利用する機能は API キー未設定時に明示的な例外やフェイルフォールバックを行う設計ですが、キーを設定していることを確認してください。
- process priority / cpu affinity の設定には psutil が必要で、OS によっては管理者権限が求められる場合があります。失敗した場合は警告を出してスキップします。

ディレクトリ構成（抜粋）
-----------------------
以下はソースツリー（src/kabusys 以下）の主要ファイル / モジュール構成です。実際のリポジトリにはさらにファイルが含まれる可能性があります。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数読み込み・Settings
  - config_setup.py            — .env 生成ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py              — ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py       — MA200 + マクロセンチメントで market_regime を判定
    - __init__.py

  - monitoring/
    - monitoring_db.py         — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py        — CPU/メモリ/プロセス/DuckDB データ鮮度チェック
    - trade_monitor.py         — 注文滞留・約定異常チェック
    - risk_monitor.py          — ドローダウン / ポジション上限監視
    - kill_switch.py           — kill.flag 書き込みユーティリティ
    - monitoring_engine.py     — 各 Monitor を束ねるエンジン
    - alert_manager.py         — （アラート送信ロジック）※実装は該当ファイル参照

  - execution/
    - broker_factory.py        — Broker クライアント生成ファクトリ
    - execution_engine.py      — 実行エンジン本体（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - order_record.py
    - ...（発注関連の実装群）

  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 株数決定・aggregate cap
    - risk_adjustment.py       — セクター制限・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py       — momentum / volatility / value 計算（DuckDB）
    - feature_exploration.py   — 将来リターン / IC / 統計サマリー
    - __init__.py

  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
    - __init__.py

  - utils/
    - process_priority.py      — psutil を使った優先度 / affinity 設定
    - __init__.py

付録：よく使うコマンド例
-----------------------
- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証（警告を fail に含める場合）
  - python -m kabusys.validate_config --strict

- Execution 起動
  - python -m kabusys.run_execution

- Monitoring 起動（ポーリング間隔を 30 秒に設定）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート（2026-04-01 〜 2026-04-11）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
-------
この README はコードベースの主要な構成と運用上のポイントをまとめたものです。実装の詳細や追加設定（LINE 通知、外部 API の挙動、各種設定ファイルの雛形）は該当モジュールの docstring や config/*.yaml、scripts/generate_config.py（存在する場合）を参照してください。必要であればさらに導入手順（systemd ユニットや Dockerfile など）や運用手順書を追記できます。