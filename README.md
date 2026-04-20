# KabuSys

日本株自動売買システムのモジュール群（ライブラリ + 起動スクリプト）。  
このリポジトリは、発注エンジン、監視、ポートフォリオ構築、リサーチ（ファクター計算）、ニュースNLP（LLM）連携などを含む設計を持ちます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株向けの自動売買フレームワークです。主要コンポーネントは以下です。

- ExecutionEngine（発注エンジン）
  - ブローカークライアント経由で発注を行う（paper_trading モードでは MockBroker を使用）
  - リスク管理、オーダーマネージャ、照合機能を組み合わせてセッション実行
- Monitoring（監視）
  - システム稼働状況、注文ログ、リスク（ドローダウン・ポジション上限）を定期的に監視
  - Kill Switch（条件に応じて停止フラグを書き込み ExecutionEngine を停止）
- Portfolio（銘柄選定・配分・株数決定）
  - 候補選定、重み付け、ポジションサイズ計算、セクター制限などの純粋関数群
- Research（ファクター計算・探索）
  - Momentum / Volatility / Value ファクター計算、将来リターンやIC計算など
- AI（ニュースNLP / レジーム検出）
  - OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント評価や市場レジーム判定
- ユーティリティ
  - 設定読み込み・ウィザード、設定検証、ログ設定、プロセス優先度設定 等

---

## 主な機能一覧

- 環境・設定管理
  - .env 自動読み込み / 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
- 起動スクリプト
  - run_execution: 発注エンジン起動（KABUSYS_ENV による paper/live 切替）
  - run_monitoring: 監視ポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可能）
- 監視機能
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス・データ鮮度監視
  - TradeMonitor: 注文の滞留・約定異常検出（trade_logs テーブル参照）
  - RiskMonitor: ドローダウン・ポジション数監視、KillSwitch 連携
  - MonitoringDB: SQLite に監視ログを永続化（テーブル作成・マイグレーション含む）
- ポートフォリオ構築
  - 候補選定（スコア順）、等金額・スコア加重配分、リスクベース配分
  - セクター制限、レジーム乗数、単元株丸め、aggregate cap スケーリング
- リサーチ
  - DuckDB を使ったファクター計算（prices_daily / raw_financials 参照）
  - forward returns, IC, 統計サマリー 等
- AI連携
  - ニュース記事のセンチメントを LLM でスコア化して ai_scores に保存
  - マクロニュース + ETF MA200 乖離で市場レジーム判定し market_regime に保存
  - OpenAI API 呼び出しはリトライやバリデーションを含む安全実装
- ツール
  - paper_verification_report: Paper Trading DB から稼働率・成功率・レイテンシ等の検証レポート生成

---

## 要件

- Python 3.10+
  - union types (X | Y) を使用しているため 3.10 以上が必要
- ランタイム依存パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - （オプション）PyYAML（validate_config の YAML 検証に使用）

