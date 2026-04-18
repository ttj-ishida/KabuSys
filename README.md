# KabuSys

日本株向け自動売買システムの主要コンポーネント群をまとめたリポジトリの README（日本語）。

この README は、提供されたコードベース（src/kabusys 以下）を元に、プロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成を記載しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するモジュール群のセットです。主な役割は以下の通りです：

- 実行エンジン（ExecutionEngine）による発注管理・注文実行（本番 / ペーパートレード対応）
- 監視（Monitoring）: システム状態、注文滞留、リスク（ドローダウン・ポジション上限）などの定期チェックとログ化
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定・セクター制約）
- リサーチ（ファクター計算、特徴量解析、IC計算 等） — DuckDB を使ったオンメモリ／SQLベース処理
- AI 支援機能：ニュースの NLP スコアリング（OpenAI）／市場レジーム判定
- CLI 補助ツール：.env ウィザード、設定検証、ペーパートレード検証レポート等
- ロギング・プロセス優先度などのユーティリティ

設計上のポイント：
- 環境変数 / .env による設定管理（Settings クラス）
- DuckDB（分析）と SQLite（監視/注文ログ）を併用
- 本番/ペーパートレードを分離（ペーパートレード時は専用 SQLite）
- OpenAI 呼び出しはリトライやバリデーションを備え、失敗時はフェイルセーフで続行

---

## 機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine 起動（KABUSYS_ENV により本番 / paper_trading を切替）
  - run_monitoring.py — SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL により間隔を調整）
- 設定管理
  - config.py — Settings クラス（.env 自動読み込みを含む）
  - config_setup.py — .env 作成・更新の対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
- 監視（monitoring）
  - monitoring_db.py — SQLite に対する永続化層（テーブル初期化・マイグレーション含む）
  - system_monitor.py / trade_monitor.py / risk_monitor.py / monitoring_engine.py / kill_switch.py / alert_manager 等
- Execution（execution）関連（発注/注文管理等）
  - ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等（エンジン起動・停止・PID/フラグ管理）
- Portfolio（portfolio）
  - portfolio_builder.py / position_sizing.py / risk_adjustment.py — 候補選定、重み計算、株数決定、セクターキャップ、レジーム乗数
- Research（research）
  - factor_research.py / feature_exploration.py — ファクター計算（momentum/value/volatility）、将来リターン、IC、統計サマリー
- AI（ai）
  - news_nlp.py — raw_news を OpenAI へ送り銘柄ごとのセンチメントを ai_scores に書き込み
  - regime_detector.py — ETF（1321）MA とマクロニュースで市場レジームを判定して保存
- Tools
  - tools/paper_verification_report.py — ペーパートレード DB を解析して PASS/FAIL レポート生成
- Utils
  - utils/logging_setup.py — 標準的なロガー設定（コンソール＋日次ローテーションファイル）
  - utils/process_priority.py — プラットフォームに依存しないプロセス優先度設定、CPU affinity

---

## セットアップ手順（開発環境）

前提：Python 3.10 以上（型ヒントの | 演算子等を使用）

1. リポジトリをクローンして作業ディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストール
   - 最低限の依存（本コードで参照される主要パッケージ）:
     - duckdb
     - psutil
     - openai
     - PyYAML（validate_config の YAML 検証を使う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   注: requirements.txt はこのリポジトリに含まれていないため、利用する機能に応じて必要パッケージを追加してください。

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（ルートに .env）。必要な環境変数の最小セット:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード時の DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能利用時）
     - LOG_LEVEL（DEBUG/INFO/…、任意）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いにできます:
     - python -m kabusys.validate_config --strict

6. ログディレクトリ
   - デフォルト: logs/
   - logging_setup が起動時にディレクトリを作成しますが、権限等で作成出来ない環境ではコンソールのみ出力になります。

---

## 使い方（代表的なコマンド）

- Execution Engine（本番 / ペーパートレード切替を KABUSYS_ENV で制御）
  - python -m kabusys.run_execution
  - 動作概要:
    - Settings を読み込み、SQLite / DuckDB に接続
    - KABUSYS_ENV=paper_trading の場合は PAPER_TRADING_SQLITE_PATH に接続し MockBrokerClient を使う（実践コードでは BrokerClientFactory が生成）
    - ExecutionEngine をスレッドで起動し、data/stop_requested.flag を検知すると停止

- Monitoring（SystemMonitor のポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は環境にかかわらず本番 sqlite_path を使用して監視ログを永続化

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告で exit(1)

- Paper Trading 検証レポート（SQLite DB を解析）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを直接指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI スコアリング / レジーム判定（プログラムから呼ぶ例）
  - news_nlp を使ってニューススコアを生成（DuckDB 接続が必要）
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key を None にすると OPENAI_API_KEY 環境変数を使う
  - レジーム判定（regime_detector）
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

