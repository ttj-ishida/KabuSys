# KabuSys

日本株向け自動売買システムのコンポーネント集（ライブラリ + 起動スクリプト群）。

本リポジトリには、発注エンジン、監視（Monitoring）群、ポートフォリオ構築・リスク制御ロジック、AI（ニュース NLP / レジーム判定）、および運用ツール類が含まれます。

## 主要機能（抜粋）

- ExecutionEngine：ブローカークライアント経由で発注管理・リスク制御を行う実行エンジン
- Monitoring：システム稼働監視、注文監視、リスク監視、Kill Switch 評価、アラート送出
- Portfolio Construction：候補選定、重み算出、ポジションサイズ計算、セクター制限、レジーム補正
- Research：ファクター（モメンタム/バリュー/ボラティリティ）計算、将来リターン・IC 計算、統計サマリ
- AI：ニュース記事を LLM（OpenAI）でセンチメント評価して ai_scores に保存、マクロセンチメントと MA 乖離を合成して市場レジーム判定
- 運用ツール：.env ウィザード（config_setup）、設定検証（validate_config）、Paper Trading 検証レポート生成（paper_verification_report）

---

## 要件（主な依存ライブラリ）

- Python 3.9+
- duckdb
- psutil
- openai （AI 機能を使う場合）
- PyYAML（config YAML の検証を行う場合／任意）

インストール例:
```bash
python -m pip install duckdb psutil openai pyyaml
```

（sqlite3 は標準ライブラリで利用可能）

---

## セットアップ手順

1. リポジトリをチェックアウトし、仮想環境を作成して依存をインストールしてください。

2. 環境変数の用意
   - `.env` を手動で作るか、対話式ウィザードを使います。

3. .env を対話式で作成（推奨）
```bash
python -m kabusys.config_setup
```
ウィザードは .env を生成または既存ファイルを更新します。重要な変数（必須）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 時の専用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を使う場合）

注意: .env は絶対にリポジトリにコミットしないでください。

4. 設定検証（起動前チェック）
```bash
python -m kabusys.validate_config
# 厳密モード（警告を FAIL とする）
python -m kabusys.validate_config --strict
```

5. DB の初期化
- 監視用 SQLite（monitoring）は起動スクリプト側で自動作成・マイグレーションが行われます（init_monitoring_db）。
- DuckDB ファイルは用途に応じて事前に準備してください（分析用）。

---

## 環境変数一覧（よく使うもの・デフォルト）

- KABUSYS_ENV: 実行環境（development / paper_trading / live） — default: development
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- JQUANTS_REFRESH_TOKEN: （必須）
- KABU_API_PASSWORD: （必須）
- OPENAI_API_KEY: OpenAI を使う機能向け
- LOG_LEVEL: ログレベル（DEBUG/INFO/...） — default: INFO
- LOG_DIR: ログの出力ディレクトリ — default: logs/
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" で有効。production では "0" 推奨）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60） — run_monitoring 用
- PAPER_FILL_MODE: paper_trading の MockBroker の fill モード（instant/partial/never/reject）

自動 .env ロードはデフォルトで有効です。無効化する場合:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（起動スクリプト）

起動スクリプトはパッケージモジュールとして実行できます。

- 実行エンジン（Execution）
```bash
python -m kabusys.run_execution
```
- 監視（Monitoring） — システム状態やリスクを定期チェック
```bash
python -m kabusys.run_monitoring
# ポーリング間隔を変更する例（30秒）
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

- Paper Trading 検証レポート（ツール）
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を明示する場合
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

- 設定ウィザード / 検証
```bash
python -m kabusys.config_setup
python -m kabusys.validate_config
```

注意点:
- KABUSYS_ENV=paper_trading の場合、実行エンジンは MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）にデータを保存します。本番 DB と完全に分離されます。
- Monitoring はどの環境でもデフォルトの sqlite_path（monitoring DB）を使用します（監視ログ共有のため）。

---

## 停止・Kill スイッチ（運用向け）

- 停止フラグ（run_execution・run_monitoring はプロセス起動時に data/stop_requested.flag の存在をチェック）
  - stop フラグを作成すると起動しない、または起動中のループが検知して安全に終了します。
  - ファイルパス:
    - run_monitoring: project_root/data/stop_requested.flag
    - run_execution: project_root/data/stop_requested.flag

- Kill Switch（監視から Execution を停止する機構）
  - Monitoring の KillSwitch は条件を満たすと data/kill.flag に理由を書き込みます（冪等）。
  - ExecutionEngine は起動時 / ループ時に kill.flag 等を参照して停止します。
  - kill.flag のパスは Settings.kill_flag_path（デフォルト data/kill.flag）で変更できます。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動で kill.flag を削除します（本番では推奨しません）。

---

## ロギングと PID

- ログはデフォルトで `logs/` に日次ローテーションで出力されます（ファイル名は app 名に対応: execution.log, monitoring.log など）。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一管理され、コンソール（stdout）とファイルの両方に出力されます。
- Execution は `data/execution.pid`（デフォルト）に PID を書きます（設定により変更可能）。

---

## AI 機能について（OpenAI）

- News NLP（kabusys.ai.news_nlp）
  - raw_news, news_symbols を集約し、OpenAI（gpt-4o-mini）に対してバッチでセンチメント評価を実行します。
  - API キー: OPENAI_API_KEY（引数での注入も可能）
  - 失敗時はリトライ（429・ネットワーク・5xx）し、最終的に部分失敗でも他データを保護する設計です。
- Regime Detector（kabusys.ai.regime_detector）
  - ETF（1321）の MA200 乖離とマクロニュースの LLM センチメントを合成して市場レジーム（bull/neutral/bear）を判定し、DuckDB の market_regime に書き込みます。
- これらを利用するには OpenAI SDK（openai）をインストールし、OPENAI_API_KEY を設定してください。

---

## ディレクトリ構成（抜粋）

プロジェクトルートは src/kabusys を想定しています。主なファイル・ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数・設定解決ロジック
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 起動前の設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/               — Execution 関連モジュール（broker_factory 等）
  - utils/
    - logging_setup.py
    - process_priority.py

- data/                      — 実行時生成ファイル（.db/.pid/.flag 等）
- logs/                      — ログ出力（デフォルト）

---

## 開発・運用上の注意

- .env のプレースホルダ値（例: *_here や "your_value"）は起動前に必ず置き換えてください。validate_config により検出可能です。
- KABUSYS_ENV を `live` にすると本番向けチェックが厳しくなります。特に kill_flag の自動クリア等は本番で無効にしてください。
- paper_trading モードは本番 DB と完全分離されるよう設計されています。実取引を行う `live` 環境での設定ミスに注意してください。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します（警告ログが出ます）。

---

以上が README の要約です。実行方法や設定項目について不明点があれば、どの部分を詳しく説明するか指定してください。