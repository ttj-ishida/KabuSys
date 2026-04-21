# KabuSys

日本株向け自動売買 / 研究基盤モジュール群

このリポジトリは、注文実行エンジン、監視機構、ファクター算出・研究ツール、AI によるニュースセンチメント評価などを含む日本株自動売買システムの一部コンポーネント群です。本 README ではプロジェクトの概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は以下の主要要素を含みます。

- Execution Engine：発注（実際のブローカー or ペーパートレード）を行うコンポーネント
- Monitoring：システム健全性、注文状況、リスク（ドローダウン・ポジション上限）を監視し、必要に応じて停止フラグ（kill.flag）を発行
- Portfolio Construction：銘柄選定・重み付け・ポジションサイズ計算の純粋関数群
- Research：DuckDB を用いたファクター計算・特徴量解析（モメンタム、バリュー、ボラティリティ等）
- AI（OpenAI）連携：ニュースセンチメントや市場レジーム判定（OpenAI API を利用）
- ツール群：.env 対話ウィザード、設定検証、Paper Trading 検証レポートなど

設計方針として、本番 DB と Paper Trading DB の分離、ルックアヘッドバイアス回避、外部 API エラーへのフォールトトレラントな対処が組み込まれています。

---

## 主な機能一覧

- 設定管理
  - .env の自動ロード / 対話式ウィザード（`kabusys.config_setup`）
  - 起動前の設定検証（`kabusys.validate_config`）
- 実行（Execution）
  - 本番（live）/ ペーパートレード（paper_trading）切替
  - Paper Trading 時は MockBrokerClient を使い DB を分離
- 監視（Monitoring）
  - CPU / メモリ / ディスク使用率、Execution プロセスの存否、データ鮮度を監視
  - トレードログ、リスクログ、ダッシュボードを SQLite に永続化
  - Kill Switch による停止フラグ（`data/kill.flag`）発行
  - 監視ループのポーリング間隔は環境変数で調整可能
- ポートフォリオ構築
  - 候補選定、等重・スコア加重、リスクベースの株数算出、セクター上限適用等
- 研究（Research）
  - DuckDB を用いたファクター算出（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）計測、統計サマリ
- AI（OpenAI）
  - ニュース記事を集約し LLM でセンチメント評価 → ai_scores に保存
  - マクロニュースと ETF MA200 を組み合わせた市場レジーム判定
- ユーティリティ
  - ロギング設定 / プロセス優先度設定 / PID / stop フラグ管理
  - Paper Trading 検証レポート生成ツール

---

## 前提 / 要件

- Python 3.10+
- 推奨パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定検証で YAML のパースを行う場合に必要）

（依存管理は pyproject.toml / requirements.txt 等で管理してください。）

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
   - 例: git clone ... && cd repo

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 例: pip install duckdb psutil openai PyYAML

