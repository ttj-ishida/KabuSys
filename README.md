# KabuSys

日本株向けの自動売買システム（ライブラリ / 実行用スクリプト群）。  
このリポジトリはトレーディング用のエンジン・監視・ポートフォリオ構築・リサーチ・AI ベースのニュース評価などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたコンポーネント群を持つシステムです。

- 戦略に基づく銘柄選定・配分（等配分・スコア加重・リスクベース）
- 発注エンジン（ExecutionEngine）と発注管理（OrderManager / OrderRepository）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）とアラート（LINE）
- Paper Trading（本番 DB と分離された専用 SQLite）サポート
- News を LLM（OpenAI）でスコアリングして AI スコアを生成
- 市場レジーム判定（レジームスコアの算出）
- DuckDB を用いたリサーチ / ファクター計算モジュール
- 各種ユーティリティ（プロセス優先度設定、設定ウィザード、検証ツール 等）

実行時の設定は主に環境変数（またはプロジェクトルートの `.env`）で行います。

---

## 主な機能一覧

- ポートフォリオ構築
  - 銘柄候補選定、等配分・スコア配分、リスクベースの株数算出
  - セクター制約・レジーム乗数の適用
- 発注・実行
  - BrokerClientFactory 経由で本番/モックブローカーを選択
  - ExecutionEngine によるセッション実行（PID ファイル管理）
- 監視
  - SystemMonitor：CPU/メモリ/ディスク、Execution プロセスの存否、データ鮮度
  - TradeMonitor：滞留注文・約定価格異常検出
  - RiskMonitor：ドローダウン・ポジション上限監視、Kill Switch（停止フラグ）
  - MonitoringEngine：各モニタを束ねたポーリングループ
- アラート
  - AlertManager：LINE Messaging API へのプッシュ通知（クールダウン管理）
- AI
  - news_nlp：OpenAI（gpt-4o-mini）でニュースを銘柄ごとにセンチメント評価し ai_scores テーブルへ書き込み
  - regime_detector：ETF（1321）MA200 とマクロニュースの LLM スコアで市場レジーム判定
- ツール
  - config_setup：対話式 .env 生成ウィザード
  - validate_config：起動前に環境変数・config YAML の検証
  - paper_verification_report：Paper Trading データを用いた稼働/注文/レイテンシ検証レポート生成

---

## 必要条件（依存ライブラリ）

- Python 3.9+
- duckdb
- psutil
- requests
- openai (AI 機能を利用する場合)
- PyYAML（config YAML の内容検証を行う場合。未インストールでも処理は継続します）

インストール例（仮想環境推奨）:
```
pip install -r requirements.txt
# または個別
pip install duckdb psutil requests openai PyYAML
```

（requirements.txt が無い場合は上記を個別にインストールしてください）

---

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を作成・有効化してください。

2. 依存パッケージをインストールします（上記参照）。

3. .env ファイルを作成する（対話式ウィザード推奨）:
```
python -m kabusys.config_setup
```
ウィザードは `.env` に各種設定を保存します。重要な必須項目:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な環境変数（デフォルト値を併記）:
- KABUSYS_ENV: execution 環境 (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 用 DB)
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、default=60）
- PAPER_FILL_MODE: paper_trading のモックフィル挙動 ("instant"|"partial"|"never"|"reject")
- OPENAI_API_KEY: OpenAI を利用する場合は設定

4. 設定検証を行う:
```
python -m kabusys.validate_config
# 警告でもエラー扱いにする場合:
python -m kabusys.validate_config --strict
```

5. 必要に応じてデータディレクトリを作成:
```
mkdir -p data
```

DB スキーマは起動時に自動作成（init_monitoring_db）されます。

---

## 起動方法（使い方）

- 監視プロセスを起動（SystemMonitor のポーリングループ）:
```
python src/kabusys/run_monitoring.py
# またはモジュール実行:
python -m kabusys.run_monitoring
```
オプション:
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（例: 30秒）
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- 監視は常に本番 sqlite_path（Settings.sqlite_path）を使って監視ログを記録します。
- 停止: プロジェクトルートの data/stop_requested.flag を作成するとループが終了します。

