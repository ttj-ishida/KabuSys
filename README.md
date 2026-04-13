KabuSys
======

日本株向けの自動売買システム（ライブラリ／実行スクリプト群）の一部コードベースです。本リポジトリには以下の機能群が含まれます：監視（Monitoring）、発注実行（Execution）、ポートフォリオ構築（Portfolio）、リサーチ（Research）、AI を用いたニュース解析（AI）など。

プロジェクト概要
--------------
KabuSys は日本株の自動売買を想定したモジュール群です。主要な責務は次のとおりです。

- Execution: ブローカーとのやり取り、注文管理、リコンシリエーション（再整合）
- Monitoring: システム稼働／データ鮮度／注文状況の定期監視、ダッシュボード、アラート（LINE）
- Portfolio: 候補選定・重み付け・ポジションサイズ決定、セクター制限などのポートフォリオ構築ロジック
- Research: ファクター計算、将来リターン・IC計算などの分析ユーティリティ
- AI: ニュースのセンチメント解析や市場レジーム判定で OpenAI を利用する機能
- Tools: Paper Trading 検証レポート生成などの小ツール

主な特徴 / 機能一覧
-----------------
- 実運用向けの監視ループ（SystemMonitor / TradeMonitor / RiskMonitor）とアラート送信（LINE）
- ExecutionEngine 起動スクリプト（本番／ペーパー取引対応）
  - KABUSYS_ENV=paper_trading の場合、Mock ブローカーを使い paper_trading 用 DB に記録して本番 DB と分離
- 監視ログ用 SQLite（monitoring.db）と分析用 DuckDB（kabusys.duckdb）を併用
- Streamlit ダッシュボード（read-only で監視 DB を可視化）
- Paper Trading の検証レポート出力ツール（metrics の集計と PASS/FAIL 判定）
- ニュースを OpenAI（gpt-4o-mini）でスコアリングする機能（batch / retry / JSON 検証）
- 市場レジーム判定（ETF MA + マクロニュースセンチメントの合成）
- ポートフォリオ構築：候補選定、等重／スコア重み、リスクベースのポジションサイズ計算、セクターキャップ適用

セットアップ手順
---------------
1. Python 環境を準備（推奨: python 3.10+）
2. 依存パッケージをインストール（例）
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   - など（プロジェクトの requirements.txt がある場合はそれを使用）
   例:
   ```
   pip install duckdb psutil requests openai streamlit
   ```

3. 環境変数 / .env ファイル
   - プロジェクトは起動時にプロジェクトルート（.git または pyproject.toml）を探索し、.env と .env.local を自動読み込みします（OS 環境変数が優先）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN — 必須
     - KABU_API_PASSWORD — 必須
   - 任意／デフォルト値（主なもの）
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - KABU_API_BASE_URL: http://localhost:18080/kabusapi
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - PAPER_FILL_MODE: instant | partial | never | reject （デフォルト: instant）
     - PID_FILE_PATH: data/execution.pid
     - KILL_FLAG_PATH: data/kill.flag
     - KILL_FLAG_CLEAR_ON_START: 0/1
     - CPU_THRESHOLD_PCT: 90.0
     - MEMORY_THRESHOLD_PCT: 85.0
     - DISK_THRESHOLD_PCT: 90.0
     - OPENAI_API_KEY: OpenAI を利用する機能で必要
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）を使う場合に必要
   - .env 例（簡易）:
     ```
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     KABUSYS_ENV=paper_trading
     ```

4. DB 初期化
   - 監視用 SQLite（デフォルト: data/monitoring.db）は起動スクリプト内で init_monitoring_db() により自動作成・マイグレーションされます。手動で用意する必要は通常ありません。

使い方（実行例）
---------------
以下は代表的なスクリプトの起動例です。各スクリプトはパッケージ経由でモジュールとして実行できます。

- 監視ループを起動（定期的に System/Trade/Risk をチェックしてログ・通知）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 起動時にプロセス優先度を "high" に設定しようとします（権限や OS により失敗する場合は警告を出します）。
  - 監視は常に本番 sqlite_path を使用します（環境にかかわらず）。

- ExecutionEngine（発注エンジン）を起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用し MockBrokerClient を利用して本番 DB と完全分離します。
  - 起動時にプロセス優先度を "high" に設定します。

