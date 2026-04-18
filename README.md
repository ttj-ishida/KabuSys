# KabuSys

日本株自動売買システム（KabuSys） — 戦略・発注・監視・研究用ユーティリティ群を含むモノリポジトリ。

この README はリポジトリ内の主要スクリプト／モジュールの使い方、セットアップ手順、ディレクトリ構成を日本語でまとめたものです。

注意
- .env に機密情報（APIキー等）を保存します。絶対に Git にコミットしないでください。
- production（本番）で動かす場合は設定値を慎重に確認してください（`validate_config` による検証を推奨）。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。主な役割は次の通りです。

- 戦略（ファクター計算、特徴量解析、ポートフォリオ構築）
- 発注（ExecutionEngine、ブローカー抽象化 / ペーパートレード対応）
- 監視（システム状態・注文滞留・リスク監視・Kill Switch）
- 研究ツール（DuckDB を使ったファクター計算や検証レポート）
- AI支援（ニュースの NLP スコアリング、市場レジーム判定）

設計方針の特徴：
- DuckDB / SQLite により履歴・分析・監視データを永続化
- Paper Trading（テスト発注）と Live（実発注）を明確に分離
- LLM（OpenAI）を利用したニュース解析・レジーム判定
- 監視ループと Kill Switch による安全停止機構

---

## 機能一覧

- 環境設定ウィザード（.env 作成）: python -m kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml のチェック）: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番/ペーパートレード判定）: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading DB に記録
- Monitoring（監視）起動スクリプト: python -m kabusys.run_monitoring
  - 環境にかかわらず、本番用 sqlite_path を監視 DB として使用
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）
- Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
- AI モジュール:
  - ニュース NLP スコアリング: kabusys.ai.score_news
  - 市場レジーム判定: kabusys.ai.regime_detector
- ポートフォリオ構築ユーティリティ（候補選定 / 重み計算 / ポジションサイズ算出）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager）
- ユーティリティ: プロセス優先度 / CPU affinity 設定、.env パーサー 等

---

## 必要な依存関係（主なもの）

（プロジェクトに requirements.txt がない場合は個別にインストールしてください）

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config YAML 検証を行う場合）
- （その他、運用時に必要なブローカークライアントや追加ライブラリがある場合あり）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順（推奨ワークフロー）

1. リポジトリをクローンし仮想環境を作成・有効化する。

2. 必要パッケージをインストールする（上記参照）。

3. 環境変数を設定する
   - 対話式で .env を生成する（推奨）:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードはプロンプトに従って .env を生成します。

   - あるいは手動で `.env` を作成し、主要な設定を記載する。主なキーとデフォルト:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR)
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意）
     - KILL_FLAG_CLEAR_ON_START (0|1)

   - .env 自動読み込みについて:
     - 起動時にプロジェクトルートに `.env` / `.env.local` があれば自動で読み込まれます（ただし環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可）。
     - プロジェクトルートは `.git` または `pyproject.toml` を基準に探索します。

4. 設定検証（必須ではないが推奨）:
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告も失敗扱い
   ```

5. DB の初期化等は各スクリプトが起動時に必要なテーブルを作成します（Monitoring は init_monitoring_db を実行）。

---

## 実行方法（よく使うコマンド例）

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ExecutionEngine を起動（バックテストではなく実行プロセス）
  - デフォルト（env によって paper/live を切替）
  ```
  python -m kabusys.run_execution
  ```
  - ペーパートレードで起動する場合:
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  - 注意:
    - ペーパートレード時は `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。
    - 起動中、PID ファイル（data/execution.pid）が書かれます。停止フラグ（data/stop_requested.flag）を使って外部から停止できます。
    - kill.flag（data/kill.flag）は Kill Switch により書き込まれる可能性があります。

