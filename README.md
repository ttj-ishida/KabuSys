# KabuSys — 日本株自動売買システム (README)

このリポジトリは日本株向けの自動売買システムのコアライブラリ群です。戦略・ポートフォリオ構築、発注エンジン、監視、研究用ユーティリティ、AIによるニュース評価などのコンポーネントを含みます。

以下は簡易ドキュメントです。開発・運用の開始手順、主要機能、使い方、ディレクトリ構成を日本語でまとめています。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数（主要項目）
- 運用上の注意
- ディレクトリ構成（ファイル説明）

---

## プロジェクト概要

KabuSys は以下を目的とした Python ベースのモジュール群です。

- 日次・実時のファクター計算とシグナル生成（研究モジュール）
- ポートフォリオ構築（候補選定、重み付け、銘柄ごとの発注株数計算）
- 発注および注文管理（ExecutionEngine と BrokerClient 抽象）
- 監視（システム状態・注文状態・リスクの定期チェック）と Kill Switch
- Paper Trading 用検証ツール、AI を使ったニュース NLP、レジーム判定
- ロギング・設定管理・ユーティリティ類

設計方針の一部：
- DuckDB / SQLite を使ったローカルデータベースで分析とログ永続化
- 環境変数（.env）の上書きに対応し、config_setup/validate_config を提供
- OpenAI API を利用した NLP 機能は任意（APIキーを必要とする）

---

## 機能一覧（抜粋）

- 環境設定ウィザード: python -m kabusys.config_setup（.env を対話式生成）
- 設定検証 CLI: python -m kabusys.validate_config（起動前チェック）
- 発注エンジン起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し paper_trading DB に記録
- 監視ポーリング: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
- 監視 DB 永続化（SQLite）: monitoring/monitoring_db.py
- RiskMonitor, TradeMonitor, SystemMonitor, KillSwitch, MonitoringEngine
- Portfolio モジュール：候補選定、重み付け、ポジションサイズ計算、セクター制約
- Research モジュール：ファクター（モメンタム・ボラティリティ・バリュー）、特徴量解析
- AI モジュール：
  - kabusys.ai.news_nlp.score_news: raw_news を LLM で評価して ai_scores に書き込み
  - kabusys.ai.regime_detector.score_regime: MA200 と LLM でレジーム判定
- ツール:
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

---

## セットアップ手順

前提:
- Python 3.9+（リポジトリの pyproject.toml / requirements を参照）
- システムに duckdb, psutil, openai（AI 機能時）、PyYAML（設定検証で YAML を検証する場合）などをインストール

例: 仮想環境作成 & 必要パッケージ（簡易）
```
python -m venv .venv
source .venv/bin/activate
pip install -e .      # パッケージを開発モードでインストール（pyproject.toml に依存）
pip install duckdb psutil openai pyyaml   # 必要に応じて追加
```

初期環境設定（.env 作成）
```
python -m kabusys.config_setup
# 対話式に入力することで .env をプロジェクトルートに作成します
```

作成後、設定検証を実行
```
python -m kabusys.validate_config
# --strict を付けると警告もエラー扱い
```

データディレクトリ（デフォルト）:
- data/: SQLite / PID / flag ファイル等を置く（自動作成されることが多い）
- logs/: ログファイル（デフォルト）

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env の作成 / 更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定チェック（起動前）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 発注エンジン（ExecutionEngine）を起動
  ```
  python -m kabusys.run_execution
  ```
  ポイント:
  - KABUSYS_ENV が `paper_trading` の場合、本番 SQLite とは別の PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）にログを記録します。
  - 実行中は pid ファイル（data/execution.pid がデフォルト）を使用します。
  - data/stop_requested.flag が存在すると起動を停止・エンジン停止を試みます。

