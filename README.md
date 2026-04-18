# KabuSys

日本株自動売買システム (KabuSys) のリポジトリ向け README。  
この README ではプロジェクト概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

KabuSys は日本株の自動売買および関連するデータ処理／監視機能を提供するモジュール群です。以下のコンポーネントを含みます。

- ExecutionEngine：発注管理・リスク管理・OrderManager 等を組み合わせて実際の（あるいはペーパートレードの）発注を行うエンジン
- Monitoring：システム稼働状況、注文ログ、リスク（ドローダウン・ポジション上限）を定期監視し、必要に応じて Kill Switch を発動
- Portfolio：候補選定・重み付け・ポジションサイズ算出・セクター制限などのポートフォリオ構築ロジック（純関数）
- Research：DuckDB を用いたファクター計算・特徴量探索／IC 計算
- AI：ニュースの NLP によるセンチメント評価、マクロニュースと価格指標を組み合わせた市場レジーム判定（OpenAI API を利用可能）
- Tools：ペーパートレード検証レポート生成などの補助スクリプト
- 設定関連：.env の対話式ウィザード、起動前チェック（validate_config）

設計方針の一部：
- DuckDB / SQLite を用いたデータ保存・解析
- 本番とペーパートレードは DB を分離（ペーパートレード時は data/paper_trading.db を使用）
- 外部 API（OpenAI 等）は失敗してもフェイルセーフで動作継続するよう実装
- .env による環境変数管理をサポート（自動読み込み機能あり）

---

## 主な機能一覧

- 実行エンジン（ExecutionEngine）起動スクリプト（run_execution）
  - 実口座／ペーパートレード切替（KABUSYS_ENV）
  - リスク制御（max position, drawdown 等）
  - 発注ログ・ポジションの永続化（SQLite）
- 監視（Monitoring）起動スクリプト（run_monitoring）
  - CPU / メモリ / ディスク使用率、Execution プロセス生存確認、データ鮮度などを定期チェック
  - Kill Switch（条件該当時に data/kill.flag を書き込み Execution を停止）
  - 監視ログは SQLite に保存（monitoring_db）
- ポートフォリオ構築（選定・重み・ポジションサイズ計算）
- 研究モジュール（ファクター計算、将来リターン、IC 計算、統計サマリー）
- AI モジュール
  - ニュースのセンチメントスコアリング（OpenAI）
  - マクロニュース + ETF MA による市場レジーム判定（OpenAI）
- ツール
  - Paper Trading 検証レポート生成スクリプト（期間指定可能）
- 設定支援
  - 対話式 .env 作成ウィザード（config_setup）
  - 設定整合性チェック（validate_config）

---

## 動作要件（推奨）

- Python 3.10 以上（型注釈や代替構文を使用）
- 必要なパッケージ（主なもの）：
  - duckdb
  - psutil
  - openai (AI 機能利用時)
  - PyYAML（config YAML 検証を行う場合、任意）
- SQLite は標準ライブラリで使用可能

（プロジェクトに requirements.txt がある場合はそれを使用してください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境の作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install -r requirements.txt
   - もし requirements.txt がない場合は少なくとも以下を入れてください：
     - pip install duckdb psutil openai

4. 初期設定 (.env) の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは .env を生成・上書きします。必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を入力してください。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）になります。

6. データディレクトリの作成（必要なら）
   - デフォルトでは `data/`、`logs/` を使用します。ウィザードでパスを変更できます。

注意:
- 自動で .env を読み込む機能が有効（プロジェクトルートが検出できる場合）。無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 環境変数（主なもの）

（デフォルト値があるものは明記します）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API のパスワード

- 実行環境
  - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）

- データベース / ファイルパス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード時の SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — ExecutionEngine 用 PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch の flag パス（デフォルト: data/kill.flag）

- ログ
  - LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト: INFO）
  - LOG_DIR — ログ保存先ディレクトリ（デフォルト: logs/）

