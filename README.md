KabuSys — 日本株自動売買システム（README）
======================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の一部を実装したコードベースです。本リポジトリは以下の機能群を提供します。

- 発注実行エンジン（ExecutionEngine）とペーパートレードモード
- システム監視（Monitoring）・アラート・Kill Switch
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- リサーチ（ファクター計算・特徴量解析）
- AI（OpenAI）を使ったニュースセンチメント評価とレジーム判定
- 運用補助ツール（対話式 .env 設定ウィザード、設定検証、ペーパートレード検証レポート 等）

主要な設計方針：
- 環境変数 / .env で設定を切り替える（自動読み込み機構あり）
- Paper Trading（KABUSYS_ENV=paper_trading）では本番 DB と分離して専用の SQLite を利用
- DuckDB を分析用 DB として使用（prices_daily / raw_financials 等）
- 実行・監視プロセスは PID / flag ファイルで制御可能

主な機能一覧
--------------
- run_execution: ExecutionEngine を起動（本番 / ペーパートレード対応、プロセス優先度設定）
- run_monitoring: SystemMonitor を定期ポーリング（MONITOR_POLL_INTERVAL で間隔指定可能）
- monitoring:
  - SystemMonitor: CPU/メモリ/ディスク、プロセス死活、データ鮮度監視
  - TradeMonitor / RiskMonitor: 注文滞留、約定異常、ドローダウン・ポジション上限監視
  - KillSwitch: 条件に応じてデータ/kill.flag を書き込み Execution 停止を促す
  - MonitoringDB: SQLite に監視ログ・トレードログ・リスクログ・ダッシュボードを永続化
- portfolio: 候補選定（select_candidates）、重み（等金額・スコア）計算、セクター制限、ポジションサイズ算出
- research: ファクター計算（モメンタム／ボラティリティ／バリュー）、将来リターン、IC 計算、統計サマリ
- ai:
  - news_nlp: raw_news を集計して OpenAI による銘柄センチメントを ai_scores に書き込む
  - regime_detector: ma200 乖離 + マクロニュースセンチメントを合成して market_regime を判定
- utils:
  - logging_setup: 標準化されたロギング（Console + 日次ローテートファイル）
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティ
- tools:
  - paper_verification_report: ペーパートレード DB を集計し PASS/FAIL レポートを生成
