# KabuSys

日本株向け自動売買システムのコードベース README（日本語）です。本ドキュメントはリポジトリ内のスクリプトとモジュール群を簡潔にまとめ、セットアップと基本的な使い方を案内します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買および研究用モジュール群を提供するシステムです。主な目的は以下：

- 戦略・ポートフォリオ構築（ファクター計算、ポジションサイジング、セクター制約など）
- ExecutionEngine による発注実行（本番／ペーパートレードの切替）
- 監視（System / Trade / Risk のモニタリング、Kill Switch）
- AI 支援（ニュースセンチメント、レジーム判定）
- Research 用ユーティリティ（ファクター計算、IC 等）
- 運用支援ツール（環境設定ウィザード、設定検証、Paper Trading 検証レポート）

設計方針の一部：
- DB は DuckDB（分析用）と SQLite（監視・発注ログ）を使用
- Paper trading は本番 DB と分離（専用 SQLite）
- OpenAI を用いた NLP 機能（設定で有効化）
- 自動 .env ロード / 対話的設定ウィザードあり

---

## 主な機能一覧

- Execution
  - ExecutionEngine（発注・注文管理・リスク管理・リコンサイル）
  - Broker クライアントの切替（本番 / Mock（paper_trading））
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/データ鮮度/プロセス検知
  - TradeMonitor / RiskMonitor: 注文遅延やドローダウン・ポジション上限の監視
  - KillSwitch: 条件で `data/kill.flag` を書き込み ExecutionEngine を止める
  - MonitoringEngine: 監視各コンポーネントの統合ポーリング
- Portfolio Construction
  - 候補選定、重み付け（等金額・スコア重み）、ポジション数算出、セクター制限、レジーム乗数
- Research
  - ファクター計算（momentum, volatility, value）、forward returns、IC、統計サマリ
- AI
  - ニュースセンチメント（OpenAI を利用）
  - 市場レジーム判定（MA + マクロセンチメント）
- Tools
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成（tools/paper_verification_report）
- Utilities
  - ロギング設定（ログローテーション）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - 環境変数自動読み込み（プロジェクトルートの .env / .env.local）

---

## セットアップ手順

前提
- Python 3.9+（コードの型注釈や一部ライブラリ利用を想定）
- SQLite は標準組み込み（追加インストール不要）

必須 / 推奨パッケージ（pip）
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（設定ファイル検証を行う場合）
- その他要求パッケージがある場合は requirements.txt を用意している可能性があります（プロジェクトに合わせて追加）

インストール例:
- 仮想環境作成 (推奨)
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- パッケージインストール
  - pip install duckdb psutil openai PyYAML

初期設定 (.env)
1. 対話式ウィザードで .env を作成:
   - python -m kabusys.config_setup
2. もしくはテンプレート `.env.example` を参考に手動作成。
3. .env の自動読み込みはデフォルトで有効。テスト等で無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

設定検証:
- python -m kabusys.validate_config
- 警告もエラー扱いにしたい場合:
  - python -m kabusys.validate_config --strict

注意:
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- OpenAI 機能を使う場合:
  - OPENAI_API_KEY を環境変数に設定するか、score_regime/score_news の api_key 引数で渡す

DB パス（デフォルト）
- DuckDB: data/kabusys.duckdb  (Settings.duckdb_path)
- SQLite (monitoring): data/monitoring.db (Settings.sqlite_path)
- Paper trading 用 SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）

ログ
- デフォルトログディレクトリ: logs/
- ログファイル名: <app_name>.log（例: logs/execution.log, logs/monitoring.log）
- ログは日次ローテーション、30日保持

---

## 使い方（起動・運用）

### 環境の準備
1. 仮想環境を有効にする
2. 必要パッケージをインストール
3. python -m kabusys.config_setup で .env を作成
4. python -m kabusys.validate_config で設定を検証

### ExecutionEngine（実行本体）の起動
- 通常起動:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用 SQLite（`data/paper_trading.db`）へ記録します（本番 DB と分離）。
  - 起動時に `data/stop_requested.flag` が存在する場合は起動を止めます。
  - `_EXECUTION_PID`（`data/execution.pid`）に PID を書き、`stop` はフラグファイルで行います。
  - プロセス優先度は起動時に "high" に設定されます（可能な場合）。

停止方法:
- `data/stop_requested.flag` を作成すると実行ループは停止します。
- Kill Switch（`data/kill.flag`）が作成されると ExecutionEngine により停止されます（KillSwitch の評価条件に依存）。

