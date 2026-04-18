# KabuSys

日本株向け自動売買システム（KabuSys）のコードベース README。

このリポジトリは、注文エンジン・監視・ポートフォリオ構築・リサーチ・AI 補助（ニュース NLP / レジーム判定）等のコンポーネントを含んだモジュール群です。CLI スクリプトや対話式設定ウィザード、運用・検証用ツールも提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能を持つ Python モジュール群です。

- 発注エンジン（ExecutionEngine）
  - 実運用（live）・ペーパートレード（paper_trading）をサポート
  - ブローカークライアントを抽象化（本番は kabuステーション、ペーパーは Mock）
  - リスク管理、注文管理、リコンシリエーション機能を備える
- 監視（Monitoring）
  - システム状態（CPU/メモリ/ディスク）・データ鮮度・注文の異常を監視
  - Kill Switch による安全停止（kill.flag）や停止フラグ（stop_requested.flag）をサポート
- ポートフォリオ構築
  - 候補選定・重み付け・ポジションサイジング・セクター制限などの純粋関数実装
- リサーチ
  - DuckDB を利用したファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン/IC 計算、ファクター統計サマリ
- AI 補助
  - ニュース記事の LLM によるセンチメント評価（OpenAI 使用）
  - マクロニュースと ETF 指標を組み合わせた市場レジーム判定
- 運用ツール
  - .env 対話ウィザード、設定検証 CLI、Paper Trading 検証レポート生成 等

---

## 機能一覧（主なもの）

- 環境設定ウィザード: `python -m kabusys.config_setup`
- 設定検証: `python -m kabusys.validate_config [--strict]`
- ExecutionEngine 起動スクリプト: `python -m kabusys.run_execution`
  - KABUSYS_ENV=paper_trading の場合、ペーパートレード専用 DB（data/paper_trading.db）を使用
- Monitoring 起動スクリプト: `python -m kabusys.run_monitoring`
  - 環境にかかわらず（development 等でも）本番用 sqlite_path を使って監視ログを残す設計
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）
- Paper Trading 検証レポート: `python -m kabusys.tools.paper_verification_report`
- DuckDB ベースのファクター計算・リサーチ関数群
- OpenAI（gpt-4o-mini）を用いたニュース NLP とレジーム判定機能
- ログ管理ユーティリティ（Console + 日次ローテートファイル）
- プロセス優先度 / CPU affinity 設定ユーティリティ
- SQLite を用いた監視 DB 永続化（テーブル・マイグレーション含む）

---

## 必要条件（推奨）

- Python 3.10+（typing 機能と型注釈を多用しているため）
- pip でインストールする主なライブラリ（プロジェクトの requirements.txt がない場合、最低限）:
  - duckdb
  - psutil
  - openai
  - PyYAML（optional、config 検証で YAML を検証したい場合）

標準ライブラリ: sqlite3, logging, threading, datetime, pathlib など

---

## インストール（ローカル開発向け簡易手順）

1. リポジトリをクローンしてワークディレクトリに移動
2. 仮想環境を作成してアクティベート（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

（必要に応じて追加パッケージを requirements.txt にまとめてください）

---

## 初期設定 (.env) の作成

対話式ウィザードで .env を作成・更新します:

```
python -m kabusys.config_setup
```

ウィザードは J-Quants トークン、kabuAPI パスワード、DB パス等を尋ねます。生成された `.env` は絶対に Git にコミットしないでください。

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL（DEBUG/INFO/...）
- OPENAI_API_KEY（AI 機能を使う場合に必要）
- PAPER_FILL_MODE（instant | partial | never | reject）
- MONITOR_POLL_INTERVAL（監視ループ間隔秒、run_monitoring で利用）

環境変数の有無や設定を事前チェック:
```
python -m kabusys.validate_config
# --strict を付けると警告も失敗扱いで exit code 1
python -m kabusys.validate_config --strict
```

---

## データベースとログ

- デフォルトファイル位置
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
- ログディレクトリ: logs/ （デフォルト）
- 停止・制御フラグ
  - data/stop_requested.flag : 実行中の run_execution/run_monitoring が検知すると停止処理を始めます
  - data/kill.flag : KillSwitch により書かれると ExecutionEngine に安全停止を指示します
  - data/execution.pid : ExecutionEngine の PID ファイル（run_execution が管理）

