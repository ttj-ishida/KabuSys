README
=====

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームの一部を構成する Python パッケージです。本リポジトリには以下を含みます（抜粋）:
- 発注実行エンジン起動スクリプト（ExecutionEngine）
- 監視ポーリング（Monitoring）
- ポートフォリオ構築・ポジションサイズ計算用の純粋関数群
- ファクター計算・リサーチユーティリティ（DuckDB 経由）
- AI（OpenAI）を使ったニュース NLP / レジーム判定
- 設定ウィザード / 設定検証ツール
- Paper Trading 向け検証レポート生成ツール

主な設計方針:
- 本番とペーパートレードの DB を分離（paper_trading モード時は専用 SQLite を使用）
- DuckDB を解析・研究用のストレージとして採用
- OpenAI を使った NLP 処理は API キー依存（フォールバック・エラー処理あり）
- ロギングやプロセス優先度設定など運用面を考慮したユーティリティ群を用意

機能一覧
--------
- ExecutionEngine 起動（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
  - プロセス優先度設定 / PID ファイル管理 / 停止フラグ対応
- Monitoring（run_monitoring.py, monitoring エンジン群）
  - システム状態（CPU/メモリ/ディスク）、データ鮮度、注文・リスクの監視
  - Kill Switch（条件を満たすと data/kill.flag を書いて ExecutionEngine を停止）
  - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可（デフォルト 60 秒）
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等ウェイト/スコア加重、リスク調整（セクターキャップ・レジーム乗数）
  - ポジションサイズ算出（単元丸め、aggregate cap、コストバッファ考慮）
- リサーチ（kabusys.research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI モジュール（kabusys.ai）
  - news_nlp: ニュースを集約し OpenAI でセンチメントスコアを生成して ai_scores に書き込み
  - regime_detector: ETF の MA とマクロニュースで市場レジームを判定
- 設定管理ツール
  - .env 対話ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- Paper Trading 検証レポート（kabusys.tools.paper_verification_report）
  - 稼働率・注文成功率・レイテンシ等を集計し PASS/FAIL 判定

前提 / 依存関係
--------------
最低限の想定:
- Python 3.10+（コードで | 型注釈や最新構文を使用）
必須パッケージ（実行する機能により変動）:
- duckdb
- psutil
- openai (AI 機能使用時)
- PyYAML（config ファイル検証を行う場合は必要）
- sqlite3（標準ライブラリ）
インストール例（仮）:
    pip install duckdb psutil openai pyyaml

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成・有効化します。
2. 依存パッケージをインストールします（上記参照）。
3. .env を作成します（対話ウィザード推奨）:
    python -m kabusys.config_setup
   - ウィザードは J-Quants / kabuAPI / DB パス 等を対話形式で作成します。
4. 作成後に設定検証を実行します:
    python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いになります。
5. 必要に応じてデータディレクトリ（data/）やログディレクトリ（logs/）のパーミッションを確認。

主要環境変数（抜粋）
-------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (DEBUG/INFO/...)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db) — Monitoring 用（production 用）
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — paper_trading 用
- PAPER_FILL_MODE (instant|partial|never|reject) — Paper Trading の挙動
- OPENAI_API_KEY — AI 機能使用時に必要
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- LOG_DIR — ログ出力先（デフォルト logs/）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（通常 0 推奨）

使い方（主要コマンド）
--------------------

- 設定ウィザード（.env 作成／更新）
    python -m kabusys.config_setup

- 設定検証
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- 監視プロセス起動（Monitoring）
    python -m kabusys.run_monitoring
  備考:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で設定できます（例: MONITOR_POLL_INTERVAL=30）。
  - 監視プロセスは Settings.sqlite_path（data/monitoring.db デフォルト）へ接続します（環境値に関わらず監視は本番 sqlite_path を使用します）。
  - 停止: プロセスを終了するか、プロジェクトルート/data/stop_requested.flag を作成するとループを抜けます。

- 実行エンジン起動（ExecutionEngine）
    python -m kabusys.run_execution
  備考:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録され、本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
  - 停止させたい場合はプロジェクトルート/data/stop_requested.flag を作成するか、monitoring の Kill Switch が data/kill.flag を書き込むと監視側から停止を促します。
  - 実行中は PID ファイル（デフォルト data/execution.pid）を管理します。

