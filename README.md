KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買システム（研究 / ポートフォリオ構築 / 発注実行 / 監視 / AI 支援）のコアモジュール群を含みます。本 README はコードベースの概要、主要機能、セットアップと起動方法、ディレクトリ構成を日本語でまとめたものです。

1. プロジェクト概要
------------------

KabuSys は以下の責務を分離して実装したモジュール群です。

- データパイプライン / DuckDB を使ったファクター計算（research）
- ポートフォリオ構築・ポジションサイジング（portfolio）
- 発注エンジン / ブローカー抽象（execution）
- 監視（システム稼働・注文状況・リスク）と Kill Switch（monitoring）
- ニュースに基づく NLP スコアリング・レジーム判定（ai）
- 開発支援ツール（設定ウィザード / 設定検証 / ペーパートレード検証レポート）

設計方針の概略：
- モジュールは可能な限り純粋関数や DB 抽象を用いて結合を緩める。
- 本番・ペーパートレードの DB を分離（KABUSYS_ENV=paper_trading では paper DB を使用）。
- ルックアヘッドバイアスを避ける設計（日時参照の扱いに注意）。
- OpenAI を用いる機能は API キー必須、失敗時はフォールバックして安全に継続。

2. 主な機能一覧
----------------

- 設定管理
  - .env の自動読み込み（プロジェクトルートの .env / .env.local、無効化可）
  - 対話式設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config

- 発注・実行（ExecutionEngine）
  - live / paper_trading 対応（paper_trading は MockBrokerClient と data/paper_trading.db）
  - リスク管理（Rate limit, max position, drawdown 等）
  - OrderRepository / OrderManager / Reconciler を備える
  - 実行プロセス優先度設定 / pid ファイル管理

- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク / データ鮮度 / 実行プロセス生存監視
  - TradeMonitor：発注・約定の異常検出（滞留注文・異常約定等）
  - RiskMonitor：ドローダウン監視・ポジション上限監視 → risk_logs / dashboard の永続化
  - KillSwitch：条件を満たすと data/kill.flag を書き込み、ExecutionEngine を停止させる
  - MonitoringEngine：上記を束ねたポーリングループ（run_monitoring.py）

- 研究・分析
  - ファクター計算（momentum, volatility, value 等） — DuckDB を使用
  - 特徴量解析（forward returns, IC, summary）

- AI（OpenAI 連携）
  - news_nlp: ニュース記事の銘柄別センチメントを取得して ai_scores に書き込み
  - regime_detector: ETF（1321）MA とマクロニュースを合成して市場レジーム判定
  - OpenAI API（gpt-4o-mini）を利用。API キー（OPENAI_API_KEY）必須。

- ユーティリティ
  - paper_verification_report: ペーパートレード DB から検証レポート生成
  - ログ設定ユーティリティ（日次ローテーション、stdout 両対応）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

3. セットアップ手順
-------------------

前提：
- Python 3.9+（typing / pathlib を活用するため推奨）
- DuckDB, psutil, openai 等のパッケージが必要（下記は一例）。

推奨パッケージ（例）
- duckdb
- psutil
- openai
- PyYAML（設定 YAML のパース検証用、必須ではない）

一般的な手順（仮想環境推奨）:

1) 仮想環境作成・有効化
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2) 依存パッケージをインストール
   pip install duckdb psutil openai PyYAML

   （実運用では requirements.txt を用意して pip install -r requirements.txt を推奨）

3) プロジェクトルートに data/ と logs/ を作成（任意）
   mkdir -p data logs

4) .env を作成
   - 対話式: python -m kabusys.config_setup
   - 手動: .env に必要環境変数を記述
   重要な環境変数（代表）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV          : development | paper_trading | live (デフォルト: development)
     - DUCKDB_PATH          : data/kabusys.duckdb (デフォルト)
     - SQLITE_PATH          : data/monitoring.db (監視用、デフォルト)
     - PAPER_TRADING_SQLITE_PATH : data/paper_trading.db (paper_trading 用)
     - OPENAI_API_KEY       : OpenAI を使う場合に必要
     - LOG_LEVEL            : DEBUG/INFO/WARNING/ERROR

5) 設定検証（任意だが推奨）
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになる:
   python -m kabusys.validate_config --strict

4. 使い方（起動・主要コマンド）
-----------------------------

- 設定ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  python -m kabusys.run_execution

  動作ポイント:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録して本番 DB と分離します。
  - 起動時に data/stop_requested.flag が既に存在する場合は起動しません（安全機構）。
  - 実行中は data/execution.pid に PID を出力（設定に応じて）。
  - 停止は data/stop_requested.flag を作成するか ExecutionEngine 側で kill.flag を検出して停止します。

