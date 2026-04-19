# KabuSys

軽量な日本株向け自動売買 / 研究プラットフォーム（ライブラリ兼実行スクリプト群）。

このリポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、
ポートフォリオ構築ロジック、リサーチ用ファクター計算、および
ニュース NLP / レジーム判定のための AI 統合を含みます。

---

## 主要な特徴（抜粋）

- ExecutionEngine 起動スクリプト（run_execution.py）
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用して本番 DB と分離（デフォルト: `data/paper_trading.db`）。
  - 実行中は PID ファイルを作成し、外部から停止フラグで制御可能。

- Monitoring（run_monitoring.py / monitoring パッケージ）
  - システム状態（CPU/メモリ/ディスク）、データ鮮度、注文・リスク監視を定期ポーリング。
  - Kill Switch による自動停止（条件：ドローダウンやポジション上限など）。
  - 監視ログは SQLite（デフォルト `data/monitoring.db`）へ永続化。

- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定、等重／スコア重み付け、ポジションサイズ計算、セクターキャップ、レジーム乗数など純粋関数群。

- リサーチ（research パッケージ）
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）、将来リターン・IC 計算、統計要約。

- ニュース NLP / レジーム判定（ai パッケージ）
  - OpenAI（gpt-4o-mini）を利用したニュースセンチメントスコアリング / 市場レジーム判定。
  - API エラーに対するリトライ・フェイルセーフ設計。

- ユーティリティ
  - 統一ロギング設定（console + 日次ローテートファイル）。
  - プロセス優先度 / CPU affinity 設定ユーティリティ。
  - .env 対話式セットアップウィザードと設定検証 CLI。

---

## 必要条件

- Python 3.10+
- 推奨／必須パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で使用。任意）
- SQLite（標準ライブラリで利用可能）
- ネットワークアクセス（kabuステーション API / OpenAI を利用する場合）

pip の例：
```
pip install duckdb psutil openai PyYAML
```

（プロジェクトに requirements.txt がある場合はそちらを参照してください）

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（有効値: `development`, `paper_trading`, `live`、デフォルト: `development`）
  - `paper_trading` は発注をモックし、専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します
- DUCKDB_PATH（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH（監視 DB。デフォルト: `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: `data/paper_trading.db`）
- LOG_LEVEL（`INFO` 等。デフォルト: `INFO`）
- OPENAI_API_KEY（AI モジュールを使う場合に必要）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔秒。デフォルト: 60）
- PAPER_FILL_MODE（ペーパートレードの約定挙動。`instant`|`partial`|`never`|`reject`、デフォルト: `instant`）
- KILL_FLAG_CLEAR_ON_START（本番で危険なのでデフォルトは `0`）

注意: Settings モジュールは起動時にプロジェクトルート（.git or pyproject.toml）から `.env` を自動でロードします。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（基本）

1. リポジトリをクローンし作業ディレクトリに移動
2. Python 仮想環境を作成・有効化
3. 依存パッケージをインストール（上の pip 参照）
4. .env を作成
   - 対話式ウィザードを推奨:
     ```
     python -m kabusys.config_setup
     ```
   - または手動で `.env` を作成。例は config_setup が生成するテンプレートを参照。
5. 設定検証（任意）:
   ```
   python -m kabusys.validate_config
   # 警告を FAIL として扱う場合:
   python -m kabusys.validate_config --strict
   ```
6. 必要なディレクトリ（`data/`, `logs/`）が自動作成されますが、権限・マウント先を事前に確認してください。

---

## 使い方（実行例）

- ExecutionEngine を起動（実運用 / ペーパートレードを切り替えるには KABUSYS_ENV を設定）
```
python -m kabusys.run_execution
```
- Monitoring を起動（デフォルトポーリング 60 秒。変更は MONITOR_POLL_INTERVAL 環境変数で）
```
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- Paper Trading の検証レポートを生成（SQLite DB を指定可）
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を指定する場合
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

停止制御:
- 実行スクリプト（run_execution/run_monitoring）はリポジトリ内 `data/stop_requested.flag` を監視します（存在するとループを終了）。
  - 手動で停止したい場合はそのファイルを作成してください（例: `touch data/stop_requested.flag`）。
