# KabuSys

日本株自動売買システムのリポジトリ（パッケージ名: `kabusys`）。  
この README は提供されたコードベースに基づき、プロジェクト概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を目的とした内部ライブラリ兼実行スクリプト群です。  
主に以下の責務を持つモジュール群で構成されています。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理を行う
- 監視システム（Monitoring）: システム稼働状態・注文状況・リスクをポーリング監視し、必要に応じてアラートや Kill Switch を発動する
- リサーチ（Research）: DuckDB 上の時系列データからファクター計算・解析を行う
- AI モジュール（AI）: OpenAI を用いたニュース NLP / レジーム判定
- ポートフォリオ構築ユーティリティ: 候補選定、重み計算、ポジションサイズ計算、セクター制限 等
- 各種 CLI ユーティリティ: .env 設定ウィザード、設定検証、レポート生成など

設計方針の一例:
- 本番 DB とペーパートレード DB を明確に分離
- ルックアヘッドバイアス対策（日時参照の扱いに注意）
- フェイルセーフ（API 失敗時は安全側のフォールバック）
- DuckDB + SQLite を組み合わせたデータ管理

---

## 主な機能一覧

- Execution
  - ブローカークライアント抽象化（実ブローカー / MockBroker の切り替え）
  - 注文管理、リスク管理（上限・利用率・ドローダウン等）
  - 発注ログの永続化（SQLite / DuckDB）
- Monitoring
  - SystemMonitor: CPU/メモリ/Disk、プロセス生存、データ鮮度の監視
  - TradeMonitor: 注文滞留・約定異常などの検出（trade_logs）
  - RiskMonitor: ドローダウン、ポジション上限監視とアラート生成
  - KillSwitch: リスクトリガー時に `data/kill.flag` を書き込み、エンジン停止を要求
  - MonitoringEngine: 上記モジュールの統合ポーリング
- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 将来リターン計算、IC（情報係数）計算、統計サマリー
- AI
  - news_nlp: ニュース記事を集約して OpenAI でセンチメント採点、ai_scores テーブルへ保存
  - regime_detector: ETF の MA とマクロニュースから市場レジーム判定
