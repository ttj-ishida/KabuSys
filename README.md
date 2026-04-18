# KabuSys

日本株自動売買システム（ライブラリ / 実行スクリプト群）のリポジトリ用 README

## 概要

KabuSys は日本株の自動売買・リサーチ・監視を行うためのコンポーネント群です。  
主な機能は以下の通りです。

- 注文実行エンジン（ExecutionEngine） — ブローカークライアント経由で発注・注文管理・リスク管理を実行
- 監視コンポーネント（Monitoring） — システム稼働状況・注文ログ・リスク検出と Kill Switch の発動
- ポートフォリオ構築（Portfolio） — 候補選定、重み付け、ポジションサイズ計算、セクター制約など
- 研究用モジュール（Research） — ファクター計算、特徴量解析、IC 計算など（DuckDB を使用）
- AI 補助（AI） — ニュースの NLP によるセンチメントスコア、レジーム検出（OpenAI API を利用）
- ツール類 — ペーパートレード検証レポート生成など

設計上のポイント:
- 環境設定は .env / 環境変数で行う（自動読み込み機能あり）  
- Paper trading（ペーパートレード）は本番 DB と分離して専用 SQLite を使用  
- ロギングは統一されたセットアップ関数で stdout + 日次ローテートファイルを出力

## 主な機能一覧

- run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて実際発注／Mock 発注を切替）
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い `data/paper_trading.db` に記録
  - プロセス優先度設定、PID ファイルの出力、停止フラグ検出（data/stop_requested.flag）
- run_monitoring.py: SystemMonitor のポーリングループ起動
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視用 SQLite（monitoring.db）に常時記録（環境に関わらず本番 sqlite_path を使用）
  - Kill Switch（data/kill.flag）作成による ExecutionEngine 停止トリガー
- monitoring_engine / SystemMonitor / RiskMonitor / TradeMonitor / KillSwitch: 監視ロジック一式
- portfolio: 候補選定・重み付け・単元丸め・セクター制約・レジーム乗数など
- research: DuckDB に保存された価格データを使ったファクター計算（momentum / value / volatility）
- ai.news_nlp / ai.regime_detector: OpenAI を使ったニュースセンチメント・市場レジーム判定
- tools.paper_verification_report: Paper Trading の検証レポート生成（稼働率・成功率・レイテンシ等）
- config_setup.py: .env の対話ウィザード（初期作成・更新）
- validate_config.py: 起動前設定検証 CLI（必須環境変数・ファイル・パス等の検査、--strict モードあり）

## 前提条件 / 依存パッケージ

- Python 3.10+
- 必須外部パッケージ（主に runtime）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
- 開発 / 一部機能で推奨:
  - PyYAML（config/*.yaml の検証に使用されるが必須ではない）
- これらは環境に応じて requirements.txt を作成して pip install で導入してください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

## 環境変数 / .env

Settings クラスは環境変数から各種設定を読み込みます。プロジェクトルートにある `.env` / `.env.local` を自動的に読み込みます（OS 環境変数が優先）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（代表例）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV（development / paper_trading / live、デフォルト development）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 時の DB、デフォルト data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading のフィルモード: instant | partial | never | reject）
- LOG_LEVEL（DEBUG/INFO/...）
- OPENAI_API_KEY（AI 機能で必要）

.env の作成はウィザードで支援できます:
```
python -m kabusys.config_setup
```

設定検証:
```
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```

## セットアップ手順（簡易）

1. リポジトリをクローンし、Python 仮想環境を用意
2. 依存パッケージをインストール（上記参照）
3. `.env` を作成（`python -m kabusys.config_setup` を推奨）
4. 設定検証（`python -m kabusys.validate_config`）
5. 必要に応じて DuckDB / SQLite データディレクトリを作成（通常はスクリプトが自動生成します）

## 使い方（主要コマンド）

- ExecutionEngine を起動（デーモンや systemd などで運用を想定）
```
python -m kabusys.run_execution
```
- Monitoring を起動
```
python -m kabusys.run_monitoring
```
- 設定ウィザード（.env 作成）
```
python -m kabusys.config_setup
```
- 設定検証
```
python -m kabusys.validate_config
```
- Paper Trading 検証レポート（期間指定可）
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または DB を直接指定
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

実行時の挙動メモ:
- run_execution は起動時にプロセス優先度を "high" に設定し、PID ファイル（data/execution.pid）を書きます。data/stop_requested.flag が存在する場合は起動せず終了します。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を指定できます（デフォルト 60 秒）。監視は本番用 sqlite_path を使用します（環境にかかわらず）。
- 監視コンポーネントは条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります（Kill Switch）。
- ExecutionEngine の Paper Trading モードは本番 DB と完全に分離され `PAPER_TRADING_SQLITE_PATH` を使用します。

停止方法:
- ExecutionEngine を安全に停止させたい場合は `data/stop_requested.flag`（run_execution が参照する）または監視側から生成される `data/kill.flag` を使います。run_execution はフラグ検出時に停止処理を開始します。
- run_monitoring のループは同様に stop_requested.flag を監視して終了します。

ログ:
- 共通の logging_setup を使い、stdout（コンソール）と日次ローテーションファイル（logs/<app_name>.log）に出力します。`LOG_DIR`/`LOG_LEVEL` でカスタマイズ可能。

## AI（OpenAI）機能について

- News NLP（ai.news_nlp）と Regime Detector（ai.regime_detector）は OpenAI API（gpt-4o-mini）を利用する設計です。使用するには `OPENAI_API_KEY` を設定してください。
- API エラー時はリトライやフォールバック（例えば macro_sentiment=0.0）を行い、フェイルセーフ設計になっています。ただしコストやレート制限に注意してください。

## ディレクトリ構成（主要ファイル）

リポジトリ内で主要なモジュール群は `src/kabusys` 以下にあります。主要ファイルの例を示します。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - config_setup.py            — .env 対話ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity 設定
  - execution/                  — Execution に関する実装（BrokerFactory, Engine, OrderManager など）
  - monitoring/
    - monitoring_db.py         — SQLite に対する永続化層
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - trade_monitor.py         — （注文監視ロジック）
    - alert_manager.py        — （LINE 等へ通知する実装想定）
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
  - data/                      — 実行時に使用するデフォルトディレクトリ（data/*.db, data/*.flag 等）
  - logs/                      — デフォルトのログ出力先（ログディレクトリは環境変数で変更可）
  - tools/
    - paper_verification_report.py

（上記は主なファイルの抜粋です。詳細は src/kabusys 以下のソースをご参照ください）

## 運用上の注意 / ベストプラクティス

- 本番（KABUSYS_ENV=live）での運用前に必ず `python -m kabusys.validate_config` で設定を検証してください。
- `.env` ファイルは機密情報を含むため Git にコミットしないでください（config_setup.py のヘッダーにも明記）。
- Paper Trading を使ってから本番に切り替える際は DB の分離（PAPER_TRADING_SQLITE_PATH）を確認してください。
- OpenAI API を利用する機能は有料となる場合があるため、API キーと利用ポリシーに留意してください。
- プロセス優先度や CPU affinity の設定は OS 権限に依存します。権限不足時はログに警告が出ますが処理は続行されます。

---

不明点や README に追記してほしい操作手順があれば教えてください。必要に応じて起動フロー図や systemd ユニット例、sample .env.example を追加できます。