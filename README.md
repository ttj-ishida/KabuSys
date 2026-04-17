KabuSys
======

日本株自動売買システムのミニマル実装（ライブラリ＋実行スクリプト群）。  
この README はリポジトリ内のコード（src/kabusys 以下）を基に作成しています。

概要
---
KabuSys は日本株に対する自動売買・監視・研究用のモジュール群です。  
主な機能は次のとおりです。

- 注文実行エンジン（ExecutionEngine）: 本番 / ペーパートレード対応
- 監視（Monitoring）: システム状態、注文滞留、リスク（ドローダウン等）の定期チェック
- ポートフォリオ構築ユーティリティ: 候補選定、重み計算、ポジションサイズ算出、セクター制約
- 研究機能（Research）: ファクター計算、将来リターン、IC 計算、統計サマリ
- AI 統合（OpenAI）: ニュースの NLP スコアリング、マクロセンチメントによるレジーム判定
- ユーティリティ: プロセス優先度設定、設定ウィザード、設定検証、レポート生成

主な特徴
---
- 環境ごとに挙動を分ける（KABUSYS_ENV: development / paper_trading / live）
- ペーパートレードは本番 DB と分離（デフォルト: data/paper_trading.db）
- 監視は SQLite にログを蓄積（デフォルト: data/monitoring.db）
- DuckDB を解析用 DB として利用（デフォルト: data/kabusys.duckdb）
- OpenAI を利用した NLP 処理（news_nlp, regime_detector）
- kill.flag / stop flag によるプロセス制御（フラグファイル方式）
- テストしやすい純粋関数群（portfolio 等）と DB 書き込み層の分離

