# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README。  
このドキュメントはリポジトリ内の主要コンポーネント、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

バージョン: 0.1.0（src/kabusys/__init__.py）

---

## プロジェクト概要

KabuSys は日本株の自動売買／研究プラットフォームです。主な機能は以下の通りです。

- 戦略（ファクター計算・特徴量解析）とポートフォリオ構築（候補選定・配分・ポジションサイズ計算）
- ExecutionEngine（発注実行）と、それを監視する Monitoring（システム状態・注文状況・リスク監視）
- Paper Trading 用の分離された DB と Mock ブローカ（`KABUSYS_ENV=paper_trading`）
- AI を利用したニュースセンチメント評価（OpenAI API 経由）と市場レジーム検知
- 運用支援ツール（.env 設定ウィザード、設定検証、Paper Trading の検証レポート生成 等）
- ログ管理（コンソール + 日次ローテートファイル）、プロセス優先度設定ユーティリティ

設計上の留意点:
- 本番（live）・ペーパートレード（paper_trading）を環境変数 `KABUSYS_ENV` で切替える。
- Paper Trading は本番 DB と完全に分離（既定: `data/paper_trading.db`）。
- 自動環境ロード（.env の読み込み）はプロジェクトルートを検出して実行される（不要なら `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`）。

---

## 主な機能一覧

- 環境設定
  - `kabusys.config_setup` — 対話式 .env 作成ウィザード
  - `kabusys.validate_config` — 起動前の設定検証 CLI

- 実行／監視
  - `run_execution.py` — ExecutionEngine 起動スクリプト（発注エンジン）
  - `run_monitoring.py` — SystemMonitor のポーリングループ起動スクリプト
  - Kill Switch（`data/kill.flag`）による安全停止

- モニタリング
  - system_monitor, trade_monitor, risk_monitor, monitoring_engine, monitoring_db
  - リスクイベントのログ、ダッシュボード集計、kill.flag 書込み

- ポートフォリオ構築
  - 候補選定、等重・スコア重み、ポジションサイズ計算、セクター上限・レジーム乗数

- リサーチ
  - ファクター計算（momentum/value/volatility）、forward returns、IC 計算、統計サマリー

- AI コンポーネント
  - `news_nlp`：ニュースを OpenAI に投げて銘柄別スコアを生成して DB へ書込む
  - `regime_detector`：ETF（1321）の MA とマクロニュースで日次レジーム（bull/neutral/bear）判定

- ツール
  - `tools.paper_verification_report`：Paper Trading DB を解析して検証レポートを生成

- ユーティリティ
  - logging_setup（統一ログ設定）
  - process_priority（プロセス優先度 / CPU affinity 制御）

---

## 前提・依存関係（例）

- Python 3.9+（型注記やモジュール記法より推奨）
- 必要な Python パッケージ（代表例）:
  - duckdb
  - psutil
  - openai
  - （任意）pyyaml（設定検証で YAML パースを行う場合）
- SQLite（Python 標準の sqlite3 を利用）
- OpenAI を使用する機能は `OPENAI_API_KEY` が必要

※ requirements.txt は本リポジトリに含まれていない可能性があるため、プロジェクトに合わせて適宜作成してください。

例（インストール）:
```bash
python -m pip install duckdb psutil openai
# YAML 検証用に PyYAML を使う場合:
python -m pip install pyyaml
```

---

## 初期セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージをインストール（上記参照）
4. 環境変数設定
   - 対話式ウィザードで .env を作成:
     ```bash
     python -m kabusys.config_setup
     ```
   - ウィザード利用後、`.env` がプロジェクトルートに生成される（Git に絶対にコミットしないでください）。
   - もしくは必要な環境変数を直接設定:
     - 必須: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`
     - 任意（運用時）: `OPENAI_API_KEY`, `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_USER_ID`
     - DB パス: `DUCKDB_PATH`, `SQLITE_PATH`（監視用）, `PAPER_TRADING_SQLITE_PATH`（paper_trading 用）

5. 設定検証（起動前チェック）
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗にする厳格モード:
   python -m kabusys.validate_config --strict
   ```

6. データ / ログ ディレクトリの作成（通常は自動作成されるが確認推奨）
   - data/（SQLite 等）
   - logs/（ログファイル）

---

## 使い方

### 実行エンジン（ExecutionEngine）の起動
- 本番/ペーパーの切替は `KABUSYS_ENV` で指定:
  - development / paper_trading / live
- 起動コマンド:
  ```bash
  python -m kabusys.run_execution
  ```
