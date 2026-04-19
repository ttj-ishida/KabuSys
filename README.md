README
======

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤です。本リポジトリは以下の主要機能を含みます。

- ExecutionEngine：発注・注文管理・リスク管理を行う実行エンジン
- Monitoring：システム稼働・注文状況・リスクをポーリング監視し、Kill Switch を発動
- Research：DuckDB を用いたファクタ計算・将来リターン・IC 計算などの分析機能
- AI モジュール：OpenAI（gpt-4o-mini）を利用したニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）
- ユーティリティ：環境設定ウィザード、設定検証、ログ設定、プロセス優先度操作、Paper Trading 検証レポート等
- ポートフォリオ構築ユーティル：候補選定、重み付け、ポジションサイズ決定、セクター制限、レジーム乗数

主な特徴
--------
- 環境別分離（development / paper_trading / live）により本番 DB とペーパートレード DB を分離
- .env ベースの設定管理（対話式ウィザードと自動ロード）
- DuckDB を分析用 DB、SQLite を監視・注文ログ用 DB として利用
- OpenAI を使った NLP パイプライン（ニュース集約 → バッチ送信 → JSON 検証 → ai_scores 書込）
- フェイルセーフ設計（API 失敗はフォールバック／ログにより安全に継続）
- Monitoring 側で Kill Switch（data/kill.flag）を作成して ExecutionEngine を停止可能

セットアップ手順
----------------

1. Python 環境
   - 推奨: Python 3.10+
   - 仮想環境を作成して有効化する例:
     - python -m venv .venv
     - source .venv/bin/activate  (Unix/macOS)
     - .venv\Scripts\activate     (Windows)

2. 依存パッケージをインストール
   - 必要な主なパッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（config/*.yaml を検証したい場合に必要）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. プロジェクトルートと data/logs ディレクトリ
   - 実行時に自動作成されますが、手動で作る場合:
     - mkdir -p data logs

4. 環境変数の設定（.env）
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN=your_token
     - KABU_API_PASSWORD=your_password
     - KABUSYS_ENV=development|paper_trading|live
     - OPENAI_API_KEY=sk-...
   - デフォルト DB パス:
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い:
     - python -m kabusys.validate_config --strict

使い方
------

- 実行エンジン（ExecutionEngine）起動
  - 本番/開発/ペーパートレードは KABUSYS_ENV によって動作が変わります。
  - 実行:
    - python -m kabusys.run_execution
  - メモ:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（既定: data/paper_trading.db）へ記録して完全に分離します。
    - data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中は data/execution.pid に PID を書きます。停止は stop フラグや kill.flag によって行います。

- 監視プロセス（Monitoring）起動
  - 実行:
    - python -m kabusys.run_monitoring
  - 説明:
    - 監視は SQLite（settings.sqlite_path）へログを記録します（環境に依らず本番の sqlite_path を使用）。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可。デフォルトは 60 秒。
    - 監視は data/stop_requested.flag を検知するとループを抜けます。
    - 監視側から条件を満たすと Kill Switch（data/kill.flag）を書き込み、ExecutionEngine を停止させることができます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示するには --db PATH を使用（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- AI モジュール（プログラム内呼び出し）
  - ニューススコア付与:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key="...")  # DuckDB 接続を渡す
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

- リサーチ / ファクター計算（プログラム内）
  - from kabusys.research import calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank
  - いずれも DuckDB 接続と target_date を渡して使用します。

環境変数（よく使うもの）
-----------------------
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant|partial|never|reject）

停止・Kill Switch・フラグファイル
------------------------------
- data/kill.flag: Kill Switch（監視側が条件に応じて書き込む）。ExecutionEngine 起動時の挙動に注意（環境変数 KILL_FLAG_CLEAR_ON_START により起動時自動クリア可）。
- data/stop_requested.flag: プロセス（run_execution/run_monitoring）の外部停止トリガー。存在するとループを抜けて終了します。
- PID ファイル: data/execution.pid 等に PID を出力します。

ログ
---
- ログはデフォルトで logs/ ディレクトリに日次ローテーションで出力されます（kabusys.utils.logging_setup.setup_logging を各スクリプトが利用）。
- コンソール出力は stdout に出ます。

ディレクトリ構成（主要ファイル）
-------------------------------

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/.env ロードと Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — （注: trade_monitor 実装を参照してください）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - monitoring_engine.py    — 各モニタを束ねるエンジン
    - kill_switch.py          — kill.flag 書き込みユーティリティ
    - alert_manager.py        — （アラート送信の実装）
  - execution/
    - execution_engine.py     — 実行エンジン（EngineConfig, run_session 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み付け
    - position_sizing.py      — 株数算出・リスク制限
    - risk_adjustment.py      — セクター制限・レジーム乗数
  - research/
    - factor_research.py      — Momentum/Value/Volatility 等の計算
    - feature_exploration.py  — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py             — ニュース集約 → OpenAI スコアリング → ai_scores 書込
    - regime_detector.py      — ETF MA + マクロセンチメントでレジーム判定
  - tools/
    - paper_verification_report.py  — Paper Trading の検証レポート生成
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定

注意事項 / ベストプラクティス
-----------------------------
- .env は決して Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）では kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）を避けることを推奨します。
- OpenAI キーを利用する機能は API コストがかかるため、local や開発環境では無効化またはモックを使用してください。
- DuckDB / SQLite ファイルはバックアップや扱いに注意してください（特に本番データ）。

トラブルシューティング
-----------------------
- config 検証でエラーが出たら: python -m kabusys.validate_config を実行して指摘内容に従って .env / config/*.yaml を修正してください。
- ログファイルが書けない場合:
  - LOG_DIR 環境変数や logs/ ディレクトリの権限を確認してください。失敗するとコンソール出力のみになります。
- psutil によるプロセス優先度 / CPU affinity 設定に失敗する場合、権限不足や未サポート OS が原因です。警告ログが出ますが処理自体は継続します。

ライセンス / バージョン
-----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

最後に
-----
この README はコードベースから抽出した現時点での使い方の概要です。追加の運用手順やデプロイ手順はプロジェクト固有のドキュメントや運用ガイドを参照してください。必要であれば、README に起動例や systemd / Supervisor 用のユニットファイル例なども追記できます。必要なら指示してください。