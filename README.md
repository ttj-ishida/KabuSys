# KabuSys

日本株向け自動売買システムのモノリポジトリ（ライブラリ + 起動スクリプト群）。

この README は提供されたコードベースに基づいて作成されています。主に環境設定、起動スクリプト、監視・リスク管理、ポートフォリオ構築、リサーチ、AI ベースのニュース解析などを含みます。

---

## 概要

KabuSys は次のような責務を持つモジュール群で構成された自動売買基盤です。

- 実行エンジン (ExecutionEngine)：発注 / 注文管理 / リスク管理のランタイム
- 監視 (Monitoring)：システム状態・発注状態・リスクを継続監視してアラートや Kill Switch を実行
- ポートフォリオ構築：シグナルをもとに候補選定・重み計算・株数決定を行う純粋関数群
- リサーチ：DuckDB 上の時系列データからファクター等を算出する分析モジュール
- AI 補助：OpenAI を用いたニュースセンチメントや市場レジーム判定（任意）
- ユーティリティ：設定読み込み、ログ設定、プロセス優先度設定など

設計上のポイント：
- Paper Trading（`KABUSYS_ENV=paper_trading`）時は本番 DB と分離（`data/paper_trading.db`）
- 環境変数は `.env` / `.env.local` から自動読み込み（必要なら自動読み込みを無効化可能）
- DuckDB を分析用 DB として利用、SQLite を監視・履歴保存に使用
- OpenAI と連携する機能は API キーが必要（失敗時はフェイルセーフ設計）

---

## 主な機能一覧

- 実行エンジンの起動 / 停止制御（run_execution）
- 監視ポーリングループ（run_monitoring）
- 監視ログ管理（SQLite）
- Kill Switch（条件により ExecutionEngine 停止フラグを書き込む）
- リスク監視（ドローダウン・ポジション上限検出）
- 注文ログ / ポジション永続化（monitoring_db）
- Portfolio construction（候補選定、重み算出、ポジションサイズ計算）
- Research モジュール（momentum, volatility, value 等のファクター計算）
- AI モジュール（ニュースセンチメント: news_nlp、市場レジーム: regime_detector）
- CLI ユーティリティ：
  - 設定ウィザード: `kabusys.config_setup`
  - 設定検証: `kabusys.validate_config`
  - Paper Trading 検証レポート: `kabusys.tools.paper_verification_report`

---

## システム要件（推奨）

- Python 3.10+
- 推奨パッケージ（代表例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML (validate_config による YAML 検証を行う場合)

requirements.txt がある場合は次のようにインストールしてください：

```
pip install -r requirements.txt
```

足りない依存は機能実行時に ImportError 等で検出されます。

---

## セットアップ手順

1. リポジトリをクローン / 展開

2. Python 仮想環境を作成して有効化（任意だが推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell)
   ```

3. 依存パッケージをインストール
   ```
   pip install duckdb psutil openai PyYAML
   ```
   ※ 実際の requirements.txt があればそれを利用してください。

4. 初期設定ファイル（.env）を作成
   - 対話型ウィザードで作成:
     ```
     python -m kabusys.config_setup
     ```
   - 既存の `.env` がある場合、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すれば自動読み込みを無効化できます。

5. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告をエラー扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

6. ディレクトリ（logs, data 等）の準備
   多くの起動コードは自動で親ディレクトリを作成しますが、必要に応じて手動で作成しておくと安心です。
   ```
   mkdir -p data logs
   ```

---

## 環境変数（主なもの）

必須（最低限設定が必要）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用に関係する主な環境変数（デフォルト値はコード中の説明を参照）:
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- DUCKDB_PATH: DuckDB データベースパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ保存先（default: logs）
- OPENAI_API_KEY: OpenAI を用いる機能で参照
- PAPER_FILL_MODE: paper_trading 時の約定動作（instant | partial | never | reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_PATH: kill.flag のパス（default: data/kill.flag）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイル（default: data/execution.pid）

詳細は `kabusys.config.Settings` を参照してください。

---

## 使い方（主要 CLI）

- 設定ウィザード（.env を生成 / 更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine（発注エンジン）を起動
  - 通常起動:
    ```
    python -m kabusys.run_execution
    ```
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient が使われ `data/paper_trading.db` に記録されます。
  - 起動時、プロセス優先度を high に設定します。
  - 停止には `data/stop_requested.flag` を作成（run_execution はこのファイルを監視して安全に終了します）。
  - 実行時に PID が `data/execution.pid` に書き込まれます。

- Monitoring（監視ループ）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - デフォルトのポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で上書き可能。
  - Monitoring は環境にかかわらず（paper/live など）本番 sqlite_path（設定された SQLITE_PATH）を使用して監視ログを記録します。
  - 停止は `data/stop_requested.flag` を作成して行います。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB は `data/paper_trading.db`。`--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

