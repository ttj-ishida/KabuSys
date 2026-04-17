# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買・研究・監視を行うためのコンポーネント群を含みます。  
以下はこのコードベースの概要、機能、セットアップ手順、基本的な使い方、ディレクトリ構成です。

注意: README はコード内の docstring / コメントをもとに作成しています。実運用前に必ず .env を適切に設定し、`python -m kabusys.validate_config` で検証してください。

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュールで構成されたシステムです。

- 発注エンジン（ExecutionEngine）: 発注・リスク管理・約定の取り扱い
- 監視（Monitoring）: システム状態、注文滞留、リスク指標のポーリング・アラート
- ポートフォリオ構築（Portfolio）: 銘柄選定・重み算出・ポジションサイズ決定
- 研究（Research）: ファクター計算・特徴量探索
- AI 補助（AI）: ニュースのセンチメント解析や市場レジーム判定（OpenAI 利用）
- ユーティリティ / ツール: 設定ウィザード・設定検証・ペーパートレード検証レポート等

設計方針の特徴:
- 環境変数 / .env による設定管理
- Paper trading（ペーパートレード）と live（本番）を明確に分離
- DuckDB（分析用）と SQLite（監視・発注ログ）を使用
- LLM 呼び出しは堅牢化（リトライ・バリデーション・フェイルセーフ）

---

## 主な機能一覧

- 環境設定ウィザード（.env 生成 / 更新）
  - `python -m kabusys.config_setup`
