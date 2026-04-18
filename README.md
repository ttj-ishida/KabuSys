# KabuSys

日本株自動売買システム用ライブラリ / 実行スクリプト群

このリポジトリは、注文実行エンジン・監視・ファクター計算・ポートフォリオ構築・AIによるニュース評価などを包含する自動売買システムのコンポーネント群です。ライブラリ部分は pure-Python の関数群で構成され、起動用スクリプトは CLI/デーモン的に実行して利用します。

---

## プロジェクト概要

- 注文実行（ExecutionEngine）: ブローカークライアントを通じて発注／注文管理を行う。
- 監視（Monitoring）: システム資源・プロセス・注文状況・リスク指標を定期ポーリングしてログ／アラート／Kill Switch を管理。
- ポートフォリオ構築: 候補選定、重み付け、ポジションサイズ計算、セクター制限などの純関数群。
- リサーチ: DuckDB 上の時系列データからファクター（モメンタム／バリュー／ボラティリティ等）を計算・評価。
- AI モジュール: OpenAI を用いたニュースのセンチメントスコアリングと市場レジーム判定。
- ツール: ペーパートレード検証レポート生成などのユーティリティスクリプト。

---

## 主な機能一覧

- run_execution.py — ExecutionEngine を起動。KABUSYS_ENV に応じて本番／ペーパーDBを分離。
- run_monitoring.py — SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔調整可）。
- config_setup.py — .env を対話式に生成／更新するウィザード。
- validate_config.py — .env および config/*.yaml の整合性チェック CLI（--strict オプション有）。
- tools/paper_verification_report.py — ペーパートレード履歴から検証レポートを作成。
- portfolio/* — 候補選定、重み計算、ポジション寸法、リスク調整ロジック（純関数）。
- research/* — DuckDB を用いたファクター計算・IC 等の研究ユーティリティ。
- ai/* — OpenAI を利用するニュース NLP とレジーム判定ロジック。
- monitoring/* — MonitoringDB（SQLite）、各種モニタ（System/Trade/Risk）、KillSwitch、MonitoringEngine。
- utils/* — ロギング設定、プロセス優先度・CPU affinity 設定などのユーティリティ。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - 任意（YAML 検証用）: pip install pyyaml

   （プロジェクト配布で requirements.txt がある場合はそれを利用してください）

4. 初期設定（.env の作成）
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または .env.example を参考に .env を作成して環境変数を設定してください。

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告もFAILとして扱う場合: python -m kabusys.validate_config --strict

注意:
- 自動で .env をロードする仕組みが組み込まれています（プロジェクトルートに .env / .env.local がある場合）。テスト等で自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数（主なもの）

必須（最低限）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

一般的／オプション:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: アラート通知（任意）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時必須）
- PAPER_FILL_MODE: instant|partial|never|reject（Paper Trading の注文充填挙動）

実行スクリプト固有:
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（"1" で有効）

---

## 使い方（コマンド例）

- 環境作成・確認
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録されます。本番 DB と完全に分離されます。

- 監視プロセスを起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は Settings.sqlite_path（通常 data/monitoring.db）を使用します（KABUSYS_ENV に依らず本番 sqlite_path を使う設計）。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db /path/to/paper_trading.db または環境変数 PAPER_TRADING_SQLITE_PATH を利用

- AI モジュールの呼び出し（ライブラリ利用）
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

ログ:
- デフォルトログディレクトリ: logs/
- setup_logging(app_name="execution") により logs/execution.log 等が生成されます。

停止・Kill Switch:
- ExecutionEngine を停止したい場合は data/kill.flag に理由文字列を書き込むか、KillSwitch API を通して生成してください。
- run_monitoring は data/stop_requested.flag を検知するとループを終了します（同様に run_execution でも stop リクエストを検出して停止します）。

---

## 重要な実装・運用上ノート

- run_monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（通常本番の monitoring.db）を使用するようになっています。監視 DB を切り替えたい場合は Settings を調整してください。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用します。本番 DB と完全分離される設計です。
- process_priority: 起動時に優先度を "high" にセットするコードが組み込まれています（psutil に依存）。権限不足や未対応 OS では警告を出してスキップします。
- OpenAI を利用するモジュール（news_nlp / regime_detector）は API のリトライ・パースチェック・フェイルセーフ（失敗時は中立値で継続）を組み込んであります。
- DuckDB 接続はリサーチ・AI モジュールなどで使用します。prices_daily / raw_financials / raw_news 等のテーブルを前提としています。
- monitoring の DB スキーマ（monitoring_db.init_monitoring_db）は冪等で作成／マイグレーションロジックを含みます。

---

## ディレクトリ構成（src/kabusys の主なファイルと役割）

- __init__.py
  - パッケージ定義（__version__, __all__）

- config.py
  - Settings クラス: 環境変数の取得・検証・デフォルト値管理
  - 自動 .env ロード機能

- config_setup.py
  - .env の対話式作成ウィザード

- validate_config.py
  - 起動前設定検証 CLI（.env と config/*.yaml の検査）

- run_execution.py
  - ExecutionEngine 起動エントリポイント（PID ファイル / stop flag の扱い）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL を参照）

- utils/
  - logging_setup.py : 統一的なログハンドリング（stdout + 日次ローテートファイル）
  - process_priority.py : プロセス優先度・CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py : SQLite スキーマ作成と永続化 API（MonitoringDB クラス）
  - system_monitor.py : CPU/メモリ/Disk/プロセス/データ鮮度のチェック
  - trade_monitor.py : （存在）発注ログの監視（滞留注文、約定異常など）
  - risk_monitor.py : ドローダウン・ポジション上限のチェック
  - kill_switch.py : data/kill.flag の生成・評価
  - monitoring_engine.py : 各 Monitor を束ねてポーリング・アラート送信

- execution/
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等（起動時に組み立てられる）

- portfolio/
  - portfolio_builder.py : 候補選定・重み付け
  - position_sizing.py : 株数決定・単元丸め・投下資金スケール
  - risk_adjustment.py : セクターキャップ、レジーム乗数

- research/
  - factor_research.py : モメンタム/ボラティリティ/バリュー等の計算
  - feature_exploration.py : 将来リターン・IC・統計サマリ等

- ai/
  - news_nlp.py : raw_news を集約して OpenAI へ問い合わせ、ai_scores を更新
  - regime_detector.py : ETF の MA 乖離 + マクロニュースから市場レジームを判定

- tools/
  - paper_verification_report.py : ペーパートレード DB からパフォーマンス／信頼性の検証レポート生成

- data/
  - 実行時に使用するファイル（例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag, data/stop_requested.flag）

---

## よく使うコマンド（まとめ）

- .env 作成（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution

- 監視起動
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- ペーパートレード検証
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 補足・運用上の注意

- .env は決してリポジトリにコミットしないでください（config_setup.py のヘッダにも注意書きがあります）。
- 本番環境（KABUSYS_ENV=live）では LINE 通知や Kill Switch 設定を十分に確認してください（validate_config の live 用ガードを参照）。
- OpenAI API の利用はコストがかかるため、本番では API キー管理／レート制御に注意してください。
- ログ・DB のパスは Settings（環境変数）で変更できます。コンテナ化／デプロイ環境に合わせて調整してください。

---

何か追加したい項目（例: サンプル .env, Docker 実行例, CI ワークフローなど）があればお知らせください。README をそれに合わせて拡張します。