- Streamlit 監視ダッシュボード（ローカルから監視 DB を参照）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスはオプション --db または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能（デフォルト: data/paper_trading.db）。
  - 生成されるレポートは稼働率、注文成功率、送信率、レイテンシ等の指標を表示し、閾値に基づいて PASS/FAIL を出力します。

- AI / ニューススコアリング（ライブラリ API）
  - ニューススコアリングは kabusys.ai.score_news（DuckDB 接続と target_date を渡す） を呼び出して利用します。OpenAI API キー（OPENAI_API_KEY） が必要です。
  - 市場レジーム判定は kabusys.ai.regime_detector.score_regime を使用します（同様に API キーが必要）。

主要な挙動・注意点
-----------------
- 環境（KABUSYS_ENV）
  - development: 開発用
  - paper_trading: 発注は MockBroker、DB は data/paper_trading.db（本番と分離）
  - live: 本番モード（実ブローカー）

- MONITORING
  - monitoring 用の SQLite DB は init_monitoring_db() によりテーブル（system_status, trade_logs, positions, risk_logs, dashboard）を作成します。既存 DB に対しても冪等にマイグレーションを行います（列追加など）。

- OpenAI 利用
  - news_nlp / regime_detector は OpenAI を使うため OPENAI_API_KEY を設定してください。呼び出しは retry / exponential backoff / JSON 検証が組み込まれています。API 失敗時はフェイルセーフ（多くは 0.0 を返す / スキップ）で継続する設計です。

- プロセス優先度
  - run_monitoring/run_execution 起動時に set_process_priority("high") を呼びます。プラットフォーム依存（Windows/Linux/macOS）に対応していますが、権限不足などで設定できない場合は警告ログを出してスキップします。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主なモジュールと役割の概観です（抜粋）。

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / .env の読み込みと Settings クラス
  - run_monitoring.py — SystemMonitor をポーリングする起動スクリプト
  - run_execution.py — ExecutionEngine を起動するスクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - monitoring/
    - monitoring_db.py — monitoring 用 SQLite のスキーマ・永続化層
    - system_monitor.py — CPU/メモリ/Disk/データ鮮度/プロセス監視
    - trade_monitor.py — 注文滞留・約定異常の検出
    - risk_monitor.py — ドローダウン・ポジション上限の監視
    - attack_manager.py (AlertManager) — LINE 通知（push）
    - kill_switch.py — フラグファイルで Execution を停止する仕組み
    - monitoring_engine.py — 各 Monitor を束ねるループ
    - streamlit_dashboard.py — Streamlit による監視ダッシュボード
  - execution/
    - order_manager.py — Order State Machine の外向き API
    - reconciler.py — 起動時の自動復旧・リコンシリエーション
    - （ブローカー関連や ExecutionEngine 等は別ファイルに実装）
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 株数算出、単元丸め、aggregate cap
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュースの LLM を用いたセンチメント化
    - regime_detector.py — ETF MA + マクロニュースでレジーム判定
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

開発・運用上の備考
-----------------
- .env のパースはシェル風の書式（export KEY=val、引用符、インラインコメント等）にある程度対応しています。自動ロードはプロジェクトルートが検出できる場合にのみ行われます。
- Monitoring の DB 操作は MonitoringDB クラスで抽象化されており、冪等性と簡潔な API を提供します。
- AI 関連は出力のバリデーションやスコアのクリッピング、部分成功時の DB 書き込みの保護（部分置換）などを考慮しています。
- Paper Trading 用の DB を分離しているため、ペーパー検証時に実口座へ影響を与えない設計です。

よく使うコマンドまとめ
---------------------
- 監視開始
  ```
  python -m kabusys.run_monitoring
  ```
  MONITOR_POLL_INTERVAL 環境変数で秒数を指定可能。

- 発注エンジン起動
  ```
  python -m kabusys.run_execution
  ```

- Streamlit ダッシュボード
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

最後に
------
この README はコードベースの主要点をまとめたものです。実際の導入時は環境変数の設定、OpenAI キー、DuckDB/SQLite のファイルパス、LINE トークン等を正しく設定してください。サンプル .env を用意して運用環境ごとに管理することを推奨します。必要であれば運用手順書（起動・停止・ログ確認・トラブルシュート）やアーキテクチャ図も別途作成できます。