インストール例:
```
pip install duckdb psutil openai pyyaml
```
あるいは requirements.txt を用意している場合:
```
pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml
4. 環境変数設定
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 主なオプション・デフォルト:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO
     - OPENAI_API_KEY: （LLM 機能を使う場合に必須）
     - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

注意:
- .env は絶対に Git にコミットしないでください（シークレット含む）。

---

## 使い方（起動・ツール）

- ExecutionEngine（発注エンジン）起動:
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し data/paper_trading.db に記録（本番 DB と分離）
    - 起動前に data/stop_requested.flag が存在する場合は起動せず終了
    - 実行中に data/stop_requested.flag を作成するとエンジンを停止する
    - 実行時、プロセス優先度を "high" に設定します（set_process_priority）
- Monitoring（監視）起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き（デフォルト 60）
  - 監視は Settings.sqlite_path（monitoring.db）を使用（KABUSYS_ENV にかかわらず）
  - 停止は data/stop_requested.flag を作成
- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - DB パスは引数、環境変数 PAPER_TRADING_SQLITE_PATH、またはデフォルト data/paper_trading.db の順で決定
- ライブラリ関数の利用例（Python から直接呼び出し）
  - ポートフォリオ: from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - リサーチ: from kabusys.research import calc_momentum, calc_volatility, calc_value
  - AI スコア: from kabusys.ai import score_news（DuckDB 接続と target_date を渡す）
  - 監視用ユーティリティ: from kabusys.monitoring.monitoring_db import MonitoringDB

---

## 運用上のフラグ・ファイル

- data/stop_requested.flag
  - run_monitoring / run_execution が監視している停止フラグファイル。存在するとループを終了する（グレースフルシャットダウン）。
- data/kill.flag (Settings.kill_flag_path)
  - KillSwitch が書き込むファイル。ExecutionEngine に対する強制停止シグナルとして機能する（存在チェックで停止）。
  - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨（自動クリアしない）。
- data/execution.pid
  - ExecutionEngine の PID ファイル（起動スクリプトで使用）。

---

## ログとプロセス優先度

- ロギング:
  - 共通ユーティリティ setup_logging を全スクリプトが呼び出します。
  - 標準出力（stdout）と日次ローテーションファイル（logs/<app_name>.log）に出力。
  - ログディレクトリは環境変数 LOG_DIR で上書き可能。
- プロセス優先度:
  - 起動時に set_process_priority("high") を呼び出して優先度を上げようとします（Windows / POSIX 対応）。権限がない場合は警告を出して継続します。

---

## ディレクトリ構成

プロジェクト内の主要ファイル・ディレクトリ（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・Settings 管理（自動 .env ロード）
  - config_setup.py               — .env 対話式ウィザード（CLI）
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring ポーリング起動スクリプト
  - utils/
    - logging_setup.py            — ログ設定ユーティリティ
    - process_priority.py         — 優先度 / CPU affinity ユーティリティ
  - execution/                     — 発注エンジン関連（broker_factory, engine, order_manager など）
  - monitoring/
    - monitoring_db.py            — SQLite 永続化層（テーブル作成・MonitoringDB クラス）
    - system_monitor.py           — システム状態・データ鮮度監視
    - trade_monitor.py            — 注文ログ監視（滞留・約定異常検出）
    - risk_monitor.py             — ドローダウン・ポジション上限監視
    - monitoring_engine.py        — Monitor を束ねるエンジン
    - kill_switch.py              — Kill Switch 実装（flag ファイル書き込み）
    - alert_manager.py            — （アラート通知のラッパー。LINE 等）
  - portfolio/
    - portfolio_builder.py        — 候補選定・重み計算
    - position_sizing.py          — 株数決定・リスク制限
    - risk_adjustment.py          — セクター上限・レジーム乗数
  - research/
    - factor_research.py          — Momentum / Volatility / Value 計算（DuckDB）
    - feature_exploration.py      — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py                 — ニュース記事の LLM スコアリング
    - regime_detector.py          — マクロ＋ETF MA によるレジーム判定
  - data/                         — （実行時に利用する SQLite / DuckDB / フラグ / pid 等）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

---

## 注意事項 / 運用のヒント

- KABUSYS_ENV が `live` の場合は設定ミスによる実トレードの危険があるため、validate_config を重点的に実行してください。
- Paper Trading モードは paper_trading 専用 DB（PAPER_TRADING_SQLITE_PATH）に記録され本番 DB と分離されます。テスト・検証はこのモードで行ってください。
- OpenAI API を使用する機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）が必要です。API 失敗時はフォールバックする実装ですが、API キーの管理に注意してください。
- DuckDB / SQLite ファイルパスの親ディレクトリが存在しない場合、起動時に自動作成される場合がありますが、アクセス権やバックアップ方針を事前に確認してください。
- kill.flag や stop_requested.flag を誤って削除・クリアすると意図しない挙動になる可能性があります。本番運用ルールを定めてください。

---

必要であれば README に「起動例」「環境変数テンプレート（.env.example）」「systemd / supervisor 用のサービスユニット例」などの具体的な運用手順を追記します。どの情報を詳しく載せたいか教えてください。