- Monitoring を起動（監視ループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更するには:
  ```
  export MONITOR_POLL_INTERVAL=30   # 30 秒ごとにポーリング
  python -m kabusys.run_monitoring
  ```
  - 監視は `Settings.sqlite_path`（デフォルト data/monitoring.db）を使用してログを永続化します。
  - 停止フラグ（data/stop_requested.flag）が置かれているとループを終了します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスはオプション `--db`、あるいは環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

- AI モジュール（プログラムから呼ぶ想定）
  - ニューススコアリング:
    - 関数: kabusys.ai.score_news.score_news(conn, target_date, api_key=None)
    - OpenAI API キーを `OPENAI_API_KEY` 環境変数か引数で指定
  - レジームスコア:
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 重要な運用ファイル / フラグ

- data/stop_requested.flag: 外部による停止要求を示すファイル（run_execution / run_monitoring が検出）
- data/execution.pid: ExecutionEngine が書き込む PID ファイル（SystemMonitor が存在チェック）
- data/kill.flag: KillSwitch（リスク発生時）が書き込む停止フラグ。ExecutionEngine はこれを参照して停止
- DB:
  - DuckDB: data/kabusys.duckdb（分析用）
  - SQLite (monitoring): data/monitoring.db（監視ログ）
  - SQLite (paper trading): data/paper_trading.db（ペーパートレード用。KABUSYS_ENV=paper_trading 時に使用）

設定 `KILL_FLAG_CLEAR_ON_START=1` にすると ExecutionEngine 起動時に kill.flag を自動クリアしますが、本番では推奨されません（誤って自動クリアしてしまうと安全機構が無効化されます）。

---

## 設定（主な環境変数一覧とデフォルト）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR（デフォルト: INFO）

- DB / ファイルパス
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag

- Monitoring / Execution
  - MONITOR_POLL_INTERVAL: 監視ポーリング秒数（デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 0 or 1（本番では 0 推奨）
  - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading のモック挙動）

- OpenAI
  - OPENAI_API_KEY

---

## ディレクトリ構成（主要ファイル）

リポジトリの src/kabusys を基準に主要ファイルを抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動読み込み）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 監視ログの永続化層（テーブル作成含む）
    - monitoring_engine.py   — 複数モニタの統合ループ
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py       — 注文滞留・約定異常監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch 制御（kill.flag 書き込み）
    - alert_manager.py       — （アラート送信用の抽象化：実装は別途）
  - execution/
    - execution_engine.py    — ExecutionEngine（起動・セッション管理）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
    - order_record.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュースの LLM によるセンチメント（ai_scores への書込）
    - regime_detector.py     — ETF MA と LLM を混合した市場レジーム判定
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成

（上記は主要モジュールの一覧です。実際にはさらに補助モジュールが存在します。）

---

## 運用上の注意とベストプラクティス

- .env は機密情報を含みます。絶対にバージョン管理にコミットしないでください。
- 本番（KABUSYS_ENV=live）での実行前に `python -m kabusys.validate_config` を実行し、警告やエラーを確認してください。
- Kill Switch / Monitoring が正常に動作することを事前にテストしてください（監視プロセスは .env の KILL_FLAG_CLEAR_ON_START に依存）。
- OpenAI API 利用時はレート制限やコストに注意してください。失敗時にはフォールバックを設ける設計になっていますが、事前に利用量を想定してください。
- DuckDB / SQLite ファイルのバックアップ・ローテーション方針を決めてください。データが蓄積するとファイルサイズが増えます。

---

## 開発者向けメモ

- モジュールは可能な限り純粋関数（副作用なし）で設計された部分と、DB 書き込み等の I/O 層を分離しています（単体テストが書きやすい）。
- OpenAI 呼び出しなど外部接続箇所はテストでモックしやすいように設計されています（private 呼出し関数を patch 可能）。
- config の自動読み込みはプロジェクトルートを基準に行われ、CWD に依存しないよう実装されています。

---

README に書かれていない細かい挙動や内部設計は、各モジュールの docstring / コメントを参照してください。追加で README に追記したい情報（デプロイ手順、CI/CD、運用 runbook など）があれば指示してください。