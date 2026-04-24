README
======

概要
----
KabuSys は日本株向けの自動売買 / 研究プラットフォームのサンプル実装です。本リポジトリは以下を含みます。

- ExecutionEngine（発注エンジン）: ブローカークライアントを通じて発注・管理を行う（本番 / ペーパートレード対応）。
- Monitoring（監視）: システム状態、発注履歴、リスク指標のポーリング監視と Kill Switch。
- Portfolio / Position Sizing: 銘柄選定・配分・枚数計算などの純粋関数群。
- Research: ファクター計算、将来リターン・IC 計算などの分析ユーティリティ（DuckDB 前提）。
- AI/LLM ユーティリティ: ニュースのセンチメント評価や市場レジーム判定用のラッパー（OpenAI を使用）。
- ツール: ペーパートレード検証レポート生成 等。

主な設計方針:
- 環境変数および .env から設定を読み込む（config モジュール）。
- 本番とペーパートレードを分離（DB 等を切り分け）。
- DuckDB を分析用に利用、SQLite を監視 / 発注ログ用に利用。
- LLM 呼び出しは失敗に強い（リトライ・フォールバック実装）。

機能一覧
--------
- 実行エンジン起動: run_execution.py（本番 / paper_trading 切替）
  - ペーパートレード時は MockBrokerClient を使用し data/paper_trading.db に記録
- 監視ループ起動: run_monitoring.py
  - CPU/メモリ/ディスク、Execution プロセスの稼働、データ鮮度、トレードログの異常検出
  - Kill Switch (data/kill.flag) で ExecutionEngine を停止可能