- 設定検証 CLI（.env と config/*.yaml の事前検査）
  - `python -m kabusys.validate_config [--strict]`
- ExecutionEngine 起動スクリプト（本番 / ペーパートレード対応）
  - `python -m kabusys.run_execution`
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い DB を分離
- SystemMonitor（プロセス生存、CPU/メモリ/ディスク、データ鮮度チェック）
  - `python -m kabusys.run_monitoring`
- MonitoringEngine（複数モニタを束ねて周期実行、KillSwitch 判定、アラート通知）
- RiskMonitor / TradeMonitor（ドローダウン、ポジション上限、滞留注文、約定異常検出）
- AI モジュール
  - ニュース NLP（OpenAI で銘柄毎センチメント算出）
  - 市場レジーム判定（ETF MA とマクロニュースの LLM 判定の合成）
- 研究モジュール（ファクター計算、将来リターン、IC など）
- ポートフォリオ構築（候補選定、等配分/スコア配分、リスクベースの発注数決定）
- ツール: Paper Trading 検証レポート生成
  - `python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]`

---

## 環境変数（重要なもの）

必須（最低限設定が必要）
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード

運用に影響する主な変数
- KABUSYS_ENV — 実行環境: `development` / `paper_trading` / `live`（デフォルト: development）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール利用時）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視）DB パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレード時の約定振る舞い（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH — 実行制御用ファイル（デフォルト: data/execution.pid / data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 実行時に kill.flag を自動クリアするか（1 = true、デフォルト: 0）

自動 .env 読み込みはプロジェクトルートの .env / .env.local を参照します。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（ローカル開発向け）

1. Python バージョンを用意
   - 本リポジトリは型注釈や新構文を使用しているため Python 3.10+ を想定しています。

2. 依存パッケージをインストール
   - 必須パッケージ（例）:
     - duckdb
     - psutil
     - openai
     - pyyaml（設定ファイル検証に利用、任意）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （実プロジェクトでは requirements.txt / poetry を使う想定です）

3. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 手動で .env を作る場合は .env.example を参考にし、必須変数を設定してください。

4. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば表示されるエラー/警告を修正してください。
   - 本番向け厳格チェック:
     - python -m kabusys.validate_config --strict

5. データディレクトリの準備（任意）
   - デフォルトの DB パス（data/）が存在しない場合は自動で作成される機能もありますが、事前に作成しておくと良いです。
     - mkdir -p data

6. DB 初期化
   - 監視用 SQLite のテーブルは run_monitoring / run_execution が起動時に `init_monitoring_db` を呼び出して冪等に作成します。明示的な初期化は不要です。

---

## 使い方（基本コマンド）

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（実注文 or ペーパートレード）
  - python -m kabusys.run_execution
  - ペーパートレードにする場合:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag の存在をチェックします。停止要求はファイルを作成するなどで行えます（実行側は stop フラグを検出して停止）。

- Monitoring 起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを明示する:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- Kill Switch / 停止制御
  - KillSwitch は data/kill.flag を作成することで ExecutionEngine に停止シグナルを送ります（KillSwitch の条件が満たされたときに自動で書き込まれます）。
  - ExecutionEngine 側は起動時に kill.flag の有無や clear-on-start 設定を確認します。

ログの出力は基本的に標準出力/標準エラーに INFO レベルで流れます。運用時は監視ツールや systemd などでログ・プロセス管理を行ってください。

---

## 停止・制御ファイル

- data/stop_requested.flag
  - run_monitoring, run_execution などがループ停止判定で読んでいる停止フラグ（存在するとループを終える）
- data/kill.flag
  - KillSwitch が作成する停止フラグ（ExecutionEngine 停止のトリガー）
- data/execution.pid
  - ExecutionEngine が書き込む PID ファイル（SystemMonitor がプロセス生存確認に使用）

---

## トラブルシューティング（よくある注意点）

- OpenAI API を使うモジュールは OPENAI_API_KEY が必須。未設定だと ValueError になります（score_regime/score_news 等）。
- Paper trading の DB は本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- 自動 .env 読み込みを止めたいときは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してからプロセスを起動してください（テストで便利）。
- run_monitoring の MONITOR_POLL_INTERVAL は 1 以上の整数を指定してください。不正な値はデフォルト 60 秒にフォールバックします。
- psutil によりプロセス優先度や CPU affinity の設定を行いますが、アクセス権限がない環境では警告が出て設定はスキップされます。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                 — 環境変数 / 設定取得ユーティリティ
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

サブパッケージ（主なモジュール）
- ai/
  - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py      — 市場レジーム判定（MA + マクロニュース）
- monitoring/
  - monitoring_db.py        — SQLite 永続化レイヤ（監視ログ）
  - monitoring_engine.py    — 各 Monitor を束ねるエンジン
  - system_monitor.py       — システム・データ鮮度監視
  - trade_monitor.py        — 注文滞留・約定異常監視
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - kill_switch.py          — Kill Switch 実装（flag ファイル書込）
  - alert_manager.py        — （アラート送信の抽象層、実装は別ファイル）
- portfolio/
  - portfolio_builder.py    — 候補選定 / 重み計算
  - position_sizing.py      — 発注株数決定 / 集約上限処理
  - risk_adjustment.py      — セクター制限 / レジーム乗数
- research/
  - factor_research.py      — Momentum / Value / Volatility 計算
  - feature_exploration.py  — 将来リターン / IC / 統計サマリー
- execution/
  - (Execution 関連のモジュール群: broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager, order_record など)
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
- data/                    — デフォルトの DB 等（リポジトリに含めないことを推奨）

（実際のファイルは src/kabusys 以下に分散しています。上記は主要なものを抜粋）

---

## 開発・寄稿時の注意

- .env は絶対に Git にコミットしないでください。
- DuckDB / SQLite のスキーマはマイグレーションロジックを一部内包しています（例: monitoring_db のカラム追加）。DB の互換性に留意してください。
- AI（OpenAI）呼び出し部分は外部 API に依存するためテスト時はモック化することを推奨します（コード内でも明示的に patch しやすい作りになっています）。
- 実トレードを行う場合は KABUSYS_ENV=live を設定し、LINE 等の通知設定や kill flag の運用を十分に検討してください。

---

## 参考コマンドまとめ

- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- ExecutionEngine 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper トレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要があれば、README にチュートリアル（例: 初回起動のハンズオン手順）、設定例（.env.example の内容）、または systemd / Supervisor 用のユニットファイル例などを追記できます。追加で欲しい情報があれば教えてください。