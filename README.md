KabuSys
======

日本株自動売買システムのコードベース（ライブラリ＋実行スクリプト群）です。本 README はリポジトリ内の主要コンポーネント・起動手順・設定方法・ディレクトリ構成をまとめたものです。

概要
----
KabuSys は以下の役割を持つモジュール群で構成されています。
- 発注・約定管理を行う ExecutionEngine（本番 / ペーパートレード対応）
- システム稼働状態・取引状況・リスク指標を監視する Monitoring 系
- ポートフォリオ構築（候補選定、配分、株数決定、リスク調整）
- リサーチ（ファクター計算・特徴量解析）
- AI を利用したニュースセンチメント・レジーム判定（OpenAI）
- 設定ウィザード / 設定検証 / 検証レポート生成ツール

主な機能
--------
- ExecutionEngine（発注エンジン）
  - 本番（kabuステーション）と Paper Trading（MockBrokerClient）に対応
  - リスク管理（max position、drawdown、利用率など）
  - Order 管理・履歴永続化

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス状態、データ鮮度監視
  - TradeMonitor: 注文の滞留・約定異常の検出
  - RiskMonitor: ドローダウン監視・ポジション上限の監視
  - KillSwitch による停止フラグ（data/kill.flag）生成
  - アラート送信フック（LINE 等の設定あり）

- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額・スコア加重、リスクベースの株数決定
  - セクター上限やレジーム乗数（market regime）による調整

- Research（リサーチ）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）評価、統計サマリー

- AI（OpenAI を利用）
  - ニュース記事を集約して銘柄単位にセンチメントスコアを算出（ai_scores）
  - マクロニュース + ETF MA200 乖離から市場レジーム判定
  - OpenAI API (gpt-4o-mini 等) を使用（APIキー必須）

- ツール
  - .env 対話式生成: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

セットアップ手順
----------------
1. 環境準備
   - Python 3.9+ を推奨
   - 仮想環境を作成して有効化してください（venv / pyenv 等）

2. 依存パッケージのインストール
   - requirements.txt がある場合はそれを使用してください。ない場合は主に以下が必要です:
     - duckdb
     - psutil
     - openai
     - pyyaml（設定検証で YAML を検証したい場合）
   例:
     pip install duckdb psutil openai pyyaml

3. .env の作成（推奨: 対話式ウィザード）
   - 以下コマンドで対話式に .env を作成できます:
       python -m kabusys.config_setup
   - 生成後、設定内容を検証:
       python -m kabusys.validate_config
     --strict オプションを付けると警告を FAIL 扱いにできます。

4. データディレクトリと DB
   - デフォルトのファイルパス（環境変数で上書き可）
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
   - ログディレクトリ: logs/（自動作成されます）

使い方（代表コマンド）
--------------------
- ExecutionEngine 起動（デフォルトで本番 DB を使用、KABUSYS_ENV に応じて Paper/Live 切替）
    python -m kabusys.run_execution

  補足:
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient が使われ、Paper DB（デフォルト data/paper_trading.db）に記録されます。
  - 起動時に data/execution.pid を作成し、data/stop_requested.flag や data/kill.flag をチェックします。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

- Monitoring 起動（バックグラウンドポーリング）
    python -m kabusys.run_monitoring

  補足:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能。デフォルトは 60 秒。
    例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - Monitoring は常に本番 sqlite_path を使用して監視ログを記録します（環境にかかわらず）。

- Paper Trading 検証レポート生成
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを指定できます。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可。

- 設定検証（CLI）
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- .env ウィザード
    python -m kabusys.config_setup

主要な環境変数（抜粋）
---------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト development
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使用する際に必要）
- PAPER_FILL_MODE: paper_trading 時のフィルモード（instant / partial / never / reject）デフォルト instant
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB パス（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

ログ
----
- ログはログディレクトリ（既定: logs/）に app_name ごとにファイル出力されます（例: logs/execution.log, logs/monitoring.log）。
- 日次でローテーションし、30 日分を保持します。
- 起動スクリプトは共通の setup_logging を使用して stdout とファイルに出力します。

Kill Switch / 停止フラグ
-----------------------
- KillSwitch は条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止を促します。
- Monitoring や実行スクリプトは data/stop_requested.flag（スクリプト側の停止フラグ）を参照して安全に終了します。
- kill.flag を手動でクリアするにはファイルを削除するか、KILL_FLAG_CLEAR_ON_START=1 を設定して起動時にクリアできます（本番では推奨されません）。

AI 機能（注意）
--------------
- OpenAI を利用する処理（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）を必要とします。利用には API 利用料が発生します。
- レスポンスパースやネットワークエラー時はフェイルセーフによりスコアをスキップまたは 0.0 として処理します（例外を起こさず継続）。

ディレクトリ構成（主要ファイル）
-------------------------------
（リポジトリの src/kabusys 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込み・Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

  - execution/                — 発注エンジン関連（BrokerFactory, ExecutionEngine, OrderManager 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI + ETF MA200）
  - data/                    — スキーマ・パイプライン関連（DuckDB テーブルを想定）
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ
    - その他ユーティリティ

補足・運用上の注意
-----------------
- 本リポジトリには発注や実際の資金移動を伴うコードが含まれます。KABUSYS_ENV を適切に設定し、本番（live）では設定内容を慎重に確認してください。
- .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダにも明記）。
- Monitoring は監視用の SQLite を使用して稼働状況を記録します。Monitoring は常に本番 sqlite_path を参照する設計になっています。
- OpenAI 等の外部 API 呼び出しはコスト・レート制限に注意してください。テスト時はモック化して実行可能です。
- ローカルでの検証は KABUSYS_ENV=development または paper_trading を利用してください。

ライセンス・貢献
----------------
- （必要に応じてここにライセンス情報、貢献方法を追記してください。）

最後に
------
この README はリファレンスとしての要点をまとめたものです。各モジュール内に詳細な docstring・コメントがあるため、実装を変更・拡張する際はそちらも参照してください。質問や追加のドキュメント化が必要であれば教えてください。