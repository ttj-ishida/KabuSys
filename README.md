# KabuSys

日本株向け自動売買システムのリポジトリ（ミニマル版）。  
この README は付属のコードベースに基づいて、プロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究パイプラインを提供するコード群です。  
主な目的は以下です。

- 日次のファクター計算・特徴量抽出（DuckDB ベース）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ決定）
- 実行エンジン（ExecutionEngine）による発注（本番 / ペーパートレード切替）
- 監視システム（SystemMonitor / TradeMonitor / RiskMonitor）による状態監視と Kill Switch
- ニュース NLP による AI ベースのセンチメント評価（OpenAI）
- ペーパートレード検証用レポート生成ツール

設計方針として、本番 DB とペーパートレード DB を分離し、安全に検証できること、LLM 呼び出しはフェイルセーフで実行されること、設定の自動ロードや検証ツールを備えることが挙げられます。

---

## 主な機能一覧

- Execution
  - 実行エンジン起動スクリプト: `run_execution.py`
  - 本番 / ペーパートレード切替（`KABUSYS_ENV=paper_trading`）
  - ブローカークライアントの抽象化（MockBrokerClient をペーパートレードで使用）
- Monitoring
  - システム稼働・データ鮮度・発注ログなどを定期的にチェック: `run_monitoring.py`
  - Kill Switch（条件を満たすと `data/kill.flag` を書き込み ExecutionEngine を停止）
  - 監視用 SQLite DB（`monitoring_db.py`）にログ永続化
- Research / Data
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）: `research` モジュール（DuckDB を使用）
  - LLM を用いたニューススコアリング（`ai/news_nlp.py`）
  - 市場レジーム判定（`ai/regime_detector.py`）
- Portfolio construction
  - 候補選定、等重・スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数
- ツール
  - ペーパートレード検証レポート生成: `kabusys.tools.paper_verification_report`
  - 対話式 .env 作成ウィザード: `kabusys.config_setup`
  - 設定検証 CLI: `kabusys.validate_config`
- ユーティリティ
  - ロギング設定（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定

---

## 必要要件（推奨）

- Python 3.10+
- pip
- OS: Linux / macOS / Windows（ほとんどのユーティリティはクロスプラットフォーム対応。ただし一部の CPU affinity / priority は制限あり）

必要な Python パッケージ（主なもの）:
- duckdb
- psutil
- openai
- pyyaml（設定ファイル検証のため任意）
- その他（必要に応じてプロジェクト固有の依存を追加）

（実際のプロジェクトでは `requirements.txt` を用意することを推奨します）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージのインストール（例）
   ```
   pip install duckdb psutil openai pyyaml
   ```

4. ディレクトリ作成（必要な場合）
   ```
   mkdir -p data logs
   ```

5. 環境変数設定（.env の作成）
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは `.env` を手動で用意する（下の「重要な環境変数」参照）。

6. 設定検証（起動前に推奨）
   ```
   python -m kabusys.validate_config
   # 警告も失敗にしたい場合:
   python -m kabusys.validate_config --strict
   ```

---

## 重要な環境変数（主なもの）

以下はコード中で参照される主要な環境変数とデフォルト値です（.env に設定します）。

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使用する場合に必須)
- LINE_CHANNEL_ACCESS_TOKEN (任意、アラート用)
- LINE_USER_ID (任意、アラート受信先)
- KABUSYS_ENV (実行環境: development / paper_trading / live) — デフォルト: development
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR) — デフォルト: INFO
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード DB, デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (paper_trading の fill 挙動: instant / partial / never / reject) — デフォルト: instant
- PID_FILE_PATH (実行エンジンの pid ファイル, デフォルト: data/execution.pid)
- KILL_FLAG_PATH (kill flag ファイルパス, デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1 — 起動時に kill.flag を自動削除するか、デフォルト 0)
- MONITOR_POLL_INTERVAL (監視ループのポーリング間隔秒, デフォルト: 60) — run_monitoring で利用

---

## 基本的な使い方

- 環境作成・検証
  1. `.env` を作成（`python -m kabusys.config_setup`）
  2. 設定を検証（`python -m kabusys.validate_config`）

- 実行エンジン起動（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient が使用され、`data/paper_trading.db` に記録されます（本番 DB と完全分離）。
  - プロセス優先度を High に設定して起動します（`psutil` の権限に依存）。

- 監視ループ起動（SystemMonitor）
  ```
  python -m kabusys.run_monitoring
  ```
  - `MONITOR_POLL_INTERVAL` 環境変数でポーリング秒数を上書き可能（例: `MONITOR_POLL_INTERVAL=30`）。
  - 監視は常に本番 sqlite_path を使用（環境に関わらず監視 DB は指定の SQLite を参照します）。
  - 監視中に `data/stop_requested.flag` が存在するとループを終了します。

