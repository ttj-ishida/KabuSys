README
======

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤の軽量フレームワークです。  
主な機能は以下の通りです:

- 注文実行エンジン（ExecutionEngine）と監視プロセス（Monitoring）による運用フロー
- ペーパートレード用の完全分離 DB / Mock ブローカ実装
- モニタリング用ログ（SQLite）と分析用 DuckDB の分離保存
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター上限など）の純粋関数群
- ファクター計算 / 研究用モジュール（Momentum, Volatility, Value 等）
- ニュース NLP / 市場レジーム判定（OpenAI を利用）
- .env 対話ウィザード & 設定検証ツール
- Paper Trading 検証レポート生成ツール

特徴
----
- KABUSYS_ENV による実行モード切替:
  - development: ローカル開発・テスト（発注なし）
  - paper_trading: ペーパートレード（MockBroker を利用、専用 DB に記録）
  - live: 本番（実際に発注）
- モニタリングと Kill Switch による安全運用（ドローダウンやポジション上限を検知して自動停止）
- DuckDB を用いた分析向けテーブル、SQLite に監視ログ / 発注ログを永続化
- OpenAI（gpt-4o-mini など）を用いたニュースセンチメント集約（ai モジュール）

セットアップ手順
----------------

前提
- Python 3.9+（ソースは typing | 標準ライブラリ機能を使用）
- システムに sqlite3 は標準搭載
- 推奨パッケージ（少なくとも以下をインストールしてください）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイルの検証に任意）
  - その他依存は実環境に応じて追加してください

例（仮想環境作成 & 必要パッケージのインストール）:
- Unix/macOS:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install --upgrade pip
  - pip install duckdb psutil openai pyyaml

.env の初期化
1. 対話式ウィザードで .env を生成:
   - python -m kabusys.config_setup
   - 生成先パスは引数 --env-file で変更可能
2. 生成後に設定を検証:
   - python -m kabusys.validate_config
   - オプション --strict を付けると警告も失敗扱い（exit 1）

データディレクトリ
- デフォルトで使用するファイル:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db
  - ログ: logs/<app_name>.log（デフォルト、LOG_DIR で変更可）
- 必要に応じて .env でパスを上書きできます（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH 等）

使い方
------

主要スクリプト（モジュールとして実行）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告を FAIL 扱いにします

- ExecutionEngine 起動（実行エンジン）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を利用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に発注ログ等を記録
    - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了
    - 実行中に data/stop_requested.flag が作成されるとエンジンを停止
    - 実行中は PID ファイル（デフォルト data/execution.pid）を利用

- Monitoring（監視プロセス）起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - Settings.sqlite_path（monitoring DB）を使用して system_status / trade_logs / risk_logs / dashboard 等を操作
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定（デフォルト 60）
    - 監視から条件を満たすと data/kill.flag を書き込む Kill Switch を通じて ExecutionEngine 停止やアラート発行が可能
    - 停止フラグ検知（data/stop_requested.flag）で監視プロセスも終了

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション --from / --to（YYYY-MM-DD）、--db で DB パスを指定可能
  - 簡易的な稼働率・注文成功率・レイテンシ等の指標を出力

主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト development）
- OPENAI_API_KEY: OpenAI API キー（ai/news_nlp/regime_detector を使用する際に必須）
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH: DB ファイルパス
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒） — run_monitoring で参照

停止と Kill Switch
- 手動で ExecutionEngine を止めたい場合:
  - data/stop_requested.flag を作成すると run_execution が次のループで停止します（run_monitoring からの停止とは別のフラグ）
- 監視により自動停止させる場合:
  - Monitoring の KillSwitch が条件を満たすと data/kill.flag を作成します。ExecutionEngine 起動時に kill_flag_clear_on_start を 1 に設定している場合は自動でクリアされますが、本番では 0 を推奨します。

ディレクトリ構成（主要ファイル）
------------------------------

ソースツリー（src/kabusys）の主要ファイルとサブパッケージ:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP（OpenAI 呼び出し、ai_scores 書き込み）
    - regime_detector.py       — 市場レジーム判定（ma200 + macro sentiment）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（テーブル作成・読込/書込関数）
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — （発注ログ監視など）※実装参照
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag の作成 / 削除ロジック
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — （LINE など通知管理）※実装参照
  - portfolio/
    - portfolio_builder.py    — 候補選定 / 重み計算
    - position_sizing.py      — 発注株数計算（単元丸め・制限・スケールダウン）
    - risk_adjustment.py      — セクター上限 / レジーム乗数
    - __init__.py
  - research/
    - factor_research.py      — Momentum / Volatility / Value 等の計算（DuckDB 使用）
    - feature_exploration.py  — 将来リターン計算、IC 計算、統計サマリー
    - __init__.py
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ（Stream + TimedRotatingFile）
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py

注意事項 / 運用上のヒント
-----------------------
- 本番（KABUSYS_ENV=live）では kill_flag_clear_on_start を 0 にして、誤って Kill Switch を自動クリアしないようにしてください。
- PAPER_TRADING では paper_trading 用の SQLite（デフォルト data/paper_trading.db）に完全分離して記録されます。本番 DB と混ざりません。
- OpenAI を利用する機能は API キーの出費やレート制限に注意してください。レスポンス失敗時はフェイルセーフでスコアを 0 とする等の設計を行っていますが、API クォータ切れ等は運用で管理してください。
- ログディレクトリ作成に失敗した場合はファイル出力を無効化し標準出力のみで継続します（utils/logging_setup の挙動）。
- DuckDB / SQLite のファイルはバックアップ、ローテーション、容量管理を考慮して運用してください（DuckDB は大容量データ向け、SQLite は監視ログ向け）。

ライセンス・バージョン
---------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス情報が別途存在する場合はプロジェクトルートの LICENSE を参照してください。

フィードバック・拡張案
---------------------
- strategy / execution 部分はカスタムブローカ実装やアルゴリズムの挿入ポイントが想定されています。
- ロギングや監視の閾値、リスク設定は config/*.yaml や .env で調整可能です（生成スクリプトやテンプレートを参照）。
- Paper Trading 検証レポートや research モジュールは外部ツールとの連携（可視化、ダッシュボード）に容易に結合できます。

以上。ご不明点や README の出力形式調整、追加したいセクション（例: 詳細な CLI 引数一覧やサンプル .env）等があれば教えてください。