セットアップ
---
前提:
- Python 3.9+
- 必要パッケージ（一部機能で必須）:
  - duckdb
  - psutil
  - openai  （AI 機能を使う場合）
  - PyYAML （config/*.yaml の文法チェックを行う場合）

インストール例（仮想環境推奨）:
- python -m venv .venv
- source .venv/bin/activate
- pip install -r requirements.txt  （requirements.txt がない場合は上記パッケージを個別にインストール）

環境変数 / .env
- プロジェクトルートに .env を置くことで設定を自動読み込みします（.env.local もサポート）。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 主要な環境変数（抜粋）:
  - JQUANTS_REFRESH_TOKEN （必須）
  - KABU_API_PASSWORD （必須）
  - KABUSYS_ENV （development / paper_trading / live、デフォルト: development）
  - DUCKDB_PATH （デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH （監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH （ペーパートレード専用 DB、デフォルト: data/paper_trading.db）
  - OPENAI_API_KEY （OpenAI を使う場合）
  - PAPER_FILL_MODE （paper_trading 時の約定モード: instant|partial|never|reject、デフォルト: instant）
  - LOG_LEVEL（DEBUG/INFO/...）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。開発のみで 1 を使うことを想定）

.env 初期化ウィザード:
- python -m kabusys.config_setup
  - 対話的に .env を生成 / 更新できます。

設定検証:
- python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります。

使い方（主要スクリプト）
---
実行系
- 実行エンジン（ExecutionEngine）起動:
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存します。
    - paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db に記録します（本番 DB と完全分離）。
  - 実行中の PID は data/execution.pid に書き込まれます（デフォルト）。
  - 停止: プロセスが監視する stop フラグファイル（data/stop_requested.flag）を作ることで安全に停止できます。
  - 実行前: Settings.kill_flag_clear_on_start=1 により起動時に kill.flag を自動クリアする設定があるため本番では注意してください。

監視系
- 監視ポーリング起動:
  - python -m kabusys.run_monitoring
  - デフォルトポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書きできます（整数秒）。
  - 監視は KABUSYS_ENV にかかわらず本番の sqlite_path（Settings.sqlite_path）を使用します。
  - 監視の停止は data/stop_requested.flag を作成するとポーリングループが終了します。

ツール
- 証券ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定することも可能です。
- AI / レジームスコアリング（ライブラリ関数として利用）:
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime
  - OpenAI API キー（OPENAI_API_KEY）必須。API 呼び出しは再試行ロジックを持ちフェイルセーフで扱います。

フラグ / ファイル制御
- 停止フラグ（両スクリプトで使用）:
  - data/stop_requested.flag — 作成されると run_monitoring / run_execution のポーリング / 待機ループが停止します。
- Kill Switch:
  - data/kill.flag — KillSwitch が書き込み、実行エンジンを強制停止するトリガーとして使う設計です。内容は理由テキストです。
  - KillSwitch は監視結果（ドローダウン、ポジション上限等）を評価して書き込みます。
- PID:
  - data/execution.pid — 実行エンジンが存在するかを監視用に書き込みます。stale PID を検出したら削除してログに記録します。

ディレクトリ構成（主なファイル / モジュール）
---
src/
  kabusys/
    __init__.py
    config.py                 — 環境変数・.env 自動読み込み / Settings
    config_setup.py           — .env 対話ウィザード
    validate_config.py        — 設定検証 CLI
    run_execution.py          — ExecutionEngine 起動スクリプト
    run_monitoring.py         — Monitoring ポーリング起動スクリプト

    ai/
      __init__.py
      news_nlp.py             — ニュース NLP スコアリング（OpenAI）
      regime_detector.py      — マクロ + MA による市場レジーム判定

    monitoring/
      monitoring_db.py        — SQLite 永続化（system_status, trade_logs, positions, risk_logs, dashboard）
      system_monitor.py       — CPU/メモリ/ディスク/データ鮮度 / PID チェック
      trade_monitor.py        — 注文滞留・約定異常監視
      risk_monitor.py         — ドローダウン・ポジション上限監視
      kill_switch.py          — kill.flag の管理
      monitoring_engine.py    — Monitors をまとめたポーリング実行
      alert_manager.py        — （未表示）通知ロジック

    execution/                 — Execution 関連（Engine, OrderManager, BrokerFactory 等）
      （この README のコード抜粋では細部は省略）

    portfolio/
      portfolio_builder.py    — 候補選定・重み（equal / score）
      position_sizing.py      — 株数決定・リスク制限・単元丸め
      risk_adjustment.py      — セクター制約・レジーム乗数

    research/
      factor_research.py      — Momentum / Volatility / Value 等のファクター計算（DuckDB）
      feature_exploration.py  — 将来リターン・IC・統計サマリ

    data/                      — 実行時に使う data ディレクトリ（DB / flag / pid）
      （例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag, data/execution.pid）

    tools/
      paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

    utils/
      process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ

使い方の例（コマンド）
---
1) .env を作る（簡易）
- python -m kabusys.config_setup

2) 設定チェック
- python -m kabusys.validate_config
- python -m kabusys.validate_config --strict

3) 監視ループを起動
- MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

4) 実行エンジン（ペーパートレード）の起動
- KABUSYS_ENV=paper_trading python -m kabusys.run_execution

5) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- または DB を直接指定:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

注意事項 / 運用上のポイント
---
- .env は機密情報（API トークンやパスワード）を含むため絶対にリポジトリにコミットしないでください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨します。自動クリアを有効にすると Kill Switch を誤って無効化する恐れがあります。
- OpenAI を用いる機能は API キーとコストに注意してください。失敗時はフェイルセーフで継続する設計ですがログは必ず確認してください。
- データベース（DuckDB / SQLite）のパスは Settings で変更可能です。運用時は適切なバックアップを検討してください。
- process_priority.set_process_priority は OS により動作が異なり（権限や未対応 OS）、失敗時は警告でスキップします。

補足（実装上の挙動）
---
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックします。
- run_execution はペーパートレード時に専用の SQLite DB（PAPER_TRADING_SQLITE_PATH）を使い、本番 DB と分離します。
- MonitoringDB.init_monitoring_db は既存 DB に対して安全なマイグレーション（カラム追加）を行います。
- AI 関連（news_nlp, regime_detector）は OpenAI の応答の不確実性に備え、JSON バリデーション・リトライ・スコアのクリッピングなどを実装しています。

ライセンス / バージョン
---
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状 0.1.0）。

必要に応じて README を更新します。特に実行手順や依存関係（requirements.txt）がリポジトリに追加された場合は、そちらに合わせて本ドキュメントを同期してください。