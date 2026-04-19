# KabuSys

日本株自動売買システムの内部ライブラリ群（プロトタイプ / 実装コア）。  
この README はリポジトリの主要コンポーネントの概要、セットアップ手順、起動方法、ディレクトリ構成をまとめたものです。

注意: 実運用で使用する前に必ず設定検証とテストを行ってください。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なコンポーネントをモジュール化したコードベースです。主な責務は次のとおりです。

- ExecutionEngine: 注文作成・送信・約定処理（本番 / ペーパートレードの切り替え対応）
- Monitoring: システム稼働監視、注文ログ監視、リスク監視、Kill Switch（停止フラグ）管理、アラート
- Portfolio construction: 候補選定、重み計算、ポジションサイジング、セクター制限、レジーム調整
- Research: ファクタ計算、将来リターンやIC計算、特徴量探索
- AI 統合: ニュース NLP によるセンチメントスコアリング（OpenAI API）
- ユーティリティ: 設定読み込み、ロギング設定、プロセス優先度制御、DB 初期化など
- ツール: Paper Trading 検証レポート生成、設定ウィザード、設定検証 CLI

---

## 主な機能一覧

- 環境設定管理 (.env の自動読み込み / 対話式ウィザード)
- 実行エンジン起動（本番 / ペーパートレード選択、MockBroker 対応）
- 監視プロセス（CPU/メモリ/ディスク、データ鮮度、Execution プロセス生存、リスクアラート）
- Kill Switch: 条件に応じて停止フラグを書き込み、Execution を停止
- リスク管理: ドローダウン・ポジション上限の検出とログ記録
- Portfolio construction: 候補選定、等金額 / スコア加重、risk-based 配分、単元丸め、aggregate cap 適用
- Research modules: momentum / volatility / value ファクター計算、forward returns、IC、統計サマリ
- AI モジュール: ニュースの銘柄別センチメント（OpenAI）、市場レジーム判定（MA + LLM）
- Paper Trading 検証レポート生成（稼働率・成功率・レイテンシなどを評価）

---

## 前提 / 必要環境