- AI / OpenAI
  - OPENAI_API_KEY — OpenAI API キー（AI 機能利用時に必要）

- Paper Trading / MockBroker
  - PAPER_FILL_MODE — "instant" | "partial" | "never" | "reject"（デフォルト: instant）

- 監視ポーリング間隔（monitoring 用）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）

- その他運用フラグ
  - KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか ("0" / "1")（デフォルト: 0）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを抑制（"1"）

---

## 使い方（基本コマンド）

- 対話式 .env 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告を失敗扱い）: python -m kabusys.validate_config --strict

- ExecutionEngine（実行エンジン）起動
  - 本番 / 開発 / ペーパートレードは KABUSYS_ENV に依存
  - python -m kabusys.run_execution
  - ペーパートレード時は KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録します。

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 注意: Monitoring は KABUSYS_ENV に関係なく本番用 sqlite_path（SQLITE_PATH）を使用します（運用上の意図に注意）

- 停止方法 / Kill Switch
  - ExecutionEngine の停止トリガー: `data/kill.flag` を書き込む（KillSwitch が検出）
  - run_execution/run_monitoring は `data/stop_requested.flag` の存在を検出するとループを抜けて終了します（運用用停止フラグ）
  - run_execution は `data/execution.pid` を PID ファイルとして使用

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（プログラム的に呼び出す例）
  - ニュース NLP（指定日でスコア生成）:
    - from kabusys.ai.news_nlp import score_news
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, datetime.date(2026, 4, 1), api_key="YOUR_OPENAI_KEY")
  - レジームスコア:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, datetime.date(2026, 4, 1), api_key="YOUR_OPENAI_KEY")
  - ※ OpenAI API キーは OPENAI_API_KEY 環境変数、または関数引数で指定可能

---

## 運用上の注意

- 本番 (KABUSYS_ENV=live) では特に LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）や KILL_FLAG_CLEAR_ON_START の値に注意してください。
- run_monitoring は常に本番用の SQLITE_PATH を参照します。テスト時に誤って本番 DB を破壊しないよう注意してください。
- OpenAI を使う機能は API 使用料が発生します。テスト時はモックや制限付きのキーを使用してください。
- ログディレクトリの作成に失敗した場合はコンソール出力のみで継続します（警告ログあり）。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要なモジュール構成（src/kabusys 配下を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings クラス、自動 .env 読込ロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト（エントリポイント）
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py       — ロギング共通設定
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite による監視ログ永続化（スキーマ初期化含む）
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - risk_monitor.py        — ドローダウン／ポジション上限監視
    - trade_monitor.py       — (注文監視ロジック)
    - monitoring_engine.py   — 各 Monitor を束ねる実行ループ
    - kill_switch.py         — kill.flag 制御（Execution 停止）
    - alert_manager.py       — (通知管理、LINE 等)
  - execution/
    - execution_engine.py    — ExecutionEngine 本体
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI）
  - data/                    — 実行時に使うファイル群（デフォルト）
    - monitoring.db (SQLITE_PATH デフォルト)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH デフォルト)
    - stop_requested.flag, kill.flag, execution.pid など

（実際のファイル構成はリポジトリを参照してください。その他のユーティリティやモジュールも存在します。）

---

## 開発・テスト

- 単体関数群（portfolio, research など）は純関数・副作用を持たないよう設計されており、ユニットテストが容易です。
- OpenAI への外部コール部分はモックしやすく設計されています（内部の _call_openai_api をテストで差し替え可能）。
- ローカルでの動作確認には KABUSYS_ENV=development を使用し、重要な環境変数はダミー値で構成してください（validate_config で警告／エラー確認）。

---

以上が README の要点です。必要に応じて README にサンプル .env のテンプレートや運用チェックリスト（起動順序、監視・発注の注意点等）を追記できます。追加で含めたい情報や、実際のコマンド例（systemd / supervisor 用のサービス定義等）があれば指定してください。