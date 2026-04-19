# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ。戦略・ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、研究用ツール、AI ベースのニュース解析などを含むモジュール群で構成されています。

## プロジェクト概要
KabuSys は日本株向けの自動売買基盤です。主な目的は、
- 戦略に基づく銘柄選定とポジションサイズ計算
- 発注実行（本番 / ペーパートレードの分離）
- システム稼働状況および注文レベルの監視とアラート / Kill Switch
- DuckDB を使った研究／ファクター計算
- OpenAI を用いたニュースセンチメント / レジーム判定（任意）

設計方針としては「フェイルセーフ」「ルックアヘッドバイアス回避」「DB の冪等書き込み」「環境分離（paper_trading）」が重視されています。

---

## 主な機能一覧

- 設定管理
  - .env 自動ロード / 対話式作成 (`kabusys.config_setup`)
  - 起動前設定検証 CLI (`kabusys.validate_config`)
- 発注（Execution）
  - ExecutionEngine（本番 / ペーパートレード切替）
  - BrokerClientFactory によるブローカー抽象化（paper_trading 時は Mock）
  - OrderRepository、OrderManager、Reconciler、RiskManager 等の実装
- 監視（Monitoring）
  - SystemMonitor：CPU / メモリ / ディスク / データ鮮度 / プロセス生存確認
  - TradeMonitor：注文滞留や約定異常の検出（ソース内に実装あり）
  - RiskMonitor：ドローダウン・ポジション数上限監視とリスクログ記録
  - KillSwitch：条件に応じて `data/kill.flag` を書き込み ExecutionEngine を停止
  - MonitoringEngine：これらを束ねてポーリング
- DB 層
  - SQLite（監視・発注ログ）用の永続化層 `monitoring_db.py`（テーブル作成・マイグレーション含む）
  - DuckDB（分析 / 研究向け）接続に対応
- 研究 / ファクター
  - ファクター計算（モメンタム / バリュー / ボラティリティなど）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ
- ポートフォリオ構築
  - 候補選定、等重 / スコア重み付け、ポジションサイズ計算、セクター上限適用、レジーム乗数
- AI
  - ニュース NLP（OpenAI を使ったセンチメント評価、ai_scores テーブル書き込み）
  - 市場レジーム判定（ma200 とマクロセンチメントの合成）
  - API 呼び出しはリトライやパース検証を備えた実装
- ツール
  - Paper Trading の検証レポート生成スクリプト（成功率・レイテンシ・稼働率など）

---

## 前提条件（簡易）

- Python 3.10 以上（型ヒントで `|` や `dict[str, ...]` を使用）
- SQLite（標準の sqlite3）
- 以下 Python パッケージ（主要なもの）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config 検証で YAML 検査を行う場合、オプション）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（実運用時は requirements.txt を用意して `pip install -r requirements.txt` を推奨します）

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成し依存をインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb psutil openai pyyaml
   ```

3. .env を作成（対話式ウィザード）
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードは `.env` を作成／更新します。J-Quants トークンや kabuステーション API パスワード、KABUSYS_ENV（development / paper_trading / live）等を入力してください。

4. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告を厳密に扱う場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ作成（必要に応じて）
   - デフォルトで `data/` 配下に DB や PID / フラグファイルが置かれます。書き込み権限を確認してください。
   - ログは `logs/`（デフォルト）に出力されます。必要なら `LOG_DIR` 環境変数で変更可。

6. OpenAI を使う場合
   - 環境変数 `OPENAI_API_KEY` を設定するか、AI 呼び出し時に API キーを渡してください。

---

## 使い方（よく使うコマンド）

- ExecutionEngine を起動（本番／ペーパートレードは KABUSYS_ENV に依る）
  ```bash
  # デフォルト: .env の KABUSYS_ENV に従う
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し、データは `data/paper_trading.db`（`PAPER_TRADING_SQLITE_PATH` で上書き可）に記録され、本番 DB と分離されます。
  - 実行中に `data/stop_requested.flag` を作成すると起動スクリプト側が検知して停止処理を行います。
  - ExecutionEngine の PID ファイルはデフォルト `data/execution.pid` に保存されます（Settings.pid_file_path 参照）。

