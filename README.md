KabuSys — 日本株自動売買システム（README）
=================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。本リポジトリは注文実行・監視・ポートフォリオ構築・リサーチ・AI（ニュース NLP / レジーム判定）などの主要コンポーネントを含むモジュール群を提供します。設計方針としては「テストしやすい純粋関数」「DB 分離」「実運用向けのフェイルセーフ」を重視しています。

主な機能
--------
- ExecutionEngine：ブローカークライアント経由で発注を管理（paper_trading モードではモックブローカーを使用して本番 DB と分離）
- Monitoring：システム稼働状況、データ鮮度、注文ログ、リスク指標（ドローダウン・保有上限）を定期ポーリングして永続化・アラート
- Kill Switch：リスク条件を満たした場合に data/kill.flag を書き込み ExecutionEngine に停止指令を送る
- Portfolio construction：候補選定、重み付け、ポジションサイズ計算、セクター上限・レジーム乗数
- Research：DuckDB を用いたファクター計算（モメンタム、バリュー、ボラティリティ）および IC / 統計解析ユーティリティ
- AI モジュール：
  - news_nlp：OpenAI（gpt-4o-mini）でニュースをスコアリングして ai_scores に保存
  - regime_detector：ETF とマクロニュースを統合して市場レジーム（bull/neutral/bear）を算出
- ユーティリティ：
  - 環境設定ウィザード（.env 作成支援）
  - 設定検証 CLI（.env と config/*.yaml の検証）
  - Paper Trading 検証レポート出力スクリプト

前提（推奨）
------------
- Python 3.10+（型ヒントに union types 等を使用）
- pip, virtualenv（仮想環境推奨）
- 必要なライブラリ（最低限の例）:
  - duckdb
  - psutil
  - openai (AI 機能利用時)
  - PyYAML（設定ファイル検証・読み込み時にあると便利）
- SQLite（組み込み）、logging は標準ライブラリ

セットアップ手順
----------------
1. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそれを使ってください：
    pip install -r requirements.txt）

3. プロジェクトルートに移動（.git または pyproject.toml を基準に自動検出する仕組みがあります）

4. .env の作成（推奨）
   - 対話式ウィザードで作成:
     python -m kabusys.config_setup
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN（J-Quants API）
     - KABU_API_PASSWORD（kabuステーション API）
     - KABUSYS_ENV（development / paper_trading / live）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - デフォルトファイルパス例:
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 失敗（エラー）があれば修正してください。
   - 警告も失敗扱いにする strict モード:
     python -m kabusys.validate_config --strict

使い方（主要コマンド）
--------------------

- ExecutionEngine（発注エンジン）を起動
  - 本番 / 開発 / ペーパートレードは KABUSYS_ENV で切替
  - 実行:
    python -m kabusys.run_execution
  - ペーパートレード（KABUSYS_ENV=paper_trading のとき）は MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録します。
  - 実行時、data/execution.pid に PID を書き出します。
  - 停止シグナル:
    - data/stop_requested.flag を作成すると run_execution は検知して終了します。
    - data/kill.flag は Kill Switch（監視側）が書き込み、実行エンジン側で停止処理のトリガーになります。

- Monitoring（監視ループ）を起動
  - 実行:
    python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は Settings により指定された SQLite（SQLITE_PATH）を使用します（Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を参照します）。
  - 停止は data/stop_requested.flag を作成することで可能です。

- .env 作成ウィザード
  - python -m kabusys.config_setup
  - 既存 .env を読み込んで対話的に編集できます。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定（オプション）:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定できます（デフォルト: data/paper_trading.db）。

注意事項 / 運用メモ
------------------
- MONITOR_POLL_INTERVAL：監視ループの秒間隔（例: MONITOR_POLL_INTERVAL=30）
- kill.flag / stop_requested.flag：
  - kill.flag: 監視側 KillSwitch が書き込み、ExecutionEngine 側で停止を促す用途
  - stop_requested.flag: 管理用の停止フラグ（run_execution, run_monitoring ともに検知）
  - これらのフラグは data/ ディレクトリ配下に作成されます
- ログ：
  - デフォルトは logs/<app_name>.log（TimedRotatingFileHandler による日次ローテーション、30 日保持）
  - 環境変数 LOG_DIR、LOG_LEVEL により制御可能
  - setup_logging() ユーティリティで全起動スクリプトが同じログポリシーを利用します
- Paper Trading（分離）：
  - KABUSYS_ENV=paper_trading の場合、ExecutionEngine は paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と切り離します
- AI 機能：
  - OpenAI を呼ぶ機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要
  - API エラー時はフォールバック動作（スコア 0.0 など）を行うよう設計されていますが、API キーは必須です
- 重要な依存ライブラリ：
  - psutil（プロセス優先度・CPU 使用率・メモリ等）
  - duckdb（リサーチ / AI のデータ参照用）
  - openai（AI 機能）

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュールと役割の抜粋です（省略あり）。

- src/kabusys/
  - __init__.py               — パッケージ本体（バージョン等）
  - config.py                 — 環境変数/設定読み込み・Settings クラス
  - config_setup.py           — .env 対話式ウィザード（CLI）
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI 呼び出し、ai_scores 書き込み）
    - regime_detector.py      — 市場レジーム判定（ETF + マクロニュース）

  - monitoring/
    - monitoring_db.py        — SQLite による監視ログ永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py       — CPU/メモリ/ディスク・データ鮮度・実行プロセス検出
    - trade_monitor.py        — （注文ログ監視等）※詳細はコード参照
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag の管理
    - monitoring_engine.py    — 各 Monitor を束ねるループ（テスト用 run_once / 本番 run）

  - execution/
    - execution_engine.py     — ExecutionEngine 本体（セッション実行）
    - order_manager.py
    - order_repository.py
    - broker_factory.py       — ブローカークライアント生成（本番 / モック）
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数決定・投下資金スケール
    - risk_adjustment.py      — セクター制限・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py      — momentum / value / volatility 等の計算（DuckDB）
    - feature_exploration.py  — 将来リターン計算、IC、統計要約
    - __init__.py

  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成ツール

  - utils/
    - logging_setup.py        — ログ初期化ユーティリティ（Stream + TimedRotatingFile）
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py

追加情報 / 開発者向けメモ
------------------------
- DuckDB / SQLite のテーブルスキーマは各モジュール（ai, research, monitoring）で期待される列が異なります。リサーチや AI 実行前に必要なテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime など）を準備してください。
- monitoring_db.init_monitoring_db() は冪等でテーブルを作成し、既存 DB に対して必要なマイグレーション（列追加）を行います。
- process_priority.set_process_priority("high") を実行スクリプトの最初に呼んでいます。psutil の権限により設定できない場合は警告ログでスキップされます。
- テスト用途では各モジュールの公開関数（calc_momentum, calc_value, score_news, score_regime 等）を直接呼び出すことで DB・API への影響を抑えつつ検証できます。AI 関連の呼び出し部分はユニットテストでモック化可能な設計です（例: _call_openai_api を patch）。

ライセンス / 貢献
----------------
- 本 README にはライセンス情報が含まれていません。実際の配布では LICENSE ファイルをプロジェクトルートに置いてください。
- バグ報告・機能改善は issue / PR を通じてお願いします。

以上です。開始手順で詰まる点があれば、環境変数や実行ログの抜粋を添えて質問してください。