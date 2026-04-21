# KabuSys — README (日本語)

このドキュメントは、KabuSys コードベースの概要・セットアップ・使い方を日本語でまとめた README です。KabuSys は日本株自動売買・リサーチ・監視を支援するモジュール群を含むプロジェクトです（このリポジトリは実運用向けコンポーネントを多数含みます）。

重要: この README はコードベースから読み取れる実装意図に基づき作成しています。実際の運用では必ずテスト環境で動作確認を行い、機密情報（.env）は Git にコミットしないでください。

---

目次
- プロジェクト概要
- 主な機能一覧
- 必要環境・依存パッケージ
- セットアップ手順
- 使い方（主要スクリプト・コマンド）
- 環境変数（主なもの）
- 動作の仕組み（概要）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムの基盤となるライブラリ/スクリプト群です。以下の要素を含みます（コード分割により、監視・発注・ポートフォリオ構築・ファクター計算・AI を用いたニュース解析などが独立モジュールとして実装されています）。

主な設計方針：
- データ永続化に SQLite / DuckDB を併用（監視ログは SQLite、分析は DuckDB）
- Paper Trading と Live を分離（Paper は専用 SQLite を使用）
- 設定は .env を中心に管理。対話式ウィザード・検証ツールあり
- ロギング、プロセス優先度調整など運用向けユーティリティ付き
- OpenAI を用いたニュース NLP / レジーム判定機能（APIキー必須）

---

## 主な機能一覧

- ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper Trading 時は MockBroker を使用し、専用 DB にログを残す
  - 実行スレッドの起動・停止、PIDファイル管理、停止フラグ対応

- Monitoring / MonitoringEngine（run_monitoring.py）
  - System / Trade / Risk モニタを定期ポーリング
  - kill.flag による ExecutionEngine 強制停止（KillSwitch）
  - 監視ログを SQLite に記録（monitoring_db）

- Portfolio 構築ユーティリティ
  - 候補選定、等金額／スコア重み、ポジションサイズ計算、セクターキャップ・レジーム調整

- Research（DuckDB を使ったファクター計算・特徴量解析）
  - momentum, volatility, value ファクター
  - 将来リターン計算、IC（Information Coefficient）など

- AI モジュール
  - news_nlp: OpenAI を使った銘柄別ニュースセンチメント付与（ai_scores へ書き込み）
  - regime_detector: マクロセンチメント + ETF MA を合成して市場レジーム判定

