# KabuSys

日本株向け自動売買システム（ライブラリ＋起動スクリプト群）

この README はコードベース（src/kabusys/*）を対象とした概要・セットアップ手順・使い方・ディレクトリ構成の説明書です。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能群を提供します。

- 市場データ集計・ファクター計算（DuckDB ベース）
- ポートフォリオ構築（候補選定・重み付け・銘柄ごとの株数計算）
- 発注エンジン（ExecutionEngine、paper_trading モードをサポート）
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）
- AI 支援機能（ニュースセンチメント / 市場レジーム判定：OpenAI を利用）
- 運用支援ツール（.env ウィザード、設定検証、Paper Trading 検証レポート等）
- ロギング・プロセス優先度調整などのユーティリティ

設計方針の一部：
- DuckDB+SQLite を使い、分析用と運用ログを分離
- paper_trading（ペーパートレード）は本番 DB から分離して記録
- 外部 API 呼び出し（OpenAI 等）は明示的にキーを渡すか環境変数で指定
- ルックアヘッドバイアス回避のため、日付参照は引数で与える設計が多い

---

## 主な機能一覧

- 環境設定ウィザード（.env 作成）：python -m kabusys.config_setup
- 設定検証 CLI：python -m kabusys.validate_config
- 実行エンジン起動スクリプト：python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し `data/paper_trading.db` に記録
- 監視ループ起動スクリプト：python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
- Paper Trading 向け検証レポート生成：python -m kabusys.tools.paper_verification_report
- ニュース NLP による銘柄センチメント評価（OpenAI 使用）
- 市場レジーム判定（ETF MA とマクロニュースの組合せ、OpenAI 使用）
- ポートフォリオ構築ユーティリティ（選定・重み付け・ポジション決定）
- 監視 DB ラッパー（SQLite）と監視エンジン（アラート・KillSwitch）

---

## 依存関係（代表）

- Python 3.9+（プロジェクトでの最小要件はコード上に明示されていませんが、型注釈などから 3.9+ を推奨）
- duckdb
- psutil
- openai （AI 機能を使う場合）
- PyYAML（config/*.yaml の構文検証を行う場合、なくても動作するが検証はスキップされる）
- sqlite3（標準ライブラリ）
- logging（標準ライブラリ）

インストール例（pip）:
```
pip install duckdb psutil openai PyYAML
```

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

推奨 / 任意・説明付き:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
  - paper_trading: 発注はモック、ペーパートレード専用 DB に記録
  - live: 本番（実際発注）※注意して設定すること
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定モード（instant／partial／never／reject。デフォルト: instant）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト: INFO）
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知設定（任意）
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch 用フラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（1=クリア、0=クリアしない。デフォルト: 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

自動 .env ロード:
- プロジェクトルートにある `.env` / `.env.local` が自動で読み込まれます（OS 環境変数を上書きしない）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン / 展開
2. 仮想環境を作る（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```
3. 依存ライブラリをインストール
   ```
   pip install duckdb psutil openai PyYAML
   ```
4. 環境変数設定（.env を作る）
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは `.env` を作成し、秘密値はマスク表示で扱います。
   - 手動で `.env` を編集する場合は `.env.example` を参考にしてください（プロジェクトに例があれば）。
5. 設定検証（必須項目の確認）
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告も失敗扱いになります:
   ```
   python -m kabusys.validate_config --strict
   ```
6. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data logs
   ```

---

## 実行方法（運用）

- 実行エンジン（ExecutionEngine）を起動:
  - 標準（環境変数に応じて本番 or paper_trading が切り替わる）
  ```
  python -m kabusys.run_execution
  ```
  - paper_trading を強制する場合（.env または環境変数で指定）:
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
  - 実行中の停止は `data/stop_requested.flag` を作成するか、PID に対する停止処理を行ってください。run_execution は stop フラグを監視して Graceful に停止します。

- 監視ループを起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更する場合:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 監視プロセスも `data/stop_requested.flag` を監視して終了します。

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスを明示する場合:
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を環境変数で設定するか、関数呼び出し時に api_key を渡してください。
  - レート制限や一時的なエラーには指数バックオフでリトライする実装がありますが、API キーとモデルの利用上限に注意してください。
  - 使用モデルは gpt-4o-mini（コード内で指定）。

---

## 運用・ファイル（注意点）

- paper_trading モードは本番 DB と分離され、デフォルトで `data/paper_trading.db` に記録します。
- 監視は常に「本番 sqlite_path」を参照する設計になっている箇所があります（run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用）。
- PID ファイル: ExecutionEngine は起動時に PID ファイル（デフォルト data/execution.pid）を扱います。run_monitoring / run_execution は stop フラグ（data/stop_requested.flag）を監視して終了します。
- Kill Switch: RiskMonitor などが KillSwitch 条件（例: ドローダウン超過）を満たすと `KILL_FLAG_PATH`（デフォルト data/kill.flag）を書き、ExecutionEngine に停止を促します。`KILL_FLAG_CLEAR_ON_START` は起動時の自動クリアを制御します（本番では 0 推奨）。

---

## ロギング

- logging の設定は共通ユーティリティ `kabusys.utils.logging_setup.setup_logging()` を使って行われます。
- ログは stdout と日次ローテートされるファイル（logs/<app_name>.log）に出力されます。ログディレクトリは `LOG_DIR` 環境変数で指定可能（デフォルト logs/）。
- ログレベルは `LOG_LEVEL` 環境変数または setup_logging の引数で制御します。

---

## 開発者向けユーティリティ

- 設定ウィザード：python -m kabusys.config_setup — `.env` の作成・更新支援
- 設定検証：python -m kabusys.validate_config — 必須環境変数や config/*.yaml のチェック
  - PyYAML が未インストールの場合、YAML の内容検証はスキップされます（警告）
- monitoring DB 初期化は `kabusys.monitoring.monitoring_db.init_monitoring_db` で行います（冪等）

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールの抜粋構成です（実際のツリーはリポジトリによる）：

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py         — 市場レジーム判定（OpenAI）
  - monitoring/
    - monitoring_db.py           — SQLite 監視 DB ラッパー
    - monitoring_engine.py       — 各 Monitor の統括
    - system_monitor.py
    - trade_monitor.py           — （実装ファイルは該当ツリーを参照）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - execution/                   — Execution 系のコンポーネント（broker, engine, order_manager 等）
  - data/                        — （静的データ、DB ファイル等を配置する想定フォルダ）

（※上記はコードベース内の主要ファイルを抜粋したもので、実際の repository ではさらに細分化されたモジュールが含まれます。）

---

## よくある操作例

- .env を生成して検証:
  ```
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

- Paper Trading の検証レポート（過去期間）:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- 監視のみ実行（デバッグ用に短いポーリング間隔）:
  ```
  MONITOR_POLL_INTERVAL=10 python -m kabusys.run_monitoring
  ```

- ExecutionEngine 停止:
  - `data/stop_requested.flag` を作成すると run_execution / run_monitoring が検知して正常終了します。
  - Kill Switch により `data/kill.flag` が書かれる場合があります（本番で注意）。

---

## 注意事項 / 運用上のヒント

- 本番（KABUSYS_ENV=live）では kill.flag の自動クリア設定（KILL_FLAG_CLEAR_ON_START）を 0 にしておくことを推奨します。自動クリアを有効にする（1）と、意図せず Kill Switch をクリアしてしまう恐れがあります。
- OpenAI を使用する機能は API キーと利用制限に依存します。API 呼び出しはリトライやフォールバックロジックを持ちますが、運用負荷やコストは事前に確認してください。
- データベースファイル（DuckDB/SQLite）はバックアップ・適切なファイルパーミッションを行ってください。
- ログは日次ローテートされます（デフォルト 30 日保持）。ログディレクトリが作成できない場合はコンソールログのみとなるため、ディレクトリ作成権限を確認してください。

---

必要であれば、README に追加する事項（CI / テストの実行方法、詳細な API 仕様、Strategy・Portfolio の理論的背景など）を教えてください。補足の README セクションを作成します。