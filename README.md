# KabuSys

日本株向けの自動売買システム（ライブラリ/実行スクリプト群）。  
本リポジトリは、戦略の研究（ファクター計算・特徴量解析）、ポートフォリオ構築、発注実行（本番／ペーパートレード）、監視/アラート、LLM を用いたニュース解析・レジーム判定などのコンポーネントを含みます。

---

## プロジェクト概要

- DuckDB / SQLite をデータ層として使用し、価格データ・財務データ・ニュース・各種ログを永続化。
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定）やリスク制御ロジックを純粋関数群として提供。
- 発注（ExecutionEngine）は実運用とペーパートレードを切り替え可能（ペーパートレードは専用 SQLite に記録）。
- 監視システム（MonitoringEngine）によりプロセス生存、データ鮮度、滞留注文、約定異常、ドローダウン等を定期チェックし、必要に応じて Kill Switch（flag ファイル）で発注エンジンを停止。
- OpenAI を利用したニュースセンチメント解析（ai.news_nlp）やマクロニュースを用いた市場レジーム判定（ai.regime_detector）を実装。
- 各種 CLI / ユーティリティ（設定ウィザード、設定検証、ペーパートレード検証レポート等）を備える。

---

## 主な機能一覧

- 実行スクリプト
  - run_execution.py：ExecutionEngine 起動（本番 or paper_trading 切替）
  - run_monitoring.py：SystemMonitor ポーリング起動
- 設定管理
  - config_setup.py：.env を対話式に作成/更新するウィザード
  - validate_config.py：環境変数・config/*.yaml の事前検証 CLI
  - config.Settings：環境変数・パス管理（PAPER_FILL_MODE 等の検証含む）
- 監視
  - monitoring/monitoring_db.py：監視ログの SQLite テーブル初期化 / 永続化 API
  - monitoring/system_monitor.py：CPU/メモリ/ディスク・プロセス・データ鮮度監視
  - monitoring/trade_monitor.py：滞留注文・約定異常検出
  - monitoring/risk_monitor.py：ドローダウン・ポジション上限監視（Kill Switch トリガ）
  - monitoring/monitoring_engine.py：各 Monitor を束ねてポーリング（アラート通知連携ポイントあり）
  - monitoring/kill_switch.py：flag ファイルによる ExecutionEngine 停止機構
- 発注関連（execution パッケージ）
  - Broker クライアントファクトリ（MockBroker を含む）
  - OrderRepository / OrderManager / RiskManager / ExecutionEngine 等（コード参照）
- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定（select_candidates）、重み計算（等配分／スコア加重）
  - レジーム乗数、セクター集中排除（apply_sector_cap）
  - 株数決定・集約キャップ処理・単元丸め（calc_position_sizes）
- 研究ツール（research パッケージ）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC（Information Coefficient）や統計サマリ（feature_exploration）
- AI（ai パッケージ）
  - news_nlp.score_news：OpenAI を使ったニュースセンチメント算出と ai_scores への書き込み
  - regime_detector.score_regime：ETF MA とマクロニュースを合成した市場レジーム判定
- ユーティリティ
  - utils.process_priority：プロセス優先度 / CPU affinity 設定ユーティリティ
  - tools.paper_verification_report：ペーパートレード検証レポート生成

---

## 前提・依存

- Python 3.10+（ソースで X | Y 型アノテーション等を使用）
- 必要パッケージ（主なもの）
  - duckdb
  - psutil
  - openai (ai 機能を使う場合)
  - PyYAML（validate_config の YAML 検証を行う場合）
- データベース
  - デフォルト DuckDB: data/kabusys.duckdb
  - 監視 SQLite: data/monitoring.db
  - ペーパートレード SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）
- 注意
  - .env を絶対にリポジトリへコミットしないこと（config_setup でも警告あり）
  - OpenAI を使う機能は OPENAI_API_KEY が必要（環境変数 or 関数引数）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（例）
   - pip install duckdb psutil openai pyyaml

   ※ 実際の requirements.txt があればそれを使ってください:
   - pip install -r requirements.txt

4. 初期設定（.env 作成）
   - python -m kabusys.config_setup
     - 対話式ウィザードで J-Quants トークンや kabu API パスワード、DB パス等を入力します。
   - もしくは手動で .env を作り、必要な環境変数を設定してください。

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合は --strict を付けます。

6. データディレクトリ作成
   - mkdir -p data

---

## 環境変数（主要）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作モード
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading のとき、MockBrokerClient を使用し data/paper_trading.db に記録します（本番 DB と分離）

- DB パス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）

- その他
  - LOG_LEVEL（DEBUG|INFO|...）
  - OPENAI_API_KEY（ai 機能）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知）
  - PAPER_FILL_MODE（instant | partial | never | reject、デフォルト: instant）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。1=クリア、0=クリアしない）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒。デフォルト 60）

- テスト用
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env の読み込みをスキップします。

---

## 使い方（代表的なコマンド）

- 設定ウィザード（.env を作成／更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- 実行エンジン起動（本番 / paper_trading は KABUSYS_ENV に依存）
  - python -m kabusys.run_execution

  実行時の挙動ポイント：
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db にデータを記録します。
  - 起動直後に data/stop_requested.flag（または kill.flag の存在など）を検知した場合は起動しません。
  - 実行プロセスは実行時に PID ファイル（デフォルト data/execution.pid）を書きます。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（例: MONITOR_POLL_INTERVAL=120）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db

- AI 機能（プログラムから呼び出す）
  - kabusys.ai.score_news(duckdb_conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=...)

---

## 注意点 / 運用メモ

- ペーパートレード用 DB は本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH）。本番データの混入に注意。
- kill_switch: risk 条件（ドローダウン等）で data/kill.flag が書かれると ExecutionEngine に停止指示を送り得ます。
- run_monitoring/run_execution は起動時にプロセス優先度を set_process_priority("high") で上げようとします。権限不足や OS によりスキップされる場合があります。
- OpenAI を使う処理は API 呼び出し失敗時にフェイルセーフ（0.0 など）で続行する設計だが、API キーの漏洩に注意。
- .env 自動ロードはプロジェクトルート判定（.git または pyproject.toml）に基づき行われます。CI／テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings
  - config_setup.py — .env ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・集約キャップ
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — momentum / value / volatility ファクター算出
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA + マクロニュース）
  - monitoring/
    - monitoring_db.py — SQLite の監視テーブル初期化 + MonitoringDB API
    - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度の監視
    - trade_monitor.py — 滞留注文・約定異常の監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — flag ファイル書き込みロジック
    - monitoring_engine.py — 各 Monitor を束ねる
    - alert_manager.py — （未表示部分）アラート送信ロジック
  - execution/（発注関連コード群）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート

---

## サンプル .env（最低限の例）

例（.env に直接保存しないでください。必ず安全に管理してください）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

---

## 開発・テスト時のヒント

- 自動 .env 読み込みを無効化したい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- validate_config をまず実行して不足している環境変数や設定を把握することを推奨します。
- AI 関連機能はテスト時に _call_openai_api をモックする設計になっています（ユニットテストが容易）。

---

必要であれば、README に実際の requirements.txt、CI 手順、デプロイ手順（systemd / Docker）や各モジュールの詳細設計（関数一覧・引数説明）を追加で作成できます。どの情報を優先的に拡充しますか？