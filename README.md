# KabuSys

日本株自動売買システムのリポジトリ（ライブラリ／実行スクリプト群）。

この README はリポジトリ内の主要スクリプト・モジュールを簡潔に説明し、ローカル環境でのセットアップ手順と実行方法、ディレクトリ構成の説明を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関する下記機能群を含むコードベースです。

- データ取得・分析（DuckDB を利用したファクター計算、リサーチ用機能）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算、セクター制限）
- 実行エンジン（ExecutionEngine） — ブローカークライアントを通じた発注処理（paper_trading モードあり）
- 監視（System / Trade / Risk Monitoring）と Kill Switch（停止シグナル）
- AI 補助（ニュースの NLP スコアリング、レジーム判定） — OpenAI API を使用
- 開発支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート等）

設計方針として、可能な限り副作用を抑え、DB 分離（本番 / ペーパートレード）・フェイルセーフ（API障害時のフォールバック）を重視しています。

---

## 主な機能一覧

- 環境設定管理（kabusys.config / config_setup.py）
  - .env の生成・更新ウィザード
  - Settings クラスによる集中管理、`.env` 自動読み込み（プロジェクトルート検出）
- 設定検証 CLI（kabusys.validate_config）
  - 必須環境変数・YAML 設定ファイルの存在や一般的な注意点をチェック
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV = paper_trading のときは MockBrokerClient を使い専用 SQLite に書き込む
  - 停止フラグ / PID 管理・プロセス優先度設定
- 監視ループ起動スクリプト（run_monitoring.py）
  - System / Trade / Risk の監視をポーリングで実行、kill.flag 生成など
  - ポーリング間隔を環境変数で上書き可能（MONITOR_POLL_INTERVAL）
- 監視永続化（monitoring/monitoring_db.py）
  - system_status / trade_logs / positions / risk_logs / dashboard 等のテーブル定義と操作
- ペーパートレード検証レポート（tools/paper_verification_report.py）
  - 稼働率・注文成功率・レイテンシ等の集計と Pass/Fail 判定を出力
- ポートフォリオ構築（portfolio/）
  - 候補選定、等比率／スコア比重、リスク制限、単元丸め、ポジションサイズ計算
- リサーチ（research/）
  - モメンタム／ボラティリティ／バリューなどファクター計算、IC・統計サマリ
- AI モジュール（ai/）
  - ニュース NLP による銘柄別センチメント、マクロニュースを用いた市場レジーム判定
  - OpenAI API（gpt-4o-mini）を利用（API キー必須）
- ユーティリティ（utils/）
  - ログ設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定

---

## 前提条件（推奨）

- Python >= 3.10（typing の | 記法を使用）
- 推奨パッケージ（用途に応じてインストール）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - pyyaml (config 検証で YAML を検証したい場合)
- OS: Linux / macOS / Windows（プロセス優先度や CPU affinity はプラットフォーム差分あり）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install duckdb psutil openai pyyaml
```
（requirements.txt がない場合は必要なパッケージを適宜インストールしてください）

---

## セットアップ手順

1. リポジトリをクローンしプロジェクトルートへ移動
2. 仮想環境を作成して有効化
3. 必要パッケージをインストール（上記参照）
4. 環境変数の準備:
   - 対話式ウィザードを使って `.env` を生成できます:
     ```bash
     python -m kabusys.config_setup
     ```
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - 主要な環境変数（代表例）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
   - 自動ロードの制御:
     - プロジェクトルート検出により `.env` が自動ロードされます。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
5. 設定検証（任意）:
   ```bash
   python -m kabusys.validate_config
   # 警告を厳格に扱う場合
   python -m kabusys.validate_config --strict
   ```
6. ログディレクトリはデフォルト `logs/` に作成されます。必要に応じて `LOG_DIR` 環境変数で変更できます。

---

## 使い方（主要コマンド）

- 監視ループ起動（Monitoring）
  - 簡単起動:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔を上書き:
    ```bash
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 動作: SystemMonitor / TradeMonitor / RiskMonitor を順に呼び、必要に応じて kill.flag を書き込む・アラートを発行します。
  - 停止: プロジェクトルートの `data/stop_requested.flag` ファイルが存在するとループは終了します（監視用の stop フラグ）。

- 実行エンジン起動（ExecutionEngine）
  - 起動:
    ```bash
    python -m kabusys.run_execution
    ```
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、`data/paper_trading.db` に操作を記録して本番 DB と分離します。
    - 起動前に `data/stop_requested.flag` が存在する場合は起動せず終了します。
    - 実行中に `data/stop_requested.flag` が作成されるとエンジンに停止指示を送ります。
  - PID と停止フラグ:
    - PID ファイル: `data/execution.pid`（デフォルト）。Settings を使って変更可能。
    - Kill Switch として `data/kill.flag` を監視し、KillSwitch による停止を実行する設計があります（監視側が生成）。