- Paper Trading 検証レポート生成
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション:
  - --db PATH で DB パス指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定して利用してください。
  - ニューススコア生成関数: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらをスクリプトやスケジューラから呼ぶことで ai_scores / market_regime 等を更新します。

運用上のポイント / トラブルシュート
---------------------------------
- .env に必須変数がないと起動時にエラーになります。config_setup と validate_config を使って事前に検証してください。
- logging はデフォルトで logs/<app_name>.log に日次ローテートで出力されます。LOG_DIR 環境変数で変更可。
- OpenAI 呼び出しではレート制限（429）やネットワーク障害に対してリトライ処理が組まれていますが、API キーが無い場合は明示的にエラーになる箇所があります。
- Paper Trading と Live の DB は分離されます。paper_trading は settings.is_paper == True で専用 SQLite を使用します。
- 停止フラグ:
  - data/stop_requested.flag は run_monitoring/run_execution が参照するため、運用での強制停止に利用できます。
  - Kill Switch（data/kill.flag）は monitoring が条件を満たしたときに書き込まれ、ExecutionEngine に停止シグナルを与える用途です。

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py               — パッケージ定義（バージョン等）
- config.py                 — 環境変数 / Settings 管理
- config_setup.py           — .env 対話ウィザード
- validate_config.py        — 設定検証 CLI
- run_monitoring.py         — Monitoring 起動スクリプト
- run_execution.py          — ExecutionEngine 起動スクリプト

サブパッケージ（主要ファイル）
- ai/
  - news_nlp.py              — ニュース NLP（OpenAI を使ったスコアリング）
  - regime_detector.py      — 市場レジーム判定
- monitoring/
  - monitoring_db.py        — SQLite テーブル初期化 + 永続化 API
  - monitoring_engine.py    — Monitor を束ねるポーリングエンジン
  - system_monitor.py       — システム状態・データ鮮度監視
  - risk_monitor.py         — ドローダウン / ポジション上限監視
  - trade_monitor.py        — （注文監視ロジック: サンプルに含まれる想定）
  - kill_switch.py          — Kill Switch 実装
  - alert_manager.py        — （アラート送信実装: LINE 等を想定）
- portfolio/
  - portfolio_builder.py    — 候補選定・重み付け
  - position_sizing.py      — 株数決定ロジック
  - risk_adjustment.py      — セクターキャップ・レジーム乗数
- research/
  - factor_research.py      — ファクター計算（Momentum / Volatility / Value）
  - feature_exploration.py  — 将来リターン / IC / 統計
- tools/
  - paper_verification_report.py — Paper Trading レポート
- utils/
  - logging_setup.py        — ログ初期化ユーティリティ
  - process_priority.py     — プロセス優先度・CPU affinity ユーティリティ

データ・ログファイル（デフォルト）
- data/kabusys.duckdb         — DuckDB（分析用）
- data/monitoring.db          — 監視用 SQLite（system_status 等）
- data/paper_trading.db       — Paper Trading 用 SQLite（KABUSYS_ENV=paper_trading 時）
- data/execution.pid          — ExecutionEngine PID（起動時に使用）
- data/kill.flag              — Kill Switch（Monitoring が書く）
- data/stop_requested.flag    — 手動停止フラグ（外部プロセスが作成）

開発上のメモ
------------
- 多くの内部機能は純粋関数として実装され、DB 参照を受けるものと受けないものがあります（ユニットテスト容易化）。
- OpenAI 呼び出しのラッパー関数はモジュール内で定義されており、テスト時はモック差替えを行う設計になっています（例: unittest.mock.patch）。
- DuckDB を解析専用に使う設計のため、大量データの集計やファクター算出は効率的に実行できます。

最後に
------
この README はコードベースの主要な使い方／運用のヒントをまとめたものです。実際の導入時は .env.example や config/*.yaml（存在する場合）を確認し、validate_config で問題がないことを必ず確認してください。もし追加のドキュメントや実行例が必要であれば教えてください。