- Monitoring を起動
  ```bash
  # 環境変数 MONITOR_POLL_INTERVAL でポーリング秒数を設定（デフォルト 60秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 監視は通常 monitoring 用 DB（Settings.sqlite_path）を利用します。`MONITOR_POLL_INTERVAL` に不正値を与えるとデフォルト 60 秒にフォールバックします。
  - 監視ループは `data/stop_requested.flag` の存在で停止します。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- .env の自動ロードを無効化（テスト向け）
  ```bash
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 python -m ...
  ```

- Kill Switch（プログラムから利用）
  - KillSwitch は `Settings.kill_flag_path`（デフォルト `data/kill.flag`）に理由文字列を書き込みます。ExecutionEngine 側はこのファイルの存在を検出して終了します。
  - `KillSwitch.clear()` は起動時に `kill.flag` を削除する用途で利用されます（本番では自動クリアを推奨しない設定があります）。

---

## 環境変数（主要）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
- LOG_DIR: ログの出力ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading 時のフィルモード（instant | partial | never | reject）

---

## 停止 / フラグ管理

- 監視・実行の停止
  - グローバルな「即時停止」は `data/stop_requested.flag` を作成すると run_monitoring/run_execution が検知して終了します（2つのスクリプトともこのフラグを確認します）。
- Kill Switch
  - KillSwitch は `data/kill.flag` を作成して ExecutionEngine に停止指令を送ります（永続的な停止）。
  - 本番環境では `KILL_FLAG_CLEAR_ON_START=0` を推奨（自動クリアを無効化）。

---

## ログ

- デフォルトでルートロガーは stdout（コンソール）と日次ローテートのファイルハンドラ（logs/<app_name>.log）を設定します。
- ログ出力先を変更するには `LOG_DIR` を設定してください。
- ログのデフォルトレベルは `LOG_LEVEL` または `INFO`。

---

## ディレクトリ構成（主要ファイル）
（リポジトリの `src/kabusys` を想定）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / Settings 管理、自動 .env ロード
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - execution/  — 発注エンジン関連（BrokerFactory / ExecutionEngine / OrderManager ...）
  - monitoring/
    - monitoring_db.py — SQLite テーブル作成・操作ラッパー
    - system_monitor.py — システム監視
    - trade_monitor.py — 注文監視（滞留・異常検出）
    - risk_monitor.py — リスクチェック（DD・上限）
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — 各 Monitor を束ねる
    - alert_manager.py — アラート通知管理（LINE など、実装参照）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数決定・丸め・集計制限
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — モメンタム／バリュー／ボラティリティ計算
    - feature_exploration.py — 将来リターン・IC・統計
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）
    - regime_detector.py — レジーム判定（ma200 + macro sentiment）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート

---

## 開発上の注意点

- Python バージョン: 3.10 以上を強く推奨（型ヒントと構文依存）。
- OpenAI を用いる機能は API キーが必須です。API のレート制限や料金に注意してください。実装にはリトライ・バックオフが組み込まれていますが、運用時は適切なキー管理を行ってください。
- データベースファイル（DuckDB / SQLite）はデフォルトで `data/` に置かれます。バックアップや永続化を検討してください。
- process priority / CPU affinity 設定はプラットフォーム依存で失敗する場合があります（権限不足など）。警告ログは出ますが、処理は継続します。
- 設定ファイル（.env）は機密情報を含むため、Git 管理下に置かないでください（config_setup.py のヘッダにも明記しています）。

---

## よくあるコマンドまとめ

- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 実行エンジン起動
  - python -m kabusys.run_execution
- 監視起動
  - python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README に記載のない細かい実装や追加のランタイム引数は各モジュール（ソースコード）のドキュメント文字列を参照してください。必要であれば README を拡張してデプロイ手順や systemd / Supervisor 用の起動スクリプト例も追加できます。