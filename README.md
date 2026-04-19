# KabuSys

日本株向け自動売買システムのサンプル実装（パッケージ: kabusys）

このリポジトリは、戦略・ポートフォリオ構築、発注実行（本番 / ペーパートレード）、監視（Monitoring）、AI を使ったニュース評価やレジーム判定、研究用ファクター計算などを含むモジュール群で構成されています。

---

## プロジェクト概要

KabuSys は以下の要素を含む自動売買基盤です。

- 戦略・ポートフォリオ構築（銘柄選定、重み計算、株数算出）
- 発注/実行エンジン（実際のブローカー or Mock ブローカーでのペーパートレード）
- 監視サブシステム（CPU/メモリ/ディスク・プロセスの死活、注文状態、リスク検知）
- Kill Switch（閾値超過時に ExecutionEngine を安全に停止）
- AI モジュール（OpenAI を用いたニュースセンチメント評価、レジーム判定）
- 研究用ツール（ファクター計算、特徴量探索、ペーパートレードの検証レポート生成）
- ユーティリティ（ロギング設定、プロセス優先度設定、環境設定ウィザード・検証 CLI）

設計上の方針として、ルックアヘッドバイアスを避ける実装、冪等な DB 初期化・書き込み、フェイルセーフな外部 API 呼び出しを重視しています。

---

## 主な機能一覧

- Environment 設定自動ロード（`.env` / `.env.local`、手動ウィザードあり）
- `run_execution`：ExecutionEngine 起動（KABUSYS_ENV により本番/ペーパー切替）
  - ペーパートレード時は MockBrokerClient を使用し DB を分離（data/paper_trading.db）
- `run_monitoring`：SystemMonitor を定期実行する監視プロセス
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を指定可能（デフォルト 60 秒）
- Monitoring サブシステム（system/trade/risk の各 Monitor、KillSwitch、AlertManager）
- AI モジュール
  - ニュースの銘柄別センチメント算出（OpenAI）
  - 市場レジーム判定（ma200 + マクロニュース）
- 研究用モジュール（ファクター計算、forward returns、IC 計測）
- tools:
  - `paper_verification_report`：ペーパートレード DB を解析して PASS/FAIL レポートを生成
- ユーティリティ
  - ロギング統一設定（コンソール + 日次ローテーション）
  - プロセス優先度 / CPU affinity 設定
  - 設定検証 CLI（`validate_config`）
  - .env 対話式セットアップ（`config_setup`）

---

## 必要な依存関係（代表）

少なくとも以下の Python パッケージが必要です（環境や機能により追加）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config YAML のパース検証を行う場合。なければ警告）
- sqlite3（標準ライブラリ）

（プロジェクトに requirements.txt がある場合はそれを参照してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install duckdb psutil openai pyyaml
   ```
   - AI 機能を使わない場合は `openai` は不要
   - `pyyaml` は `validate_config` の YAML 検証でのみ必要

4. 環境変数の準備
   - 対話式ウィザードで .env を生成:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは `.env`（プロジェクトルート）を生成・更新します。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN（J-Quants API）
     - KABU_API_PASSWORD（kabuステーション API）
   - AI 機能利用時:
     - OPENAI_API_KEY を設定

5. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   # 警告も fail にしたい場合:
   python -m kabusys.validate_config --strict
   ```

6. 必要ディレクトリの作成（.env のパスやデフォルトに従う）
   ```
   mkdir -p data logs
   ```

---

## 実行方法（主なコマンド）

