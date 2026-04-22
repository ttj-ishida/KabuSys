KabuSys
======

日本株向け自動売買システムのコアライブラリ群と起動スクリプト群を含むリポジトリの README（日本語）。

概要
----
KabuSys は日本株の自動売買に関する以下の主要コンポーネントを提供します：

- 実行エンジン（ExecutionEngine）: 注文発行 / リスク管理 / 注文再整合などを担当
- 監視（Monitoring）: システム状態・注文状態・リスク監視と Kill Switch の評価
- ポートフォリオ構築（Portfolio）: 銘柄選定・重み付け・株数決定ロジック（純粋関数）
- リサーチ（Research）: ファクター計算・特徴量探索ユーティリティ（DuckDB を使用）
- AI モジュール: ニュース NLP（OpenAI）を用いたセンチメントスコアや市場レジーム判定
- ユーティリティ: ロギング設定、プロセス優先度設定、設定ウィザード/検証ツール 等

特徴一覧
--------
主な機能 / 特性

- 環境分離:
  - KABUSYS_ENV により development / paper_trading / live を切り替え。
  - paper_trading モードでは MockBrokerClient を使用し、paper_trading 用 DB に記録して本番 DB と分離。
- 監視機能:
  - システム（CPU/メモリ/ディスク）、データ鮮度、滞留注文、約定異常、ドローダウン監視。
  - Kill Switch によるフラグファイル書き込みで ExecutionEngine の停止信号発行。
- ロギング:
  - 統一的な setup_logging による stdout + 日次ローテートファイル出力（logs/<app>.log）。
- DuckDB を用いたリサーチ / ファクター計算（prices_daily / raw_financials 等を参照）。
- OpenAI（gpt-4o-mini 等）を利用したニュースセンチメント集計とレジーム判定（API キー必要）。
- Paper Trading 検証レポート生成ツール。
- 設定ウィザード（.env 作成）と設定検証 CLI。

セットアップ手順
--------------
前提
- Python 3.10 以上（型注釈で "A | B" を使用）
- SQLite（標準ライブラリ）
- 推奨パッケージ（明示的 requirements.txt がある場合はそちらを利用してください）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証で任意）
  - （その他プロジェクトの要件に応じて追加）

例: 仮想環境作成とパッケージインストール
- Unix / macOS:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install -U pip
  - pip install duckdb psutil openai pyyaml
- Windows (PowerShell):
  - python -m venv .venv
  - .\.venv\Scripts\Activate.ps1
  - pip install -U pip
  - pip install duckdb psutil openai pyyaml

設定ファイル（.env）の準備
- 対話式ウィザードで .env を生成:
  - python -m kabusys.config_setup
- 生成後に設定内容を検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱いになります。

必須環境変数（主要なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)

主な任意 / デフォルト（代表）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO
- OPENAI_API_KEY: OpenAI API を使う場合に必要
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用の挙動）

使い方
------

1) .env を作成 / 確認
- python -m kabusys.config_setup
- python -m kabusys.validate_config

2) 監視ループ起動（Monitoring）
- 監視プロセスを起動:
  - python -m kabusys.run_monitoring
- 環境変数でポーリング間隔を変更:
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring
- 監視はデフォルトで settings.sqlite_path（SQLITE_PATH）を使用してログを保存します。Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用します。

3) 実行エンジン起動（Execution）
- ExecutionEngine を起動:
  - python -m kabusys.run_execution
- paper_trading モード:
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient が使われ、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録します。
- 停止制御:
  - 停止フラグ: data/stop_requested.flag が存在すると run_execution および run_monitoring のループを終了します。
  - Kill Switch: monitoring 側の条件（ドローダウン等）が満たされた場合、data/kill.flag が書き込まれ、ExecutionEngine に停止シグナルとなります。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では推奨されません）。

4) Paper Trading 検証レポート
- レポート生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB パス:
  - --db オプション または 環境変数 PAPER_TRADING_SQLITE_PATH を指定

5) AI 関連（ニュース NLP / レジーム判定）
- OpenAI API キーを環境変数 OPENAI_API_KEY に設定する必要があります。
- ニューススコア計算（関数）:
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key=None)  # api_key None の場合は env を参照
- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key=None)
- 注意: API 呼び出しはリトライ・フェイルセーフを備えていますが、API キーの設定とコストにご注意ください。