- Python 3.10+（型注釈に `X | Y` を使用）
- SQLite（標準ライブラリで使用）
- DuckDB Python パッケージ
- psutil（プロセス優先度・CPU affinity、システム指標取得）
- openai（OpenAI API クライアント）
- PyYAML（config/*.yaml の内容検証はオプション。インストールされていない場合は警告）

推奨: 仮想環境を作成して依存を管理してください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil openai pyyaml
```

（実プロジェクトでは `requirements.txt` を用意してください）

---

## 環境変数 / .env

アプリケーションは .env ファイル（プロジェクトルート）または OS 環境変数から設定を読み込みます。自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能です。

主要な環境変数（一部）:

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 任意 / デフォルトあり
  - KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO（DEBUG 等を指定可能）
  - KABU_API_BASE_URL: kabu ステーションのベース URL（デフォルト localhost）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（本番では必須にすべき）
  - OPENAI_API_KEY: OpenAI 呼び出し時に必要（AI モジュール使用時）
  - PAPER_FILL_MODE: ペーパートレードの約定挙動（instant / partial / never / reject）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）
  - MONITOR_POLL_INTERVAL: 監視プロセスのポーリング間隔（秒。run_monitoring から参照、デフォルト 60）

対話式で .env を作る:
```bash
python -m kabusys.config_setup
```

設定検証:
```bash
python -m kabusys.validate_config
python -m kabusys.validate_config --strict  # 警告も失敗扱い
```

---

## セットアップ手順（概要）

1. Python 3.10+ を用意し、仮想環境を作成して有効化
2. 必要パッケージをインストール:
   pip install duckdb psutil openai pyyaml
3. プロジェクトルートに `.env` を配置（`python -m kabusys.config_setup` を推奨）
4. DB 用ディレクトリを作成（`data/` と `logs/` は自動作成される場合がありますが確認）
5. 設定検証を実行:
   python -m kabusys.validate_config
6. 実行 / 監視プロセスを起動（後述）

---

## 使い方（起動例）

- ExecutionEngine を起動（本番 or ペーパーは KABUSYS_ENV に依存）:
  ```bash
  python -m kabusys.run_execution
  ```
  ペーパートレード時は `KABUSYS_ENV=paper_trading` を設定すると MockBrokerClient を使い、`data/paper_trading.db` に記録します。

- Monitoring を起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
  ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒、デフォルト 60）で変更できます。

- Paper Trading 検証レポート生成:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  デフォルトの DB パスは `PAPER_TRADING_SQLITE_PATH` 環境変数または `data/paper_trading.db`。

- AI 関連（プログラムから呼ぶ例）:
  - ニュースの銘柄別スコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="YOUR_OPENAI_KEY")
  - 市場レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="YOUR_OPENAI_KEY")

OpenAI を使う機能は `OPENAI_API_KEY` の設定が必須です（もしくは api_key 引数で渡す）。

---

## 重要な挙動・運用ノート

- run_monitoring は常に「本番」用の sqlite_path を使用します（監視 DB は環境に依存せず本番 DB パスに書き込む実装になっています）。
- run_execution は `KABUSYS_ENV=paper_trading` の場合、paper 用 DB（`PAPER_TRADING_SQLITE_PATH`）を使用して本番 DB と分離します。
- 停止フラグ:
  - 実行停止リクエスト: `data/stop_requested.flag`（run_* スクリプトが監視）
  - Kill Switch（Execution 停止）: `data/kill.flag`（KillSwitch が作成。`Settings.kill_flag_clear_on_start` に注意）
- ログ:
  - デフォルトは `logs/` に app_name ごとの日次ローテートログを作成（TimedRotatingFileHandler）。ログディレクトリ作成が失敗した場合はコンソール出力のみになります。
- プロセス優先度設定は psutil を使って行います。権限不足時は警告を出してスキップします。
- DuckDB / SQLite のスキーマ初期化やマイグレーションは `monitoring_db.init_monitoring_db` で実行されます（冪等）。
- LLM への API 呼び出しはリトライ、バックオフ、レスポンス検証を備えていますが、API 失敗時はフェイルセーフでスキップし、致命的な例外を投げない設計です。

---

## ディレクトリ構成（主要ファイルの説明）

リポジトリ内の主なパス（src/kabusys を基準）:

- kabusys/
  - __init__.py — パッケージ宣言
  - config.py — 環境変数 / Settings（.env 自動ロード含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py — 統一的なロギング設定
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py — CPU/メモリ/ディスク / データ鮮度 / pid チェック
    - trade_monitor.py — （監視関連のトラッキング、滞留注文検知など）※実装ファイルあり
    - risk_monitor.py — ドローダウン・ポジション数監視
    - kill_switch.py — Kill Switch（flag ファイル作成/削除）
    - monitoring_engine.py — 各 Monitor の束ね（ポーリングループ）
    - alert_manager.py — （アラート送信のラッパー。LINE 等）※実装ファイルあり
  - execution/
    - execution_engine.py — ExecutionEngine（起動 / run_session / stop 等）※実装ファイルあり
    - broker_factory.py — BrokerClient の生成（実ブローカ or Mock）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 発注周り
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数・aggregate cap・lot 切り捨て
    - risk_adjustment.py — セクター制限・レジーム補正
  - research/
    - factor_research.py — momentum/volatility/value 等のファクター計算
    - feature_exploration.py — forward returns / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュースセンチメント集約 + OpenAI 呼び出し + ai_scores への永続化
    - regime_detector.py — MA200 + LLM を組み合わせた市場レジーム判定

（注）上記に示したファイル群は主な実装ファイルであり、各サブモジュールにはさらに補助的な実装やテストが存在する可能性があります。

---

## よく使うコマンド一覧

- .env 作成ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Execution 起動:
  python -m kabusys.run_execution

- Monitoring 起動:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  または:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

---

## 開発メモ / 注意事項

- 本リポジトリは運用用途での利用を想定した設計が含まれています。特に本番環境（KABUSYS_ENV=live）では LINE 通知設定や kill flag の扱い、権限設定などを慎重に確認してください。
- OpenAI API を用いる機能は通信コストとレイテンシ、API 利用制限を考慮して運用してください。API キーは厳重に管理し、.env をリポジトリにコミットしないでください。
- DB スキーマの自動マイグレーションは限定的です。重要な変更を行う場合はバックアップ / migration を設計してください。
- 依存パッケージのバージョンや互換性（duckdb / openai / psutil 等）は運用環境に合わせて固定することを推奨します。

---

必要であれば、README に「セットアップ手順（詳細）、例の .env テンプレート、起動 & 運用フロー、よくあるトラブルと対処」を追記できます。どの項目を詳細化したいか教えてください。