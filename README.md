KabuSys — 日本株自動売買システム
=================================

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買（発注エンジン＋監視・解析ツール）を想定した Python コードベースです。
主な機能は以下の通りです。

- 発注実行（ExecutionEngine）: live / paper_trading / development 環境に対応
- 監視（Monitoring）: システム稼働・データ鮮度・注文・リスクの定期チェックとアラート、Kill Switch
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ決定、セクター上限・レジーム補正
- リサーチ: ファクター計算（モメンタム・バリュー・ボラティリティ）、特徴量解析（IC 等）
- AI ユーティリティ: ニュースの NLP スコアリング、レジーム判定（OpenAI API を利用）
- 運用支援ツール: .env 対話式作成、設定検証、Paper Trading の検証レポート生成
- 永続化: SQLite（監視ログ等）と DuckDB（時系列・リサーチ用分析）を利用

主な設計方針
- 環境依存（CWD など）に強いパス解決、.env をプロジェクトルート基準で自動読み込み
- 本番 / ペーパーで DB を分離（paper_trading は data/paper_trading.db）
- ルックアヘッドバイアス防止（date.today() 等に依存しない実装）
- フェイルセーフ：API 失敗やデータ不足時は安全側にフォールバックする設計

機能一覧
--------
- 実行関連
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV=paper_trading で MockBroker 使用）
  - ブローカーファクトリ、OrderManager、RiskManager、Reconciler など

- 監視関連
  - run_monitoring: SystemMonitor のポーリングループ実行（MONITOR_POLL_INTERVAL で間隔変更可）
  - MonitoringEngine: System/Trade/Risk の統合実行、Kill Switch 評価、AlertManager 経由で通知
  - MonitoringDB: SQLite を用いた監視ログ（system_status, trade_logs, positions, risk_logs, dashboard）

- ポートフォリオ関連
  - 銘柄選定、等分配／スコア重み配分、リスクベースのポジションサイズ計算
  - セクターキャップ適用、レジーム乗数計算

- リサーチ／研究
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（情報係数）計算、統計サマリ

- AI（OpenAI）
  - news_nlp: raw_news を集約して LLM でセンチメントを算出し ai_scores に書き込み
  - regime_detector: MA200 とマクロセンチメントを組み合わせて market_regime を判定

- ツール
  - config_setup: .env を対話式で作成/更新
  - validate_config: 起動前に必須 env や config YAML をチェック
  - paper_verification_report: ペーパートレード DB を解析し PASS/FAIL レポートを生成

セットアップ手順
----------------
1. Python の準備
   - 推奨: Python 3.10+（コードは型注釈や一部新しい構文を利用）
   - 仮想環境の作成（例）
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - requirements.txt がある想定で:
     - pip install -r requirements.txt
   - 主な外部依存 (必要に応じて)
     - duckdb
     - psutil
     - openai
     - PyYAML（validate_config の YAML 検証に使用）
   - 注意: 環境によりネイティブ依存があるパッケージ（psutil 等）に注意

3. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動で作成
   - 最低必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他よく使う環境変数（一部）:
     - KABUSYS_ENV: development | paper_trading | live (default: development)
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
     - OPENAI_API_KEY: OpenAI を使う場合に必要
     - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（run_monitoring 側で参照）

4. 設定の検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）

5. データディレクトリ
   - デフォルトで data/ 以下に DB やフラグファイルを置く想定
   - logs/ にログファイルが出力されます（例: logs/execution.log, logs/monitoring.log）

使い方
------
- 実行エンジン（Execution）
  - 本番/ペーパーに応じて .env の KABUSYS_ENV を設定後、起動:
    - python -m kabusys.run_execution
  - ペーパー取引時は paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用します。
  - 起動時、data/stop_requested.flag が存在すると起動しません。
  - 停止：監視側やオペレータが data/stop_requested.flag を作成すると実行スレッドが停止します。
  - PID ファイル: data/execution.pid（Settings.pid_file_path で設定可能）

