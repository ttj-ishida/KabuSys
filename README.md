# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買／研究／監視に関するユーティリティ群および起動スクリプト群をまとめたものです。  
本 README はコードベース（src/kabusys配下）を元に、導入・起動・主要機能の概要を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は次の責務を持つモジュール群で構成されています。

- 実行エンジン（ExecutionEngine）の起動・発注管理（run_execution.py、execution/*）
- システム監視（SystemMonitor / MonitoringEngine）と Kill Switch による自動停止（monitoring/*）
- ポートフォリオ構築・ポジションサイズ計算（portfolio/*）
- ファクター計算・特徴量探索（research/*）
- ニュース NLP を使ったセンチメント算出・レジーム判定（ai/*）
- 設定読み込み・ウィザード・検証ツール（config_*.py, validate_config.py）
- 各種ユーティリティ（utils/*）
- 運用用ツール（tools/*）

設計方針の一部：
- 本番・ペーパートレードはデータベースファイルで分離（paper_trading 用 DB を使用）
- ルックアヘッドバイアス防止のため日付参照は明示的な引数で扱う設計
- OpenAI（LLM）呼び出しはエラー耐性あり（リトライ・フェイルセーフ）

---

## 主な機能一覧

- 環境設定ウィザード（.env の対話作成）：python -m kabusys.config_setup
- 設定検証 CLI（.env、config/*.yaml のチェック）：python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い paper_trading DB に記録
  - 停止フラグ（data/stop_requested.flag / data/kill.flag）で安全に停止
- Monitoring 起動スクリプト（run_monitoring.py）
  - SystemMonitor のポーリング（デフォルト 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能）
  - 監視ログは SQLite（settings.sqlite_path）に永続化（監視は環境に関係なく本番 sqlite_path を使用）
- Monitoring の個別コンポーネント
  - SystemMonitor：CPU/MEM/DISK、プロセス生存、データ鮮度チェック
  - TradeMonitor：注文滞留・約定異常などの検出（trade_logs等参照）
  - RiskMonitor：ドローダウン・ポジション数監視（dashboard テーブルを参照）
  - KillSwitch：リスク条件で data/kill.flag を書き、ExecutionEngine 停止を誘発
  - AlertManager（通知管理）経由で LINE 等への通知（設定がある場合）
- ポートフォリオ構築ユーティリティ（選定・重み・サイズ決定・セクター制約）
- 研究用モジュール（DuckDB を用いたファクター計算、forward returns、IC 計算）
- AI モジュール
  - news_nlp.score_news：ニュース記事を集約して LLM でセンチメント算出 → ai_scores に書き込み
  - regime_detector.score_regime：MA200 とマクロ記事の LLM センチメントを合成して市場レジーム判定
- 運用ツール
  - tools/paper_verification_report.py：ペーパートレード DB を解析して検証レポートを生成

---

## セットアップ手順（開発・運用向け）

前提：
- Python 3.10+（typing | None 等の使用から推測）
- DuckDB、psutil、openai、（必要に応じて）PyYAML などが必要

1. リポジトリをクローンして作業ディレクトリに移動
   (この README は src/kabusys 配下の実装を前提としています)

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     ```
     pip install -r requirements.txt
     ```
   - 個別に必要なパッケージ:
     ```
     pip install duckdb psutil openai
     # 任意: pip install pyyaml
     ```

4. .env の作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   - 生成後、必要な環境変数が設定されているか確認してください。
   - 必須環境変数（最低限必要なもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 任意・運用用:
     - KABUSYS_ENV (development / paper_trading / live)
     - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL, LOG_DIR 等

5. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告を厳密に扱いたい場合は --strict を追加
   ```

6. データディレクトリやログディレクトリを作成（必要に応じて）
   - デフォルトの DB / PID / flag パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - PID / flag: data/execution.pid, data/stop_requested.flag, data/kill.flag
   - Log ディレクトリ: logs/（LOG_DIR 環境変数で変更可）

---

## 使い方（起動例と主要コマンド）

- ExecutionEngine を起動（通常）
  ```
  python -m kabusys.run_execution
  ```
  挙動:
  - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用し、MockBrokerClient により発注を模擬記録。
  - 起動前に data/stop_requested.flag が存在する場合は起動しません。
  - 実行中は data/execution.pid を作成します。停止は stop flag を置くことで行えます。

- Monitoring を起動（ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
  - 監視は常に Settings.sqlite_path（本番 monitoring DB）を参照します。
  - 停止はプロセスに KeyboardInterrupt を送るか、上位の stop flag を置くことで行います（data/stop_requested.flag を検出して終了）。

- Kill Switch をトリガーする（手動）
  - KillSwitch は data/kill.flag を作成します。ExecutionEngine は起動時にこのフラグを見て動作を制御します。
  - kill.flag は Settings.kill_flag_path（デフォルト data/kill.flag）から参照されます。
  - 実運用では Monitoring が自動で kill.flag を書くことがあります（例: ドローダウン超過）。

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を指定
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```
  - 出力は標準出力にテキストレポートを表示します。

- AI（ニューススコア / レジーム判定）
  - OpenAI APIキーが必要（OPENAI_API_KEY 環境変数 または関数引数）
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date を受け取ります。アプリケーション内から呼び出して利用してください。

---

## 主要設定項目（主な環境変数）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード

- 実行環境
  - KABUSYS_ENV: development / paper_trading / live
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアする（1 = クリア、0 = クリアしない）

- DB / ファイルパス
  - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
  - PID_FILE_PATH: PID ファイルパス（デフォルト data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）

- ログ
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR: ログ保存先ディレクトリ（デフォルト logs/）

- モニタリング
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

- AI
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 用）

---

## 停止・フラグの取り扱い

- data/stop_requested.flag
  - run_execution.py、run_monitoring.py はこのファイルを監視しており、存在すると起動を止めたり実行を停止します（運用側の手動停止用）。
- data/kill.flag
  - KillSwitch が生成するフラグ。ExecutionEngine 起動時に存在すると自動起動を抑止することが期待されます。運用上は本番での不用意な自動クリアを避けるため KILL_FLAG_CLEAR_ON_START を `0` にすることを推奨します。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主なファイル・ディレクトリ構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py       — (注文監視)
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       — （通知管理）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - data/                    — デフォルトで使われる DB/flag/pid の格納先（repo ルートの data/）

※ 実際のファイルは上記以外にも細かいモジュールがあります。詳細は各ファイルの docstring を参照してください。

---

## 運用上の注意点（要確認）

- 本番環境（KABUSYS_ENV=live）では設定を厳密に確認してください（validate_config の警告を重視）。
- Kill Switch / stop flag の扱いは厳格に運用ルールを定めてください（誤って本番を停止させるリスク）。
- OpenAI を使う機能は API 利用料・レート制限に注意してください。API キーは安全に管理してください。
- DuckDB / SQLite ファイルのバックアップやファイルアクセスの競合に注意（同一ファイルに複数プロセスが同時書込みするような運用は避ける）。
- run_monitoring は監視ログのために本番 sqlite_path を使用します（環境変数にかかわらず本番監視 DB に書き込みます）。運用時は sqlite_path の設定に注意してください。

---

## よく使うコマンド一覧（まとめ）

- .env 作成（ウィザード）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Execution 起動
  ```
  python -m kabusys.run_execution
  ```

- Monitoring 起動
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README に書ききれない内部仕様（API の詳細、Engine の挙動、OrderRepository の契約など）は各モジュールの docstring に詳述されています。開発・運用の際は該当ファイルの docstring を参照してください。

必要であればこの README を基にさらに詳細な運用手引き（デプロイ手順、systemd ユニット例、監視プレイブック等）を作成できます。ご希望があれば教えてください。