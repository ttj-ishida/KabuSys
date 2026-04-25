KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買／研究プラットフォームです。本リポジトリは以下の主要機能を含むモジュール群で構成されています。

- 発注実行エンジン（ExecutionEngine）
- 監視／アラート（Monitoring）
- ポートフォリオ構築（候補選定・配分・株数算出）
- リサーチ（ファクター計算・特徴量解析）
- AI 支援（ニュースセンチメント / レジーム判定：OpenAI を利用）
- 環境設定ウィザード / 設定検証ツール
- ペーパートレード検証レポート生成ツール

主な設計方針
- 環境変数 / .env による設定管理
- DuckDB / SQLite を利用したデータ保持（分析用と監視用で分離）
- Paper Trading (KABUSYS_ENV=paper_trading) 時は本番 DB と完全分離して動作
- LLM 呼び出し（OpenAI）は失敗時にフォールバックし、システム全体を停止させないフェイルセーフ設計

機能一覧
--------
- 設定ウィザード: python -m kabusys.config_setup で .env の作成・更新が可能
- 設定検証: python -m kabusys.validate_config（--strict オプションで警告をエラー扱い）
- 実行エンジン起動: python -m kabusys.run_execution
  - 本番 / ペーパートレードの切替（KABUSYS_ENV）
  - 外部ブローカークライアントの抽象化（BrokerClientFactory）
  - PID ファイル管理、停止フラグ検出（data/stop_requested.flag 等）
- 監視プロセス起動: python -m kabusys.run_monitoring
  - システムリソース・データ鮮度・注文状態・リスクをポーリング
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）
  - 監視ログは SQLite（monitoring.db）へ永続化
- Kill Switch: 条件に応じて data/kill.flag を書き、ExecutionEngine に停止シグナルを送信
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- ポートフォリオ構築ユーティリティ
  - 候補選定、等分配 / スコア加重配分、セクター制約、ポジションサイズ算出
- リサーチユーティリティ
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）など
- AI モジュール
  - news_nlp: ニュース記事を LLM（gpt-4o-mini 想定）でセンチメント評価して ai_scores に格納
  - regime_detector: ETF MA 等とマクロセンチメントを合成して regime（bull/neutral/bear）判定

セットアップ手順
----------------

前提
- Python 3.10+（typing の union 型などを想定）
- 必要な Python パッケージ（例: duckdb, psutil, openai, PyYAML（任意））

推奨インストール例（venv を使用）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   （requirements.txt が無い場合は少なくとも duckdb, psutil, openai をインストールしてください）
   - 例:
     - pip install duckdb psutil openai PyYAML

環境変数 / .env
- 初期設定は対話式ウィザードで作成できます:
  - python -m kabusys.config_setup
- 重要な環境変数（主なもの）
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 DB（paper_trading 時）
  - OPENAI_API_KEY — AI モジュール利用時に必要
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（0/1、本番では 0 推奨）

自動 .env ロード
- デフォルトでプロジェクトルートの .env / .env.local を自動ロードします。
- 無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

設定検証
- .env を作成したら設定を検証できます:
  - python -m kabusys.validate_config
  - 警告をエラー扱いにする場合: python -m kabusys.validate_config --strict

使い方（実行例）
----------------

1) 監視プロセスを起動
- デフォルト（ポーリング間隔 60 秒）
  - python -m kabusys.run_monitoring
- ポーリング間隔を変更する場合:
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring
- 監視プロセスは data/stop_requested.flag が作成されるとループを終了します。

2) 実行エンジンを起動
- 本番/ペーパートレードは KABUSYS_ENV で切り替え
  - python -m kabusys.run_execution
- ペーパートレード時は MockBrokerClient が使われ、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）へ記録されます。
- 実行エンジンは data/stop_requested.flag の存在で停止します。エンジンの PID は data/execution.pid に書き込まれます。

3) ペーパートレード検証レポート
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- データベース指定:
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

4) AI モジュール（ニューススコア / レジーム）
- OpenAI API キーが必要（OPENAI_API_KEY）。
- news_nlp.score_news / regime_detector.score_regime をアプリケーションから呼び出して利用します（直接コマンドラインエントリは提供されていませんが、スクリプトに組み込まれています）。

停止・Kill Switch
- 監視や運用上の緊急停止は KillSwitch により data/kill.flag を作成して通知する設計です。
- また run_*.py は data/stop_requested.flag の検出で安全に停止します（運用側でフラグファイルを作成することで停止できます）。

データベース / マイグレーション
- 監視テーブルの初期化は init_monitoring_db() により冪等に作成されます（既存 DB に対するマイグレーションも一部自動で実施します）。
- DuckDB と SQLite を用途に応じて使い分けます（DuckDB: 分析 / リサーチ、SQLite: 監視・発注ログなど）。

ディレクトリ構成（主要ファイル）
--------------------------------
以下はリポジトリ内 src/kabusys 以下の主なファイル/ディレクトリ（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (参照あり)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照あり)
  - execution/
    - execution_engine.py (参照あり)
    - broker_factory.py (参照あり)
    - order_manager.py (参照あり)
    - order_repository.py (参照あり)
    - reconciler.py (参照あり)
    - risk_manager.py (参照あり)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

（上記は抜粋であり、さらに細かいモジュールが含まれます。）

開発・デバッグのヒント
- ロギングは kabusys.utils.logging_setup.setup_logging を各起動スクリプトから呼び出して統一管理しています。ログ出力先はデフォルト logs/<app_name>.log（30日保持）です。
- 自動ロードを無効化してユニットテストを行う場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI など外部 API は失敗した場合にフォールバック動作するよう設計されていますが、AI 関連機能を本番で使う場合は API キーと出力バリデーションに注意してください。

ライセンス / バージョン
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

最後に
------
この README はコードベースの主要機能と運用方法の要約です。実際のデプロイ・運用時には .env の設定、DB パス、バックアップ・監視体制を十分に整備してください。特に KABUSYS_ENV=live で運用する場合は設定検証（python -m kabusys.validate_config）を必ず行ってください。質問や追記してほしい項目があれば教えてください。