- 補足:
  - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用し、ペーパートレード用 DB（既定: data/paper_trading.db）に記録します。
  - 起動時に `data/kill.flag` が既に存在する場合、エンジンは起動を中止します。
  - プロセス優先度を "high" に設定して起動します。
  - 実行中は `data/execution.pid` が PID ファイルとして設定されます。

### 監視ループの起動（SystemMonitor）
- 監視ループ起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
- 補足:
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可（デフォルト 60 秒）。
  - 監視は常に本番 sqlite_path を使用（KABUSYS_ENV にかかわらず）。
  - 停止フラグファイル（data/stop_requested.flag）を置くと監視ループが終了します。
  - 監視は system_status / trade_logs / risk_logs / dashboard 等へ書き込みます。
  - `KillSwitch` はリスク条件で `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送ります。

### Paper Trading 検証レポート生成
- コマンド例:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
- オプション:
  - `--db PATH` : SQLite DB ファイルを直接指定（デフォルトは環境変数 `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`）
- 出力: 稼働率 / 注文成功率 / レイテンシ 等のサマリと PASS/FAIL 判定

### 環境設定の注意点（本番向け）
- `KABUSYS_ENV=live` 設定時は、LINE 通知設定（`LINE_CHANNEL_ACCESS_TOKEN`, `LINE_USER_ID`）の設定忘れ等をチェック（validate_config が警告を出します）。
- `KILL_FLAG_CLEAR_ON_START=1` は本番では危険（自動的に kill.flag をクリアしてしまうため）。production では `0` を推奨。

---

## 主要 CLI / スクリプト一覧（実行方法）

- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

## 環境変数一覧（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

重要（運用・任意）:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI API を使う場合に必要（news_nlp / regime_detector）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒, デフォルト 60）
- PAPER_FILL_MODE — paper_trading の約定挙動: instant | partial | never | reject
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — アラート通知（任意）

---

## ディレクトリ構成（概要: src/kabusys ベース）

主要ファイル／モジュールのみ抜粋:

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理、自動 .env ロード機能
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — Execution 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書込む
    - regime_detector.py — 市場レジーム判定（MA + マクロ NLP）
  - portfolio/
    - portfolio_builder.py — 候補選定、等重/スコア重み
    - position_sizing.py — 株数計算、aggregate cap、lot 単位調整
    - risk_adjustment.py — セクター上限、レジーム乗数
  - research/
    - factor_research.py — momentum/value/volatility ファクター計算
    - feature_exploration.py — forward returns / IC / 統計サマリ
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化 / 永続層
    - system_monitor.py — システム・データ鮮度監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - trade_monitor.py — （trade 関連の監視: ファイルに含まれる）
    - monitoring_engine.py — 各 Monitor を束ねる
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — （アラート通知管理: 実装参照）
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（stdout + 日次ファイル）
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
  - data/（実行時に作成されることが想定）
    - *.db, kill.flag, stop_requested.flag, execution.pid 等

※実際のファイル一覧はリポジトリの tree を参照してください。上記は代表的な構成の抜粋です。

---

## 運用上の注意 / ベストプラクティス

- 本番起動前に `python -m kabusys.validate_config` で必須環境変数や設定ファイルを検証してください。
- `.env` は機密情報を含むため、決して Git にコミットしないでください（config_setup のヘッダにも注意喚起あり）。
- `KABUSYS_ENV=live` 時は `KILL_FLAG_CLEAR_ON_START` を `0` にしておくことを強く推奨します。
- Paper Trading は本番と分離された DB に記録されるため、テスト／検証の際はこちらを利用してください。
- OpenAI の呼び出しは API の可用性に依存します。API 失敗時のフォールバックやリトライ処理が組み込まれていますが、運用時のコスト／レート制限には注意してください。
- ログ・DB のバックアップ・削除運用を検討してください（特に DuckDB/SQLite ファイルサイズ）。

---

## 開発者向け補足

- 主要なモジュールは純粋関数（副作用なし）で設計されている部分が多く、ユニットテストが容易です（例: portfolio/*.py, research/*.py）。
- DB への書き込み・トランザクションは明示的に行われる（`BEGIN` / `COMMIT` / `ROLLBACK` の利用例あり）。
- OpenAI API 呼び出しは内部でラップされており、テスト時は該当関数をモック可能です（モジュール内で `_call_openai_api` を patch する想定）。

---

必要であれば、README に以下を追加できます:
- requirements.txt の推奨内容（pin 固定）
- デプロイ / systemd / supervisor 用の unit ファイルテンプレート
- サンプル .env.example（各キーの説明付き）
- より詳細なディレクトリ tree（自動生成）

追加希望があれば教えてください。