- Monitoring（監視ループ）起動
  python -m kabusys.run_monitoring

  動作ポイント:
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60 秒）。
  - 監視は monitoring DB（Settings.sqlite_path）に書き込みます。
    run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視は本番 DB を観測するため）。
  - data/stop_requested.flag を検知すると監視ループを終了します。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report
  期間指定例:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB 指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（ライブラリ関数）
  - ニューススコアリング:
    from kabusys.ai import score_news
    score_news(duckdb_conn, target_date, api_key=...)
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key=...)

  注意: OpenAI API 呼び出しを行う機能は OPENAI_API_KEY または api_key 引数が必須です。API 利用制限や課金に注意してください。

ログ
- 標準出力（stdout）とログファイル（logs/<app_name>.log）に出力されます。
- ログは日次ローテーション（30 日分保持）されます。

プロセス優先度 / CPU affinity
- 起動スクリプトは最初に set_process_priority("high") を呼び出します（psutil が必要）。失敗しても起動は継続します。

停止フラグの使い分け
- data/stop_requested.flag: 明示的にプロセス（monitoring / execution）を止めるためのフラグ（run_* が監視している）。
- data/kill.flag: Monitoring の KillSwitch が条件を満たしたときに書き込む（ExecutionEngine に停止信号を送るための自動フラグ）。
- KILL_FLAG_CLEAR_ON_START 環境変数 = 1 にすると起動時に kill.flag を自動クリアする（本番では 0 推奨）。

5. ディレクトリ構成（主要ファイル）
-----------------------------------

リポジトリの主要なパッケージ構成（src/kabusys 配下の重要モジュールを抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings クラス（KABUSYS_ENV 等）
  - config_setup.py          — .env 対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py       — 設定検証 CLI（python -m kabusys.validate_config）
  - run_execution.py         — ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - run_monitoring.py        — SystemMonitor 起動スクリプト（python -m kabusys.run_monitoring）

  - execution/               — 発注エンジン関連（EngineConfig, ExecutionEngine, OrderManager, Reconciler, BrokerFactory 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py       — 注文ログ解析（滞留注文・約定異常など）
    - risk_monitor.py        — ドローダウン・ポジション上限チェック
    - kill_switch.py         — Kill Switch（kill.flag 書き込み）
    - monitoring_engine.py   — 監視コンポーネントを束ねるエンジン
    - alert_manager.py       — （アラート送信：LINE 等）（実装参照）

  - portfolio/
    - portfolio_builder.py   — 候補選定・等重/スコア重み計算
    - position_sizing.py     — 発注株数計算・aggregate cap 等
    - risk_adjustment.py     — セクター上限・レジーム乗数

  - research/
    - factor_research.py     — momentum / volatility / value 計算（DuckDB）
    - feature_exploration.py — forward returns / IC / summary 等

  - ai/
    - news_nlp.py            — ニュースを LLM でスコアリングして ai_scores に書き込み
    - regime_detector.py     — ETF MA + マクロニュースでレジーム判定

  - data/                    — 実行時に使用するディレクトリ（例: data/*.db, data/kill.flag, data/stop_requested.flag）
  - logs/                    — ログファイル出力先（logs/<app>.log）

6. 重要な注意点 / 運用上のヒント
--------------------------------
- 本番環境（KABUSYS_ENV=live）では .env の値を慎重に管理してください。validate_config は live 時に注意喚起を出します。
- Kill Switch の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は本番での誤設定に注意。通常は 0（クリアしない）を推奨します。
- OpenAI を使う処理は API 呼び出し回数・コスト・応答の不確実性に留意してください。失敗時は多くの箇所でフェイルセーフが組み込まれていますが、監視は必須です。
- DuckDB / SQLite のパスは環境変数で変更可能（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）。
- ロギング設定は kabusys.utils.logging_setup.setup_logging を通して統一しています。カスタム設定が必要な場合はここを参照してください。

7. 開発・寄稿
--------------
- 新しい機能追加や修正を行う場合、ユニットテスト・設定検証を実行し、設定や DB スキーマ変更があれば migrate を忘れないでください（monitoring_db.init_monitoring_db には簡易マイグレーションが含まれています）。
- ドキュメントやコメントは設計意図（ルックアヘッド回避やフェイルセーフ）を尊重して更新してください。

お問い合わせ・補足が必要でしたら、どの部分の README を詳しく書き起こすか（例：ExecutionEngine の起動パラメータ説明、AI モジュールの使用例、DB スキーマの詳細など）を教えてください。必要に応じてサンプル .env テンプレートや起動スクリプト例も追加します。