- ツール
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env / config/*.yaml 検証 CLI
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成

- ユーティリティ
  - logging_setup: 一貫したログ設定（コンソール + 日次ローテーションファイル）
  - process_priority: プロセス優先度／CPU affinity 設定ユーティリティ

---

## 必要環境・依存パッケージ

（最低限の推奨パッケージ。実運用では requirements.txt を整備してください）

- Python 3.10+
- duckdb
- psutil
- openai (AI モジュールを使う場合)
- PyYAML（validate_config の YAML 検証を行いたい場合）
- （必要に応じて）その他 DB ドライバなど

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を作成・有効化
2. 必要パッケージをインストール（上記参照）
3. 初期設定ファイル（.env）を作成
   - 対話式ウィザードを使う:
     ```bash
     python -m kabusys.config_setup
     ```
   - ウィザードは .env を生成します。生成後は必須値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を正しく設定してください。
4. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # 警告を厳密に扱う場合:
   python -m kabusys.validate_config --strict
   ```
5. 必要なディレクトリを作成（data, logs 等は自動作成されることが多いですが、権限やパスの確認を推奨）
   ```bash
   mkdir -p data logs
   ```
6. OpenAI を使う場合は環境変数 OPENAI_API_KEY を設定するか、score_news / score_regime 呼び出し時にキーを渡す

---

## 使い方（主要スクリプト）

- 実行エンジン（ExecutionEngine）を起動:
  - 本番 or 開発は KABUSYS_ENV 環境変数で制御（development / paper_trading / live）
  - Paper Trading の場合、専用 DB（デフォルト: data/paper_trading.db）に記録され、本番 DB と分離されます。
  ```bash
  # 例: paper trading 環境で起動
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- 監視ループを起動:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト: 60）
  - 監視は常に本番 sqlite_path を使う（KABUSYS_ENV にかかわらず）
  ```bash
  python -m kabusys.run_monitoring
  # 例: 30秒間隔
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- 停止制御:
  - run_execution / run_monitoring はプロジェクトルートの data/stop_requested.flag を検知して安全終了します。
    - 停止したい場合はこのファイルを作成してください（任意の内容で可）。
  - KillSwitch: 監視が危険な状況を検出した際に data/kill.flag を作成し、ExecutionEngine に停止シグナルを送ります。
    - kill.flag が存在すると ExecutionEngine 側で検知して適切に停止します。
  - run_execution は起動時に KILL_FLAG_CLEAR_ON_START が 1 の場合 kill.flag をクリアする設定があります（本番では 0 推奨）。

- .env 管理:
  - 対話式ウィザード:
    ```bash
    python -m kabusys.config_setup
    ```
  - 設定検証:
    ```bash
    python -m kabusys.validate_config
    ```

- Paper Trading 検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11
  ```

- AI 関連（ニューススコア・レジーム判定）:
  - OpenAI API キーを環境変数 OPENAI_API_KEY に設定するか、関数呼び出しで明示的に渡します。
  - 例（Python から）:
    ```python
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,1), api_key="sk-...")
    ```

---

## 主な環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading のフィルモード（instant/partial/never/reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）
- PID_FILE_PATH / PID ファイルは data/execution.pid 等に保存されます（設定可能）

---

## 動作の仕組み（概観）

- run_execution:
  - 設定を読み、プロセス優先度を "high" に設定（psutil を用いる）
  - 環境に応じて SQLite の参照パスを切替（paper_trading の場合は paper_sqlite_path）
  - BrokerClient を生成し、OrderRepository / OrderManager / RiskManager / Reconciler 等を組み立てる
  - ExecutionEngine を別スレッドで起動し、data/stop_requested.flag を監視して停止

- run_monitoring:
  - プロセス優先度を "high" に設定
  - 監視用 DB（SQLite）と DuckDB に接続
  - SystemMonitor（プロセス稼働・データ鮮度）、TradeMonitor、RiskMonitor を使って定期チェック
  - KillSwitch により条件を満たせば data/kill.flag を書き込み Execution を停止させる
  - MONITOR_POLL_INTERVAL に従いループ

- DB：
  - monitoring_db.init_monitoring_db() により監視用テーブル群を冪等で作成
  - MonitoringDB クラスは監視ログの読み書きを担う
  - DuckDB は分析・リサーチ用に利用

---

## ディレクトリ構成（抜粋）

以下はコードベース内の主なファイル／ディレクトリ（src/kabusys 配下）です。実際のプロジェクトルートは src/ をパッケージルートとして想定しています。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック (.env 自動読み込み含む)
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py            — ニュースを OpenAI でスコアリングして ai_scores へ書き込む
    - regime_detector.py     — マクロ + ETF MA を合成してレジーム判定
    - __init__.py

  - monitoring/
    - monitoring_db.py       — SQLite 用永続化層（schema init 等）
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - system_monitor.py      — システム稼働・データ鮮度監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みロジック
    - (trade_monitor 等 他ファイル)

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py

  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py

  - tools/
    - paper_verification_report.py
    - __init__.py

  - utils/
    - logging_setup.py       — 共通ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity
    - __init__.py

（実際のリポジトリには更に execution / data / strategy 等のサブパッケージやスクリプトが存在する可能性があります）

---

## 運用上の注意点

- .env に機密情報（API トークン / パスワード）を保存する場合は取り扱いに注意し、Git 等にコミットしないでください。
- KABUSYS_ENV=live 設定時は、本番発注が行われるため実設定値（API パスワード・通知設定・リスクパラメータ等）を十分確認してください。
- kill.flag / stop_requested.flag / PID ファイル周りは運用オペレーションでの合意を持って扱ってください（手動停止 / 自動停止の混在で意図しない停止が発生することがあります）。
- OpenAI 呼び出しはコストがかかります。API キー管理と呼び出し頻度に注意してください。

---

必要であれば、README にサンプル .env テンプレートや systemd / supervisor 用のサービス定義例、より詳細なディレクトリツリー、ユニットテスト・CI 実行手順などを追加します。どの情報を追加したいか教えてください。