- ExecutionEngine（本番 / ペーパートレード切替）
  - 本番（env に応じた動作）:
    ```
    python -m kabusys.run_execution
    ```
  - ペーパートレードに切替:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
    - ペーパートレード時は MockBrokerClient が使用され、`PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に記録されます。

- Monitoring（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更する場合:
    ```
    export MONITOR_POLL_INTERVAL=120  # 120 秒毎にポーリング
    ```

- 設定ウィザード（.env の作成・編集）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

---

## 重要な環境変数（主なもの）

- KABUSYS_ENV: 実行環境
  - "development", "paper_trading", "live"
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリア（"1" で有効）

---

## 停止・Kill Switch の取り扱い

- run_execution / run_monitoring はプロセス制御用フラグを `data/` 下に置きます:
  - 停止フラグ（プロセス終了要求）:
    - `data/stop_requested.flag` — これが存在するとループは終了します（run_monitoring/run_execution 共に検出）。
  - Kill Switch（ExecutionEngine を停止させるためのフラグ）:
    - `data/kill.flag` — KillSwitch により書き込まれる。ExecutionEngine は起動時にこのフラグを検出すると起動を中止するか停止処理を行う。
  - PID ファイル:
    - `data/execution.pid`（設定で変更可）

- `KILL_FLAG_CLEAR_ON_START=1` を設定すると ExecutionEngine 起動時に `kill.flag` を自動削除します（本番では 0 推奨）。

---

## ログ

- 共通ロギング設定は `kabusys.utils.logging_setup.setup_logging` で行われます。
- コンソール（stdout）とファイル（日次ローテーション）が有効になります。デフォルトログディレクトリは `logs/`。
- ログファイル名は起動時の app_name（例: `execution`）に基づき `logs/execution.log` になります。

---

## 開発・運用メモ

- run_execution は環境変数 `KABUSYS_ENV=paper_trading` で MockBrokerClient を使用し、発注は DB に保存され本番 DB と分離されます。
- AI 機能（news_nlp, regime_detector）は OpenAI (gpt-4o-mini) を利用するため API キーが必要。外部呼び出しはリトライやフェイルセーフ実装がありますが、API 利用制限に注意してください。
- `validate_config` は起動前の必須環境変数や config/*.yaml の存在と整合性をチェックします。`--strict` オプションで警告を失敗扱いにできます。
- DuckDB 接続は研究・ファクター計算向けに利用されます。prices_daily、raw_financials、raw_news 等のテーブルを利用する想定です。
- 各種 DB 初期化（監視用）は `monitoring_db.init_monitoring_db` により冪等に作成・マイグレーションされます。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数読み込み / Settings（.env 自動ロード含む）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースを LLM でスコアリング
  - regime_detector.py — 市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py — システム状態・データ鮮度チェック
  - trade_monitor.py — 発注ログ監視（滞留注文、約定異常 等）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — Kill Switch 実装（kill.flag の書き込み/クリア）
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - alert_manager.py —（通知管理、LINE 等の統合想定）
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - （発注処理・ブローカー抽象化）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数計算
  - risk_adjustment.py — セクター上限 / レジーム乗数
- research/
  - factor_research.py — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — forward returns, IC, 統計サマリ
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

その他:
- data/ — デフォルト DB ファイル、フラグファイル、pid 保存先（実行時に作成）
- logs/ — ログ出力先（設定により変更可能）

---

## よくある質問 / トラブルシューティング

- Q: ペーパートレードのデータが見つからない
  - A: `PAPER_TRADING_SQLITE_PATH` 環境変数や `--db` オプションで DB パスを指定してください。デフォルトは `data/paper_trading.db`。

- Q: OpenAI 呼び出しで失敗する
  - A: `OPENAI_API_KEY` が正しく設定されているか確認。API リミットやネットワークの一時的エラーは組み込みのリトライで緩和されますが、最終的にスコア取得が失敗する場合があります（その場合はログを確認してください）。

- Q: ログファイルが作成されない
  - A: デフォルトでは `logs/` に作成します。パーミッションやディレクトリ作成に失敗した場合はコンソール出力のみになります。`LOG_DIR` で保存先を変更できます。

---

必要に応じて README を拡張します（例: 実行フロー図、サンプル .env、ユニットテストの実行方法、CI 設定など）。追加で欲しい情報があれば教えてください。