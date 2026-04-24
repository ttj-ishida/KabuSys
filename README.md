README
======

概要
----
KabuSys は日本株の自動売買／リサーチ基盤を想定した Python パッケージです。本リポジトリには以下の主要機能群が含まれます。

- 発注エンジン（ExecutionEngine）とペーパートレード切替
- 監視サブシステム（System / Trade / Risk の監視、Kill Switch）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイジング）
- リサーチ（ファクター計算・特徴量探索）
- AI 支援（ニュース NLP によるセンチメント評価、レジーム判定）
- 運用支援ツール（設定ウィザード、設定検証、Paper Trading 検証レポート）

主な設計方針：
- 設定は .env / 環境変数で管理（自動ロード機能あり）
- 本番 DB／ペーパー DB を分離可能
- DuckDB をデータ分析用に使用、SQLite を監視／注文ログ用に使用
- OpenAI（gpt-4o-mini 等）との連携はオプション（OPENAI_API_KEY 必須）

機能一覧
--------
- 環境セットアップウィザード: kabusys.config_setup.run_wizard（python -m kabusys.config_setup）
- 設定検証 CLI: kabusys.validate_config（python -m kabusys.validate_config）
- ExecutionEngine 起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading で MockBrokerClient を使用し、data/paper_trading.db に書き込む
- Monitoring 起動: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を参照（KABUSYS_ENV に依存しない）
- Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
- ポートフォリオ構築関数群
  - 候補選定 / 等重・スコア重み付け / ポジションサイズ計算 / セクター上限適用 / レジーム乗数
- AI モジュール
  - kabusys.ai.news_nlp.score_news: raw_news から銘柄別センチメントを取得して ai_scores に書き込み
  - kabusys.ai.regime_detector.score_regime: ETF とマクロ記事を合成してレジーム判定
- 監視周り
  - system_monitor / trade_monitor / risk_monitor / monitoring_engine / kill_switch
  - monitoring_db: SQLite のテーブル作成・マイグレーションロジック

セットアップ手順
----------------

前提
- Python 3.10 以上を推奨（型ヒントに union 型 | を使用）
- 必要パッケージ（最低限）:
  - duckdb
  - psutil
  - openai （AI 機能を使う場合）
  - PyYAML（config/*.yaml の内容検証を行う場合）
- 任意: 仮想環境を作成してからインストールしてください。

1. 依存ライブラリのインストール（例）
   - pip install duckdb psutil openai PyYAML

2. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
     - ウィザードで J-Quants トークン、kabu API パスワード、その他パス等を入力して .env を生成します。
   - あるいは手動で .env を作成（.env.example を参照してください）。

3. 設定検証（起動前）
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります。

4. DB 準備
   - 監視用 SQLite（デフォルト: data/monitoring.db）は各起動スクリプトが init を行います（init_monitoring_db）。
   - DuckDB（デフォルト: data/kabusys.duckdb）は分析用。必要なテーブル（prices_daily, raw_financials, raw_news 等）は外部工程で準備してください。

主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB）
- OPENAI_API_KEY（AI 機能使用時に必須）
- LOG_LEVEL / LOG_DIR
- MONITOR_POLL_INTERVAL（監視ポーリング秒；run_monitoring 用）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag をクリアするか）

使い方
------

設定・検証
- 対話式で .env を作る:
  - python -m kabusys.config_setup
- 設定を検証:
  - python -m kabusys.validate_config
  - 例: python -m kabusys.validate_config --strict

監視（Monitoring）
- 起動:
  - python -m kabusys.run_monitoring
- ポーリング間隔を調整する:
  - export MONITOR_POLL_INTERVAL=30
- 停止:
  - デプロイ用の stop フラグ（data/stop_requested.flag）を作るとループが終了します。
  - または Ctrl-C（KeyboardInterrupt）

実行エンジン（ExecutionEngine）
- 起動（本番 or 開発）:
  - python -m kabusys.run_execution
- ペーパートレード（MockBroker）で起動:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
  - ペーパートレード DB はデフォルトで data/paper_trading.db を使用（PAPER_TRADING_SQLITE_PATH で変更可能）
- 停止:
  - data/stop_requested.flag を作成するとエンジン実行スレッドが停止します。
- 実行時に data/execution.pid が作成されます（PID 管理用）。

Paper Trading 検証レポート
- 期間を指定してレポートを生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB パスを指定:
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

AI 機能
- OpenAI キーが必要:
  - export OPENAI_API_KEY=sk-...
- ニュース NLP（銘柄センチメント）:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - 既存の DuckDB 接続を渡し、score_news が ai_scores テーブルへ書き込みます。
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

ログ
- ログは stdout とファイル（logs/<app_name>.log）に出力されます。ログディレクトリは LOG_DIR 環境変数またはデフォルトの logs/。
- ログレベルは LOG_LEVEL（デフォルト INFO）。

停止と Kill Switch
- Kill Switch は kabusys.monitoring.kill_switch が data/kill.flag を書き込み、ExecutionEngine 側がこれを検知して安全停止します。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番環境では 0 推奨）。

ディレクトリ構成
----------------

（src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_monitoring.py         — Monitoring ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - data/                     — （外部）データパイプライン関連（prices_daily 等を想定）
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート生成 CLI
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメント取得（OpenAI 連携）
    - regime_detector.py      — マーケットレジーム判定（ETF MA + マクロ記事）
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ初期化 / 永続化層
    - system_monitor.py       — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py        — （コードベース内に存在、注文滞留等を検出）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag 書き込みユーティリティ
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — （通知管理; LINE 等への通知を想定）
  - execution/
    - execution_engine.py     — ExecutionEngine 本体（セッション管理）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py       — BrokerClient の生成（実ブローカ or Mock）
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 発注株数計算・資金割当
    - risk_adjustment.py      — セクター上限・レジーム乗数
  - research/
    - factor_research.py      — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py  — 将来リターン、IC、統計サマリー
  - utils/
    - logging_setup.py        — ロギング初期化ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/monitoring_db.py  — SQLite テーブル作成・マイグレーション
  - その他モジュール群（data.stats 等）

補足（実運用上の注意）
--------------------
- 本パッケージには実際の発注 API への接続ロジックや資金管理の最終設計などが必要です。live 環境での起動は十分なレビュー・テストを行ってください。
- .env は絶対にリポジトリにコミットしないでください（config_setup も注意書きを出しています）。
- OpenAI 等の外部 API を利用する際はレート制限・コストに注意してください。
- psutil によるプロセス優先度設定や CPU affinity の変更は権限によって失敗することがあります（ログに警告が出ます）。

ライセンス・バージョン
----------------------
- パッケージバージョン: __version__ = "0.1.0"（kabusys/__init__.py）
- ライセンス情報が別途ある場合はリポジトリの LICENSE を参照してください。

以上。README に含めたい追加情報（例: サンプル .env、requirements.txt の内容、実行のユニットテスト方法等）があれば指示してください。