- .env ウィザード（初期設定）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連（プログラム API）
  - ニュース NLP スコア登録: kabusys.ai.score_news (DuckDB 接続を渡す)
  - レジーム判定: kabusys.ai.regime_detector.score_regime (DuckDB 接続を渡す)
  - 注意: OpenAI API キーは `OPENAI_API_KEY` 環境変数か関数引数で指定する必要があります。

---

## 重要な挙動・運用注意点

- KABUSYS_ENV が `live` のときは本番運用です。validate_config は live を検出すると注意喚起を出します（LINE 通知等の設定漏れに注意）。
- 監視は常に「本番用の sqlite_path」を参照する設計（monitoring は環境にかかわらず `SQLITE_PATH` を使用）。
- ペーパートレード時はデータベースが分離され、本番 DB を汚染しないようになっています（`PAPER_TRADING_SQLITE_PATH`）。
- Kill Switch:
  - KillSwitch は監視側が条件を満たしたとき `data/kill.flag` を書き込み、ExecutionEngine 側がこれを参照して停止する仕組みです。
  - `KILL_FLAG_CLEAR_ON_START=1` を本番で利用するのは危険（validate_config は警告します）。
- ログ:
  - デフォルトで stdout と日次ローテートファイル（`logs/<app_name>.log`）の両方に出力します。ログレベルは `LOG_LEVEL` 環境変数で制御。
- プロセス優先度:
  - 起動スクリプトは起動時に `set_process_priority("high")` を呼びます（プラットフォームにより失敗する場合があるため警告ログで継続します）。

---

## 環境変数（抜粋）

必須（最小セット）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用に重要なもの:
- KABUSYS_ENV: development | paper_trading | live
- DUCKDB_PATH: DuckDB ファイル（分析用）
- SQLITE_PATH: monitoring DB（監視ログ）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（paper_trading モードのみ）
- LOG_LEVEL: DEBUG|INFO|...
- OPENAI_API_KEY: OpenAI を使う場合必須
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（Settings で参照）

設定は `.env` に保存し、`config_setup.py` で生成できます。自動ロードはプロジェクトルートの `.env` / `.env.local` を読み込む仕組みになっています（OS 環境変数が優先）。

---

## ディレクトリ構成

リポジトリの主要なファイル／ディレクトリ（src/kabusys を基準）:

- src/kabusys/
  - __init__.py
  - config.py                — Settings / .env 自動読み込みロジック
  - config_setup.py          — .env ウィザード（対話式）
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 呼び出し、ai_scores 書込）
    - regime_detector.py     — 市場レジーム判定（ma200 + マクロニュース）
  - monitoring/
    - monitoring_db.py       — SQLite ベースの監視 DB（テーブル作成 / DB 操作）
    - monitoring_engine.py   — 各 Monitor を束ねる Engine
    - system_monitor.py      — CPU / メモリ / PID / データ鮮度チェック
    - trade_monitor.py       — （トレード監視ロジック）
    - risk_monitor.py        — ドローダウン・ポジション上限の監視
    - kill_switch.py         — kill.flag 書込みロジック
    - alert_manager.py       — アラート送信（LINE 等、実装次第）
  - execution/
    - execution_engine.py    — 実行エンジン本体
    - order_manager.py
    - order_repository.py
    - broker_factory.py      — 本番/モックのブローカークライアント生成
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/
    - pipeline.py            — prices / raw_financials 取得等（DuckDB の参照）
    - stats.py               — zscore 正規化等ユーティリティ
  - utils/
    - logging_setup.py       — 統一ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/、execution/、ai/、portfolio/、research/ などのテスト用ユーティリティや実装ファイル群

注意: 上記はソース内にある主要モジュールを抜粋して説明しています。実際のリポジトリ全体構成はツリーを参照してください。

---

## 開発・拡張のポイント

- DuckDB を使った分析系関数は副作用がなく、テストしやすい（関数に DuckDB コネクションを渡す設計）。
- AI 部分は OpenAI SDK に依存するが、API 呼び出し関数（内部 _call_openai_api 等）はテストで差し替え可能なように実装されています。
- monitoring_db はスキーママイグレーション（カラム追加）を起動時に行うため、既存 DB との後方互換を考慮しています。
- 実運用時は `KABUSYS_ENV=live` の設定と LINE 通知等の設定を慎重に行ってください（validate_config でのチェック推奨）。

---

## トラブルシューティング

- .env が読み込まれない／自動読み込みを無効にしたい:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを抑制できます。
- ログファイルが作成されない:
  - `LOG_DIR` のパーミッションや作成権限を確認してください。ディレクトリ作成に失敗した場合は stdout のみで動作します。
- OpenAI 呼び出しでエラーが出る:
  - `OPENAI_API_KEY` が正しく設定されているか確認。API のレート制限や一時的な接続エラーはライブラリ側でリトライ処理がありますが、鍵やネットワークの問題は切り分けてください。

---

README は以上です。必要であれば以下の追加情報を作成します：
- 具体的な .env.example（サンプルファイル）
- systemd / supervisor 用のサービスユニット例（実運用向け）
- 開発・テストのための簡易データ生成スクリプト例

どれが必要か教えてください。