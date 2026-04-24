# KabuSys

KabuSys は日本株向けの自動売買 / リサーチ基盤の一部を実装した Python パッケージです。  
ポートフォリオ構築、ポジションサイジング、リスク制御、監視、Paper Trading 検証、さらにニュースの NLP スコアリングやレジーム判定といった機能を備えています。

---

## 主な特徴
- ポートフォリオ構築（候補選定・スコア重み・等分配など）
- ポジションサイジング（リスクベース・等分配・スコア加重）
- セクター集中制限・レジーム乗数（リスク調整）
- リサーチ機能（モメンタム、ボラティリティ、バリュー等のファクター計算）
- 実行系（ExecutionEngine）と監視系（MonitoringEngine）を分離
  - KABUSYS_ENV=paper_trading のときは MockBroker を用いた Paper Trading に対応（本番 DB とは分離）
- 監視・Kill Switch（データ鮮度、プロセス監視、ドローダウンやポジション上限で flag 発行）
- ニュースの NLP（OpenAI）による銘柄別センチメントスコア化
- Paper Trading の検証レポート生成ツール

---

## 前提（Prerequisites）
- Python 3.10+
- SQLite（Python 標準ライブラリ sqlite3 を使用）
- 依存パッケージ（主なもの）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config.yaml の検証に必要。任意）
- SQLite / DuckDB ファイルはデフォルトで `data/` 下を参照します。

インストール例（仮）:
```
python -m pip install duckdb psutil openai pyyaml
```
（プロジェクトに requirements.txt がある場合はそちらを使ってください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動します。

2. .env の作成（対話式ウィザード）
```
python -m kabusys.config_setup
```
ウィザードは `.env` を生成／更新します。重要な必須項目:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

その他:
- KABUSYS_ENV: `development` / `paper_trading` / `live`（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（Paper Trading 用データベース）
- OPENAI_API_KEY（AI 機能を使う場合）

自動ロード:
- デフォルトでプロジェクトルートの `.env` と `.env.local` を自動読み込みします。無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