- 監視プロセス（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔(秒)を上書き可能（デフォルト 60）
  - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に依らず）
  - 停止フラグ: data/stop_requested.flag を作成すると監視ループが終了

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告があると exit(1) になります

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を環境変数か関数引数で与えて使用します
  - 例（プログラム内部で呼ぶ場合）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

ログ
---
- ログは logs/<app_name>.log に日次ローテーションで保存（defaults: logs/）
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一
- 起動スクリプトは最初に setup_logging を呼び出します

停止／Kill Switch
----------------
- kill.flag（Settings.kill_flag_path, default: data/kill.flag）:
  - KillSwitch がトリガー条件を満たした際に作成され、ExecutionEngine に対して停止信号を送ります
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START が 1 であれば自動的にクリアする挙動を設定可能（本番では 0 推奨）
- stop_requested.flag（data/stop_requested.flag）:
  - ローカル管理用の停止リクエスト。run_execution / run_monitoring はこのファイルの存在を見て終了します。

ディレクトリ構成（主なファイル）
----------------------------
src/kabusys/
- __init__.py
- config.py
  - Settings クラス: 環境変数の解決・既定値・バリデーション
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前チェック CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト（PID・STOP フラグ管理）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト

- execution/
  - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
  - 発注に関するロジック群（ブローカ抽象化、注文管理、リコンシリエーション、リスク管理）

- monitoring/
  - monitoring_db.py      — SQLite テーブル定義・永続化 API
  - system_monitor.py      — システム稼働・データ鮮度監視
  - trade_monitor.py       — 注文滞留・約定異常検出（コードベースにあり）
  - risk_monitor.py        — ドローダウン／ポジション上限監視
  - kill_switch.py         — kill.flag 書き込みロジック
  - monitoring_engine.py   — 各 Monitor を束ねる実行ループ
  - alert_manager.py       — （通知の送信を担う想定）

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - ポートフォリオ構築・サイズ決定・リスク補正

- research/
  - factor_research.py
  - feature_exploration.py
  - リサーチ／ファクター計算・IC 等

- ai/
  - news_nlp.py           — ニュースを OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py    — MA200 とマクロセンチメントを合成してレジーム判定

- tools/
  - paper_verification_report.py  — Paper Trading DB を解析して検証レポート生成

- utils/
  - logging_setup.py      — 共通ログ設定
  - process_priority.py   — プロセス優先度 / CPU affinity ユーティリティ
  - その他ユーティリティ

注意事項 / 運用上のヒント
------------------------
- 本番環境（KABUSYS_ENV=live）では特に注意して環境変数と kill_flag の設定を確認してください（validate_config の live ガード参照）。
- OpenAI を利用する機能は API キーと利用コストに注意。API の失敗は安全にフォールバックする設計ですが、運用方針を定めてください。
- logs/ と data/ は Git にコミットしない（.env と同様に扱うこと）。
- DuckDB は分析用に大量の時系列データを扱う設計になっています。性能・ストレージ運用に注意してください。
- psutil などネイティブ拡張を使うパッケージは platform 依存の注意が必要です。CI / デプロイ先でビルドできるか事前確認を推奨します。

トラブルシューティング
----------------------
- validate_config でエラーが出る場合: 必須環境変数が未設定か、KABUSYS_ENV / LOG_LEVEL の値が不正です。
- run_monitoring が起動しない: data/stop_requested.flag が存在していないか確認。MONITOR_POLL_INTERVAL が不正な値の場合（0 以下等）、デフォルト 60 秒にフォールバックします。
- OpenAI 呼び出しで頻繁に RateLimitError: リトライとバックオフを実装していますが、利用制限緩和やバッチ戦略の見直しを検討してください。

ライセンス / バージョン
----------------------
- パッケージバージョン: src/kabusys/__version__ = "0.1.0"
- ライセンス情報はリポジトリのトップに配置してください（本 README には含めていません）。

以上が README の概要です。必要であれば、実際の運用向けに「デプロイ手順」「systemd / Supervisor 用のサービス定義例」「サンプル .env.example」を追加できます。どの情報を補足しますか？