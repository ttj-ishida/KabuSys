# KabuSys

KabuSys は日本株の自動売買システムのコードベースです。本リポジトリは取引エンジン、監視・アラート、ポートフォリオ構築、リサーチ／ファクター計算、LLM を利用したニュース分析などのコンポーネントを含みます。

---

## プロジェクト概要

- 目的: 日本株の自動売買を支援するためのバックエンドライブラリ群および運用用スクリプト群。
- 主要設計方針:
  - 実行環境（development / paper_trading / live）を切り替え可能。
  - Paper Trading（模擬発注）は本番 DB と完全分離して記録。
  - DuckDB を分析用 DB として使用、SQLite を監視・取引ログ用に使用。
  - OpenAI（gpt-4o-mini 等）を使ったニュース NLP / レジーム判定機能を搭載（API キー必須）。
  - ログ設定・プロセス優先度調整・kill-switch 等の運用機能を提供。

---

## 機能一覧

- 実行コンポーネント
  - ExecutionEngine 起動スクリプト（run_execution.py）
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い `data/paper_trading.db` に記録
    - プロセス優先度を設定し、スレッドで実行
- 監視コンポーネント
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねた MonitoringEngine（run_monitoring.py）
  - 監視ログの永続化（SQLite）とアラート発火
  - KillSwitch による停止フラグ（data/kill.flag）生成
  - stopRequested フラグ（data/stop_requested.flag）で外部からループ停止可能
- ポートフォリオ構築
  - 候補選定、重み計算（等金額・スコア重み）、ポジションサイズ計算、セクター上限処理、レジーム乗数
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上の prices_daily, raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI（LLM）関連
  - news_nlp: ニュース記事を集約して LLM に投げ、銘柄ごとのセンチメント（ai_scores）を算出・保存
  - regime_detector: ETF の MA200 乖離と LLM によるマクロセンチメントを合成して日次で市場レジーム判定
- 運用ツール
  - 環境設定ウィザード（config_setup.py）で .env を対話的に作成
  - 設定検証 CLI（validate_config.py）で必須環境変数や config/*.yaml の有無をチェック
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）

---

## 前提条件

- Python 3.9+
- 推奨パッケージ（抜粋）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証時に必要）
- SQLite（標準ライブラリで利用可能）
- ネットワーク（OpenAI API を使う場合）

※ requirements.txt はプロジェクトに含めていない想定のため、上記パッケージを環境に合わせて pip でインストールしてください。

例:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. .env の作成
   - 対話式で作る: python -m kabusys.config_setup
     - J-Quants / kabu API のトークンや KABUSYS_ENV（development / paper_trading / live）などを設定します。
   - 手動で作る: リポジトリルートに .env を配置（.env.example を参考に）
5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする: python -m kabusys.validate_config --strict
6. データディレクトリの作成（必要なら）
   - デフォルトの DB / ログ / data ディレクトリは自動で作成されますが、権限等で失敗する場合は手動で作成してください。

---

## 主要な環境変数（よく使うもの）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring 用、デフォルト: 60）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1=クリアする、default 0。live では注意）

---

## 使い方（主要コマンド）

- 環境ウィザード（.env の生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合は paper_trading の専用 SQLite に記録され本番 DB と分離されます。

- Monitoring 起動（監視ループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH を使用して DB パスを指定することも可能

- LLM を使った処理（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI キーは引数または OPENAI_API_KEY 環境変数で渡す
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 停止 / Kill フラグの扱い

- stop_requested.flag（data/stop_requested.flag）
  - run_monitoring.py / run_execution.py はこのファイルの存在を監視しており、存在すると安全にループを終了します。外部から両プロセスを停止させたいときに使えます。
- kill.flag（Settings.kill_flag_path、デフォルト: data/kill.flag）
  - KillSwitch（監視側）が書き込むことで ExecutionEngine 停止を要求する専用フラグです（リスク条件がトリガーした場合など）。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動的に clear されますが、本番環境では危険なのでデフォルトは 0 を推奨します。

---

## ログ

- ログは kabusys.utils.logging_setup.setup_logging() によって設定されます。
  - コンソール（stdout）出力 + 日次ローテーションのファイル出力（logs/<app_name>.log）
  - ログディレクトリは環境変数 LOG_DIR またはデフォルト `logs/` を使用
  - 保持期間は 30 日（TimedRotatingFileHandler の backupCount）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- run_execution.py             — ExecutionEngine 起動スクリプト
- run_monitoring.py            — Monitoring ポーリング起動スクリプト
- config.py                    — 環境変数 / 設定管理
- config_setup.py              — .env 対話式ウィザード
- validate_config.py           — 設定検証 CLI
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成
- ai/
  - news_nlp.py                 — ニュース NLP（OpenAI 経由でスコアを生成）
  - regime_detector.py          — 市場レジーム判定（MA + LLM）
- monitoring/
  - monitoring_db.py            — 監視用 SQLite 永続化層
  - system_monitor.py           — システム状態・データ鮮度監視
  - trade_monitor.py            — 発注/約定監視（参照用）
  - risk_monitor.py             — ドローダウン・ポジション上限監視
  - kill_switch.py              — Kill Switch ロジック
  - monitoring_engine.py        — 各 Monitor の束ね役
  - alert_manager.py            — （アラート送信ラッパー、実装参照）
- portfolio/
  - portfolio_builder.py        — 候補選定・重み付け
  - position_sizing.py          — 株数決定・単元丸め・利用キャッシュによるスケール
  - risk_adjustment.py          — セクター上限・レジーム乗数
- research/
  - factor_research.py          — ファクター計算（momentum/vol/value/volatility）
  - feature_exploration.py      — 将来リターン・IC・統計サマリー
- utils/
  - logging_setup.py            — ログ初期化ユーティリティ
  - process_priority.py         — プロセス優先度 / CPU affinity 設定
- monitoring/... (上記に含む)
- その他: execution/*、data/*、strategy/* 等は別モジュール群（リポジトリの全体構成に依存）

---

## 運用上の注意

- 本番環境（KABUSYS_ENV=live）では設定とシークレットに十分注意してください。validate_config の警告を無視しないでください。
- Paper Trading は本番 DB と分離されますが、設定ミスに備えて .env や DB パスを二重に確認してください。
- OpenAI API を利用する機能は API コスト・レイテンシに注意して運用してください。失敗時はフェイルセーフで継続する設計ですが、結果品質は入力プロンプトやモデルに依存します。
- ログと DB のバックアップ・アクセス権限管理を適切に行ってください。

---

## 開発・貢献

- 新しい機能や設定を追加する場合、config/*.yaml（各種設定テンプレート）と validate_config を更新して整合性を保ってください。
- LLM 呼び出し関数はユニットテストで patch/モックしやすいように分離実装されています。自動テストを書く際は _call_openai_api 等を差し替えてください。

---

必要であれば README の英語版、より詳細な運用手順（systemd / Supervisor / Docker を使ったデプロイ例）、または各モジュールごとの API ドキュメントを追加で作成します。どの情報が優先か教えてください。