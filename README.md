# KabuSys

日本株向け自動売買システムのコアライブラリ群（ライブラリ兼 CLI / 起動スクリプト群）。  
この README はリポジトリの主要機能・セットアップ・実行方法・ディレクトリ構成を日本語でまとめたものです。

注意: 実際の運用前に必ず `.env` を作成し、`python -m kabusys.validate_config` で検証してください。

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群で構成されています。

- 市場データ / ファクター計算（DuckDB を利用）
- ポートフォリオ構築（候補選定・重み付け・数量算出）
- ExecutionEngine（発注管理・リスク管理・リコンシリエーション）
- 監視（System / Trade / Risk のポーリング、Kill Switch）
- AI モジュール（ニュースセンチメント・市場レジーム判定 via OpenAI）
- 各種ユーティリティ、CLI ツール（.env ウィザード、設定検証、ペーパートレード検証レポート 等）

設計方針として、実運用での安全性（フェイルセーフ、冪等性、ルックアヘッドバイアス回避）が重視されています。

---

## 主な機能一覧

- 環境設定ウィザード（.env の対話的作成/更新）
  - python -m kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml の事前チェック）
  - python -m kabusys.validate_config [--strict]
- ExecutionEngine 起動スクリプト
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 専用 DB に記録
- Monitoring 起動スクリプト（SystemMonitor のポーリングループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で間隔を上書き（デフォルト 60 秒）
  - Monitoring は環境に関わらず本番用 sqlite_path を利用して監視ログを記録
- 監視エンジン（MonitoringEngine）：System / Trade / Risk の統合およびアラート/kill 判定
- Kill Switch：kill.flag による ExecutionEngine 停止
- Paper Trading 検証レポート出力ツール
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- AI モジュール
  - kabusys.ai.news_nlp.score_news(...) — OpenAI を使ったニュースセンチメント算出（ai_scoresに書き込み）
  - kabusys.ai.regime_detector.score_regime(...) — マクロ + ETF MA200 で市場レジーム判定
  - いずれも OpenAI API キー（OPENAI_API_KEY）が必要
- 研究/リサーチ用ユーティリティ（ファクター計算、IC 計算、統計サマリー 等）

---

## 必要要件（想定）

