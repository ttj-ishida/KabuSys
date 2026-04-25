README
======

概要
----
KabuSys は日本株向けの自動売買 / リサーチ用ライブラリ兼実行フレームワークです。本リポジトリは以下の主要機能を含みます。

- 実行エンジン（ExecutionEngine）による発注処理（本番 / ペーパートレード切替）
- 監視コンポーネント（System / Trade / Risk Monitor）と Kill Switch
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出・セクター制限）
- リサーチ（ファクター計算、特徴量解析、IC計算等）— DuckDB ベース
- ニュース NLP（OpenAI を用いた銘柄別センチメントスコアリング）およびレジーム判定
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート生成）

主な設計方針：
- DB（SQLite / DuckDB）をデータ永続化と解析に活用
- 実行ロジックと解析ロジックを分離（研究用モジュールは発注 API に依存しない）
- 本番とペーパートレードはデータベースとブローカークライアントで完全分離可能

機能一覧
--------
- 実行/監視
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録。
  - run_monitoring.py: SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL で間隔変更可（デフォルト 60 秒）。
  - Kill Switch（data/kill.flag）による安全停止トリガー（ドローダウンやポジション上限で発動）。
- モニタリング DB
  - SQLite ベースの monitoring DB（system_status / trade_logs / positions / risk_logs / dashboard）。
  - 関連ユーティリティ（MonitoringDB）でログ記録やダッシュボード集計の upsert 等を提供。
- ポートフォリオ構築
  - 候補選定（select_candidates）、重み付け（等金額 / スコア加重）、ポジションサイズ算出（risk_based / equal / score）、セクター上限適用、レジーム乗数。
- リサーチ
  - ファクター計算（momentum / value / volatility）、将来リターン計算、IC（スピアマン）・統計サマリー。
  - DuckDB 接続を受け取り SQL で高効率に計算。
- AI / NLP
  - news_nlp: raw_news を OpenAI に送信して銘柄別の ai_score を ai_scores テーブルへ書き込み。
  - regime_detector: ETF（1321）の ma200 乖離とマクロニュースの LLM センチメントの合成で市場レジーム（bull/neutral/bear）を判定して保存。
  - OpenAI API 呼び出しは再試行・安全フォールバック実装あり。
- ツール
  - config_setup.py: .env 初期作成・更新の対話ウィザード。
  - validate_config.py: 環境変数や config/*.yaml の事前検証（--strict モードあり）。
  - tools.paper_verification_report: ペーパートレード DB を解析し Pass/Fail レポートを出力。

セットアップ手順
--------------
1. Python 環境（推奨: venv）を作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 本プロジェクトに requirements.txt は含まれていないため、最低限以下をインストールしてください。
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証を行う場合）
   例:
     pip install duckdb psutil openai pyyaml

   ※ 実行環境により追加で依存が必要になる可能性があります（例: ネットワーク/SSL ライブラリ等）。

3. .env の準備（推奨）
   - 対話ウィザードで作成:
     python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - （OpenAI を使う場合）OPENAI_API_KEY
   - 主要なオプション / デフォルト:
     - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO
     - KILL_FLAG_CLEAR_ON_START: 0（本番では 0 推奨）

4. 設定検証
   - python -m kabusys.validate_config
   - 厳密モード（警告も失敗とする）:
     python -m kabusys.validate_config --strict

5. データ/ログディレクトリの確認
   - デフォルトのログ出力先: logs/。環境変数 LOG_DIR で変更可能。
   - SQLite / DuckDB のデフォルトパスは .env の値または上記デフォルトを使用。

使い方
-----

一般的な起動例
- 監視ループ起動（MONITOR_POLL_INTERVAL で秒数上書き可: 60 秒がデフォルト）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視ループはプロジェクトルート/data/stop_requested.flag の存在を検知すると停止します。

- 実行エンジン起動（本番 / ペーパートレードは KABUSYS_ENV に依存）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - ExecutionEngine は起動時に data/stop_requested.flag の存在をチェックし、既に立っている場合は起動を停止します。
  - 実行中は data/execution.pid に PID を書きます（デフォルト）。停止は stop フラグによるか Kill Switch による kill.flag により行われます。

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAILURE 扱いで exit(1) します。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db でデータベースパス指定可能（未指定時は PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db）。

- AI / レジーム関連（プログラムから直接呼び出す）
  - ニューススコアリング（例: Python スクリプト内）
    from kabusys.ai.news_nlp import score_news
    import duckdb, datetime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=datetime.date(2026,4,1), api_key="sk-...")

  - レジーム判定
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=datetime.date(2026,4,1), api_key="sk-...")

注意点 / 実運用のヒント
- MONITOR_POLL_INTERVAL は run_monitoring.py で使用（デフォルト 60 秒）。0 以下は無効でデフォルトにフォールバックします。
- run_monitoring は KABUSYS_ENV にかかわらず「本番」sqlite_path を使用して監視情報を記録します（監視用 DB は本番パスで一貫）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離します。
- KillSwitch（data/kill.flag）は RiskMonitor などから書き込まれ、実行エンジンに停止シグナルを与えます。起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動でクリアされますが、本番では 0 を推奨します。
- ログは logs/<app_name>.log に日次ローテーションで保存されます。LOG_DIR 環境変数でフォルダを変更できます。
- process priority の設定（高優先度）は psutil を使って行われます。権限が不足する場合は警告を出してスキップします。
- OpenAI API を利用する機能（news_nlp/regime_detector）は OPENAI_API_KEY を設定するか、api_key を関数に渡してください。API エラーや JSON 解析失敗はフォールバック（安全動作）する設計です。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要ファイルと役割の簡易一覧です。

- kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / .env 自動読み込み・Settings クラス
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- kabusys/monitoring/
  - monitoring_db.py — SQLite スキーマ初期化 + 永続化レイヤ
  - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・プロセス監視
  - trade_monitor.py — （売買監視ロジック）※実装ファイルあり（本ツリーに含まれる想定）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — data/kill.flag 制御
  - monitoring_engine.py — 各 Monitor を束ねるエンジン/ポーリング制御
  - alert_manager.py — 通知送信（LINE など）（実装ファイルが存在する想定）
- kabusys/execution/
  - execution_engine.py — 発注セッション実行（Engine）
  - broker_factory.py — ブローカークライアント生成（Mock / 実ブローカー切替）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注管理・リスク制御
- kabusys/portfolio/
  - portfolio_builder.py — 候補選定、重み計算
  - position_sizing.py — 株数算出・集約キャップ処理
  - risk_adjustment.py — セクター上限・レジーム乗数
- kabusys/research/
  - factor_research.py — momentum / value / volatility 等のファクター計算
  - feature_exploration.py — forward returns / IC / 統計サマリー
- kabusys/ai/
  - news_nlp.py — ニュース NLP（OpenAI）による銘柄別スコア算出
  - regime_detector.py — market regime 判定（ma200 + macro LLM）
- kabusys/tools/
  - paper_verification_report.py — ペーパートレード結果の検証レポート生成
- kabusys/utils/
  - logging_setup.py — 統一的なログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

付録: 主要な環境変数（抜粋）
---------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能利用時)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト data/paper_trading.db)
- LOG_LEVEL (デフォルト INFO)
- LOG_DIR (ログ出力ディレクトリ)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング秒数)

最後に
-----
この README はコードベース（src/kabusys 下のモジュール）に基づく概要および運用手順の要約です。開発・運用時は必ず python -m kabusys.validate_config で設定の検証を行い、.env を Git に絶対にコミットしないようご注意ください。問題や不明点があれば該当モジュールの docstring を参照してください。