3. 設定検証
```
python -m kabusys.validate_config
# 警告も fail にしたい場合:
python -m kabusys.validate_config --strict
```
このコマンドは必須環境変数や config/*.yaml（存在する場合）や DB パス周りをチェックします。PyYAML がない場合は YAML の検証はスキップされ、警告が出ます。

---

## 使い方（実行例）

- 実行エンジン（ExecutionEngine）起動
```
python -m kabusys.run_execution
```
- 監視ポーリング（MonitoringEngine）起動
```
python -m kabusys.run_monitoring
```

挙動のポイント:
- `run_execution` は KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し DB は `data/paper_trading.db`（または `PAPER_TRADING_SQLITE_PATH`）に保存します。本番 DB（monitoring.db）とは完全に分離されます。
- 監視プロセス（run_monitoring）は環境に関わらず本番用の `sqlite_path` を使って監視テーブルを初期化します（monitoring 用 DB を共有）。
- 両スクリプトとも起動時にプロセス優先度を「high」に設定しようとします（psutil を利用）。
- graceful stop: プロジェクトルートの `data/stop_requested.flag` を監視し、存在するとループを抜けます（`run_monitoring` / `run_execution` が参照）。

- Paper Trading 検証レポート生成
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを指定する場合:
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キーは環境変数 `OPENAI_API_KEY` または各関数の引数で渡します。
  - ニュースのスコアリング: kabusys.ai.score_news（内部で OpenAI を呼びます）
  - レジーム判定: kabusys.ai.regime_detector.score_regime

- ログ
  - ログはデフォルトで `logs/` に日次ローテーションで保存されます（`LOG_DIR` で変更可能）。
  - 起動時に `kabusys.utils.logging_setup.setup_logging(app_name="execution")` のように呼ばれ、`logs/<app_name>.log` に出力されます。
  - 環境変数 `LOG_LEVEL` で出力レベルを変更できます（DEBUG/INFO/...）。

- ポーリング間隔（監視）
  - 環境変数 `MONITOR_POLL_INTERVAL` で秒数を指定できます（デフォルト 60 秒）。無効な値や 0 以下はデフォルトにフォールバックします。

---

## 重要なファイル / フラグ
- データベース（デフォルト）
  - DuckDB: data/kabusys.duckdb (env: DUCKDB_PATH)
  - SQLite（監視）: data/monitoring.db (env: SQLITE_PATH)
  - SQLite（Paper Trading）: data/paper_trading.db (env: PAPER_TRADING_SQLITE_PATH)
- PID / フラグ
  - 実行 PID: data/execution.pid
  - Kill Switch: data/kill.flag（KillSwitch が書き込むと ExecutionEngine 停止対象）
  - Stop Request: data/stop_requested.flag（run_* スクリプトが存在を検知して終了）
- 環境設定ファイル
  - .env / .env.local（config_setup による生成・自動ロード）

KillSwitch の仕様（監視 -> Execution 停止）:
- RiskMonitor がドローダウンやポジション上限を検出すると、KillSwitch が `data/kill.flag` を書き込みます。ExecutionEngine はこのフラグを検知して安全停止することを想定しています。

---

## 環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — instant | partial | never | reject（Paper Trading の約定挙動）
- OPENAI_API_KEY — AI 機能で使用
- LOG_LEVEL — ログレベル（デフォルト INFO）
- LOG_DIR — ログ保存ディレクトリ
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動でクリアするか（0/1）

（その他の設定は README 内の説明やソースの Settings クラスを参照してください）

---

## 開発・テスト
- 自動環境変数ロードを無効化するには:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```
- validate_config は設定の早期検出に有用です（本番起動前に必ず実行することを推奨）。
- 各モジュールは比較的純粋関数として設計されており、ユニットテストが書きやすい構成になっています。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要なファイル構成（src 以下）:

```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py                # 環境変数 / Settings
   ├─ config_setup.py          # .env ウィザード（対話式）
   ├─ validate_config.py       # 設定検証 CLI
   ├─ run_execution.py         # ExecutionEngine 起動スクリプト
   ├─ run_monitoring.py        # Monitoring ポーリング起動スクリプト
   ├─ execution/               # 実行系関連（Engine, Broker, OrderManager 等）
   ├─ monitoring/
   │  ├─ monitoring_db.py      # Monitoring DB ラッパー（SQLite）
   │  ├─ system_monitor.py
   │  ├─ trade_monitor.py
   │  ├─ risk_monitor.py
   │  ├─ monitoring_engine.py
   │  ├─ kill_switch.py
   │  └─ alert_manager.py
   ├─ portfolio/
   │  ├─ portfolio_builder.py
   │  ├─ position_sizing.py
   │  └─ risk_adjustment.py
   ├─ research/
   │  ├─ factor_research.py
   │  └─ feature_exploration.py
   ├─ ai/
   │  ├─ news_nlp.py           # ニュース NLP（OpenAI）
   │  └─ regime_detector.py
   ├─ data/                    # データパイプライン関連（DuckDBアクセス等）
   ├─ tools/
   │  └─ paper_verification_report.py
   └─ utils/
      ├─ logging_setup.py      # ログ設定ユーティリティ
      ├─ process_priority.py   # プロセス優先度設定
      └─ ...
```

---

## 補足 / 注意事項
- 本リポジトリには実行用の Broker や Exchange への直接アクセス部分（本番向けの実ブローカ接続）は分離・抽象化されています。Paper Trading 用の挙動は明確に切り分けられており、本番 DB を汚染しない設計です。
- AI（OpenAI）機能は外部 API を使用します。API キーや呼び出しに伴うコストに注意してください。API のレート制限や一時的な失敗にはリトライロジックが組み込まれていますが、運用時はキーの管理・コスト管理を行ってください。
- システム優先度設定や CPU affinity の設定は OS の権限に依存します。権限不足時はログにワーニングが出ますが、処理自体は継続します。

---

必要に応じてこの README をプロジェクト固有の情報（実ブローカ設定、CI 手順、追加の依存関係）で拡張してください。質問や追記してほしいセクションがあれば教えてください。