# KabuSys — README

このリポジトリは日本株向けの自動売買 / 研究 / 監視ツール群（KabuSys）のコア部分です。本 README はコードベース（src/kabusys 以下）の概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

KabuSys は以下のような機能を持つモジュール群から構成されています。

- 実行エンジン（ExecutionEngine）: 発注ロジック・注文管理・リスク管理を担う（実際のブローカ API またはモックを利用可）
- 監視（Monitoring）: システム稼働状況、注文ログ、リスク指標を定期ポーリングして記録・アラートを発行
- ポートフォリオ構築（Portfolio）: 候補選定、重み計算、ポジションサイズ算出、セクター制約・レジーム調整
- 研究（Research）: ファクター計算、将来リターン、IC 計算、統計要約
- AI モジュール: ニュースの NLP によるセンチメント評価（OpenAI API を使用）
- ユーティリティ: ロギング設定、プロセス優先度制御、環境設定ウィザード / 検証 CLI
- 永続領域: DuckDB（分析用）・SQLite（監視 / 発注ログ）

設計方針の一部:
- データベース・ファイルパスは環境変数 / .env で指定可能（デフォルトはプロジェクト配下の data/）
- Paper Trading（模擬発注）は本番 DB と完全分離（data/paper_trading.db）
- ルックアヘッドバイアスを避けるため、日付計算は明示的に渡す設計
- フェイルセーフ: 外部 API 等が失敗してもシステム全体が停止しない設計

---

## 機能一覧（主なもの）

- 実行/発注関連
  - ExecutionEngine 起動スクリプト: src/kabusys/run_execution.py
  - ブローカクライアントは環境に応じて実際のクライアント or Mock を選択
  - Paper Trading は専用 SQLite に記録

- 監視関連
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / Execution プロセス監視
  - TradeMonitor: 注文滞留・約定の異常検出（trade_logs）
  - RiskMonitor: ドローダウン・ポジション上限監視、Kill Switch（kill.flag）発行
  - MonitoringEngine: 各 Monitor を束ねたポーリングループ
  - run_monitoring 起動スクリプト（MONITOR_POLL_INTERVAL 環境変数で間隔変更可）

- 研究 / データ処理
  - ファクター計算（momentum, volatility, value）: duckdb 上で SQL+Python で計算
  - feature exploration（forward returns, IC, rank, summary）
  - DuckDB を用いた分析に最適化

- AI（LLM）関連
  - ニュース NLP（OpenAI）で銘柄ごとにセンチメントを算出し ai_scores に格納
  - 市場レジーム判定（ETF ma200 とマクロニュースの LLM スコアを合成）

