KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の小規模フレームワークです。本コードベースは以下の主要機能群を持ちます。

- 実行（ExecutionEngine）: 発注・注文管理・リスク管理を行うエンジン（paper_trading モードでモックブローカー対応）
- 監視（Monitoring）: システム状態・注文状況・リスクを定期ポーリングし、Kill Switch（停止フラグ）やアラートを発行
- ポートフォリオ構築: 候補選定、重み計算、株数決定、セクター制約などの純粋関数群
- リサーチ: DuckDB を用いたファクター計算・特徴量探索ユーティリティ
- AI モジュール: ニュースの NLP スコアリング（OpenAI）やレジーム判定
- ユーティリティ: ロギング設定、プロセス優先度設定など
- ツール: Paper Trading 検証レポート生成などの CLI スクリプト
- 設定管理: .env ウィザード・検証ツール

主な特徴
--------
- 環境ごとの分離: KABUSYS_ENV による実行モード（development / paper_trading / live）
- Paper Trading モードでは本番 DB と分離された専用 SQLite（data/paper_trading.db）を使用
- 監視は本番の監視 DB（SQLITE_PATH）を使用して稼働状況をロギング
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価・レジーム判定（API キー必要）
- DuckDB を分析用 DB として利用（prices_daily, raw_financials などのテーブル参照）
- ロギングはコンソール + 日次ローテートファイル出力で統一（logs/）

セットアップ（開発環境）
---------------------
前提
- Python 3.9+（typing の近代機能・標準ライブラリの型ヒント使用）
- sqlite3 は標準モジュール
- system パッケージ: duckdb, psutil, openai, PyYAML（任意だが設定検証で有用）

例: 仮想環境作成とインストール
- 仮想環境作成
  python -m venv .venv
  source .venv/bin/activate  # Windows: .venv\Scripts\activate

- 必要パッケージのインストール（最低限）
  pip install duckdb psutil openai

- 追加（構成検証や YAML パースのため）
  pip install pyyaml

環境変数（.env）
- プロジェクトルートに .env を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 主要な環境変数（例）:
  - KABUSYS_ENV=development | paper_trading | live
  - JQUANTS_REFRESH_TOKEN=your_token_here
  - KABU_API_PASSWORD=your_password_here
  - KABU_API_BASE_URL=http://localhost:18080/kabusapi
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  - OPENAI_API_KEY=sk-...
  - LOG_LEVEL=INFO
  - KILL_FLAG_CLEAR_ON_START=0
  - PAPER_FILL_MODE=instant | partial | never | reject

.env を対話式で作成 / 更新
- 設定ウィザードを実行して .env を生成できます:
  python -m kabusys.config_setup

