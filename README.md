# KabuSys

日本株自動売買システムの一部（ライブラリ / 実行スクリプト / ツール群）。

この README は提供されたコードベースに基づいて、日本語でプロジェクト概要・機能一覧・セットアップ手順・使い方・ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買および関連解析パイプラインを構成するモジュール群です。主な責務は以下です。

- 注文の生成・発注（ExecutionEngine、OrderManager 等）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch の実装
- ポートフォリオ構築（候補選定、配分、ポジションサイズ計算、セクター制限等）
- 研究用ファクター計算・特徴量解析（DuckDB を利用）
- ニュースの NLP によるセンチメント評価（OpenAI API 経由）
- ペーパートレード用の検証レポート出力 等

設計上の特徴：
- 設定は環境変数 / .env ファイルで管理（自動ロード機能あり）
- 本番 DB とペーパートレード DB の分離（KABUSYS_ENV により切替）
- DuckDB を分析用に利用、SQLite を監視ログ・取引ログ保管に利用
- ロギングは統一的に設定（stdout + 日次ローテーションファイル）

---

## 機能一覧（抜粋）

- 起動スクリプト
  - run_execution.py — ExecutionEngine（発注エンジン）起動
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db を使用して本番 DB と分離
  - run_monitoring.py — SystemMonitor ポーリングループ起動
    - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は monitoring 用の sqlite_path を常に使用（環境にかかわらず本番 sqlite_path）
- 設定関連
  - config_setup.py — 対話式 .env 生成ウィザード
  - validate_config.py — 起動前の設定検証 CLI（--strict で警告も fail 扱い）
- ツール
  - tools.paper_verification_report — ペーパートレード検証レポート生成（期間指定可能）
- 監視/リスク管理
  - monitoring.* : SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch 等
  - monitoring_db: SQLite を用いた永続化層（テーブル作成・マイグレーション含む）
- ポートフォリオ構築
  - portfolio.* : 候補選定、重み計算、ポジションサイズ、セクター制限、レジーム乗数
- 研究用
  - research.* : ファクター計算（momentum/value/volatility）や IC 計算、特徴量探索
- AI 関連
  - ai.news_nlp — ニュース記事を OpenAI でセンチメント評価して ai_scores に書き込み
  - ai.regime_detector — MA200 とマクロニュースを組み合わせて市場レジーム判定

---

## 必須・推奨環境 / 依存

最低限必要なもの（主なパッケージ）：

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（設定検証で YAML 検証を行いたい場合、任意だが推奨）

例（pip）:
```
pip install duckdb psutil openai pyyaml
```

SQLite は Python 標準ライブラリに含まれます。

---

## セットアップ手順

1. リポジトリをクローン／展開
2. Python 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt
   ```
   requirements.txt がない場合は上記の主要パッケージを個別にインストールしてください。
4. .env の作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - もしくはプロジェクトルートに .env を配置（.env.example を参照して作成）
5. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も FAIL にする
   ```

主要な必須環境変数（.env に設定必須）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な任意 / デフォルト値
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI を使用する機能で必要
- PAPER_FILL_MODE: ペーパートレードの約定動作（instant/partial/never/reject、デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

Settings モジュールの挙動:
- プロジェクトルートが特定できれば `.env` → `.env.local` の順で自動読み込みされます（OS 環境変数は保護される）。
- 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 使い方（代表的コマンド）

- ExecutionEngine（発注エンジン）を起動
  ```
  # 本番/開発/ペーパートレードを env で切り替え
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  # もしくは
  python -m kabusys.run_execution
  ```
  補足:
  - KABUSYS_ENV=paper_trading の場合、MockBroker を用いて `data/paper_trading.db` に記録します（本番 DB と完全分離）。
  - 実行中は `data/execution.pid` が利用されます。`data/stop_requested.flag` が存在すると起動せず停止します。

- SystemMonitor（監視ループ）を起動
  ```
  # ポーリング間隔を環境変数で変更（秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  補足:
  - デフォルト 60 秒。
  - 監視は Settings の sqlite_path（通常 data/monitoring.db）を常に使用します（KABUSYS_ENV に依存しない）。
  - 監視ループ中にプロセス優先度が "high" に設定されます（set_process_priority）。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ペーパートレード検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を手動指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- OpenAI を利用する機能（ニューススコアリング / レジーム判定）
  - 環境変数 `OPENAI_API_KEY` を設定するか、API キーを関数呼び出しに渡してください。
  - API エラーはリトライ等のフェイルセーフが実装されていますが、未設定の場合は例外になります。

---

## 運用上のメモ（重要）

- Kill Switch（監視側で保護機能）
  - リスク条件（ドローダウン超過、ポジション上限超過等）を検出すると `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送ります。
  - kill.flag をクリアしたい場合は `data/kill.flag` を手動で削除するか、起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定して自動クリアを行えます（本番では危険なので推奨しません）。
- DB（SQLite / DuckDB）
  - monitoring 用の SQLite（デフォルト `data/monitoring.db`）は監視ログやトレードログを格納します。
  - ペーパー用 SQLite（KABUSYS_ENV=paper_trading）: `data/paper_trading.db`（PAPER_TRADING_SQLITE_PATH で上書き可能）
  - DuckDB（デフォルト `data/kabusys.duckdb`）は分析・研究用テーブルを置く想定です。
- ロギング
  - デフォルトで stdout と日次ローテートファイル（logs/<app_name>.log）に出力されます。
  - LOG_DIR 環境変数でログ保存先を変更できます。ログディレクトリが作成できない場合はファイル出力をスキップして stdout のみになります。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトルート / src/kabusys 想定）

- src/kabusys/
  - __init__.py
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングスクリプト
  - config.py                — Settings クラス（環境変数・.env 自動ロード）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py      — レジーム判定（MA200 + マクロ NLP）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル作成 & 永続化 API
    - monitoring_engine.py   — Monitor を束ねるエンジン
    - system_monitor.py      — システム監視（CPU/メモリ/ディスク・データ鮮度）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 管理
    - trade_monitor.py       — （存在を想定、取引監視ロジック）
    - alert_manager.py       — （存在を想定、通知管理）
  - portfolio/
    - __init__.py
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定・aggregate cap
    - risk_adjustment.py     — セクター上限・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py     — モメンタム/ボラティリティ/バリュー計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - utils/
    - __init__.py
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

（注）実際のリポジトリには data / logs 等のディレクトリや追加モジュール（execution.*, data.* など）が存在する想定です。

---

## よくある操作例

- 監視を60秒ごとに起動（デフォルト）
  ```
  python -m kabusys.run_monitoring
  ```
- 監視を30秒ごとに起動
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- ペーパートレードでエンジン起動（MockBroker 使用）
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
- .env を生成して検証
  ```
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

---

## 開発・拡張時の注意点

- Settings はプロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を自動ロードします。テストで自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- AI 関連（news_nlp / regime_detector）は OpenAI API に依存するため、API キーの管理とレート制限に注意してください。失敗はフェイルセーフとなるよう実装されていますが、結果の信頼性はログで確認してください。
- データ鮮度チェックや発注ロジックはルックアヘッドバイアスを避ける設計になっています。外部から日付を与えるテストや再現性の確保に配慮してください。
- Log ファイルはデフォルトで 30 日分保持する TimedRotatingFileHandler を利用します。ディスク使用量に注意してください。

---

もし README に追加したい詳細（例えば各モジュールの API ドキュメント、実運用時の systemd / supervisor サンプル、テスト方法や CI 設定例など）があれば教えてください。必要に応じて追記・整形します。