### Monitoring（監視）の起動
- python -m kabusys.run_monitoring
- 挙動:
  - Monitoring は常に Settings.sqlite_path（本番 sqlite_path）を使用して監視情報を記録します（KABUSYS_ENV に依存しない）。
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能。デフォルト 60 秒。
  - `data/stop_requested.flag` を検知すると監視ループを終了します。

監視で行われる主なチェック:
- SystemMonitor: CPU/メモリ/Disk、プロセス生存確認、データ鮮度検査
- TradeMonitor: 注文滞留・約定異常などの検出
- RiskMonitor: ドローダウン・ポジション上限検出
- KillSwitch の評価により `data/kill.flag` を書き込むと ExecutionEngine に停止シグナルを送る

### ローカルでの短時間テスト・ユーティリティ
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）

### AI 機能（ニュース NLP / レジーム判定）
- ニュースのスコアリング:
  - 実行関数: kabusys.ai.score_news(conn, target_date, api_key=None)
  - OpenAI API キーを環境変数 `OPENAI_API_KEY` にセットするか、api_key 引数で渡す
- レジーム判定:
  - 実行関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI が必須（未設定時は ValueError）

注意:
- AI 機能は API レート制限や一時エラーに対してリトライ・フォールバックを行いますが、API キーの発行や料金に注意してください。

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
- LOG_LEVEL (DEBUG/INFO/...)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (paper_trading の模擬約定挙動: instant|partial|never|reject)
- OPENAI_API_KEY (AI 機能利用時)
- MONITOR_POLL_INTERVAL (監視のポーリング秒数、デフォルト: 60)
- KILL_FLAG_CLEAR_ON_START (本番環境での自動クリア抑止推奨: 0)

---

## 運用上の注意点

- 本番（KABUSYS_ENV=live）では `LINE_CHANNEL_ACCESS_TOKEN` / `LINE_USER_ID` を設定してアラートを受け取れるようにしてください。
- `KILL_FLAG_CLEAR_ON_START=1` は本番では危険です（Kill Switch を自動クリアしてしまうため）。デフォルトは `0` を推奨。
- Monitoring は常に production sqlite_path を使います。Paper trading の監視も別 DB に記録したい場合は適切にパスを設定してください。
- ログディレクトリの作成に失敗した場合はコンソール出力のみになります（警告が出ます）。
- プロセス優先度 / CPU affinity の設定は権限に依存します。権限不足の場合は警告ログが残り、処理は継続します。

---

## ディレクトリ構成（抜粋）

以下はリポジトリ内の主要ファイル / ディレクトリ（src/kabusys 配下を中心に抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック（.env 自動読み込み）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成スクリプト
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI）
  - research/
    - factor_research.py     — ファクター計算（momentum, value, volatility）
    - feature_exploration.py — forward returns, IC, 統計サマリ
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み付け
    - position_sizing.py     — 株数決定・投下資金制限・単元丸め
    - risk_adjustment.py     — セクター上限・レジーム乗数
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化・読み書きユーティリティ
    - system_monitor.py      — システム状態・データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション監視
    - trade_monitor.py       — （注文監視; ファイル中にあり）
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - kill_switch.py         — kill.flag の書き込みユーティリティ
    - alert_manager.py       — （通知管理; ファイル中にあり）
  - execution/
    - execution_engine.py    — 実行エンジン（メインロジック）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - utils/
    - logging_setup.py       — ログ初期化（コンソール + ローテートファイル）
    - process_priority.py    — プロセス優先度・CPU affinity 設定
  - data/                    — 実行時に使用されるデータ・DB・フラグファイル（例: monitoring.db, paper_trading.db, kill.flag, execution.pid）

（注: 上記はリポジトリ内の主要部のみ抜粋しています。実際のファイル一覧はリポジトリ全体をご参照ください。）

---

## 追加情報 / デバッグヒント

- 監視や実行ログは logs/<app_name>.log に出力されます。まずはログを確認してください。
- デバッグ時に環境変数 LOG_LEVEL=DEBUG を設定すると詳細ログが出ます。
- テストや CI で .env 自動ロードを無効にする場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB / SQLite に関するマイグレーション（カラム追加等）は monitoring_db.init_monitoring_db にて冪等で実施されます。
- OpenAI 呼び出しはリトライロジックや JSON 検証を含むため、レスポンスの不正や API 制限下でもシステム全体の停止を防ぐ設計です。

---

この README はコードベースの主要な動作と運用フローの把握を目的としています。詳細な仕様（戦略ロジック、ExecutionEngine の内部実装、ブローカー実装等）は該当モジュールのドキュメント・ソースコードの docstring を参照してください。質問や補足が必要なら教えてください。