設定検証
- .env や config/*.yaml を起動前に検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告も FAIL 扱い

使い方（主なコマンド）
-------------------

- ExecutionEngine を起動（本番/ペーパー両対応）
  python -m kabusys.run_execution
  動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
    - 起動時に停止フラグ（data/stop_requested.flag）が既にあれば起動を中止します。
    - 実行中は data/execution.pid に PID を書く設計（Settings.pid_file_path の値に従う）。
    - 停止は stop_requested.flag を作成すると検知してシャットダウンします。

- Monitoring を起動
  python -m kabusys.run_monitoring
  動作:
    - デフォルト 60 秒間隔でポーリング（環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能）。
    - 監視は settings.sqlite_path（デフォルト data/monitoring.db）に永続化します（monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用）。
    - stop_requested.flag を検出すると安全に終了します。

- Paper Trading 検証レポート生成（ツール）
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD  --to YYYY-MM-DD  --db PATH
  簡易指標（稼働率、注文成功率、レイテンシ等）を出力します。

- AI モジュール（プログラム API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    DuckDB 接続を渡してニュースをスコア化し ai_scores テーブルへ書き込みます。api_key が None の場合は OPENAI_API_KEY 環境変数を参照します。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    ETF（1321） MA200 とマクロニュースを合成して market_regime テーブルへ書き込みます。

重要ファイル / フラグ
- data/stop_requested.flag: run_execution / run_monitoring が終了を検知するためのファイル
- data/kill.flag: Monitoring 側の KillSwitch が書き込むことで ExecutionEngine に停止シグナルを送る「Kill Switch」
- data/execution.pid: 実行エンジンの PID 保存（Settings.pid_file_path）
- logs/: ログファイル保存ディレクトリ（setup_logging で作成・日次ローテーション）

注意点 / 運用メモ
- 監視（Monitoring）は監視用 DB（SQLITE_PATH）に対して常に本番パスを使用します。テスト時には適切にパスを分離してください。
- Paper Trading は本番 DB と完全に分離するよう PAPER_TRADING_SQLITE_PATH を設定してください。
- OpenAI API 呼び出しを行う機能（news_nlp, regime_detector）は API キーが必須です。API の障害時はフェイルセーフ（例: 0.0 にフォールバックする等）を行う実装になっていますが、API 料金やレート制限に注意してください。
- ログディレクトリや data ディレクトリは起動時に自動作成されますが、パーミッション等により失敗する場合はコンソールログに警告が出ます。
- KABUSYS_ENV=live の場合は設定値を慎重に確認してください（validate_config が本番モード特有のチェックを行います）。

ディレクトリ構成（抜粋）
-----------------------
以下は主要なファイル・パッケージの概観（src/kabusys 配下）:

- __init__.py
- config.py                — 環境変数・設定の読み込みと Settings クラス
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — CLI による設定検証

- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring ポーリング起動スクリプト

- execution/               — 発注エンジン・OrderManager 等（エンジン本体はここに配置想定）
- monitoring/
  - monitoring_db.py       — SQLite スキーマ・永続化ラッパ
  - system_monitor.py      — CPU/メモリ/ディスク・データ鮮度監視
  - trade_monitor.py       — （注文監視機能）
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — kill.flag 書き込みロジック
  - monitoring_engine.py   — 各 Monitor を束ねる

- portfolio/
  - portfolio_builder.py   — 候補選定・スコア順ソート
  - position_sizing.py     — 株数決定と投下資金スケールロジック
  - risk_adjustment.py     — セクターキャップ・レジーム乗数

- research/
  - factor_research.py     — Momentum / Volatility / Value 等の計算（DuckDB）
  - feature_exploration.py — 将来リターン計算・IC 等の統計関数

- ai/
  - news_nlp.py            — ニュースを OpenAI でスコア化して ai_scores に書込
  - regime_detector.py     — マクロニュース + MA200 で市場レジーム判定

- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成 CLI

- utils/
  - logging_setup.py       — 一貫したログ設定ユーティリティ
  - process_priority.py    — プロセス優先度・CPU affinity 設定ユーティリティ

サンプル .env（最小）
--------------------
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
OPENAI_API_KEY=sk-...

開発・デプロイのヒント
---------------------
- まず config_setup で .env を作成し、validate_config で検証してください。
- Paper Trading で機能を確認してから live 環境に切り替えることを推奨します。
- 本番稼働時は LOG_LEVEL=INFO/ERROR、KILL_FLAG_CLEAR_ON_START=0 を推奨します。
- systemd / Supervisor / cron 等で run_execution.py / run_monitoring.py をサービス化する場合は、出力先のディレクトリ（logs/, data/）の権限に注意してください。

貢献・拡張
----------
- DuckDB のテーブル（prices_daily / raw_financials / raw_news 等）にデータを投入すれば、research/ や ai/ の関数はそのまま動作します。
- brokerage（実ブローカー）連携は execution/broker_factory 等の拡張ポイントを用意しています（MockBroker は paper_trading 用）。
- ユニットテストの追加、config/*.yaml の自動生成スクリプト、CI の導入などが今後の改善点です。

ライセンス
---------
（この README にはライセンス情報は含めていません。プロジェクトの LICENSE ファイルを参照してください。）

以上。セットアップや実行で不明点があれば、どの部分について知りたいか教えてください。具体的なコマンド例や .env のテンプレートなども提供できます。