- ユーティリティ
  - 環境設定ウィザード（`.env` 作成補助）
  - 設定検証 CLI（.env と config/*.yaml の事前チェック）
  - Paper Trading 検証レポート生成スクリプト

---

## 前提条件 / 推奨環境

- Python 3.10+
  - 型アノテーション（`X | Y`）を使用しているため 3.10 以上を推奨
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（`validate_config` の YAML 構文チェックに使用）
- SQLite は標準ライブラリで提供されます

requirements.txt がない場合は次のようにインストールしてください（例）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンし、venv を作成して依存パッケージをインストールする。

2. `.env` の作成
   - 対話式ウィザードを使って初期 `.env` を生成できます:

     ```bash
     python -m kabusys.config_setup
     ```

   - もしくはリポジトリ内の `.env.example`（存在する場合）を参考に `.env` を作成してください。

3. 設定検証（任意）
   - `.env` と `config/*.yaml` の基本チェック:

     ```bash
     python -m kabusys.validate_config
     # 警告を FAIL 扱いにしたい場合
     python -m kabusys.validate_config --strict
     ```

4. DB ファイルのパス、LOG_DIR、PID ファイルなどは `.env` で設定できます（下記「環境変数」を参照）。

5. OpenAI を利用する機能を使う場合は環境変数 `OPENAI_API_KEY` を設定してください（API を直接引数で渡すことも可能）。

---

## 主要な環境変数

- 必須（最低限）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境 / 動作制御
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
  - KILL_FLAG_CLEAR_ON_START: 0 | 1（本番では 0 推奨）

- データベース / ファイルパス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）

- Paper trading
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- OpenAI
  - OPENAI_API_KEY（news_nlp / regime_detector で使用）

- 監視間隔（Monitoring スクリプト専用）
  - MONITOR_POLL_INTERVAL（秒。デフォルト 60 秒）

- 自動 .env 読み込みの無効化
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（実行コマンド）

各スクリプトはパッケージモジュールとして起動可能です。例:

- 実行エンジン（ExecutionEngine）の起動:

  ```bash
  python -m kabusys.run_execution
  ```

  動作:
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、`data/paper_trading.db`（`PAPER_TRADING_SQLITE_PATH`）へ記録します。実 DB と分離されます。
  - 起動時に `data/stop_requested.flag` が存在すると起動を中止します。
  - 停止は `data/stop_requested.flag` を作成するか、ExecutionEngine の仕組みによる停止（Kill Switch 等）で行われます。

- 監視ループの起動:

  ```bash
  python -m kabusys.run_monitoring
  ```

  オプション / 環境変数:
  - MONITOR_POLL_INTERVAL=30 などでポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は環境にかかわらず本番の `SQLITE_PATH` を使用します（監視データを一元管理するため）。

- 設定ウィザード（.env 作成）:

  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証（事前チェック）:

  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート生成:

  ```bash
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 関連、Research、Portfolio 機能はライブラリ API として利用できます（例: スクリプトや別モジュールから呼び出す）。

---

## 実行時の停止 / フラグ

- run_monitoring.py / run_execution.py はプロジェクトルートの `data/stop_requested.flag` を監視しています。ファイルが存在すると監視ループや実行エンジンは適切にシャットダウンします。
- KillSwitch（監視側）は `data/kill.flag` を書き込むことで ExecutionEngine 側に停止要求を出す役割を持ちます。`KILL_FLAG_CLEAR_ON_START` により起動時に自動クリアする設定もあります（本番では無効推奨）。

---

## ログ

- ログ設定ユーティリティ: `kabusys.utils.logging_setup.setup_logging(app_name="...")`
  - 標準出力（stdout）への StreamHandler と、日次ローテートされたファイル（デフォルト `logs/<app_name>.log`）が設定されます。
  - デフォルトログディレクトリ: `logs/`（`LOG_DIR` 環境変数で変更可能）
  - ローテーション保有期間: 30 日

---

## 主要ファイル / ディレクトリ構成

（提供されているソースファイルに基づく簡易構成）

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス（環境変数読み込み・検証、自動 .env ロード）
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - Monitoring ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py
      - ログの一元設定
    - process_priority.py
      - プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py
      - SQLite テーブル定義・ストレージ層
    - system_monitor.py
      - システム状態、データ鮮度チェック
    - trade_monitor.py (参照)
      - 注文滞留・約定異常チェック（存在）
    - risk_monitor.py
      - ドローダウン / ポジション上限監視
    - kill_switch.py
      - Kill Switch 策定と flag 書き込み
    - monitoring_engine.py
      - 各 Monitor を束ねるエンジン
    - alert_manager.py (参照)
      - アラート送信ロジック（LINE 等）
  - execution/ (主要ロジック（ファイルは抜粋）)
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（注）上記は提供されたファイル群を要約したもので、実際にはさらに補助ファイルや未表示のモジュールがある場合があります。

---

## サンプル .env（最小例）

以下は最小の例です。必須トークン類は実際の値を設定してください。

```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

（`.env` は機密情報を含むため、Git にコミットしないでください）

---

## 注意事項 / 運用メモ

- Monitoring は監視データの一元化のため、`KABUSYS_ENV` に関わらず `SQLITE_PATH`（本番 monitoring DB）を使用します。監視データを分離したい場合は運用設計で注意してください。
- Paper trading (KABUSYS_ENV=paper_trading) は発注ロジックで MockBroker を使用し、`PAPER_TRADING_SQLITE_PATH` にのみ記録することで本番 DB と完全に分離します。
- OpenAI API を用いる処理は API 制限やエラーを考慮したリトライ実装が含まれていますが、API キーやコスト管理には十分に注意してください。
- 本番（live）環境では `KILL_FLAG_CLEAR_ON_START=0`、LINE 通知設定（`LINE_CHANNEL_ACCESS_TOKEN` / `LINE_USER_ID`）の確認を推奨します。
- `validate_config` は起動前の簡易チェックに有効です。`--strict` を使うと警告も失敗扱いになります。

---

README はここまでです。必要に応じて以下を追加できます：

- 実行エンジン / ブローカーの実装詳細（BrokerClient の使い方）
- ExecutionEngine の CLI オプションやログ出力例
- データベーススキーマの詳細（DuckDB テーブル定義）
- CI / デプロイ手順（systemd / Supervisor / Docker 起動例）

追加要望があれば教えてください。