- 停止 / Kill Switch
  - ExecutionEngine を強制停止させたい場合は `data/kill.flag` を作成（KillSwitch が検出すると ExecutionEngine 停止をトリガー）  
    KillSwitch はリスク基準（ドローダウン、ポジション上限など）を評価して自動で書き込みます。
  - 監視ループや実行エンジンの即時停止（テスト用）は `data/stop_requested.flag` の作成で行われます。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に `kill.flag` を自動でクリアします（本番では推奨されません）。

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` オプションで別の SQLite ファイルを指定可能（環境変数 `PAPER_TRADING_SQLITE_PATH` でも指定可）。
  - レポートは稼働率、注文成功率、送信率、レイテンシ（P95）などを表示し、閾値に基づいて PASS/FAIL を判定します。

- AI 機能
  - news_nlp.score_news / ai.regime_detector.score_regime を DuckDB 接続と日付、OpenAI API キーで呼び出すことで ai_scores / market_regime が更新されます。
  - OpenAI の呼び出しは再試行やエラー時のフォールバック等が組み込まれていますが、API キーは必須です。

---

## ログと DB

- ログ
  - ロギングは共通設定ユーティリティ `kabusys.utils.logging_setup.setup_logging` で行われます。
  - デフォルトは stdout と `logs/<app_name>.log`（日次ローテーション、30日保持）。
  - ログディレクトリは `LOG_DIR` 環境変数またはデフォルト `logs/`。

- DB
  - 分析用: DuckDB（デフォルト `data/kabusys.duckdb`）
  - 監視・軽量永続化: SQLite（デフォルト `data/monitoring.db`）
  - ペーパートレード: 別 SQLite（デフォルト `data/paper_trading.db`）

---

## ディレクトリ構成（抜粋）

以下はプロジェクト内の主要ファイル／ディレクトリの例（実際のリポジトリ全体に合わせて参照してください）。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - config_setup.py                — 対話式 .env ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポートツール
  - ai/
    - news_nlp.py                   — ニュース NLP スコアリング
    - regime_detector.py            — 市場レジーム判定
  - monitoring/
    - monitoring_db.py              — 監視 DB ラッパー（SQLite）
    - system_monitor.py             — システム監視
    - risk_monitor.py               — リスク監視（ドローダウン等）
    - kill_switch.py                — Kill Switch 管理
    - monitoring_engine.py          — 各 Monitor を束ねるエンジン
  - portfolio/
    - portfolio_builder.py          — 候補選定・重み計算
    - position_sizing.py            — 発注株数計算
    - risk_adjustment.py            — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py            — ファクター計算
    - feature_exploration.py        — IC / 統計解析
  - utils/
    - logging_setup.py              — ログ設定ユーティリティ
    - process_priority.py           — プロセス優先度設定ユーティリティ
  - monitoring/*.py                 — 上記監視関連

（上記はリポジトリ内の一部抜粋です。詳細はソースツリーを参照してください）

---

## よくある運用フロー（例）

1. 開発環境で `.env` を作成 → `python -m kabusys.config_setup`
2. 設定検証 → `python -m kabusys.validate_config`
3. DuckDB に過去価格データや財務データをロード（プロジェクト外のスクリプトで想定）
4. 研究用スクリプトを実行してファクターを検証（`kabusys.research` モジュールを利用）
5. ペーパートレードで ExecutionEngine を起動して挙動確認
   ```
   KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   ```
6. 監視を別プロセスで起動（常時監視）
   ```
   python -m kabusys.run_monitoring
   ```
7. 必要に応じて `data/kill.flag` を確認・クリア・作成して安全制御

---

## 注意事項 / 補足

- 本リポジトリの .env は機密情報（API キーやパスワード）を含みます。絶対にバージョン管理にコミットしないでください（`config_setup.py` のヘッダにも警告あり）。
- 本番環境（`KABUSYS_ENV=live`）では設定を十分に確認してください。`validate_config` は本番特有の注意点（LINE 通知設定や kill_flag の取り扱い）を警告します。
- `psutil` を使った優先度設定や affinity 設定は OS と権限に依存します。権限不足時は警告を出して続行します。
- OpenAI API を利用する機能は API 利用料が発生します。API キーは厳重に管理してください。
- DuckDB / SQLite のファイルパスは環境変数で簡単に切り替え可能です。ペーパートレード時は DB 分離が行われるため本番データへの影響はありません。

---

この README はコードベースの主要点をまとめたものです。実際に運用・拡張する際はソース内ドキュメント（docstring）、および付随するドキュメントファイル（例: PortfolioConstruction.md, StrategyModel.md 等）を参照してください。必要であれば README にさらに具体的なデプロイ手順、CI 設定、requirements.txt の例などを追加できます。