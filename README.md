KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買プラットフォーム「KabuSys」のコア実装です。
主要機能はシグナル生成／ポートフォリオ構築／発注（ExecutionEngine）と、稼働監視・アラート（Monitoring）、
研究用ファクター計算、AI を使ったニュースセンチメント／レジーム判定、ペーパートレード検証などを含みます。

主な特徴
--------
- 実運用とペーパートレードを明確に分離（KABUSYS_ENV による挙動切替）
- DuckDB を用いた分析用データベース、SQLite を用いた監視・ログ永続化
- OpenAI (gpt-4o-mini 等) を使ったニュースセンチメント（ai/news_nlp）・レジーム判定（ai/regime_detector）
- モジュール化されたポートフォリオ構築（候補選定・重み付け・ポジションサイジング・リスク制御）
- 監視（system / trade / risk）と Kill Switch による自動停止、ログのローテーション設定
- 対話式 .env 作成ウィザード、設定検証 CLI、Paper Trading 検証レポート生成スクリプト

必須／推奨依存パッケージ
--------------------
（requirements.txt は含まれていないためプロジェクトに合わせてインストールしてください）
- Python 3.9+
- duckdb
- psutil
- openai (AI モジュールを使う場合)
- PyYAML（config/*.yaml の構文チェックを有効にする場合）
- （標準ライブラリ: sqlite3, logging, datetime 等）

セットアップ手順
--------------
1. リポジトリをチェックアウトして仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）:
   - pip install duckdb psutil openai pyyaml

3. 初期設定（.env の作成）:
   - python -m kabusys.config_setup
     - 対話形式で .env を生成します。生成された .env はプロジェクトルートに作成されます。
     - .env は絶対に Git にコミットしないでください（API キー等が含まれます）。

4. 設定検証（起動前チェック）:
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合は --strict を付けます。

5. データディレクトリとログディレクトリを作成（必要に応じて）:
   - デフォルトのデータディレクトリは data/
   - ログは logs/ に日次ローテートで保存されます
   - （例）mkdir -p data logs

環境変数（主要なもの）
--------------------
主に .env に設定する項目です。必須は下記。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

重要（デフォルトを上書き可能）:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - paper_trading: MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
  - live: 実際に発注が行われるモード（注意して利用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（monitoring.db）のパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード時の SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector）用 API キー
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

実行と使い方
------------

起動スクリプト（主要なモジュール）
- 実行エンジン（ExecutionEngine）起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使い、Paper DB に記録されます。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中は data/execution.pid に PID を書きます。停止は Kill Switch（kill.flag）や stop_requested.flag により行えます。

- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で秒数を上書きできます（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は本番 sqlite_path（Settings.sqlite_path）を常に使用します（環境に依らず本番監視 DB に記録）。

設定関連ツール
- .env ウィザード:
  - python -m kabusys.config_setup
  - 対話形式で必要な環境変数を設定し .env を生成します。

- 設定検証:
  - python -m kabusys.validate_config
  - config/*.yaml の存在や YAML パース（PyYAML 必須）・環境変数の有無などを検査します。

研究・分析ツール
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db または環境変数 PAPER_TRADING_SQLITE_PATH
  - レポートは稼働率、注文成功率、レイテンシなどを集計し PASS/FAIL を判定します。

AI 関連
- ニュースセンチメント（kabusys.ai.news_nlp）とレジーム判定（kabusys.ai.regime_detector）は OpenAI API を利用します。
  - OPENAI_API_KEY を .env もしくは引数で設定してください。
  - API 呼び出しはリトライ・バックオフ実装済みで、失敗時はフェイルセーフ（スコア 0 やスキップ）で継続します。

停止・Kill Switch
-----------------
- Kill Switch:
  - リスク条件（ドローダウン、ポジション上限など）で自動的に data/kill.flag を書くことがあります（停止シグナル）。
  - ExecutionEngine は Settings.kill_flag_path（デフォルト data/kill.flag）を参照して停止します。
- 手動停止フラグ:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループは安全に終了します。
- kill.flag のクリア:
  - 実行前に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアを行う設定がありますが、本番では 0 を推奨します。
  - 直接削除する場合は rm data/kill.flag を実行します（注意して操作してください）。

ログ
---
- ログは logs/<app_name>.log に日次ローテートで保存されます（logs/ ディレクトリが必要）。
- 各起動スクリプトは setup_logging(app_name=...) を呼び出し、コンソール（stdout）とファイル出力を統一管理します。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要モジュールと役割の概観です。

- src/kabusys/
  - __init__.py               — パッケージ定義（バージョン等）
  - config.py                 — Settings クラス（.env / 環境変数の読み込み・管理）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングスクリプト

  - ai/
    - news_nlp.py             — ニュースの LLM ベースセンチメント集計（ai_scores へ書込）
    - regime_detector.py      — マーケットレジーム判定（ma200 + マクロセンチメント合成）

  - monitoring/
    - monitoring_db.py        — monitoring DB（SQLite）テーブル初期化・永続化 API
    - system_monitor.py       — CPU/メモリ/ディスク / データ鮮度 / プロセスチェック
    - trade_monitor.py        — （注文ログ監視: ファイルに含まれる想定）
    - risk_monitor.py         — ドローダウン／ポジション上限監視
    - kill_switch.py          — kill.flag 書込ロジック
    - monitoring_engine.py    — 各 Monitor を束ねる実行エンジン
    - alert_manager.py        — （LINE 等への通知を行う想定の manager、コードベースに含まれる）

  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数決定・ロット丸め・キャップ調整
    - risk_adjustment.py      — セクターキャップ、レジーム乗数

  - research/
    - factor_research.py      — Momentum / Volatility / Value 等のファクター計算（DuckDB 使用）
    - feature_exploration.py  — 将来リターン・IC・統計サマリ等

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI

  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ

注意事項・トラブルシューティング
------------------------------
- .env を誤ってコミットしないでください。API キー等の秘密情報が含まれます。
- logs/ や data/ ディレクトリに書き込み権限がないとファイルハンドラや DB 作成に失敗します。権限を確認してください。
- process_priority の変更は管理者権限を要求する場合があります。アクセス拒否時はワーニングが出ますが処理は継続します。
- OpenAI を利用する機能は API 利用料が発生します。API キーと利用量に注意してください。
- DuckDB / SQLite のファイルパスは .env で調整できます。テスト環境／本番環境で DB を分離してください。

開発
----
- 各モジュールはユニットテストを想定した分離設計です（純粋関数として実装されている部分が多い）。
- AI 呼び出し部分は _call_openai_api の差し替えや mock でテスト可能です（コメントにもその旨が記載されています）。
- config/*.yaml やデータパイプライン、ExecutionEngine の詳細は別ドキュメント（Design / README）にある想定です。

ライセンス・貢献
----------------
- この README ではライセンス情報は記載していません。実プロジェクトでは LICENSE ファイルを追加してください。
- 貢献方法やコードスタイルは別途 CONTRIBUTING.md を用意してください。

以上がこのコードベースの概要・セットアップ・主要な使い方です。特定の機能（例: ExecutionEngine の細かい挙動、BrokerClient の実装、strategy 設計）についてさらに詳しいドキュメントが必要であれば教えてください。