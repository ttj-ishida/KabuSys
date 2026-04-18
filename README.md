# KabuSys

日本株自動売買システムのモジュール群（ライブラリ + 起動スクリプト類）。  
この README はコードベースの主要機能・セットアップ・使い方・ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買/リサーチ/監視機能を備えたシステムです。  
主な要素は以下の通りです。

- ExecutionEngine: 発注・オーダー管理・リスク管理を行う実行エンジン（実口座 / ペーパートレード対応）
- Monitoring: システム稼働状況・注文ログ・リスク指標の定期チェックとアラート・Kill Switch
- Research: DuckDB 上の価格・ファイナンスデータからファクター計算・バックテスト補助
- AI モジュール: ニュースのセンチメント解析や市場レジーム判定（OpenAI API を使用）
- ユーティリティ: ロギング設定、プロセス優先度設定、設定ウィザード、設定検証など
- ツール: Paper Trading 検証レポート生成など

設計方針として、コアロジック（ポートフォリオ構築、ポジションサイジング等）は純粋関数として実装され、
データ永続化や外部 API 呼び出しは責務を分離して実装されています。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV=paper_trading で MockBroker を使用し DB を分離）
  - run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）
- 設定支援
  - config_setup: 対話式ウィザードで .env を生成/更新
  - validate_config: .env と config/*.yaml の事前検証ツール（--strict フラグあり）
- モニタリング
  - システム状態、データ鮮度、注文ログ、リスク（ドローダウン・ポジション上限）監視
  - kill.flag / stop_requested.flag を用いた停止制御（Kill Switch）
  - MonitoringDB: SQLite に監視ログを永続化（冪等な初期化 & マイグレーション）
- ポートフォリオ構築
  - 候補選定、等重/スコア重み付け、セクター上限適用、ポジションサイズ算出（単元丸め等）
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - forward returns, IC（Spearman）や統計サマリ等
- AI（OpenAI）連携
  - news_nlp.score_news: ニュース集合を LLM でスコア化し ai_scores に書き込み
  - regime_detector.score_regime: ETF の MA 負荷 + マクロニュースで日次レジーム判定
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート出力（稼働率 / 成功率 / レイテンシ等）

---

## セットアップ手順

前提
- Python 3.10 以上（コードは PEP 604 型注釈等を使用）
- SQLite は標準ライブラリで含まれます
- 推奨（最低限）ライブラリ:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config 検証で YAML 検査を行う場合）

例: 仮想環境作成とインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil openai PyYAML
```

ディレクトリ（runtime）作成
```bash
mkdir -p data logs
```

環境変数・設定
- 対話式ウィザードで .env を作成するのが簡単です（下記参照）。
- 必須環境変数（少なくとも設定必須）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 代表的な環境変数（.env に設定可能）
  - KABUSYS_ENV (development | paper_trading | live)
  - DUCKDB_PATH (例: data/kabusys.duckdb)
  - SQLITE_PATH (例: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB)
  - LOG_LEVEL, LOG_DIR
  - OPENAI_API_KEY（AI 機能利用時）
  - PAPER_FILL_MODE（paper_trading の注文約定モード: instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: 0/1）

.env を対話式に生成:
```bash
python -m kabusys.config_setup
```

設定検証:
```bash
python -m kabusys.validate_config
# 警告も失敗にしたい場合:
python -m kabusys.validate_config --strict
```

---

## 使い方（起動コマンド例）

ログ設定は起動時に自動で行われ、デフォルトで `logs/` に日次ローテーションログを出力します。

ExecutionEngine を起動（通常はプロダクション / ペーパートレードいずれも）:
```bash
# 本番/開発/ペーパートレードは KABUSYS_ENV で制御
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```
- paper_trading モードの場合、MockBrokerClient を使用し、ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に記録します。
- 起動前に `data/stop_requested.flag` が存在すると起動を中止します。
- エンジンを停止するには Kill Switch（kill.flag）や stop flag を利用できます（詳述下記）。

Monitoring を起動:
```bash
# ポーリング間隔は MONITOR_POLL_INTERVAL（秒）で上書き可。デフォルト 60 秒。
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```
- Monitoring は KABUSYS_ENV にかかわらず、本番の sqlite_path を使用して監視ログを記録します（監視 DB は common monitoring DB）。
- 停止は `data/stop_requested.flag` を作成することでポーリングループが検知して終了します。

Paper Trading 検証レポート（コマンドラインツール）:
```bash
# デフォルト DB: data/paper_trading.db
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または別 DB を指定:
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

AI 系の関数（ライブラリ呼び出し例）
- ニューススコア集計:
  - duckdb 接続を渡して `kabusys.ai.score_news(conn, target_date, api_key=None)` を呼び出す。
  - api_key が None の場合は環境変数 `OPENAI_API_KEY` を参照します。
- レジーム判定:
  - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

ログレベルやログ出力先
- 環境変数 LOG_LEVEL（例: DEBUG/INFO）と LOG_DIR を設定できます。
- ログはデフォルトで `logs/<app_name>.log` に日次ローテートで保存されます。

停止・Kill フロー
- stop_requested.flag (`data/stop_requested.flag`):
  - run_monitoring と run_execution のメインループが監視している停止フラグ。存在するとループが終了します（手動で作成／削除）。
- kill.flag (`Settings.kill_flag_path`、デフォルト `data/kill.flag`):
  - KillSwitch が条件を満たすとファイルを書き込み、ExecutionEngine 側に停止シグナルを送ります（部分停止 / フェイルセーフ）。  
  - 環境変数 `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動でこのフラグをクリアします（本番では 0 推奨）。

---

## ディレクトリ構成（主要ファイル）

以下はコードベース（src/kabusys）の主要構成です。実際のリポジトリには他のモジュール（execution 関連等）も含まれますが、ここでは主要なものを抜粋しています。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動読み込み機能）
  - config_setup.py          — 対話式 .env 生成ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI 統合）
  - monitoring/
    - monitoring_db.py      — SQLite テーブル定義 / MonitoringDB クラス
    - system_monitor.py     — システム・データ鮮度監視
    - trade_monitor.py      — （注文の滞留・約定異常等をチェックする実装）
    - risk_monitor.py       — ドローダウン・ポジション数監視
    - monitoring_engine.py  — 各 Monitor を束ねるポーリング実装
    - kill_switch.py        — KillFlag の作成・評価
    - alert_manager.py      — （アラート送信の抽象 / LINE 等への通知）
  - portfolio/
    - portfolio_builder.py  — 候補選定・重み計算
    - position_sizing.py    — 発注株数計算（リスクベース等）
    - risk_adjustment.py    — セクター制限・レジーム乗数
  - research/
    - factor_research.py    — Momentum / Volatility / Value 計算（DuckDB）
    - feature_exploration.py — forward returns, IC, statistical summaries
  - utils/
    - logging_setup.py      — ロギング初期化ユーティリティ
    - process_priority.py   — プロセス優先度設定（psutil ベース）
  - monitoring/（上記）
  - execution/               — Execution 関連（OrderManager, BrokerFactory 等）※別ファイル群

ランタイム用ディレクトリ（プロジェクトルート）
- data/    — SQLite DB ファイル、PID、フラグファイル等を配置（例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag）
- logs/    — ログファイル出力先（デフォルト）

---

## 追加メモ / よくある質問

- Python バージョン:
  - 型注釈に `X | None` 形式を使っているため Python 3.10 以上が推奨です。
- DuckDB:
  - リサーチ/AI モジュールは DuckDB 接続を使用します。DuckDB ファイルは `DUCKDB_PATH` で指定。
- PyYAML:
  - validate_config は PyYAML があると config/*.yaml の構文チェックを行います。インストールされていない場合は警告が出ますが検証自体はスキップされます。
- OpenAI API:
  - AI 機能を利用する場合は `OPENAI_API_KEY` を設定してください。API 呼び出しは各モジュール（news_nlp, regime_detector）で行われ、レスポンスのバリデーションやリトライ制御が組み込まれています。
- 本番運用注意:
  - KABUSYS_ENV=live では設定ミスが致命的になるため、validate_config で警告や必須変数を確認してください。
  - `KILL_FLAG_CLEAR_ON_START=1` は本番では危険（起動と同時に kill.flag がクリアされるため）なので通常は `0` を推奨します。
- 停止方法:
  - 通常の優雅な停止は監視スクリプトやエンジンが監視する `data/stop_requested.flag` を作成することで行えます。KillSwitch による停止は `data/kill.flag` が書き込まれると ExecutionEngine に停止シグナルを送ります。

---

この README はコードベース（src/kabusys）を参照して作成しています。実運用・デプロイする際は .env の適切な管理（Git にコミットしない）、監視・ログ保管の運用設計、OpenAI API のレート・コスト管理に留意してください。質問や追記してほしい内容があれば教えてください。