ログ
----
- ログ出力先: logs/<app_name>.log（デイリーローテーション、30日分保持）
- setup_logging(app_name="execution" など) で一貫したログ設定が行われます。
- コンソール出力は stdout に送られます。

データベース
------------
- DuckDB: 分析・リサーチ用（デフォルト: data/kabusys.duckdb）
- SQLite: 監視・注文ログ（デフォルト: data/monitoring.db）
- Paper trading 用 SQLite: data/paper_trading.db（paper_trading モード用）
- 初回起動時、必要なテーブルの作成と簡単なマイグレーションは自動で行われます（monitoring_db.init_monitoring_db）。

停止 / Kill フラグ
- stop_requested.flag: 実行スクリプト（run_execution / run_monitoring）はこのファイル存在を検知してループを終了します（手動停止など）。
- kill.flag: KillSwitch（監視ロジック）により書き込まれる停止要求ファイル。ExecutionEngine はこのファイルの存在を確認して停止します。
- ファイルは data/ 以下に作成されます。手動で削除（clear）することで解除できます。

ディレクトリ構成（主要ファイル）
--------------------------------
（リポジトリの src/kabusys 以下の主要なファイル・ディレクトリを抜粋）

- src/kabusys/
  - __init__.py                         — パッケージ定義
  - config.py                           — 環境変数 / Settings 管理
  - config_setup.py                     — .env 対話式ウィザード
  - validate_config.py                  — 設定検証 CLI
  - run_execution.py                    — ExecutionEngine 起動スクリプト
  - run_monitoring.py                   — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py      — Paper Trading 検証レポート生成
  - portfolio/
    - portfolio_builder.py              — 銘柄選定・重み付けロジック
    - risk_adjustment.py                — セクター制限・レジーム倍率
    - position_sizing.py                — 株数決定・ロット丸め・投下キャップ適用
    - __init__.py
  - research/
    - factor_research.py                — momentum/value/volatility 等の計算
    - feature_exploration.py            — 将来リターン / IC / 統計サマリ
    - __init__.py
  - ai/
    - news_nlp.py                       — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py                — 市場レジーム判定（MA + macro sentiment）
    - __init__.py
  - monitoring/
    - monitoring_db.py                  — SQLite 永続化レイヤ（テーブル生成・CRUD）
    - system_monitor.py                 — システム・データ鮮度監視
    - trade_monitor.py                   — （※実装例ベース）注文監視（ファイル中にあり）
    - risk_monitor.py                   — ドローダウン・ポジション上限監視
    - kill_switch.py                    — Kill Switch のフラグ書き込み
    - monitoring_engine.py              — モニタ群を束ねるループ
    - alert_manager.py                  — アラート送信（LINE など）※ファイル参照
  - execution/
    - execution_engine.py               — 実行エンジン本体（起動/セッション管理）
    - broker_factory.py                 — BrokerClient の生成（Mock / 実ブローカ）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py (参照上)
  - utils/
    - logging_setup.py                  — 統一的なログ設定
    - process_priority.py               — プロセス優先度 / CPU affinity 設定
  - data/                                — 実行時生成されるデータファイル（logs, DB, flags 等）

注意事項 / 運用ヒント
-------------------
- 本番環境（KABUSYS_ENV=live）では kill.flag および related 設定を慎重に扱ってください。validate_config は live 時に追加チェックを行います。
- paper_trading は実トレードと完全分離することを意図しています（専用 SQLite を使用）。
- OpenAI への呼び出しには料金が発生します。API 利用時はキー/コスト管理を行ってください。
- ログディレクトリ作成に失敗した場合、ファイルハンドラは無効化され stdout のみになります（setup_logging がその旨を警告します）。
- process_priority はプラットフォーム差異を吸収しますが、権限不足で設定できない場合は警告が出ます。

開発 / 貢献
------------
- 既存のモジュールはテストしやすい純粋関数（特に portfolio / research）と、DB / API に依存するインタフェースに分離されています。ユニットテストを追加する際は外部依存をモックしてください（例: OpenAI 呼び出し関数はモック可能に実装されています）。
- 設定ファイルや DB パスは .env で管理します。.env は絶対に Git にコミットしないでください。

ライセンス / バージョン
----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

問い合わせ
----------
実装上の不明点や追加説明が必要であれば、どのファイル／機能について知りたいか教えてください。コードの特定部分（例: ExecutionEngine の起動フロー、AI モジュールの API 呼び出し部分、監視のアラート条件等）について詳細なドキュメントを追加で作成できます。