# KabuSys — 日本株自動売買システム

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリ群です。戦略・ポートフォリオ構築、発注（Execution）、監視（Monitoring）、リサーチ、AI ニューススコアリングなどのコンポーネントを含みます。

---

## プロジェクト概要

KabuSys は以下のような機能を持つモジュール化された自動売買システムです。

- 市場データ（DuckDB）を用いたファクター計算・リサーチ
- シグナル→ポートフォリオ構築→発注数量決定（position sizing）
- 発注エンジン（ExecutionEngine）とブローカークライアント（本番 / ペーパートレード分離）
- 実行・注文に対する監視（Monitoring）：プロセス稼働、注文滞留、ドローダウン等
- LLM（OpenAI）を使ったニュースのセンチメント集計・レジーム判定
- 簡易 CLI ユーティリティ（環境設定ウィザード、設定検証、ペーパートレード検証レポート等）

設計方針として「できるだけ副作用を抑え、ルックアヘッドバイアスを避ける」「フェイルセーフ（API失敗時に例外を投げずフォールバックする）」ことが各モジュールで意識されています。

---

## 主な機能一覧

- config
  - .env ファイルの自動読み込み（.env, .env.local、OS環境変数優先）
  - Settings クラスによる環境変数の取得・バリデーション
  - 環境設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- execution
  - ExecutionEngine（EngineConfig と run_session）
  - ブローカークライアントファクトリ（本番 / paper_trading 用に分離）
  - OrderRepository / OrderManager / RiskManager / Reconciler 等
  - ペーパートレード時は専用 SQLite（data/paper_trading.db）に記録
- monitoring
  - SystemMonitor（CPU/メモリ/ディスク、データ鮮度、PID チェック）
  - TradeMonitor（滞留注文、約定価格異常）
  - RiskMonitor（ドローダウン・ポジション上限の監視と dashboard 更新）
  - KillSwitch（条件に応じて data/kill.flag を書き込み ExecutionEngine 停止）
  - MonitoringEngine（複数 Monitor を束ねたポーリング）
  - SQLite ベースの監視 DB 層（monitoring_db）
- portfolio
  - 候補選定、等重/スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数
- research
  - ファクター計算（momentum, volatility, value）
  - 将来リターン / IC / 統計サマリー
  - zscore 正規化（kabusys.data.stats 経由）
- ai
  - news_nlp: raw_news を LLM へ送って銘柄別センチメント（ai_scores）を書き込み
  - regime_detector: ETF (1321) の MA とマクロニュースを使って market_regime を判定
  - OpenAI API（gpt-4o-mini 想定）での呼び出し・リトライ・レスポンス検証ロジック
- tools
  - paper_verification_report: ペーパートレード DB から期間レポートを生成

---

## セットアップ手順（開発 / 実行）

前提
- Python 3.9+（型ヒント等を利用しているため比較的新しい Python を推奨）
- 必要な外部パッケージ（下記参照）

1. リポジトリをチェックアウト、ワークディレクトリをプロジェクトルートに移動

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必須パッケージをインストール（例）
   - pip install duckdb psutil openai
   - （設定検証で YAML をパースしたい場合）pip install pyyaml

   （requirements.txt がある場合は pip install -r requirements.txt を推奨）

4. 初期環境変数ファイルを作成
   - 対話式ウィザード: python -m kabusys.config_setup
     - .env を生成します（Git へは絶対にコミットしないでください）
   - 手動で .env を作る場合は以下の最低限の環境変数を設定してください:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルトは development
     - OPENAI_API_KEY （AI 機能を使う場合）
     - （デフォルト DB パス）
       - DUCKDB_PATH=data/kabusys.duckdb
       - SQLITE_PATH=data/monitoring.db
       - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db（ペーパー用）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）

6. データディレクトリ作成（必要なら）
   - mkdir -p data

---

## 主要な環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API のパスワード

- 実行環境
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL

- データベース
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 用）

- ペーパートレード
  - PAPER_FILL_MODE — instant / partial / never / reject（デフォルト instant）

- PID / Kill Switch
  - PID_FILE_PATH — 実行エンジンが書く pid ファイル（デフォルト data/execution.pid）
  - KILL_FLAG_PATH — kill.flag のパス（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1"=する, デフォルト 0）