監視用の DB スキーマとマイグレーションは `kabusys.monitoring.monitoring_db.init_monitoring_db` が担います（起動時に自動作成/移行）。

---

## 使い方（主なコマンド）

- ExecutionEngine 起動（バックグラウンドや systemd で起動する想定）
```
python -m kabusys.run_execution
```
- Monitoring 起動
```
# ポーリング間隔を 30 秒に設定したい場合
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```
- Paper Trading 検証レポート（期間指定可能）
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を別パスで指定する場合
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

- AI 機能（プログラム内で呼び出す）
  - ニュース NLP（銘柄ごとのスコアを ai_scores テーブルへ書き込む）
    - kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（duckdb.connect(...)）を渡して使用します。

- リサーチ関数の利用（例: モメンタム計算）
  - kabusys.research.calc_momentum(duckdb_conn, target_date)

注: OpenAI を呼び出す処理は API キー（OPENAI_API_KEY）を必要とします。ペーパートレード化している場合も AI を使えば外部 API にリクエストが飛びます。

---

## 停止・安全機構

- 停止フラグ:
  - `data/stop_requested.flag` が存在すると run_execution/run_monitoring は次のループで停止します（手動でファイルを置くことで安全に停止できます）。
- Kill Switch:
  - 監視コンポーネントが規定のリスク（例: ドローダウン閾値超過、ポジション上限超過）を検出すると `data/kill.flag` を書き込み、ExecutionEngine に停止を促します。
  - `Settings.kill_flag_clear_on_start` が `1` の場合、ExecutionEngine 起動時に kill.flag を自動クリアします（本番では `0` を推奨）。

---

## 開発者向け：主なモジュール一覧

- kabusys.config — 環境変数 / .env 読み込み・Settings クラス
- kabusys.config_setup — .env 対話ウィザード
- kabusys.validate_config — 起動前チェック CLI
- kabusys.run_execution — ExecutionEngine 起動スクリプト
- kabusys.run_monitoring — SystemMonitor ポーリング入口
- kabusys.execution.* — ブローカー抽象・エンジン・注文管理等（細部実装は該当ファイル参照）
- kabusys.monitoring.* — monitoring DB、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、MonitoringEngine 等
- kabusys.portfolio.* — 銘柄選定・重み付け・ポジションサイジング・リスク調整関数群
- kabusys.research.* — DuckDB を使ったファクター計算・IC や統計処理
- kabusys.ai.* — news_nlp（ニュースの LLM スコア）・regime_detector（市場レジーム判定）
- kabusys.tools.* — 補助ツール（paper_verification_report など）
- kabusys.utils.* — logging_setup、process_priority などのユーティリティ

---

## ディレクトリ構成（抜粋）

例: src ディレクトリ配下

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - execution/
      - (Engine, OrderManager, BrokerFactory 等)
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
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
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - data/（実行時に使用するファイル群: *.db, *.pid, *.flag など）

（実際のファイルはリポジトリの src/kabusys 以下を参照してください）

---

## 運用上の注意

- .env は機密情報を含むため絶対に Git 等へコミットしないでください。
- 本番（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を必ず確認してください（アラート送信先）。
- run_monitoring は監視データを SQLite に永続化します。monitoring は KABUSYS_ENV に依らず `Settings.sqlite_path`（本番パス）を使用する点に注意してください。
- Paper Trading は本番 DB と分離するよう設計されています。KABUSYS_ENV=paper_trading の時は `PAPER_TRADING_SQLITE_PATH` を利用します。
- OpenAI 呼び出しには API 利用料が伴います。開発・テスト時は API キーの利用を注意してください（テスト時は呼び出し箇所をモックすることを推奨）。

---

## よくあるコマンドまとめ

- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要に応じて README を拡張して、CI 設定、systemd ユニット例、Dockerfile、requirements.txt、より詳細なモジュール別ドキュメント（API リファレンス）を追加してください。必要であればその草案も作成します。