- 設定ウィザード: config_setup.py（対話式 .env 生成・更新）
- 設定検証: validate_config.py（.env と config/*.yaml の検証）
- ペーパートレード検証レポート: tools/paper_verification_report.py
- Portfolio 構築・サイズ計算（等ウェイト、スコアウェイト、リスクベース）
- Research モジュール: momentum / volatility / value 等のファクター計算、IC・統計解析
- AI モジュール: news_nlp（ニュースセンチメント → ai_scores）、regime_detector（市場レジーム判定）
- ログ設定ユーティリティ（stdout + 日次ローテートファイル）

前提（依存関係）
----------------
主な Python ライブラリ（プロジェクト内に requirements.txt が無い場合は下記をインストールしてください）:

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（validate_config で YAML 検証を行う場合）
- sqlite3 は標準ライブラリとして利用

インストール例:
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai PyYAML

セットアップ手順
----------------
1. リポジトリをクローンしてワークディレクトリへ移動する。

2. 仮想環境の作成（推奨）と依存ライブラリのインストール（上記参照）。

3. 環境変数設定 (.env)
   - 対話式ウィザードで .env を生成:
       python -m kabusys.config_setup
   - 必須環境変数:
       - JQUANTS_REFRESH_TOKEN
       - KABU_API_PASSWORD
   - 重要な環境変数（主なもの）:
       - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
       - DUCKDB_PATH: 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
       - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
       - PAPER_TRADING_SQLITE_PATH: ペーパートレード時の SQLite（デフォルト: data/paper_trading.db）
       - LOG_LEVEL: DEBUG/INFO/...
       - OPENAI_API_KEY: OpenAI を使う機能を利用する場合に必要
       - KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（"0"推奨）

   - 生成後、設定検証を実行:
       python -m kabusys.validate_config
     --strict を付けると警告もエラー扱いで終了コード 1 を返します。

4. ディスク上のデータディレクトリ作成（必要に応じて）
   - デフォルトでは data/ と logs/ にファイルを作成します。権限が必要な場合は作成してください。
     mkdir -p data logs

使い方
------
起動スクリプト（パッケージモードで実行）:

- 監視プロセスを起動:
    python -m kabusys.run_monitoring
  オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（デフォルト 60 秒）。
  備考:
    - run_monitoring はドキュメント通り「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用」します。
    - 停止は data/stop_requested.flag ファイルを作成すると検出して終了します。

- 実行エンジンを起動:
    python -m kabusys.run_execution
  備考:
    - KABUSYS_ENV=paper_trading に設定した場合は MockBrokerClient を使用し、ペーパートレード用 DB に記録します。
    - run_execution は data/stop_requested.flag を検出すると稼働中のエンジンを停止します。
    - 実行中は PID ファイル（デフォルト data/execution.pid）を作成します。

- 設定ウィザード（.env 作成）:
    python -m kabusys.config_setup

- 設定検証:
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- ペーパートレード検証レポート:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    あるいは --db PATH で DB を指定可能（環境変数 PAPER_TRADING_SQLITE_PATH が優先される場合あり）。

- AI 関連（プログラムから呼び出す）:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  注意: OPENAI_API_KEY を環境変数に設定するか、api_key を渡してください。

停止 / Kill Switch
------------------
- 実行エンジン停止要求:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring が検出して停止します（これらは主に開発用の停止フラグ）。
- Kill Switch（リスクにより強制停止）:
  - KillSwitch は監視結果に応じて data/kill.flag（デフォルト）を書き込みます。Execution 起動時にこの flag があれば起動を抑止できます。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると実行開始時に kill.flag が自動削除されますが、本番では 0（無効）を推奨します。

ログ
---
- ログはデフォルトで stdout（コンソール）と日次ローテートファイル logs/<app_name>.log に出力されます。
- ログディレクトリは環境変数 LOG_DIR、ログレベルは LOG_LEVEL で上書き可能です。

ディレクトリ構成
----------------
以下は主要なファイル / モジュールの概要（src/kabusys 配下）です。

- kabusys/
  - __init__.py            — パッケージ情報（バージョン等）
  - config.py              — 環境変数 / 設定読み込み・Settings クラス
  - config_setup.py        — 対話式 .env ウィザード
  - validate_config.py     — 設定検証 CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — Monitoring ポーリングループ起動スクリプト

  - execution/             — 実行エンジン関連（ブローカーファクトリ、エンジン、注文管理、リスク管理等）
    （詳細実装ファイルは実装済み想定）

  - monitoring/
    - monitoring_db.py     — SQLite による永続化層（テーブル作成 / CRUD）
    - system_monitor.py    — CPU/メモリ/ディスク、プロセス、データ鮮度監視
    - trade_monitor.py     — 発注ログの健全性チェック（滞留注文、約定異常等）
    - risk_monitor.py      — ドローダウン・ポジション上限監視
    - kill_switch.py       — Kill Switch 実装（kill.flag 書き込み）
    - monitoring_engine.py — 各 Monitor を束ねるループ実行
    - alert_manager.py     — 通知管理（LINE 等への通知ラッパー、実装想定）

  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py   — 枚数計算・上限・丸め
    - risk_adjustment.py   — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py   — Momentum/Volatility/Value ファクター計算（DuckDB）
    - feature_exploration.py — IC / 将来リターン / 統計サマリー
    - __init__.py

  - data/
    - pipeline.py          — データ取得/前処理ユーティリティ（get_last_price_date 等）
    - stats.py             — 正規化等ユーティリティ（zscore_normalize 等）

  - ai/
    - news_nlp.py          — ニュースを LLM で評価し ai_scores に書き込む
    - regime_detector.py   — ETF + マクロニュースで市場レジーム判定
    - __init__.py

  - tools/
    - paper_verification_report.py — ペーパートレードの検証レポート生成

  - utils/
    - logging_setup.py     — ログ設定ユーティリティ（stdout + 日次ファイル）
    - process_priority.py  — プロセス優先度 / CPU affinity 設定
    - その他ユーティリティ

補足 / 運用上の注意
------------------
- 本リポジトリは「実際の発注を行う可能性」があるため .env やシークレットは決して Git にコミットしないでください。
- KABUSYS_ENV が live のときは特に注意して設定を検証してください（validate_config にそれ用のガードがあります）。
- OpenAI を使う機能は API コストとレイテンシに注意してください。API キーは安全に管理してください。
- システム監視や Kill Switch の自動化は慎重に運用ルールを決めてください（誤検知による停止リスク等）。

ライセンス / その他
------------------
README に明記のない場合はプロジェクトルートの LICENSE を確認してください。

お問い合わせ・貢献
----------------
バグ報告や改善提案は issue を作成してください。開発に参加される場合はまず validate_config と config_setup を使ってローカル環境を整えてください。