KabuSys — 日本株自動売買システム
==============================

概要
----
KabuSys は日本株向けの自動売買システムのコードベースです。  
設計方針として、取引ロジック・ポートフォリオ構成・リサーチ・監視・AI 支援の各機能をモジュール化しており、本番（live）／ペーパートレード（paper_trading）／開発（development）モードをサポートします。  
主な実行コンポーネントは ExecutionEngine（発注エンジン）と Monitoring（監視エンジン）です。

主な機能
--------
- 実行エンジン（ExecutionEngine）
  - ブローカークライアントの抽象化（paper_trading 時は MockBroker を使用し DB を分離）
  - 注文管理、リスク管理、突合（reconciler）等の実装基盤
- 監視（Monitoring）
  - システム稼働監視（CPU/メモリ/ディスク、プロセス生存）
  - 注文ログ / リスクログ / ダッシュボード永続化（SQLite）
  - Kill Switch（ドローダウンやポジション超過時に停止フラグを作成）
  - アラート送出（LINE などの通知は設定に依存）
- ポートフォリオ構築ユーティリティ（選定・重み付け・ポジションサイズ計算・セクター制限）
- リサーチ（DuckDB を用いたファクター計算、将来リターン、IC 計算、統計サマリー）
- AI モジュール
  - ニュース NLP（OpenAI を用いたニュースセンチメントの銘柄別スコア化）
  - レジーム判定（ETF の MA とマクロニュースを合成して market_regime を算出）
- ツール
  - Paper Trading の検証レポート生成スクリプト
- 開発支援
  - .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ...（省略）

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（代表例）
   - pip install duckdb psutil openai
   - validate_config の YAML 検証を使う場合: pip install pyyaml
   - その他、実行環境に応じて追加の依存が必要な場合があります。

4. .env を作成
   - 対話ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに .env を作成（.env.example を参照）。

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告も厳格に扱う場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリの準備
   - デフォルトの DB/ログパスは .env の設定に従います。デフォルト例:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading DB: data/paper_trading.db
   - ログディレクトリ: logs/（デフォルト）

重要な環境変数（抜粋）
-----------------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 運用関連
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
  - DUCKDB_PATH (例: data/kabusys.duckdb)
  - SQLITE_PATH (例: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード時の専用 SQLite)
  - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START

- 監視専用 / 実行時
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化

使い方（代表的な実行例）
-----------------------
- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を用い paper_trading 用 DB（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中は data/execution.pid に PID を書く設計（pid_file は設定で変更可）。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番用 sqlite_path を使用（環境に依らず同一の監視 DB を参照）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH を指定する代わりに使えます）

API / ライブラリ的な利用
------------------------
- ポートフォリオユーティリティ
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- リサーチ
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
  - これらは DuckDB 接続を受け取り、prices_daily / raw_financials 等のテーブルを参照します。
- AI モジュール
  - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None) — DuckDB 接続 & target_date を渡して ai_scores を更新
  - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None) — market_regime テーブルへ書き込み
  - OpenAI API キーは api_key 引数か環境変数 OPENAI_API_KEY で指定

プロセス制御・停止
-----------------
- 優雅停止：
  - run_execution / run_monitoring はプロジェクトの data/stop_requested.flag を監視し、存在を検知するとループを抜けて停止します。
- Kill Switch：
  - monitoring/risk_monitor や kill_switch により条件を満たすと data/kill.flag が書き込まれ、ExecutionEngine が検出して停止します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアする動作になるため、本番では注意が必要。

ログ
---
- setup_logging によりコンソール (stdout) と日次ローテーションされるファイルログ（logs/<app_name>.log）を併用します。
- デフォルトログディレクトリ: logs/
- ログローテーション: 日次、30日分保持

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定読み込み・Settings
  - config_setup.py         — .env 対話ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py           — ニュース NLP（OpenAI 経由で銘柄ごとにスコア化）
    - regime_detector.py    — 市場レジーム判定
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py      — monitoring 用 SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py      — （trade 関連監視ロジック）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py      — （アラート送出の抽象化）
  - execution/
    - (order_manager, engine, broker_factory, risk_manager, reconciler, order_repository 等)
  - data/                   — 既定のデータ / DB / フラグファイル (ランタイム生成)
  - logs/                   — ログ出力ディレクトリ（ランタイム生成）

注意点 / 運用上のヒント
----------------------
- .env は絶対にリポジトリへコミットしない（config_setup でも警告あり）。
- KABUSYS_ENV=live の場合は本番運用となるため、KILL_FLAG_CLEAR_ON_START=1 等の設定に注意してください。
- process_priority（psutil を使用）で優先度を上げる処理があります。権限不足で警告が出る場合がありますが動作は継続します。
- DuckDB / SQLite のパスやログディレクトリは .env で変更可能。ディレクトリの親が存在しない場合は起動時に作成される（場合による）。
- validate_config は .env と config/*.yaml の基本的な検証を行います。PyYAML が無い場合は YAML 検証をスキップします（警告出力）。

ライセンス / バージョン
----------------------
- パッケージバージョン:
  - kabusys.__version__ = "0.1.0"

最後に
------
この README はコードベース内の主要なスクリプト・モジュールの概要と運用手順をまとめたものです。各モジュールの詳細な使い方・引数・内部ロジックは該当ソースファイルの docstring やコメントを参照してください。必要であれば、特定モジュールの使い方（例: ExecutionEngine の設定項目、AI モジュールのテスト方法、monitoring のカスタマイズ方法）についてさらに詳しいドキュメントを作成します。