備考:
- 停止フラグ・キルスイッチ:
  - data/stop_requested.flag: 実行ループの外部停止検知に使用（run_execution/run_monitoring で参照）
  - data/kill.flag: KillSwitch が書き込むことで ExecutionEngine を停止させる用途（Settings.kill_flag_path により位置指定可能）
- ログ:
  - デフォルトは logs/<app_name>.log（日次ローテート、30 日保持）と stdout 出力

---

## 主要環境変数（抜粋）

必須/重要なもの：
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）、デフォルト: development
- OPENAI_API_KEY — OpenAI API を使う機能で必要（news_nlp / regime_detector）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading 時に使用）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 本番で誤設定すると危険（詳細は validate_config の警告を確認）

validate_config.py に未設定チェックやパス存在チェック等のロジックが含まれます。運用前に検証を推奨します。

---

## ディレクトリ構成（src/kabusys の主要ファイル）

下記は本リポジトリ内の src/kabusys の主要ファイル／ディレクトリの構成イメージです。

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数/Settings
    - config_setup.py                — .env ウィザード（CLI）
    - validate_config.py             — 設定検証 CLI
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - run_monitoring.py              — Monitoring ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py — ペーパートレード検証レポート
    - portfolio/
      - __init__.py
      - portfolio_builder.py         — 候補選定、等重/スコア重み
      - position_sizing.py           — 株数算出、aggregate cap ロジック
      - risk_adjustment.py           — セクターキャップ、レジーム乗数
    - research/
      - __init__.py
      - factor_research.py           — Momentum/Value/Volatility 等
      - feature_exploration.py       — 将来リターン、IC、統計サマリー
    - ai/
      - __init__.py
      - news_nlp.py                  — ニュース NLP（OpenAI）→ ai_scores 書き込み
      - regime_detector.py           — 市場レジーム判定（MA + マクロニュース）
    - monitoring/
      - monitoring_db.py             — SQLite スキーマ・CRUD ヘルパ
      - system_monitor.py            — CPU/メモリ/ディスク/データ鮮度監視
      - risk_monitor.py              — ドローダウン・ポジション上限監視
      - kill_switch.py               — kill.flag 書き込みロジック
      - monitoring_engine.py         — 各 Monitor を束ねるエンジン
      - trade_monitor.py             — （注文滞留等の監視。実装参照）
      - alert_manager.py             — LINE 等への通知（実装参照）
    - execution/
      - execution_engine.py          — 実行エンジン本体
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - broker_factory.py
      - risk_manager.py
    - monitoring/ (上記)
    - utils/
      - __init__.py
      - logging_setup.py             — ログ設定ユーティリティ
      - process_priority.py          — プロセス優先度 / CPU affinity
    - data/                           — 実行時に参照する data ディレクトリ（logs は別）
      - (stop_requested.flag / kill.flag / *.db 等がここに配置される想定)
    - config/                         — YAML テンプレ等（system_config.yaml など、generate 用）

（注）一部ファイル・サブモジュールはここで省略しています。実装を詳しく見るには個別ファイルを参照してください。

---

## 運用上の注意

- KABUSYS_ENV を `live` にする前に validate_config で必須項目・警告を確認してください。本番では kill flag の自動クリア等が危険になる設定があるため注意が必要です。
- OpenAI API（news_nlp / regime_detector）を利用する場合、API 呼び出しはレート制御・リトライを行いますが、API 費用やレイテンシに注意してください。
- run_monitoring と run_execution は stop_requested.flag（data/stop_requested.flag）を監視して自己終了/停止するため、外部からの停止制御は flag ファイルを書き込むか実行プロセスにシグナルを送ってください。
- ログディレクトリのパーミッションやディスク容量に注意。ログローテーションは 30 日分保持します。
- DuckDB / SQLite のパスは .env / 環境変数で調整できます。ペーパートレードでは専用 SQLite を使い本番 DB と分離してください。

---

## 参考：よく使うコマンドまとめ

- .env を対話的に作る：
  - python -m kabusys.config_setup
- 設定検証：
  - python -m kabusys.validate_config
- 実行エンジン起動：
  - python -m kabusys.run_execution
- 監視ループ起動：
  - python -m kabusys.run_monitoring
- ペーパートレード検証レポート：
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
- Python REPL / スクリプト内で AI 機能呼び出し：
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

---

必要であれば、README に以下の追加情報も追記できます：
- 依存パッケージの完全な requirements.txt（生成して添付）
- 実行例（ログ出力例、monitoring DB のスキーマ説明）
- 各モジュールのより詳細な API 使用方法（関数引数・戻り値のサンプル）
- デプロイ手順（systemd / コンテナ化 など）

上のどれかを追記希望でしたら教えてください。