4. .env の初期作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
     - ウィザードに従い J-Quants トークン、kabu API パスワード、DB パス、環境（KABUSYS_ENV）等を入力します。
   - 生成された `.env` は絶対に Git にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - 問題がある場合は表示されるエラー/警告に従って .env / config/*.yaml を修正してください。
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

6. データディレクトリの用意（必要に応じて）
   - デフォルトで使用されるパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - ログ: logs/
     - PID/フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag
   - これらは自動作成される場合もありますが、権限等の問題がある場合は事前に作成しておくと安全です。

---

## 環境変数（主なもの）

- KABUSYS_ENV
  - `development`（開発） / `paper_trading`（ペーパートレード） / `live`（本番）
  - paper_trading の場合、発注は MockBrokerClient を使用し DB を `PAPER_TRADING_SQLITE_PATH` に分離します
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（紙取引の約定モード）
  - 有効値: "instant" | "partial" | "never" | "reject"（デフォルト: "instant"）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（デフォルト: logs/）
- OPENAI_API_KEY（AI モジュールを利用する場合に必要）
- MONITOR_POLL_INTERVAL（監視ループのポーリング間隔（秒）。run_monitoring で使用。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（本番起動時に kill.flag を自動クリアするか。デフォルト 0）

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - Strict モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- Execution Engine を起動
  - python -m kabusys.run_execution
  - 挙動
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を接続します
    - 起動時に data/stop_requested.flag が存在すると起動を抑止します
    - 実行中は data/execution.pid に PID を書き込みます
    - data/stop_requested.flag が作成されるとスレッドを停止して終了します

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 挙動
    - ポーリングループで SystemMonitor.check_once() を定期実行（デフォルト 60 秒）
    - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可
    - 監視用 SQLite は環境にかかわらず本番用 sqlite_path（SQLITE_PATH）を使用します
    - data/stop_requested.flag を検知するとループを終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH を使用

- AI 関連（ニューススコア / レジーム判定）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは引数または OPENAI_API_KEY 環境変数で指定
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 同様に OPENAI_API_KEY が必要

注意: 上記の多くはパッケージ内部 API を直接呼ぶ形です。実運用ではそれらを呼び出すスクリプトやジョブを用意してください。

---

## 停止 / Kill Switch の挙動

- ExecutionEngine を安全に停止させたい場合:
  - `data/kill.flag` を監視コンポーネント（KillSwitch）により書き込むことで実行エンジンに停止シグナルを与える設計になっています（kill.flag は監視が検出して書き込む）。
- 手動停止用のフラグ:
  - `data/stop_requested.flag` を作成すると `run_execution` / `run_monitoring` のループは検出して停止します（主に開発用の強制停止フラグ）。
- `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアしますが、本番では危険なためデフォルトは `0` を推奨します。

---

## ロギング

- ログはデフォルトで標準出力（stdout）と日次ローテートされるファイル（logs/<app_name>.log）に出力されます。
- 設定:
  - LOG_LEVEL 環境変数でログレベルを指定（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR 環境変数でログ保存先を変更可能

ログ設定ユーティリティ: `kabusys.utils.logging_setup.setup_logging(app_name="execution")`

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要モジュールと配置の概観（src/kabusys 以下）です。実際のファイル数はこれ以外にも存在する前提です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成ツール
  - execution/               — 発注関連（Engine / OrderManager / BrokerFactory 等）
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に使用されるディレクトリ、デフォルト)
    - kabusys.duckdb
    - monitoring.db
    - paper_trading.db
    - execution.pid
    - kill.flag
    - stop_requested.flag
  - logs/ (デフォルトログ出力先)

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください。）

---

## よくある運用フロー（例）

1. `.env` を作成: python -m kabusys.config_setup
2. 設定を検証: python -m kabusys.validate_config
3. DuckDB / SQLite にデータを準備（prices_daily 等のテーブル）
4. Execution（または PaperTrading）を起動: python -m kabusys.run_execution
5. 別プロセスで Monitoring を起動: python -m kabusys.run_monitoring
6. 定期的に Paper Trading の検証レポートを作成: python -m kabusys.tools.paper_verification_report --from ... --to ...
7. AI 評価やレジーム判定はスケジュールジョブや手動で呼び出す（OPENAI_API_KEY 必須）

---

## 注意事項

- `.env` ファイルは機密情報（API トークン、パスワード等）を含むため、絶対にバージョン管理にコミットしないでください。
- 本番（KABUSYS_ENV=live）での実行は責任を伴います。validate_config の指摘や LINE 通知設定などを確認し、kill フラグの取り扱いに注意してください。
- OpenAI 等外部 API の使用にはレート制限・課金が発生します。API キーの管理・コスト管理に注意してください。
- DuckDB / SQLite のスキーマはコード中で参照されています。DB を手動で準備する場合はスキーマ整合を保ってください。

---

この README はコードベースの現状に基づく簡易ドキュメントです。より詳しい実装仕様や運用手順（デプロイ手順、cron / systemd ユニット例、バックアップ方針など）は別途整備することを推奨します。質問や追記したい項目があれば教えてください。