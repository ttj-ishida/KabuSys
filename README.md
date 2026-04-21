KabuSys — 日本株自動売買システム
================================

このリポジトリは、日本株向けの自動売買 / リサーチ / モニタリング機能をまとめた内部ライブラリ群です。
README ではプロジェクト概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめます。

要点
- Python パッケージとして提供。主要サブシステム: Execution（発注実行エンジン）、Monitoring（監視）、Research（因子計算）、Portfolio（銘柄選定・サイズ決定）、AI（ニュース NLP / レジーム判定）、各種ツール類。
- 環境変数（.env）で設定を管理。対話式ウィザードと検証 CLI を備えます。
- DuckDB / SQLite をデータ格納に利用。Paper Trading モードは本番 DB と完全分離されます。

プロジェクト概要
----------------
KabuSys は自動発注のためのライブラリ群と起動スクリプトを提供します。主な役割は以下。

- 発注エンジン（ExecutionEngine）: ブローカークライアントを通じて注文を出す。KABUSYS_ENV に応じて paper_trading（Mock）/ live を切替。
- 監視（Monitoring）: システム稼働状況、取引ログ、リスク（ドローダウン・ポジション上限）を定期的にチェックし、kill flag の書き込みや通知を行う。
- ポートフォリオ構築: 候補選定、重み付け、ポジションサイズ計算、セクター制限など純粋関数群。
- リサーチ: DuckDB 上でファクター計算、将来リターン計算、IC などを提供。
- AI モジュール: OpenAI を用いたニュースのセンチメントスコア付与（news_nlp）、マクロ＋価格を用いた市場レジーム判定（regime_detector）。
- ツール: Paper Trading 検証レポート生成や設定ウィザード等の CLI。

主な機能一覧
--------------
- 設定管理
  - .env 自動ロード（プロジェクトルートの .env / .env.local）
  - Settings クラス（型変換・検証を含む）
  - 対話式設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config

- 実行・監視
  - 実行エンジン起動: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
  - 監視ループ起動: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可（デフォルト 60 秒）
  - Kill Switch（data/kill.flag）書き込みによるエンジン停止シグナル
  - stop_requested.flag（data/stop_requested.flag）によるループ停止検知（両スクリプト）

- モニタリング DB（SQLite）
  - system_status / trade_logs / positions / risk_logs / dashboard テーブルの自動作成・マイグレーション

- ポートフォリオ構築
  - 候補選定、等重/スコア重み、リスクベースの position sizing、セクターキャップ、レジーム乗数

- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 使用）
  - 将来リターン、IC、統計サマリ等

- AI（LLM）
  - ニュースセンチメントスコア化（OpenAI gpt-4o-mini を想定）
  - マクロニュース＋ETF MA に基づくレジーム判定（冪等 DB 書き込み）

- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

