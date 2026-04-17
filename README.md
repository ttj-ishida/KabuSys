# KabuSys — README (日本語)

概要
-----
KabuSys は日本株自動売買システムのコードベースです。ファクター計算、ポートフォリオ構築、発注実行、監視、AI を使ったニュース評価などのコンポーネントを持ち、以下のような用途に向いています。

- 日次／短期ファクターベースの銘柄選定と配分
- 発注エンジン（本番 / ペーパートレード）
- システム稼働状況・注文状態・リスクの監視・Kill Switch
- ニュース NLP による銘柄/マクロセンチメント評価（OpenAI 経由）
- Paper Trading の検証レポート生成

主な機能
---------
- 環境設定ウィザード（.env 作成 / 更新）: kabusys.config_setup
- 起動前設定検証 CLI: kabusys.validate_config
- ExecutionEngine 起動スクリプト: kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、data/paper_trading.db に書き込む（本番 DB と分離）
- Monitoring ポーリングループ起動スクリプト: kabusys.run_monitoring
  - 監視は環境にかかわらず本番の sqlite_path を使用
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で変更可（デフォルト 60 秒）
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager）
- ポートフォリオ構築ユーティリティ（候補選定・重み計算・リスク調整・株数算出）
- リサーチ機能（ファクター計算・将来リターン・IC 等）
- AI モジュール
  - news_nlp: raw_news をまとめて OpenAI へ投げ、銘柄ごとに ai_score を作成
  - regime_detector: ETF を用いた MA200 比とマクロニュースの LLM 評価を合成して市場レジーム判定
- ツール: paper_verification_report（ペーパートレード検証レポート生成）

セットアップ手順
----------------
※ Python 環境は事前に用意してください（推奨: venv）。

1. リポジトリをクローン
   - プロジェクトルートに README 等がある想定

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 最低限必要なライブラリ（環境に応じて追加してください）:
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - PyYAML（config/*.yaml の検証に必要）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. データディレクトリを作成（任意）
   - mkdir -p data

5. 環境変数 (.env) の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または .env を手動で作成（.env.example を参考にしてください）。
   - 自動ロード: モジュールはプロジェクトルートの .env および .env.local を自動で読み込みます（OS 環境変数優先）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

必須・重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- OPENAI_API_KEY — AI 機能を使う場合に必要
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時のみ使用。デフォルト data/paper_trading.db）
- LOG_LEVEL — DEBUG/INFO/...

使い方（主要コマンド）
--------------------

1. 設定の作成（対話ウィザード）
   - python -m kabusys.config_setup
   - 完了後、python -m kabusys.validate_config で検証を推奨

2. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱い（終了コード 1）

3. ExecutionEngine を起動（本番/ペーパー両対応）
   - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading のときは paper_trading 用 DB を使用し MockBrokerClient で発注（本番 DB と完全分離）
     - 起動前に data/stop_requested.flag があれば起動せず終了
     - 実行中は data/execution.pid に PID を書き込む
     - 停止: data/stop_requested.flag の作成、または Ctrl+C（KeyboardInterrupt）

4. Monitoring を起動
   - python -m kabusys.run_monitoring
   - 特記事項:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定（デフォルト 60）
     - 監視プロセスは Settings.sqlite_path（本番用 monitoring DB）を常に参照（KABUSYS_ENV に依らない）
     - 停止フラグ: data/stop_requested.flag を作成するとループが終了

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
   - デフォルト DB は data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で変更可）

注意点・運用のヒント
- Kill Switch
  - KillSwitch はリスク条件（ドローダウン、ポジション上限等）で data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。
  - 本番で KILL_FLAG_CLEAR_ON_START=1 に設定すると起動時に kill.flag を自動でクリアしますが、本番では 0 を推奨します。
- PID / stop フラグ
  - 実行管理は data/execution.pid, data/stop_requested.flag, data/kill.flag を用います。CI や運用スクリプトからこれらを操作できます。
- Paper Trading
  - paper_trading モードでは MockBrokerClient が使用され、発注は専用 DB（PAPER_TRADING_SQLITE_PATH）へ記録されます。本番 DB と完全に分離されます。
- AI 機能
  - news_nlp / regime_detector は OpenAI を利用します。API キーが未設定だと該当機能はエラーまたはフェイルセーフ（0.0 など）で処理されます。API 呼び出しは再試行ロジックや JSON 検証を含み、部分失敗でも他データを守る実装です。
- 自動 .env ロード
  - config.Settings は起動時にプロジェクトルート（.git または pyproject.toml）を探索し .env/.env.local を自動で読み込みます。テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

ディレクトリ構成（概要）
----------------------
（プロジェクトの src/kabusys 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（デフォルト値・妥当性チェック）
  - config_setup.py
    - .env 対話ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
  - ai/
    - news_nlp.py — ニュースの LLM スコアリング（ai_scores へ書き込み）
    - regime_detector.py — マクロ+MA200 による市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・実行プロセス監視
    - trade_monitor.py — 注文滞留・約定異常価格検出
    - risk_monitor.py — ドローダウン/ポジション上限監視
    - kill_switch.py — フラグファイルによる停止シグナル
    - monitoring_engine.py — 各 Monitor を束ねるランナー
    - alert_manager.py — （アラート送信の抽象レイヤ）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・リスク/上限処理
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — momentum/value/volatility 等のファクター計算（DuckDB を使用）
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

（その他）
- data/ — デフォルトの DB・PID・フラグファイル等がここに置かれる想定
  - data/kabusys.duckdb（デフォルト）
  - data/monitoring.db（監視用 SQLite）
  - data/paper_trading.db（ペーパートレード用 SQLite）
  - data/execution.pid
  - data/kill.flag
  - data/stop_requested.flag

補足
----
- 設定ファイル（config/*.yaml）は存在すれば検証されます（PyYAML が必要）。generate_config.py のようなスクリプトで生成する運用想定です。
- 実機運用時は KABUSYS_ENV=live 設定や LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）などを慎重に確認してください（validate_config は live 向けの追加警告を出します）。
- DB マイグレーション等は monitoring_db.init_monitoring_db が自動でマイグレーションを行う設計になっています（列が無い場合の ALTER 等）。

ライセンスや貢献方法、さらなるドキュメント（API 仕様やアーキテクチャ図など）は別途ドキュメントを用意してください。

以上。README の追加要望（例: 具体的な環境変数サンプル、systemd ユニット例、Dockerfile テンプレ等）があれば追記します。