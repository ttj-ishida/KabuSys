KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買システムの骨組みを提供するリポジトリです。本リポジトリには以下の主要機能を含んでいます:

- 注文実行エンジン（ExecutionEngine：本番 / ペーパートレード対応）
- 監視サブシステム（System / Trade / Risk のモニタリング、Kill Switch）
- ポートフォリオ構築ロジック（候補選定・重み付け・ポジションサイズ計算）
- リサーチ用ファクター計算・特徴量検討ツール（DuckDB ベース）
- ニュース NLP / レジーム判定（OpenAI を用いたセンチメント評価）
- ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード／検証ツール）
- Paper Trading 検証レポート生成ツール

主な設計方針:
- 本番とペーパートレードは DB を分離して運用（ペーパートレード用 DB: data/paper_trading.db）
- 設定は .env（自動読み込み機構あり）または環境変数で管理
- DuckDB を解析用途、SQLite を運用ログ・監視用に使用
- OpenAI API 呼び出しは外部 API として分離しフェイルセーフ設計

機能一覧
--------
- 実行
  - run_execution: ExecutionEngine 起動スクリプト（KABUSYS_ENV により本番/ペーパー切替）
  - BrokerClientFactory によるブローカークライアント生成（paper_trading 時は Mock を使用）
- 監視
  - run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）
  - MonitoringEngine: System / Trade / Risk 各 Monitor を束ねて定期実行、アラート・Kill Switch 評価
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - RiskMonitor: ドローダウン・ポジション上限監視
  - MonitoringDB: SQLite に対する読み書き API（system_status, trade_logs, positions, risk_logs, dashboard）
- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 重み付け（等金額、スコア加重）
  - セクター制限（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - ポジションサイズ計算（calc_position_sizes）
- リサーチ
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC 計算、統計サマリー
- AI（OpenAI）
  - news_nlp.score_news: ニュース記事から銘柄別センチメントを取得して ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF の MA とマクロニュースから市場レジーム判定（bull/neutral/bear）