セットアップ手順
-----------------
以下は開発環境での一般的な手順（例）。実際の要件ファイル requirements.txt がある場合はそちらを使用してください。

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（推定）
   - pip install duckdb psutil openai
   - （オプション）PyYAML があれば config/*.yaml の検証が可能: pip install PyYAML

   ※ 実際の requirements.txt があればそれを使用してください。

3. .env を作成
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参照）

4. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば修正し、--strict オプションで警告も FAIL 扱いにできます:
     - python -m kabusys.validate_config --strict

5. データディレクトリ作成（自動作成は多くの箇所で行われますが、手動で準備しておくと良い）
   - mkdir -p data logs

重要な環境変数（主なもの）
--------------------------------
- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API パスワード

- 実行環境切替
  - KABUSYS_ENV : development | paper_trading | live  （デフォルト: development）

- データ / ログ
  - DUCKDB_PATH    : DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH    : SQLite 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH : Paper Trading 用 SQLite（既定: data/paper_trading.db）
  - LOG_DIR        : ログディレクトリ（デフォルト: logs/）
  - LOG_LEVEL      : ログレベル（DEBUG/INFO/...、デフォルト INFO）

- AI
  - OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector 使用時）

- 監視関連
  - PID_FILE_PATH  : 実行エンジンの pid ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH : kill flag（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START : 起動時に kill flag を自動クリアするか（0/1）

- Paper Trading 固有
  - PAPER_FILL_MODE : instant | partial | never | reject （デフォルト: instant）

使い方（よく使うコマンド）
--------------------------

1) 環境設定ウィザード（.env の作成・更新）
   - python -m kabusys.config_setup

2) 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い:
     - python -m kabusys.validate_config --strict

3) 実行エンジン起動
   - python -m kabusys.run_execution
   - 補足:
     - KABUSYS_ENV=paper_trading に設定した場合、MockBrokerClient を使用し data/paper_trading.db に記録します。
     - 起動前に data/stop_requested.flag が存在する場合は起動を行いません（フラグを確認）。

4) 監視ループ起動
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒数で指定できます（デフォルト 60）。
     - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

5) Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

停止・Kill 操作
---------------
- Graceful stop（監視ループ / 実行エンジンの停止）:
  - プロジェクトルートの data/stop_requested.flag を作成すると、run_monitoring と run_execution のループが検知して終了します。

- Kill Switch（ExecutionEngine への停止シグナル）:
  - Monitoring の KillSwitch は条件を満たしたとき data/kill.flag を書き込みます。ExecutionEngine は Settings.kill_flag_path（デフォルト data/kill.flag）を参照して動作します。
  - kill.flag は Settings.kill_flag_clear_on_start=1 が設定されていない限り、起動時自動クリアされません（設定に注意）。

ログ
----
- ログはデフォルトで logs/ ディレクトリにアプリケーション別ファイル（例: execution.log, monitoring.log）として日次ローテーションで出力されます。stdout への出力も行われます。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一管理されています。

注意事項 / 運用上の補足
---------------------
- Paper Trading と Live は DB を分離する設計です（settings は paper_sqlite_path を持つ）。
- AI（OpenAI）を使う機能は API キーが必要です。API の失敗時はフェイルセーフ（0 やスキップ）で継続する実装方針です。
- 一部の検証（config/*.yaml の内容検証）は PyYAML のインストールが必要です。インストールされていない場合は警告が出ますが処理は継続します。
- プロセス優先度設定など OS に依存する処理は psutil を利用しており、権限不足等で設定に失敗する可能性があります（警告ログが出ます）。

ディレクトリ構成（主要ファイル）
--------------------------------
（src/kabusys をルートとした相対構成の抜粋）

- kabusys/
  - __init__.py                — パッケージ定義、バージョン
  - config.py                  — 環境変数読み込み・Settings クラス、自動 .env ロード
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring 起動スクリプト

  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI を使ったセンチメント）
    - regime_detector.py       — レジーム判定（ETF + マクロニュース）

  - monitoring/
    - monitoring_db.py         — SQLite テーブル作成・永続化層
    - system_monitor.py        — システム／データ鮮度検査
    - trade_monitor.py         — （注: trade_monitor 実装ファイルあり）
    - risk_monitor.py          — ドローダウン・ポジション監視
    - kill_switch.py           — kill.flag 管理
    - monitoring_engine.py     — 各モニタの統合ループ
    - alert_manager.py         — （通知管理：LINE 等を扱う実装がある想定）

  - execution/
    - execution_engine.py      — ExecutionEngine（起動・セッション制御）
    - broker_factory.py        — ブローカークライアント生成（paper/live 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 発注株数計算・集約制限
    - risk_adjustment.py       — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py       — Momentum/Volatility/Value 等の計算（DuckDB）
    - feature_exploration.py   — 将来リターン / IC / サマリー

  - data/                      — 実行時 DB / フラグ / pid 等が置かれる想定 (プロジェクト直下)
    - monitoring.db (デフォルト SQLite)
    - paper_trading.db (paper trading 用)
    - kabusys.duckdb
    - execution.pid
    - kill.flag
    - stop_requested.flag

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI

開発者向けメモ
----------------
- DuckDB 接続は DuckDBPyConnection を前提に SQL を発行する設計です。prices_daily / raw_financials / raw_news 等のテーブルを想定します。
- 多くの関数は「ルックアヘッドバイアス防止」のため date.today()/datetime.now() を直接参照しない設計になっています（引数で日付を渡す）。
- DB 書き込みは冪等性（DELETE → INSERT や ON CONFLICT）を考慮した実装が多くあります。
- OpenAI 呼び出し部分はエラー時にリトライ・フォールバックするよう実装されています。ユニットテストでは _call_openai_api をモックする設計が想定されています。

ライセンス・貢献
----------------
この README はコードベースに合わせた簡易ガイドです。実運用時は運用ルール・セキュリティ（API キー管理、commit での .env 禁止等）を必ず守ってください。

問題や機能拡張提案があれば Issue を立ててください。

以上。必要があれば README の英語版、詳細な運用手順（systemd / supervisor 用のユニット例）、あるいは各モジュールの API リファレンスを追加で作成します。どれを優先しますか？