- Monitoring
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）

- OpenAI
  - OPENAI_API_KEY — OpenAI を使う機能（news_nlp, regime_detector）で必要

その他はコードの Settings クラスおよび validate_config を参照してください。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env の生成 / 更新）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（注文実行）
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存:
    - paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録（本番 DB と完全分離）
  - エンジン停止は data/stop_requested.flag の作成または KillSwitch による kill.flag の書き込みで制御
  - PID ファイルは data/execution.pid に書き込まれる（監視が存在する場合は SystemMonitor が PID を確認）

- Monitoring 起動（ポーリング監視）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）
  - 監視は Settings.sqlite_path（monitoring DB）と duckdb を使用します
  - 停止は data/stop_requested.flag を作成することで監視ループが終了

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルトのペーパートレード DB は data/paper_trading.db。--db で指定可能

- AI 関連（プログラム API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OPENAI_API_KEY 環境変数か引数で API キーを渡してください

---

## 停止 / Kill Switch の動作

- data/stop_requested.flag
  - run_execution / run_monitoring のループはこのファイルの有無をチェックします。作成すると安全にループを終了します（運用者がプロセス停止を要求するためのファイル）。
- data/kill.flag
  - KillSwitch（監視側）が条件を満たした場合に書き込まれるファイル。ExecutionEngine は起動時や定期チェックでこのファイルを見て停止処理を行う設計（設定により起動時自動クリアの動作を制御）。
- data/execution.pid
  - ExecutionEngine が起動時に自身の PID を書き込みます。SystemMonitor はこの PID を使ってプロセス生存確認を行います。古い PID ファイルは stale と見なされると削除され、リスクイベントとして記録されます。

---

## サンプル .env（最小例）

以下は開発 / テスト向けの最小例です（実運用では秘密情報を正しく保護してください）。

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

（config_setup を使うと対話形式で安全に作成できます）

---

## ディレクトリ構成（抜粋）

プロジェクトルート（src/kabusys 配下を参照）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 生成ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングスクリプト
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - execution/               — 発注関連コンポーネント（OrderRepository 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続層（監視ログテーブル定義）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/                    — 既定のデータディレクトリ（DB・フラグファイル等）
  - tools/
    - paper_verification_report.py

（実際のファイルは src/kabusys 以下に多数存在します。README は主なものを抜粋しています）

---

## 開発上の注意点 / 補足

- DB 分離:
  - paper_trading モードでは paper_trading 専用の SQLite を使い、本番 DB と完全に分離される設計です（安全上の配慮）。
- LLM / OpenAI:
  - news_nlp / regime_detector は OpenAI を使用します。API 呼び出しに失敗した場合はフォールバックする実装（例: macro_sentiment=0.0）になっているため、API の一時エラーでプロセスが止まることは基本的にありません。ただし API キーは必須（使用時）。
- 監視:
  - Monitoring はデフォルトで本番の sqlite_path（Settings.sqlite_path）を使います。MONITOR_POLL_INTERVAL でポーリング間隔を制御可能。
- テスト性:
  - 外部 API 呼び出し部分（OpenAI 呼び出しなど）はテスト時に差し替え可能な設計（関数呼び出しをラップ）になっています。
- ログ:
  - LOG_LEVEL で出力レベルを制御します。実行スクリプトは logging.basicConfig(level=logging.INFO) を設定していますが、Settings.log_level を利用してカスタム設定することもできます。

---

## よくある運用コマンド例

- .env を作る（対話式）
  - python -m kabusys.config_setup
- 設定チェック（起動前）
  - python -m kabusys.validate_config
- 実行エンジン起動（ペーパートレード）
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- 監視起動（別ターミナル）
  - python -m kabusys.run_monitoring
- 停止（安全停止要求）
  - touch data/stop_requested.flag
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードベースの主要な使い方・設定をまとめたものです。詳細な挙動や内部実装については各モジュール（src/kabusys/*）のドキュメント文字列（docstring）およびコメントを参照してください。必要であれば、セットアップ手順や運用ドキュメントを追加で作成します。