- 設定管理 / ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 起動前設定検証 CLI（validate_config）: env / config/*.yaml のチェック
  - ログ設定ユーティリティ（stdout + 日次ローテートファイル）
  - プロセス優先度・CPU affinity 設定ユーティリティ

- ツール
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

---

## セットアップ手順（開発環境）

1. Python 環境
   - Python 3.10+ を推奨（コード内の型注釈等より）
   - 仮想環境作成（例）
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージのインストール
   - 必須ライブラリ（例）:
     - duckdb
     - psutil
     - openai  （AI 機能を使わない場合は不要）
     - PyYAML （config YAML のパースを実行したい場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （※ リポジトリに requirements.txt がない場合は上記を手動でインストールしてください）

3. プロジェクトルートの位置
   - config_setup / validate_config はプロジェクトルート（.git や pyproject.toml を探索）を基準に動作します。
   - .env 自動読み込みはデフォルトで有効。自動ロードを無効化する場合は環境変数:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 初期設定 (.env)
   - 対話式ウィザードを使って .env を作成:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN（J-Quants 用）
     - KABU_API_PASSWORD（kabuステーション API）
   - 主要な環境変数（概要）:
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH: data/kabusys.duckdb（分析用）
     - SQLITE_PATH: data/monitoring.db（監視ログ）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
     - OPENAI_API_KEY: OpenAI を使う場合必須
     - LOG_LEVEL / LOG_DIR
     - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（run_monitoring 用、デフォルト: 60）

5. 設定検証
   - 起動前に設定を検証:
     - python -m kabusys.validate_config
     - 警告を FAIL として扱う strict モード:
       - python -m kabusys.validate_config --strict

---

## 使い方（起動コマンド・主要フロー）

- ExecutionEngine（売買エンジン）を起動
  - 本番または paper_trading に応じて DB / ブローカが切り替わります
  - コマンド:
    - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録
    - 起動時に data/stop_requested.flag が存在する場合は起動をスキップ
    - 実行中は data/execution.pid に PID を書きます
    - 停止は kill.flag（KillSwitch）や stop_requested.flag による仕組みを利用できます

- Monitoring（監視ループ）を起動
  - コマンド:
    - python -m kabusys.run_monitoring
  - 振る舞い:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60秒）
    - 監視は常に production の sqlite_path を使用（環境に無関係）
    - 監視ループは data/stop_requested.flag を検知すると終了

- Paper Trading 検証レポート生成
  - コマンド:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB 指定:
      - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- .env の作成 / 更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- AI 機能（ニューススコアリング / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY か関数呼び出し時に引数指定）
  - 関数:
    - kabusys.ai.score_news(...)
    - kabusys.ai.regime_detector.score_regime(...)

---

## 実運用での注意点 / 運用メモ

- Kill Switch / stop フラグ
  - data/kill.flag: Kill Switch による ExecutionEngine 停止シグナル（作成は KillSwitch.evaluate）
  - data/stop_requested.flag: run_* スクリプトの外部停止フラグ（存在検知でループ終了）
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動で kill.flag をクリアしますが、本番では推奨されません（危険）

- Paper Trading と本番 DB の分離
  - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite に完全分離されます（本番 DB へ影響しない）

- ログ
  - ログは標準出力と日次ローテートファイル（デフォルト logs/）へ出力されます
  - ログレベルは LOG_LEVEL 環境変数で変更可能

- DB マイグレーション
  - monitoring_db.init_monitoring_db は起動時に必要テーブルと簡易マイグレーション（カラム追加）を行います（冪等）

- 外部 API エラー対応
  - OpenAI 等の API 呼び出しはリトライ／フォールバックの実装あり（RateLimit, timeout, 5xx など）
  - API キーが未設定の場合は例外やフォールバック動作があるため、ログをよく確認してください

---

## ディレクトリ構成（主要ファイルの説明）

（ルート: src/kabusys）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL で間隔指定可。

- run_execution.py
  - ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は MockBroker を使用。

- config.py
  - 環境変数 / .env の自動読み込み、Settings クラス（アプリ設定）定義。

- config_setup.py
  - .env を対話的に作成・更新するウィザード。

- validate_config.py
  - 起動前の設定検証 CLI（環境変数と config/*.yaml の基本チェック）。

- __init__.py
  - パッケージ情報（__version__ 等）。

- tools/
  - paper_verification_report.py: Paper Trading の検証レポート生成。

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算（等重・スコア加重）
  - position_sizing.py: 株数計算（各種上限・lot 切り捨て・aggregate cap）
  - risk_adjustment.py: セクターキャップ適用・レジーム乗数算出
  - __init__.py: 公開 API

- monitoring/
  - monitoring_db.py: SQLite を利用した監視ログ永続化層（テーブル作成・CRUD ヘルパ）
  - system_monitor.py: システム稼働・データ鮮度チェック
  - trade_monitor.py: （注文ログ監視、該当ファイルあり）
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag 書き込みロジック
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - alert_manager.py: （アラート通知の管理、該当ファイルあり）

- ai/
  - news_nlp.py: ニュースを LLM（OpenAI）でスコアリングし ai_scores に書込
  - regime_detector.py: ETF MA200 とマクロニュース LLM スコアを組合せてレジーム判定
  - __init__.py

- research/
  - factor_research.py: Momentum/Volatility/Value 等のファクター計算
  - feature_exploration.py: 将来リターン / IC / 統計サマリー
  - __init__.py

- utils/
  - logging_setup.py: 共通ロギング設定（stdout + TimedRotatingFileHandler）
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

- data/ （実行時に利用するディレクトリ・ファイル）
  - monitoring.db（SQLite、デフォルト）
  - paper_trading.db（Paper Trading 用）
  - kabusys.duckdb（分析用）
  - execution.pid / stop_requested.flag / kill.flag（運用用フラグ / pid）

- config/ （設定テンプレート）
  - system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
  - validate_config で存在チェックや YAML パースを行えます（PyYAML が必要）

---

## 代表的な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI を使う場合の API キー
- LOG_LEVEL — ログレベル（INFO / DEBUG / ...）
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒, デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（0/1、0 推奨）

---

## よくある操作例

- .env を対話的に作る
  - python -m kabusys.config_setup

- 設定チェック（警告を FAIL とする場合）
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（バックグラウンド等はシェルツールで管理）
  - python -m kabusys.run_execution

- 監視エンジン起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート（過去期間）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## トラブルシューティング / ヒント

- ログファイルが作成されない場合
  - LOG_DIR のパーミッションやディレクトリ作成に失敗していないか確認。setup_logging は失敗時に stdout のみで継続します。

- 起動スクリプトが即終了する / 起動しない場合
  - data/stop_requested.flag の有無を確認（存在すると起動をスキップ）
  - validate_config で必須環境変数が満たされているか確認

- OpenAI 関連で JSON パースエラーが出る場合
  - API レスポンスが期待フォーマットでない場合、ログに出力されるので内容を確認。キーやモデル、料金制限（429）も確認

- DB 接続 / テーブル不整合
  - monitoring_db.init_monitoring_db は必要テーブルの作成と簡易マイグレーションを実施します。テーブルが存在しない場合はまず init が呼ばれているか確認

---

この README は該当コードベース（src/kabusys 配下）の主要な使い方と設計意図をまとめたものです。詳細な設計文書（PortfolioConstruction.md / StrategyModel.md 等）や追加のスクリプトがリポジトリ内に存在する場合、それらも参照して運用してください。必要であれば、さらに詳しいデプロイ手順（systemd / Supervisor / Docker 化など）や CI / テスト手順の追記も対応できます。