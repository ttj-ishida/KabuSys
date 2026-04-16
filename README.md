KabuSys — 日本株自動売買システム (README)
=====================================

概要
----
KabuSys は日本株の自動売買を想定した小～中規模のシステム群です。本リポジトリには以下の主要機能を含みます。

- 実行エンジン（ExecutionEngine）: ブローカーとの注文発行・状態管理・リスク管理を行う
- 監視（Monitoring）: システム状態・注文滞留・リスク（ドローダウン等）をポーリングしてログ／アラートを出す
- ポートフォリオ構築ユーティリティ: 候補選定、重み付け、株数算出、セクター制限、レジーム調整
- リサーチモジュール: ファクター計算、将来リターン、IC 等の統計ユーティリティ
- AI 補助: ニュースセンチメント集計（OpenAI）・市場レジーム判定
- ツール: Paper Trading 検証レポート生成、Streamlit ダッシュボード等
- 設定/ユーティリティ: .env 自動読込、プロセス優先度設定など

特徴
----
主な特徴・設計方針:

- 環境（development / paper_trading / live）に応じた挙動を切り替え（paper_trading は本番 DB と分離）
- DuckDB（時系列 / ファクターデータ）＋SQLite（監視ログ／注文ログ）を併用
- OpenAI を用いたニュースセンチメント・レジーム判定（APIキー必要、フェイルセーフあり）
- 冪等設計（DB初期化・書き込み）や再起動時のリコンシリエーション処理を実装
- 監視用にLINE通知・Streamlitダッシュボードをサポート
- 各機能は可能な限り副作用を抑えた純粋関数／独立モジュールで実装

セットアップ手順
----------------

前提
- Python 3.10 以上（型注釈で | 演算子を使用）
- Git
- 必要パッケージ（例: pip でインストール）

推奨パッケージ（主なもの）
- duckdb
- psutil
- openai
- requests
- streamlit

例: 仮想環境作成とインストール
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール（requirements.txt がある場合はそれを利用）
   - pip install duckdb psutil openai requests streamlit

（プロジェクトに requirements.txt / setup.py があれば pip install -e . や pip install -r requirements.txt を用いてください）

環境変数 / .env
- 自動でプロジェクトルートの .env と .env.local を読み込みます（OS 環境変数が優先）。
- 自動読込を無効にする場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 重要な環境変数（例）:
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能使用時必須）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（外部 API 用）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視用デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading の DB、デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE（paper_trading の約定挙動: instant | partial | never | reject）
  - PID_FILE_PATH / KILL_FLAG_PATH 等

簡易 .env.example（参考）
- KABUSYS_ENV=development
- OPENAI_API_KEY=your_openai_key
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

データディレクトリ
- data/ 配下に DB・PID・フラグファイル等を配置します（自動で作成される箇所もあります）。

使い方
------

実行エンジン（Execution）
- run_execution.py を起動すると ExecutionEngine が起動します。
- Module 実行例:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。
  - 停止は data/stop_requested.flag を作成することで実施（KillSwitch 経由の停止は別：data/kill.flag）。

監視ループ（Monitoring）
- run_monitoring.py を起動すると SystemMonitor のポーリングループが開始され、監視ログを SQLite に記録します。
- Module 実行例:
  - python -m kabusys.run_monitoring
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60）。
- 監視ループは data/stop_requested.flag を検知すると終了します。
- 監視は実行エンジンの PID（設定された PID ファイル）存在を確認し、プロセス stale を検出します。

Streamlit ダッシュボード
- 起動方法（読み取り専用で監視 DB を開く）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

Paper Trading 検証レポート
- ツール: kabusys.tools.paper_verification_report
- 実行例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB を指定可能（--db PATH）

AI 機能（ニュース NLP / レジーム判定）
- OpenAI API キーが必要（env: OPENAI_API_KEY または関数引数）。
- ライブラリ関数として利用:
  - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None) → ai_scores テーブルへ書き込み、戻り値は書き込み銘柄数
  - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None) → market_regime テーブルへ書き込み
- API 呼び出しに失敗してもシステムはフェイルセーフ（デフォルト値を使って継続）する設計です。

停止制御 / フラグ
- data/stop_requested.flag: run_* スクリプトの外部停止トリガー（存在検知でループ終了）
- data/kill.flag: KillSwitch が生成する停止フラグ（ExecutionEngine に停止信号）
- PID ファイル: data/execution.pid（ExecutionEngine が自身の PID を書き込む）

主要設定の挙動まとめ
- KABUSYS_ENV:
  - development: 開発用（デフォルト）
  - paper_trading: Mock Broker + paper_trading DB を使用（本番 DB と完全分離）
  - live: 本番運用想定
- PAPER_FILL_MODE (paper_trading):
  - instant / partial / never / reject（不正値はエラー）
- MONITOR_POLL_INTERVAL: SystemMonitor のポーリング間隔（秒、デフォルト 60）

ディレクトリ構成
----------------
主要なファイル・モジュール:

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / .env ロードと Settings
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py  — ExecutionEngine 起動スクリプト
  - data/              — 実行時生成される DB / PID / flag の想定場所（リポジトリ直下）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py     — SQLite テーブル作成・読み書きラッパー
    - system_monitor.py    — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py     — 注文滞留・約定異常検出
    - risk_monitor.py      — ドローダウン・ポジション上限監視
    - kill_switch.py       — フラグ書き込みによる停止シグナル作成
    - alert_manager.py     — LINE プッシュ通知
    - monitoring_engine.py — 監視コンポーネントの統合ループ
    - streamlit_dashboard.py — Streamlit ベースの可視化ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py (実行エンジン本体ファイルがある想定)
    - broker_factory.py / broker_api.py など（ブローカー関連）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py         — ニュースのセンチメントスコアリング（OpenAI）
    - regime_detector.py  — マーケットレジーム判定（MA + マクロセンチメント）
    - __init__.py
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成 CLI
    - __init__.py

（上記はコードベースに含まれる主要ファイルの抜粋です）

運用上の注意
------------
- 本システムは実際の発注を想定するため、live 環境では注意して運用してください。
- paper_trading モードを使うことで、本番 DB と完全に分離して挙動検証が可能です。
- OpenAI API を利用する処理は呼び出し回数やバッチサイズに制約があるため、APIキー管理・利用量に注意してください。
- DB スキーマは init_monitoring_db() により冪等に初期化されますが、バックアップ運用を推奨します。
- プロセス優先度・CPU affinity の設定はプラットフォーム（権限）に依存しており、失敗した場合は警告ログが出ますが処理は継続します。

サポート / 貢献
----------------
- バグ報告や改善提案は Issue を立ててください。
- テストや CI の導入、requirements.txt の整備、セットアップスクリプト (setup.py/pyproject.toml) の追加を歓迎します。

以上。必要であれば、README に含める具体的な .env.example の完全版、requirements.txt の推奨内容、あるいは各モジュールの API 使用例（コードスニペット）を追加します。どの項目を詳しく書き足しますか？