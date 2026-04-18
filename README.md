# KabuSys — README

日本株向け自動売買システムのサブモジュール群（ライブラリ兼実行用スクリプト群）の README です。  
このリポジトリは発注/監視/ポートフォリオ構築/研究/AI（ニュース NLP）などの主要機能を含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローを構成する Python モジュール群です。主な関心は次の通りです。

- Execution Engine：発注ロジック・注文管理・リスク管理
- Monitoring：システム稼働状況・データ鮮度・注文状態の監視と Kill Switch
- Portfolio Construction：銘柄選定・重み付け・ポジションサイジング
- Research：ファクター計算・特徴量解析・IC 計算
- AI：ニュースに基づくセンチメント評価（OpenAI）
- Tools：ペーパートレード検証レポート等のユーティリティ

設計方針として、実運用とペーパートレード（paper_trading）を分離し、DuckDB / SQLite を用いたデータ保存、OpenAI API 呼び出しのフェイルセーフ設計、ログの統一管理を行っています。

---

## 主な機能一覧

- 環境設定ウィザード（.env の対話式作成）: `kabusys.config_setup`
- 起動前設定検証 CLI: `kabusys.validate_config`
- ExecutionEngine 起動スクリプト: `kabusys.run_execution`
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い DB を分離
- Monitoring ポーリングループ: `kabusys.run_monitoring`
  - MONITOR_POLL_INTERVAL で間隔を変更可能（デフォルト 60s）
  - 監視データは本番の sqlite_path を使用
- MonitoringEngine：System / Trade / Risk Monitor をまとめて実行、アラート・Kill Switch 評価
- Kill Switch：条件に応じて `data/kill.flag` を書き込み ExecutionEngine を停止
- Portfolio モジュール：候補選定、重み算出、ポジションサイズ計算、セクター制限、レジーム乗数
- Research：モメンタム・ボラティリティ・バリュー等のファクター計算、IC 計算、統計サマリ
- AI：
  - news_nlp: ニュース記事を OpenAI でスコア化し ai_scores に保存
  - regime_detector: ma200 とマクロセンチメントを合成して市場レジーム判定
- Tools：Paper Trading 検証レポート生成スクリプト（`kabusys.tools.paper_verification_report`）
- 共通ユーティリティ：ロギング設定、プロセス優先度設定など

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリ>
   ```

2. Python 環境（推奨: venv）を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール（例）
   - 本プロジェクトの requirements ファイルがない場合は、以下をインストールしてください。
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML を使う場合に推奨）
   ```
   pip install duckdb psutil openai PyYAML
   ```

4. .env ファイルの作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードで入力した値が `.env` に保存されます。必須環境変数:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   重要な環境変数（主なもの）:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
   - SQLITE_PATH: data/monitoring.db（監視用）
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード時）
   - OPENAI_API_KEY: OpenAI を使う機能で必要（AI モジュール）
   - LOG_LEVEL / LOG_DIR など

5. 設定検証（必須項目のチェック）
   ```
   python -m kabusys.validate_config
   # 警告もエラーとして扱う場合
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリ作成（ログ・DB など）
   ```
   mkdir -p data logs
   ```

備考:
- `KILL_FLAG_CLEAR_ON_START=1` にすると Execution 起動時に `data/kill.flag` を自動でクリアしますが、本番では `0` 推奨です。
- Monitoring は実行環境にかかわらず本番 sqlite_path を使って監視情報を保存します（run_monitoring の仕様）。

---

## 使い方（実行例）

- Execution Engine の起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し `PAPER_TRADING_SQLITE_PATH`（既定: data/paper_trading.db）に記録します。
  - 起動前に `data/stop_requested.flag` が存在する場合は起動しません。

- Monitoring の起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - 監視ループ中に `data/stop_requested.flag` を作成するとループが終了します。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- .env の作成／更新
  ```
  python -m kabusys.config_setup
  ```

- 設定の妥当性チェック
  ```
  python -m kabusys.validate_config
  ```

- ログ
  - ログはデフォルトで `logs/` に日次ローテーションで出力されます（例: logs/execution.log, logs/monitoring.log）。
  - ログ設定は `kabusys.utils.logging_setup.setup_logging()` を通じて一元管理されます。

---

## ファイル / ディレクトリ構成

以下は主要なソース配置（src/kabusys 以下）です。パッケージのエントリポイントやユーティリティ、モジュール別に整理されています。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env ロード機能含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py       — 共通ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル作成・CRUD ラッパー）
    - monitoring_engine.py   — Monitor を束ねる実行エンジン
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （注文監視ロジック）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 制御
    - alert_manager.py       — （通知送信ロジック）
  - execution/
    - execution_engine.py    — ExecutionEngine（発注・セッション管理）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み付け
    - position_sizing.py     — 発注株数計算
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — モメンタム / ボラティリティ / バリュー算出
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（ma200 + マクロセンチメント）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成

プロジェクトルート（パッケージ外）:
- .env.example（存在する場合）
- config/*.yaml（system_config.yaml 等、実行設定用テンプレート）
- data/ ディレクトリ（デフォルトの DB / PID / flag）
  - data/monitoring.db
  - data/paper_trading.db
  - data/execution.pid
  - data/kill.flag
  - data/stop_requested.flag
- logs/（ログファイル格納）

---

## 重要な運用注意点

- 本番（KABUSYS_ENV=live）では必須パラメータや通知設定（LINE）等を十分に確認してください。validate_config は live 時の追加警告を出します。
- Kill Switch（`data/kill.flag`）は Monitoring／リスクロジックから書き込まれ、ExecutionEngine はこれを検出して安全停止します。`KILL_FLAG_CLEAR_ON_START` を誤設定すると危険です（本番は 0 推奨）。
- Monitoring は監視用 DB（SQLITE_PATH）を使用します。run_monitoring は環境に関係なく本番 sqlite_path を参照します。
- OpenAI を使う機能を利用する際は `OPENAI_API_KEY` を設定してください。API 呼び出しはリトライ・フォールバック実装がありますが、キー未設定は例外になります。
- ログディレクトリ作成に失敗するとファイル出力は無効化されコンソール出力のみになります（警告が出ます）。

---

## 開発者向け / テスト時のヒント

- 自動で .env を読み込む仕組みがあります。テスト時に自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ユニットテストでは OpenAI など外部 API 呼び出しをモックしてください（news_nlp._call_openai_api や regime_detector._call_openai_api 等は差し替え可能に設計されています）。
- DuckDB / SQLite 接続はモジュールで受け取る設計なので、テスト用の一時 DB を渡すことで副作用を抑えられます。
- ログを調整したい場合は `kabusys.utils.logging_setup.setup_logging(app_name="...")` を呼んで設定してください。

---

以上がプロジェクトの概要・セットアップ・基本的な使い方です。追加で README に記載したいコマンドや設定例（.env のサンプル、docker / systemd のユニットファイル例など）があればお知らせください。