- KillSwitch（監視コンポーネント）は条件を満たすと `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送ります。
  - `data/kill.flag` を消す場合は削除してください（起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定していると自動でクリアされる場合がありますが本番では推奨されません）。

ログ:
- デフォルトログディレクトリ: `logs/`
- ログファイル名は起動アプリ名に基づき `logs/execution.log`, `logs/monitoring.log` などが生成され、日次ローテーションされます。

AI 関連:
- news_nlp / regime_detector を利用するには `OPENAI_API_KEY` を設定してください。
- AI 呼び出しはリトライ・バックオフ、部分失敗時のフェイルセーフが考慮されていますが、API コストとレート制限に注意してください。

---

## CLI ユーティリティ一覧

- python -m kabusys.config_setup
  - .env を対話的に作成 / 更新
- python -m kabusys.validate_config [--strict]
  - .env と config/*.yaml の基本チェック
- python -m kabusys.run_execution
  - 発注エンジンを起動
- python -m kabusys.run_monitoring
  - 監視ループを起動
- python -m kabusys.tools.paper_verification_report
  - ペーパートレード検証レポートを生成

---

## ディレクトリ構成（主要ファイル）

（このプロジェクトのソースは `src/kabusys` 配下に配置されています）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py
      - 統一ロギング設定（console + 日次ファイル）
    - process_priority.py
      - プロセス優先度・CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py
      - SQLite 用永続化層（テーブル作成・CRUD ヘルパ）
    - system_monitor.py
      - システム状態・データ鮮度のチェック
    - trade_monitor.py
      - （注文の滞留／約定異常検出などの監視ロジック）
    - risk_monitor.py
      - ドローダウン・ポジション上限監視
    - kill_switch.py
      - Kill Switch ロジック（フラグ書き込み）
    - monitoring_engine.py
      - 各 monitor を束ねるエンジン
    - alert_manager.py
      - （LINE などへ通知する責務）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
    - （発注・リスク管理のコア）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - （ポートフォリオ構築に関する純粋関数）
  - research/
    - factor_research.py
    - feature_exploration.py
    - （DuckDB を用いたファクター計算・評価）
  - ai/
    - news_nlp.py
    - regime_detector.py
    - （OpenAI 連携ロジック）
  - tools/
    - paper_verification_report.py
    - （運用向けレポート）

---

## 実装上の注意点 / 運用上の知見

- 環境分離
  - Monitoring は常に本番の sqlite_path を使用して監視ログを記録します（KABUSYS_ENV に関わらず）。
  - Execution は `paper_trading` 時に paper DB に記録して本番 DB と完全分離します。

- .env の取り扱い
  - `.env` は機密情報を含むため絶対に VCS にコミットしてはいけません（config_setup も警告を出します）。
  - 自動ロード順: OS 環境変数 > .env.local > .env（必要に応じて自動ロードを無効化可能）。

- フェイルセーフ設計
  - AI 呼び出しはリトライとクリップを行い、失敗時はデフォルト値で継続する設計です（例: macro_sentiment=0.0）。
  - 監視コンポーネントはエラー時に例外を捕捉してループ継続するようになっています。

---

## よく使うコマンドまとめ

- .env 作成
  ```
  python -m kabusys.config_setup
  ```
- 設定検証
  ```
  python -m kabusys.validate_config
  ```
- 実行エンジン起動
  ```
  python -m kabusys.run_execution
  ```
- 監視起動（ポーリング間隔 30 秒にする例）
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
  ```

---

README に書かれていない内部 API（関数の詳細な引数や戻り値）については、各モジュール（例えば portfolio/*.py、research/*.py、ai/*.py、monitoring/*.py）にドキュメンテーションと docstring を用意しています。実装を拡張・運用する際は該当モジュールの docstring を参照してください。

必要であれば、起動フロー図・設定テンプレート・運用手順（デプロイ、監視アラート設定、バックアップ）など運用向けドキュメントも作成します。どの情報が欲しいか教えてください。