- 実行エンジン（ExecutionEngine）を起動:
```
python -m kabusys.run_execution
```
挙動:
- KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）へ記録します。本番 DB と分離されます。
- 実行中は PID ファイル（デフォルト: data/execution.pid）を作成します。
- 停止: data/stop_requested.flag を作成するとエンジン停止シグナルとして検知して停止します。
- Kill Switch: 監視側が重大なリスクを検知し data/kill.flag を書き込むと、エンジン側の設定により起動時に停止またはアクションを取ります（Settings.kill_flag_clear_on_start を参照）。

- Paper Trading 検証レポート生成:
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を明示する場合:
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```
デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI（ニュース NLP）およびレジーム判定:
  - OpenAI API キーが必要（OPENAI_API_KEY を環境変数に設定、または関数引数で渡す）
  - 関数を直接呼び出して利用する:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 重要なファイル・フラグ

- data/stop_requested.flag
  - run_monitoring.py / run_execution.py がループ停止判定に使う（存在するとループを抜ける）
- data/kill.flag
  - KillSwitch が書き込む。ExecutionEngine 側で自動的にチェック/反映する用途
- data/execution.pid
  - 実行エンジンが生成する PID ファイル（SystemMonitor が存在を確認）
- DB
  - 監視ログ（デフォルト）: data/monitoring.db
  - DuckDB（分析用）: data/kabusys.duckdb
  - Paper Trading 専用 SQLite: data/paper_trading.db

---

## 設定ウィザード / 検証コマンド

- 対話式 .env 作成:
```
python -m kabusys.config_setup
```

- 設定検証（起動前推奨）:
```
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```

validate_config は必須環境変数・KABUSYS_ENV の妥当性・DB パスの親ディレクトリ存在・config/*.yaml の存在/パース（PyYAML がある場合）等をチェックします。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings 管理（.env 自動読み込み機能含む）
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 設定検証 CLI
- run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py         — ExecutionEngine 起動スクリプト

subpackages:
- ai/
  - news_nlp.py            — ニュースを LLM でスコアリングするロジック
  - regime_detector.py     — レジーム判定（MA200 + マクロニュース）
- monitoring/
  - monitoring_db.py       — SQLite のスキーマ作成 & 永続化 API
  - system_monitor.py      — システム状態・データ鮮度監視
  - trade_monitor.py       — 注文滞留・約定異常検出
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — kill.flag の管理
  - monitoring_engine.py   — 各 Monitor を束ねるポーリングエンジン
  - alert_manager.py       — LINE 通知ユーティリティ
- execution/
  - （OrderManager, ExecutionEngine, BrokerFactory 等の実装）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py     — Momentum / Volatility / Value のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計サマリ
- monitoring/
  - monitoring_db.py（上記）
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
- utils/
  - process_priority.py     — プロセス優先度 / CPU affinity 設定
- data/                    — 実行時に利用するファイル（DB、PID、flag 等）

（上記は主要ファイルの抜粋です。実装は更に細分化されています）

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）では .env の管理に注意してください（.env は Git にコミットしない）。
- validate_config の警告も重要（特に LINE 通知や KILL フラグの設定）。
- AI 機能を利用する際は OPENAI_API_KEY を安全に管理してください。API 呼び出しはリトライロジックを持ちますが、費用発生に注意。
- Paper Trading は本番データベースと完全分離されるよう設計されています。paper_trading モードでの挙動を十分に検証してから本番運用してください。
- プロセス優先度や CPU affinity の設定は psutil を用いて行います。権限や OS により設定できない場合は警告が出てスキップされます。

---

## 開発者向けメモ

- MonitoringDB.init_monitoring_db によって必要なテーブル・カラムのマイグレーションを行います（冪等）。
- run_monitoring.py は監視ループで定期的に MonitoringDB へログを残し、kill_flag の評価や LINE 通知を行います。
- run_execution.py は ExecutionEngine をスレッドで起動し、stop flag を監視して安全停止します。
- LLM 関連の HTTP/API 呼び出し部分はテスト容易性のため外部呼び出しを差し替え可能に設計されています（ユニットテストでのモックが可能）。

---

README に書かれていない細かな挙動については該当するモジュール（src/kabusys/...）の docstring を参照してください。質問や更に詳しい運用手順（起動スクリプトの systemd 設定例や Docker 化など）を希望される場合は教えてください。