- ツール
  - config_setup: .env 初期作成・更新ウィザード（対話式）
  - validate_config: .env と config/*.yaml の事前検証 CLI
  - tools.paper_verification_report: Paper Trading 用検証レポート生成 CLI
- ユーティリティ
  - logging_setup.setup_logging: stdout + 日次ローテートファイルハンドラ
  - process_priority.set_process_priority / set_cpu_affinity: OS に依存しない優先度設定ユーティリティ

セットアップ手順
----------------
前提:
- Python 3.9+（本コードは typing の記法等を利用しています）
- SQLite は標準ライブラリとして利用
- 必要な外部パッケージ:
  - duckdb
  - psutil
  - openai （ニュース NLP / レジーム判定を使う場合）
  - PyYAML（config の YAML 検証を行う場合）
インストール例:
  pip install duckdb psutil openai PyYAML

推奨ディレクトリ作成:
  mkdir -p data logs

環境変数 / .env:
- .env ファイルを使って設定できます。手動で作成するか、対話式ウィザードを利用します。
- 対話式ウィザード:
    python -m kabusys.config_setup
  これにより .env を生成・更新できます。
- 代表的な必須環境変数:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
- よく使う設定:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
  - LOG_LEVEL（DEFAULT: INFO）
  - OPENAI_API_KEY（AI 機能を使う場合）

設定検証:
  python -m kabusys.validate_config
  --strict オプションを付与すると警告もエラー扱いになります。

使い方
------
ログ設定（すべての起動スクリプト内で自動的に行われます）:
- ログは stdout と logs/<app_name>.log（TimedRotatingFileHandler：日次・30日保持）に出力されます。

実行エンジン起動:
- 本番 or development:
    python -m kabusys.run_execution
  このスクリプトは Settings に応じて使用する SQLite ファイル（本番 or PAPER_TRADING）を選択し、ExecutionEngine をスレッドで起動します。
  起動前に data/stop_requested.flag が存在すると起動せず終了します。
  実行中に stop を指示する場合は stop フラグを作成すると検知して停止します（stop flag の場所: data/stop_requested.flag）。

監視プロセス起動:
    python -m kabusys.run_monitoring
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒指定できます（デフォルト 60）。
- 監視は環境にかかわらず本番 sqlite_path を使用してログを永続化します。
- 監視プロセスは data/stop_requested.flag を検知すると終了します。

Paper Trading 検証レポート:
    python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH か data/paper_trading.db

AI 機能（ニューススコアリング / レジーム判定）:
- OpenAI API キーが必要です（環境変数 OPENAI_API_KEY または関数引数で指定）。
- ニュース NLP:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key=None)
- レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key=None)

停止方法 / Kill Switch:
- KillSwitch はデータベース監視の結果に応じて data/kill.flag を作成します。ExecutionEngine はそのフラグを見て安全に停止します。
- 手動で停止したい場合は data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検知して終了します。

ログ出力:
- デフォルト: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
- ログレベルは環境変数 LOG_LEVEL または setup_logging の引数で指定可能

ディレクトリ構成
----------------
以下は本リポジトリの主要ファイルとディレクトリ（抜粋）です:

- src/kabusys/
  - __init__.py
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - config.py                 — Settings クラス（環境変数/.env の読み取り）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証ツール
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - ai/
    - __init__.py
    - news_nlp.py              — ニュースの LLM ベースセンチメント評価
    - regime_detector.py       — 市場レジーム判定
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
    - system_monitor.py       — システム監視（CPU/メモリ/ディスク/データ鮮度）
    - trade_monitor.py        — （トレード監視: 滞留注文・約定異常など）※実装参照
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — Kill Switch 実装
    - monitoring_engine.py    — 各 Monitor の統合ランナー
  - portfolio/
    - __init__.py
    - portfolio_builder.py    — 候補選定・重み付け
    - position_sizing.py      — 株数決定・キャップ・単元丸め
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー
  - utils/
    - __init__.py
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ

運用上の注意
-------------
- 本番運用時は KABUSYS_ENV=live を必ず確認し、LINE 通知等の設定が正しいことを検証してください（validate_config にて警告）。
- .env は絶対にソース管理にコミットしないでください（config_setup のヘッダにも注意喚起あり）。
- OpenAI キーを使用する機能は外部 API 呼び出しを伴います。レート制限やコストに注意してください。
- run_execution は実際の発注を行います。テストは paper_trading モードで実施してください。
- process_priority の設定は権限に依存します。許可がない場合は警告が出てスキップされます。

トラブルシューティング
----------------------
- ログディレクトリ作成に失敗した場合、ファイル出力は無効化され stdout のみで出力されます（警告あり）。
- DuckDB / SQLite に関するパスは環境変数で調整可能。validate_config で親ディレクトリの存在有無など確認できます。
- OpenAI 呼び出しで 429 / タイムアウト / 5xx が発生した場合、内部で指数バックオフしてリトライしますが、最終的に失敗した場合はフェイルセーフ（スコア=0 やスキップ）で継続します。

貢献 / 拡張案
--------------
- ブローカークライアントの追加（実際の API 用プラグイン）
- stocks マスタによる銘柄別 lot_size サポート（position_sizing の拡張）
- モニタリングのアラート送信先拡張（LINE / Slack / PagerDuty）
- 単体テスト・CI 設定、さらにドキュメントの API 仕様書化

ライセンス
----------
（この README にライセンス記載はありません。プロジェクトルートの LICENSE を参照してください。）

お問い合わせ
-------------
リポジトリ内の各モジュールの docstring に利用方法・設計方針が記載されています。まずは config_setup と validate_config を利用して環境を整え、run_monitoring/run_execution を順に起動して運用確認してください。

必要であれば、README を補足して CLI 使用例やユニットテスト実行手順、docker 化手順等を追加できます。どの情報を追加希望か教えてください。