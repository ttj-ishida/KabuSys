KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システム（研究・ポートフォリオ構築・発注・監視・AI 補助）を想定した Python コードベースです。  
主な設計方針は次の通りです。

- 研究（Research）は DuckDB を用いたオフライン集計・ファクター計算に注力（本番口座へはアクセスしない）。
- Execution（発注）は本番 / ペーパートレードを分離（KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録）。
- Monitoring（監視）は SQLite にログを残し、リスク（ドローダウン、ポジション上限）・注文滞留・プロセス状態・データ鮮度を監視してアラート / Kill Switch を実行。
- AI モジュール（ニュース NLP / レジーム判定）は OpenAI API を用いてセンチメント等を算出し、DuckDB のテーブルへ書き込む（API キー必須）。

機能一覧
--------
主な機能（コードから抜粋）：

- 設定管理
  - .env 自動読み込み、対話式ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Settings クラスで各種環境変数の取得と妥当性チェック
- Execution（発注周り）
  - ExecutionEngine（エンジン起動スクリプト: run_execution.py）
  - ペーパートレード時は専用 SQLite（PAPER_TRADING_SQLITE_PATH）
  - ブローカーファクトリで本番／モックを切替
- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセスの生存確認、データ鮮度チェック
  - TradeMonitor: 注文滞留・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件に応じて data/kill.flag を書き込み Execution を停止させる
  - MonitoringEngine／run_monitoring.py：ポーリングループ起動
  - Monitoring DB 層（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard の永続化
- ポートフォリオ構築（純関数群）
  - 候補選定、等重／スコア重み、セクター制限、レジーム乗数、ポジションサイズ計算
- 研究（Research）
  - ファクター計算（momentum / volatility / value 等）
  - 将来リターン計算、IC 計算、統計サマリ
- AI（OpenAI）
  - news_nlp.score_news: ニュースを LLM で採点して ai_scores に保存
  - regime_detector.score_regime: マクロニュース + ETF MA 乖離で市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB を解析して検証レポートを生成

セットアップ手順
----------------
以下は一般的な開発環境のセットアップ手順例です。

1. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - 任意 (設定検証で YAML を検証する場合): pip install PyYAML

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を推奨）

3. プロジェクトルートに移動し、.env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参照する想定）

   重要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   主要オプション（代表）
   - KABUSYS_ENV: development | paper_trading | live
   - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
   - SQLITE_PATH: data/monitoring.db（デフォルト）
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
   - OPENAI_API_KEY: OpenAI を使用する場合必須
   - LOG_LEVEL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, KILL_FLAG_CLEAR_ON_START 等

   注意: .env は機密情報を含むため絶対にリポジトリにコミットしないでください。

4. 設定検証
   - python -m kabusys.validate_config
   - 警告も FAIL にしたい場合は --strict を付与

5. data ディレクトリ作成（必要なら）
   - mkdir -p data

使い方（実行例）
----------------

- 監視ループを起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - python -m kabusys.run_monitoring
  - 監視は常に production 用の sqlite_path（Settings.sqlite_path）を使用して監視ログを記録します。
  - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループが検知して終了します。

- Execution Engine を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録して本番 DB と分離します。
  - 実行時に data/execution.pid が作成されます。停止は data/stop_requested.flag を作成するか、Kill Switch（data/kill.flag）で強制停止となります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH で PAPER_TRADING_SQLITE_PATH を上書き可能

- AI モジュールをプログラムから呼ぶ例
  - ニュース NLP（対象日を指定してスコアを DuckDB に書き込む）
    - from datetime import date
      from kabusys.ai.news_nlp import score_news
      score_news(duckdb_conn, date(2026, 4, 11), api_key="sk-...")

  - レジーム判定
    - from kabusys.ai.regime_detector import score_regime
      score_regime(duckdb_conn, date(2026, 4, 11), api_key="sk-...")

  （注）OpenAI API を使用する関数は api_key 引数または環境変数 OPENAI_API_KEY を必要とします。API 呼び出しはリトライやフェイルセーフを内蔵していますが、クオータやコストに注意してください。

停止・Kill 操作
----------------
- 優雅なプロセス停止（run_monitoring / run_execution のループ停止）
  - プロジェクトルート/data/stop_requested.flag を作成すると監視・実行ループが検知して終了します。

- Kill Switch（Execution 停止用）
  - KillSwitch は risk 条件等に応じて data/kill.flag を書き込みます。Execution 側ではこのフラグの存在を参照して停止処理を行う設計です。
  - 手動でクリアしたい場合はファイルを削除してください（KillSwitch.clear() 相当）。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアしますが、本番では 0 を推奨します。

設定検証ツール
--------------
- python -m kabusys.validate_config
  - .env の必須変数・KABUSYS_ENV の妥当性・DB パスの親ディレクトリ存在可否・config/*.yaml の存在（PyYAML がある場合はパース検証）等をチェックします。

ディレクトリ構成（主要ファイル）
-------------------------------
リポジトリ内の主要な構成（src/kabusys 以下を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数読み込み・Settings クラス
  - config_setup.py         — .env 対話ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py           — ニュース NLP（OpenAI）→ ai_scores 書込み
    - regime_detector.py    — レジーム判定（ETF MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py      — SQLite テーブル作成・読み書きラッパー
    - system_monitor.py     — CPU/MEM/DISK, プロセス, データ鮮度監視
    - trade_monitor.py      — 注文滞留・約定異常検出
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - kill_switch.py        — kill.flag 書き込みユーティリティ
    - monitoring_engine.py  — 各 Monitor を束ねる実行エンジン
    - alert_manager.py      — （アラート送信管理 — 実装はファイル末尾に続く想定）
  - portfolio/
    - portfolio_builder.py  — 候補選定・重み計算
    - position_sizing.py    — 株数決定・スケール調整
    - risk_adjustment.py    — セクター上限・レジーム乗数
  - research/
    - factor_research.py    — momentum / volatility / value 計算
    - feature_exploration.py— 将来リターン・IC・統計サマリー
  - execution/               — 発注エンジン関連（repo, order_manager 等） ※抜粋
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - process_priority.py   — プロセス優先度 / CPU affinity 設定ユーティリティ

補足・注意事項
--------------
- 設定 (.env) に機密情報（API トークン等）が含まれます。決して Git にコミットしないでください。
- 本番環境（KABUSYS_ENV=live）では、LINE 通知設定や KILL_FLAG_CLEAR_ON_START の有無などに注意してください（validate_config が警告を出します）。
- OpenAI を使う機能は API キーが必須であり、コストとレート制限に注意して運用してください。実装はリトライやフォールバックを含みますが、それでも API 呼び出しの失敗による部分的な欠損はあり得ます。
- DuckDB / SQLite のスキーマはコード内で初期化 / マイグレーション処理が行われます（init_monitoring_db 等）。既存 DB を扱う場合はバックアップをとってください。

ライセンス・貢献
----------------
この README はコードベースの概要説明であり、実際の運用では安全性（注文ロジックの検証、フェイルセーフ、手動監視）と法令順守が必須です。  
貢献やバグ報告はリポジトリの issue / PR を利用してください。

以上。必要であれば「環境変数の完全一覧」「CLI の詳細なコマンド例」「実行フロー図」などを追加で作成します。どの情報を補足しますか？