（requirements.txt がある場合はそれを利用してください。以下は主な依存パッケージ）

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能利用時)
- PyYAML（config/*.yaml の内容検証は optional）

インストール例:
- python -m venv .venv
- source .venv/bin/activate
- pip install -r requirements.txt
（requirements.txt がない場合は個別に pip install duckdb psutil openai PyYAML を行ってください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成して依存をインストール
3. .env の作成
   - 対話的ウィザード: python -m kabusys.config_setup
   - ウィザードで作成した `.env` は決して Git にコミットしないでください
4. 設定検証:
   - python -m kabusys.validate_config
   - 問題がある場合はメッセージに従い修正。--strict を付けると警告もエラー扱いになります
5. DB ディレクトリ（data/ 等）が必要であれば作成（多くの起動スクリプトは自動で親ディレクトリを作成しますが、権限に注意）

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API パスワード

重要（デフォルトあり）:
- KABUSYS_ENV — execution 動作モード: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、発注は MockBrokerClient となりデータは専用 DB に記録
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（monitoring.db）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレード時の約定動作: instant | partial | never | reject（デフォルト: instant）
- OPENAI_API_KEY — OpenAI を使うモジュールで必要
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0。本番は 0 推奨）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

監視 / PID / Stop フラグ:
- PID ファイル: data/execution.pid（Settings.pid_file_path で上書き可能）
- Kill flag: data/kill.flag（Settings.kill_flag_path）
- run_* スクリプトの停止フラグ: data/stop_requested.flag（存在を検知してループを終了）

---

## 実行方法（代表例）

- 環境変数を読み込んだ後、各スクリプトを実行します。

1) .env を作成（ウィザード）
   - python -m kabusys.config_setup

2) 設定検証
   - python -m kabusys.validate_config
   - 厳密チェック：python -m kabusys.validate_config --strict

3) ExecutionEngine 起動
   - python -m kabusys.run_execution
   - 注意:
     - 起動時にプロセス優先度を "high" に設定します（set_process_priority）
     - KABUSYS_ENV=paper_trading のときは PAPER_TRADING_SQLITE_PATH を使い、本番 DB と分離します
     - data/stop_requested.flag が既存なら起動しません
     - 停止は data/stop_requested.flag を作成するか、ExecutionEngine 側の kill.flag によって停止します

4) Monitoring 起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60）
   - Monitoring は環境に関係なく本番用 Settings.sqlite_path を監視 DB として使用します

5) Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db で DB パスを明示できます（デフォルト: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

6) AI / 研究系の関数を直接呼ぶ（スクリプト／REPL）
   - 例: from kabusys.ai.news_nlp import score_news
     - score_news(conn, target_date, api_key=...) は OpenAI API キーが必要
   - regime 判定: from kabusys.ai.regime_detector import score_regime

ログレベルは .env の LOG_LEVEL または Settings.log_level で制御できます。

---

## 停止 / Kill Switch の取り扱い

- 手動でエンジンや監視ループを止めたい場合:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のポーリングループが検知して終了します
- Kill Switch（自動停止）:
  - リスク監視で重大な条件（例: ドローダウン超過、ポジション上限超過）が満たされた場合、kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）を書き込み、ExecutionEngine の停止を誘導します
  - 本番環境では KILL_FLAG_CLEAR_ON_START=0 を推奨（起動時自動クリア禁止）

---

## 開発 / テスト向けポイント

- 多くのモジュールは副作用を抑え、DB 書き込みや外部 API 呼び出しは明示的です。関数単位でユニットテストがしやすい設計になっています。
- AI 関連は API 呼び出し部分を独立させてあり、テスト時は該当関数を patch して外部通信をモックできます（例: unittest.mock.patch）。
- .env 自動読み込みは Settings モジュールがプロジェクトルートを検出して行います。テスト時に自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

（ルートは src/kabusys 以下を想定）

- src/kabusys/__init__.py
  - パッケージ定義、バージョン情報

- src/kabusys/config.py
  - Settings クラス：環境変数読み込み・検証・デフォルト値

- src/kabusys/config_setup.py
  - .env 対話ウィザード

- src/kabusys/validate_config.py
  - 設定検証 CLI

- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト（PID 管理、stop フラグ監視、paper_trading 分離）

- src/kabusys/run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 対応）

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite ベースの監視ログ層（初期化・CRUD）
  - system_monitor.py — システム状態 / データ鮮度チェック
  - trade_monitor.py — 注文滞留・約定異常チェック
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の書き込み／管理
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - alert_manager.py — （アラート送信管理: 実装はファイル中に続きがある想定）

- src/kabusys/execution/
  - ExecutionEngine / OrderManager / BrokerFactory / Reconciler / RiskManager 等（起動と発注管理に関係）

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数算出・スケールダウンロジック
  - risk_adjustment.py — セクター上限・レジーム乗数

- src/kabusys/research/
  - factor_research.py — モメンタム/ボラ/バリュー等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリー

- src/kabusys/ai/
  - news_nlp.py — ニュースセンチメント（OpenAI）スコアリング
  - regime_detector.py — マクロ + MA200 合成によるレジーム判定

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading の検証レポート出力

- src/kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity のユーティリティ

- data/
  - デフォルトで生成される DB / flag / pid ファイルの格納場所（例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag, data/stop_requested.flag）

---

## 追加メモ / 運用上の注意

- Monitoring は監視 DB に対して書き込みを行います。Monitoring をテスト実行する場合は事前にバックアップを取るか、別の sqlite_path を指定してください。
- Paper Trading は本番 DB と分離されるよう設計されていますが、環境変数の設定ミスで上書きしないよう注意してください。
- OpenAI を利用する機能は API 利用料金が発生します。バッチサイズやリトライ・バックオフの挙動は実装済みですが、運用時はコストとレート制限に注意してください。
- ログとアラート連携（LINE 等）は設定次第で有効化されます。LINE の token / user id は .env に設定してください。

---

必要であれば README に含める具体的なコマンド例や systemd サービス定義、運用チェックリスト（起動順序、監視ポリシーなど）も追記できます。どの内容を詳しく書きたいか指示してください。