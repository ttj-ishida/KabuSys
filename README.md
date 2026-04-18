KabuSys
=======

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤のミニマル実装です。  
主な目的は以下のとおりです。

- 日次・常時の監視（Monitoring）
- 発注実行エンジン（ExecutionEngine／ペーパー取引を含む）
- ファクター計算・リサーチ（DuckDB を用いた時系列計算）
- ポートフォリオ構築（銘柄選定・ウェイト算出・ポジションサイズ計算）
- ニュース NLP（OpenAI を用いたセンチメント評価）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード/検証）

特徴
----
- モジュール化された監視（system / trade / risk）と Kill Switch による安全停止
- DuckDB を分析用 DB として利用、SQLite を監視・履歴保存に利用
- ペーパートレードモード（KABUSYS_ENV=paper_trading）で本番 DB と完全分離
- OpenAI を利用したニュースのセンチメント評価と、市場レジーム判定のための LLM 統合（失敗時はフェイルセーフ）
- 設定ウィザード（.env 生成）と起動前の設定検証 CLI を提供

セットアップ手順
----------------

前提
- Python 3.9+（typing の構文に依存）
- システムに SQLite3 が利用可能
- （AI 機能を使う場合）OpenAI API キー

依存パッケージの例（最低限）
- duckdb
- psutil
- openai
- PyYAML（config 検証時に YAML のパースを行う場合）

インストール例（仮想環境推奨）
- 仮想環境を作成して有効化
- 必要パッケージをインストール
  - pip install duckdb psutil openai PyYAML

初期設定
1. プロジェクトルート（この README がある階層）に移動します。
2. 対話式ウィザードで .env を作成:
   - python -m kabusys.config_setup
   - コマンドに従って値を入力してください（J-Quants / kabuステーションの認証情報は必須）。
3. 設定検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

環境変数（主なもの）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
    - paper_trading の場合、MockBrokerClient が使用され、書き込み先 SQLite は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
- DB パス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（任意）
- ロギング
  - LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
  - LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs/）
- AI
  - OPENAI_API_KEY — OpenAI API キー（news/regime 機能で使用）
- モニタリング制御
  - MONITOR_POLL_INTERVAL — SystemMonitor のポーリング間隔（秒、デフォルト: 60）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — Execution 停止制御やプロセス PID の管理
- その他
  - PAPER_FILL_MODE — ペーパートレードでの約定モード（instant | partial | never | reject）

使い方
------

起動スクリプト（モジュールとして実行可能）
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（秒単位、正の整数）。
  - 実行中にプロジェクト内 data/stop_requested.flag を作成するとループが終了します。
- 実行エンジンを起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します。
  - 実行中に data/stop_requested.flag を作成するとエンジン停止を試みます。
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Paper Trading レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD / --to YYYY-MM-DD / --db PATH

API（ライブラリ的利用）
- 監視 DB 操作
  - from kabusys.monitoring.monitoring_db import MonitoringDB
- ポートフォリオ構築
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- リサーチ
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize
- AI (ニュース)
  - from kabusys.ai import score_news
  - OpenAI API キーが必要（api_key 引数または OPENAI_API_KEY 環境変数）

安全停止（Kill Switch / stop flag）
- KillSwitch は監視結果に基づき data/kill.flag を書き込み、ExecutionEngine 停止要求を出します。
- 管理用の停止フラグ: data/stop_requested.flag（起動中の run_* スクリプトが検出して終了処理を行う）
- ExecutionEngine は data/execution.pid にプロセス PID を書きます（pid ファイル関連のパスは Settings で変更可）。

ログ
- 共通の logging 設定ユーティリティが用意されています:
  - from kabusys.utils.logging_setup import setup_logging
  - デフォルトで stdout + 日次ローテートファイル（logs/<app_name>.log）を出力します。

ディレクトリ構成（主要ファイル）
------------------------------

src/kabusys/
- __init__.py
- run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py               — ExecutionEngine 起動スクリプト
- config.py                      — 環境変数／設定管理
- config_setup.py                — .env 対話式ウィザード
- validate_config.py             — 設定検証 CLI

パッケージ
- ai/
  - news_nlp.py                   — ニュース NPL スコアリング（OpenAI 統合）
  - regime_detector.py            — 市場レジーム判定（MA + LLM）
- monitoring/
  - monitoring_db.py              — SQLite 監視 DB レイヤ
  - system_monitor.py             — システム状態・データ鮮度監視
  - trade_monitor.py              — （トレード監視: 滞留注文・約定異常など）※実装参照
  - risk_monitor.py               — ドローダウン・ポジション上限監視
  - kill_switch.py                — kill.flag 書込ロジック
  - monitoring_engine.py          — 各 Monitor を統合するエンジン
  - alert_manager.py              — アラート送信ロジック（LINE 等）
- portfolio/
  - portfolio_builder.py          — 候補選定・スコア順序付け
  - position_sizing.py            — 発注株数算出（各種制約・丸め）
  - risk_adjustment.py            — セクターキャップ・レジーム乗数
- research/
  - factor_research.py            — モメンタム／ボラティリティ／バリュー計算（DuckDB）
  - feature_exploration.py        — 将来リターン / IC / 統計サマリ
- tools/
  - paper_verification_report.py  — ペーパートレード検証レポート生成
- utils/
  - logging_setup.py              — ログ設定ユーティリティ
  - process_priority.py           — プロセス優先度 / CPU affinity 設定
- monitoring/monitoring_db.py etc.

補足・運用上の注意
-----------------
- KABUSYS_ENV が live の場合、設定ミスによる誤発注は致命的です。validate_config を必ず実行して設定を確認してください。
- .env ファイルは絶対にリポジトリにコミットしないでください（機密情報を含む）。
- OpenAI 等外部 API 呼び出しは失敗時にフェイルセーフ（多くの箇所で 0 や既定値へフォールバック）を実装していますが、運用前に十分なテストを行ってください。
- ログディレクトリや data/ 以下（pid/flag/db）は起動前に作成されるようになっていますが、アクセス権やディスク容量には注意してください。

貢献
----
プルリクエスト歓迎です。機能追加・バグ修正の際は unit test と簡単なドキュメントを添えてください。

ライセンス
----------
（プロジェクトに応じてここにライセンス情報を記載してください）

以上。README の補足・具体的なコマンドやサンプル .env を追加したい場合は、どの形式（短い例 or 詳細なテンプレート）で欲しいか教えてください。