- AI 関連
  - ニュースセンチメント評価（プログラム API）:
    ```
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")
    ```
  - レジーム判定:
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")
    ```

---

## 停止 / Kill Switch に関して

- run_monitoring / run_execution は `data/stop_requested.flag` の存在を監視して安全に停止します。
- Kill Switch: `kabusys.monitoring.kill_switch.KillSwitch` が条件（ドローダウンやポジション上限等）を満たすと `data/kill.flag` を書き込み、ExecutionEngine に停止を促します。
- 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動でクリアしますが、本番では `0` を推奨します。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内 `src/kabusys` の主要構成です（抜粋）。

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings
  - config_setup.py                — .env 対話型ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — Monitoring 起動スクリプト
  - monitoring/
    - monitoring_db.py             — SQLite の永続化層
    - system_monitor.py            — システム状態 / データ鮮度監視
    - trade_monitor.py             — 注文関連監視（存在）
    - risk_monitor.py              — ドローダウン / ポジション上限監視
    - monitoring_engine.py         — 各 Monitor の統合ポーリング
    - kill_switch.py               — kill.flag 書き込みロジック
    - alert_manager.py             — アラート送信（存在）
  - execution/
    - execution_engine.py          — 実行エンジン本体（存在）
    - order_manager.py             — 注文管理（存在）
    - order_repository.py          — 注文リポジトリ（存在）
    - broker_factory.py            — ブローカクライアント生成
    - reconciler.py                — 差分整合処理
    - risk_manager.py              — 実行時リスク管理
  - portfolio/
    - portfolio_builder.py         — 候補選定、重み計算
    - position_sizing.py           — 株数算出
    - risk_adjustment.py           — セクター制限 / レジーム乗数
  - research/
    - factor_research.py           — momentum / volatility / value 等
    - feature_exploration.py       — IC / フォワードリターン等
  - ai/
    - news_nlp.py                  — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py           — 市場レジーム判定（OpenAI + MA）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py             — ログ設定ユーティリティ
    - process_priority.py          — プロセス優先度 / CPU affinity
  - data/ (runtime)
    - monitoring.db (default: data/monitoring.db)
    - paper_trading.db (paper trading 用)
    - execution.pid
    - kill.flag / stop_requested.flag

（実際のリポジトリにはさらに多くの補助ファイル・モジュールがあります）

---

## 開発 / テストのヒント

- 自動環境読み込みを無効化したいテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使用して .env の自動読み込みをスキップできます。
- validate_config の `--strict` を使うと警告も失敗（exit 1）として扱えます。CI の事前チェックに便利です。
- AI 関連機能は OpenAI API に依存します。ユニットテストでは OpenAI 呼び出し関数（内部の _call_openai_api など）をモックしてください。
- DuckDB / SQLite のスキーマはコード中で self-contained に作成・マイグレーションが行われる設計です（monitoring_db.init_monitoring_db 等）。

---

## ライセンス・バージョン

パッケージバージョンは `kabusys.__version__ = "0.1.0"` に定義されています。ライセンスはリポジトリ内の LICENSE ファイルを参照してください（存在する場合）。

---

## 参考（よくあるコマンドまとめ）

- .env 作成:
  ```
  python -m kabusys.config_setup
  ```
- 設定チェック:
  ```
  python -m kabusys.validate_config
  ```
- 実行エンジン起動:
  ```
  python -m kabusys.run_execution
  ```
- 監視起動:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README の内容はコードベース（src/kabusys 配下）を参照して作成しています。追加の詳細（API ドキュメント、設計書、運用手順など）が必要であれば、その目的を教えてください。