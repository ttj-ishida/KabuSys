README — KabuSys
=================

概要
----
KabuSys は日本株の自動売買／研究／監視を行うための軽量なフレームワークです。本リポジトリには次の要素が含まれます:

- ExecutionEngine（発注・注文管理・リスク管理）
- Monitoring（システム監視・トレード監視・Kill Switch）
- Portfolio 構築（候補選定、重み計算、ポジションサイズ算出）
- Research（ファクター計算・特徴量解析・IC 計測）
- AI モジュール（ニュースセンチメント評価、レジーム判定：OpenAI を利用）
- ユーティリティ（ログ設定、プロセス優先度設定、環境設定ウィザード等）
- ツール（Paper Trading 検証レポート生成）

目的は、実運用に耐えうる工程（ログ、DB 永続化、Kill Switch、フェイルセーフ）を備えつつ、
研究・検証も同じコードベースで行えることです。

主な機能
--------
- Execution
  - 実際のブローカー or ペーパートレード（KABUSYS_ENV=paper_trading）を切替可能
  - OrderManager / RiskManager / Reconciler を備えた ExecutionEngine
  - 発注ログを SQLite（monitoring DB / paper_trading DB）へ永続化
- Monitoring
  - CPU/メモリ/Disk、Execution プロセスの死活監視（SystemMonitor）
  - 滞留注文・異常約定の監視（TradeMonitor）
  - ドローダウン・ポジション上限監視（RiskMonitor）と Kill Switch
  - ポーリングループ（run_monitoring.py）と Alerts 出力連携
- Portfolio
  - 候補選定（スコア順）、等金額・スコア重み、リスクベース発注サイズ
  - セクター上限適用、レジーム乗数の算出
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - 将来リターン、IC、統計サマリー
- AI（OpenAI と連携）
  - ニュースを LLM に投げて銘柄ごとのセンチメントを算出し ai_scores へ保存
  - マクロニュースと ETF MA を用いた市場レジーム判定
  - API 呼び出しは再試行・フェイルセーフ実装（リトライ、部分書き込みで他を保護）
- ツール
  - .env を対話式に作る config_setup.py
  - 起動前チェック validate_config.py
  - Paper Trading の検証レポート生成ツール

要件
----
- Python 3.10+
- 主な Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config ファイル検証用）
- ファイルベース DB（SQLite, DuckDB）を使用

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリに移動します。
   - プロジェクトルートは .git または pyproject.toml を基準に自動検出します。

2. 仮想環境作成・有効化、依存パッケージをインストールします（例）:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
   - pip install duckdb psutil openai
   - （PyYAML を使う場合）pip install pyyaml

   （注）requirements.txt は付属していないためプロジェクトに応じて必要なパッケージを追加してください。

3. 環境変数の準備
   - .env をプロジェクトルートに置くか、環境変数を直接設定します。
   - 対話的に作成するには:
     - python -m kabusys.config_setup
   - 作成後に設定を検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告もエラー扱いになります。

主な環境変数（代表）
- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABUSYS_ENV（development | paper_trading | live）デフォルト: development
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
- OPENAI_API_KEY（AI モジュールを使う場合に必須）
- MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリア: 0/1）

使い方
------

起動スクリプト（モジュール実行）
- 監視ループを起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で変更可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番用 sqlite_path を使用して監視テーブルを更新します（KABUSYS_ENV に依存しない）

- 実行エンジンを起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - 停止フラグ data/stop_requested.flag が存在すると起動しません / 実行中に検出すると停止します。
  - 実行中は data/execution.pid に PID が書き込まれます。

- .env ウィザード:
  - python -m kabusys.config_setup

- 起動前検証:
  - python -m kabusys.validate_config
  - --strict で警告を失敗扱いにできます。

ツール
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH の代替）

AI 機能（OpenAI）
- ニュース自動スコアリングやレジーム判定は OPENAI_API_KEY が必要です。
- モジュール API（プログラムから呼ぶ想定）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- API 呼び出しに失敗した場合はフェイルセーフ（スコア 0.0 等）で継続する設計です。

監視・Kill Switch
- KillSwitch はリスク条件（ドローダウンやポジション上限）を満たすと data/kill.flag を書き込みます。
- ExecutionEngine はこの kill.flag を検知すると安全に停止する仕組みになっています。
- 既存の kill.flag は Settings.kill_flag_clear_on_start=1 で起動時に自動クリアできます（本番では通常 0 推奨）。

ログ
- ログは stdout と file（logs/<app_name>.log）に出力されます。ログローテーションは日次で最大 30 世代保持。
- setup_logging() を全スクリプトが呼び出して統一的に設定します。

データベース
- デフォルトパス:
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper-trading SQLite: data/paper_trading.db
- monitoring_db (SQLite) は init_monitoring_db() でテーブル・インデックス作成と簡単なマイグレーションを行います。

ディレクトリ構成（抜粋）
-----------------------
以下は主なファイル/ディレクトリの概要（src/kabusys 以下）:

- __init__.py
- config.py                         — 環境変数 / Settings
- config_setup.py                   — .env 対話式ウィザード
- validate_config.py                — 起動前チェック CLI
- run_monitoring.py                 — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py                  — ExecutionEngine 起動スクリプト

- utils/
  - logging_setup.py                — ログ設定ユーティリティ
  - process_priority.py             — プロセス優先度 / CPU affinity

- monitoring/
  - monitoring_db.py                — monitoring 用 SQLite ラッパー
  - system_monitor.py               — CPU/メモリ/Disk・データ鮮度・Execution PID チェック
  - trade_monitor.py                — （トレード監視: 滞留注文等）※実装ファイル参照
  - risk_monitor.py                 — ドローダウン・ポジション上限チェック
  - kill_switch.py                   — kill.flag 書き込み
  - monitoring_engine.py            — 各 Monitor を束ねる

- execution/
  - execution_engine.py             — ExecutionEngine（run_session 等）
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py

- portfolio/
  - portfolio_builder.py            — 候補選定 / 重み計算
  - position_sizing.py              — 発注株数計算
  - risk_adjustment.py              — セクター制限 / レジーム乗数

- research/
  - factor_research.py              — Momentum/Volatility/Value 等
  - feature_exploration.py          — forward returns / IC / summary

- ai/
  - news_nlp.py                     — ニュースを OpenAI でスコア化
  - regime_detector.py              — マクロ + ETF MA によるレジーム判定

- tools/
  - paper_verification_report.py    — Paper Trading 検証レポート

運用上の注意
-------------
- 本番（KABUSYS_ENV=live）での運用は十分なテストと設定確認（validate_config）を行ってから行ってください。特に KILL_FLAG_CLEAR_ON_START=1 は本番だと危険です。
- データベースパスやログディレクトリは適切なディレクトリ権限の下で動作させてください。ログディレクトリ作成に失敗した場合はファイル出力が無効化され、コンソールのみになります。
- OpenAI を使う機能は API 料金が発生します。必要な API キーと利用ポリシーを確認してください。

貢献
----
バグ報告・改善提案は Issues を通してください。コードスタイルは PEP8 準拠を旨とし、公開リポジトリでは .env をコミットしないでください。

ライセンス
--------
（プロジェクトに応じてライセンスを明記してください）

付録: よく使うコマンド例
-----------------------
- .env 作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視起動
  - export MONITOR_POLL_INTERVAL=60
  - python -m kabusys.run_monitoring

- 実行エンジン起動
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上。README に不足する情報や追記したい利用例があれば教えてください。