- 監視ループを起動
  ```
  python -m kabusys.run_monitoring
  ```
  ポイント:
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書きできます（整数秒）。
  - 監視は本番 sqlite_path を使います（環境に関係なく本番 DB を参照する仕様）。
  - 監視は system/trade/risk モジュールを回し、必要に応じて kill.flag を書き込む・アラート送出を行います。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # --db で DB パスを明示指定可能
  ```

- AI 機能（ニュース評価 / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数で指定）
  - 例（Python REPL から実行）:
    ```python
    from pathlib import Path
    import duckdb
    from kabusys.ai.news_nlp import score_news
    from datetime import date

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,1), api_key="sk-...")
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,1), api_key="sk-...")
    ```

---

## 環境変数（主要項目・デフォルト）

（.env を config_setup で作成できます）

- 必須（運用時）
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）

- データベース / ファイルパス
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag

- ログ
  - LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR: logs/

- Paper Trading の振る舞い
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- 監視ループ
  - MONITOR_POLL_INTERVAL: ポーリング秒数（run_monitoring で利用、デフォルト 60）

- OpenAI
  - OPENAI_API_KEY: AI 機能を使う場合に必要

- LINE 通知（任意、本番時推奨）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID

- その他
  - KILL_FLAG_CLEAR_ON_START: 0/1（本番では 0 推奨）

---

## 運用上の注意

- 本番環境（KABUSYS_ENV=live）では kill フラグや LINE 通知などの設定を慎重に行ってください。validate_config は live 時に追加のチェックと注意喚起を行います。
- run_monitoring は監視データの書き込み先に sqlite_path（monitoring DB）を常に使用します。paper_trading と分離したい場合は設定を調整してください。
- run_execution は paper_trading モード時、paper_trading 用 DB に記録するため、本番 DB と完全に分離されます。
- OpenAI を使う機能は API エラーやレート制限を想定し、リトライやフェイルセーフが組み込まれていますが、API キー管理・コストには注意してください。
- ログディレクトリの作成に失敗した場合はコンソールログのみで動作します。運用環境では logs/ の書き込み権限を確認してください。
- kill.flag（Settings.kill_flag_path）を作成すると ExecutionEngine に停止シグナルを送ります。存在確認・クリアのタイミングは設定に依存します。

---

## ディレクトリ構成（主要ファイルの説明）

src/kabusys/
- __init__.py — パッケージ宣言、バージョン
- config.py — 環境変数 / 設定解決ロジック（Settings クラス）
- config_setup.py — .env 対話式ウィザード（python -m kabusys.config_setup）
- validate_config.py — 起動前の設定検証 CLI（python -m kabusys.validate_config）

scripts / エントリポイント相当（モジュール）
- run_execution.py — ExecutionEngine 起動スクリプト（pid, stop flag 処理, paper_trading 切り分け）
- run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 対応）

monitoring/
- monitoring_db.py — SQLite のスキーマ定義 / 永続化層（MonitoringDB）
- system_monitor.py — システム監視（CPU/メモリ/ディスク、データ鮮度、プロセス監視）
- trade_monitor.py — （存在するがコード抜粋に含まれない）取引監視ロジック
- risk_monitor.py — ドローダウン・ポジション上限監視
- monitoring_engine.py — 各 Monitor を束ねる実行エンジン
- kill_switch.py — kill.flag の書き込み / 管理
- alert_manager.py — （存在: アラート送出ロジック）

execution/
- execution_engine.py — 実際の発注ループ／セッション管理（Engine）
- broker_factory.py — BrokerClient の生成 (本番 / Mock 切り替え)
- order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注・リスク関連

portfolio/
- portfolio_builder.py — 候補選定 / 重み計算
- position_sizing.py — 株数算出・丸め処理・上限・aggregate cap
- risk_adjustment.py — セクターキャップ・レジーム乗数

research/
- factor_research.py — momentum/volatility/value のファクター計算（DuckDB を使用）
- feature_exploration.py — forward returns, IC, summary

ai/
- news_nlp.py — raw_news を LLM で評価して ai_scores に書き込む
- regime_detector.py — MA200 と LLM を合成して market_regime を出力

tools/
- paper_verification_report.py — ペーパートレード検証レポート生成 CLI

utils/
- logging_setup.py — 統一ロギング設定（console + 日次ローテーションファイル）
- process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

data/ (推奨)
- デフォルトのデータファイル置き場（SQLite, DuckDB, pid/flag ファイル 等）
  - data/kabusys.duckdb
  - data/monitoring.db
  - data/paper_trading.db
  - data/execution.pid
  - data/kill.flag
  - data/stop_requested.flag

logs/（デフォルト）
- アプリケーションログ（例: logs/execution.log, logs/monitoring.log）

---

最後に

- この README はコードベースに含まれる docstring と設計コメントを元に要点をまとめています。実際の運用前に python -m kabusys.validate_config を実行し、.env を適切に設定してください。
- 追加で必要な情報（詳細な ExecutionEngine の設定、Broker 実装、TradeMonitor の挙動、アラート先の設定など）を希望される場合は、該当モジュールのドキュメント化を行いますので教えてください。