- 設定補助:
  - config_setup: 対話式 .env 生成ウィザード
  - validate_config: .env と config/*.yaml の整合性チェック CLI

セットアップ手順
----------------
前提
- Python 3.10+（typing の一部表記やモジュール前提）
- system パッケージ: duckdb, psutil, openai（必要に応じて PyYAML）

基本手順（例）
1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows では .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - 設定検証で YAML を使う場合: pip install PyYAML

   （requirements.txt がある場合は pip install -r requirements.txt）

3. .env を用意する
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または .env.example を参考に .env を手動作成

   自動読み込み:
   - プロジェクトルートに .env / .env.local があれば自動で読み込まれます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合: python -m kabusys.validate_config --strict

5. 必要なディレクトリを作成（logs / data 等は自動作成されますが、権限等の問題で失敗する場合があります）
   - mkdir -p data logs

使い方（コマンド例）
------------------
- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV 環境変数で切り替え（development / paper_trading / live）
  - ペーパートレード時は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に書き込みます

- Monitoring（システム監視）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒、デフォルト 60）で変更可能（不正値はデフォルトにフォールバック）
  - 監視は常に production の sqlite_path（Settings.sqlite_path）を使用してログを記録します

- 対話式 .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを個別指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能）

- AI スコア / レジーム判定
  - AI 機能は OpenAI API キー（OPENAI_API_KEY）を必要とします。プログラムからは kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出します。

停止／フラグについて
- 停止フラグ（手動停止）
  - data/stop_requested.flag を作成すると、run_execution / run_monitoring のループが検知して安全に停止します。
- Kill Switch
  - KillSwitch は条件を満たすと data/kill.flag（パスは Settings.kill_flag_path）を書き込みます。これにより Execution 停止等の運用上の判断を行います（設定により起動時に自動クリアされる場合あり：KILL_FLAG_CLEAR_ON_START）。

主な環境変数（代表）
---------------------
- JQUANTS_REFRESH_TOKEN（必須）: J-Quants API 用トークン
- KABU_API_PASSWORD（必須）: kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB パス（デフォルト data/monitoring.db）
- LOG_LEVEL: ログレベル（INFO など）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_PATH: Kill flag のパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に Kill flag をクリアするか（"1" で有効、開発用）

ログ
----
- ログは標準出力（コンソール）と logs/<app_name>.log（日次ローテート、30日保持）に出力されます。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一されています。

ディレクトリ構成（主要ファイル）
--------------------------------
（リポジトリ内の src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / .env 読み込み、Settings クラス
  - config_setup.py                  — 対話式 .env ウィザード（CLI）
  - validate_config.py               — 設定検証 CLI
  - run_execution.py                 — ExecutionEngine 起動スクリプト（エントリポイント）
  - run_monitoring.py                — SystemMonitor ポーリング起動スクリプト（エントリポイント）
  - tools/
    - paper_verification_report.py   — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py               — ログ初期化ユーティリティ
    - process_priority.py            — プロセス優先度／CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py               — SQLite 永続化層（監視ログ）
    - system_monitor.py              — システム状態監視
    - risk_monitor.py                — ドローダウン・ポジション監視
    - kill_switch.py                 — kill.flag 書き込みユーティリティ
    - monitoring_engine.py           — 各 Monitor を束ねるループ
    - ...（TradeMonitor, AlertManager 等の実装が存在）
  - portfolio/
    - portfolio_builder.py           — 候補選定・重み（等金額 / スコア）
    - position_sizing.py             — 発注株数算出（単元丸め・利用可能資金制約）
    - risk_adjustment.py             — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py             — Momentum/Volatility/Value ファクター計算（DuckDB）
    - feature_exploration.py         — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py                    — ニュースNLP（OpenAI）で銘柄センチメントを生成
    - regime_detector.py             — 市場レジーム判定（ma200 + マクロセンチメント）
  - ... その他モジュール

注意事項 / 運用メモ
-------------------
- Paper Trading モードでは本番用 SQLite（SQLITE_PATH）と完全に分離した PAPER_TRADING_SQLITE_PATH を使用するようにしてください。KABUSYS_ENV=paper_trading を指定すると専用 DB に記録されます。
- .env ファイルは絶対にリポジトリにコミットしないでください（機密情報を含みます）。
- OpenAI を利用する機能は API 呼び出しに依存するため、API キーと使用量に注意してください。API エラー時はフェイルセーフのフォールバック（スコア 0.0 等）処理が組み込まれていますが、期待する精度を得るには安定した接続と適切な API プランが必要です。
- ログディレクトリの作成に失敗した場合、ファイル出力は無効化されコンソール出力のみになります。logs ディレクトリへの書き込み権限を確認してください。
- 設定検証（validate_config）は運用前に必ず実行し、KABUSYS_ENV=live の場合は特に LINE の通知設定や Kill Switch 設定を確認してください。

貢献・拡張案
-------------
- 個別銘柄の lot_size を stocks マスタ化して対応する（現在は全銘柄共通 lot_size）
- position_sizing のコスト見積り（手数料・スリッページ）を動的に推定して反映
- monitoring の各種アラート（LINE / 他チャネル）を AlertManager に実装・拡張
- research モジュールをバッチジョブ・スケジューラに組み込み（DuckDB の定期更新）

お問い合わせ
--------------
実運用に関する質問や拡張提案はリポジトリのイシューに記載してください。README にない実装詳細は各モジュール（src/kabusys/**）の docstring を参照してください。

--- 
以上。必要であれば README を英語版に翻訳したり、サンプル .env.example を追加したり、起動スクリプトの systemd / supervisor 用ユニット例を用意できます。どの内容を優先して追加しますか？