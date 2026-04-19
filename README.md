# KabuSys

日本株向け自動売買システム（リサーチ / ポートフォリオ構築 / 発注エンジン / 監視 / AI 補助機能）の参照実装です。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能群を備えたモジュール式自動売買フレームワークです。

- データ分析（DuckDB ベース）のための research/ファクター計算
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ決定、セクター制限）
- Execution エンジン（ブローカー抽象化、ペーパートレード分離）
- 監視（システム稼働状況、注文ログ、リスク監視、Kill Switch）
- AI 補助（ニュース NLP によるセンチメント、マーケットレジーム判定）
- 運用ツール（ペーパートレード検証レポート等）
- 環境設定ウィザード・設定検証 CLI

設計方針として、実行系と研究系の責務を分離し、テスト可能でフォールトトレラントな実装を目指しています。

---

## 主な機能一覧

- Execution
  - 実際のブローカークライアント/Mock を切り替えて実行可能（KABUSYS_ENV に依存）
  - リスク管理（ポジション上限・利用率等）
  - 注文管理・再整合（reconciler）

- Monitoring
  - CPU/メモリ/ディスクの監視と永続化（SQLite）
  - 発注ログ・リスクログの記録
  - Kill Switch（条件に応じて data/kill.flag を書き込み、Execution を安全停止）
  - ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔変更可）

- Portfolio
  - 候補選定（スコア順、上位 N 件）
  - 重み付け（等金額、スコア加重）
  - リスク補正（セクターキャップ、レジーム乗数）
  - ポジションサイズ決定（単元株丸め、aggregate cap のスケール）

- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）などの解析ユーティリティ

- AI
  - ニュース NLU による銘柄センチメント（OpenAI 使用）
  - マクロニュース + ETF ma200 による市場レジーム判定

- Tools
  - Paper Trading 検証レポート生成スクリプト

- 開発支援
  - .env 対話式ウィザード（kabusys.config_setup）
  - 起動前設定検証 CLI（kabusys.validate_config）

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（typing の | 演算子を使用）
- system に duckdb, psutil, openai 等をインストール

1. リポジトリをクローンし、作業ディレクトリへ移動
   - （例）git clone ... && cd <repo>

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  # Linux/macOS
   - .venv\Scripts\activate     # Windows

3. 必要なパッケージをインストール
   - 一例:
     - pip install duckdb psutil openai pyyaml
   - validate_config で YAML 検証を行う場合は `PyYAML` が必要です。

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードで J-Quants や kabuAPI のパスワードなどを設定します。

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6. データディレクトリ（data/）やログディレクトリ（logs/）は自動作成されますが、パーミッション等に注意してください。

---

## 環境変数（主要）

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

推奨 / オプション
- KABUSYS_ENV — 実行環境。development | paper_trading | live（デフォルト: development）
  - paper_trading: Mock ブローカーを使い、data/paper_trading.db を使用
  - live: 本番（実際に発注）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs/）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知設定（任意）
- OPENAI_API_KEY — OpenAI を使う機能で使用
- MONITOR_POLL_INTERVAL — monitoring のポーリング間隔（秒、デフォルト: 60）

Paper Trading 特有
- PAPER_FILL_MODE — paper_trading 時の約定挙動:
  - instant | partial | never | reject（デフォルト: instant）

Kill Switch / PID
- data/kill.flag — Kill Switch が書き込まれると ExecutionEngine 停止
- data/execution.pid — ExecutionEngine の PID ファイル（起動時に生成）

---

## 使い方（基本コマンド）

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- Execution エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、paper DB に記録されます。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI / 研究系（ライブラリ呼び出し）
  - ライブラリ関数として利用可能:
    - from kabusys.ai import score_news
    - from kabusys.ai import score_regime  # kabusys.ai.regime_detector.score_regime
    - research モジュール: kabusys.research.calc_momentum 等

運用メモ:
- 停止: data/stop_requested.flag を作成すると run_monitoring/run_execution 側で検出してGraceful停止します。
- Kill Switch はリスク基準を満たした場合に data/kill.flag を生成します（Execution 側は起動時にこれを検査）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- config_setup.py
- validate_config.py
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py         — Monitoring ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py              — ニュースセンチメント（OpenAI）
  - regime_detector.py       — レジーム判定（ma200 + マクロセンチメント）
- monitoring/
  - monitoring_db.py         — SQLite 永続化層
  - system_monitor.py
  - trade_monitor.py         — （存在する想定のモジュール）
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py         — （通知処理、存在する想定）
- execution/
  - execution_engine.py
  - broker_factory.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

プロジェクトルート
- .env (ユーザー作成)
- data/ (DB・フラグ・PID 等)
- logs/ (ログ出力)

※ 上記はリポジトリ内の主なファイル・モジュールを抜粋した構成です。

---

## 運用・開発上の注意

- KABUSYS_ENV によって DB の使い分けやブローカー実装が変わるため、paper_trading と live は明確に分離して運用してください。
- .env は秘匿情報を含むため、決して Git にコミットしないでください。
- OpenAI API を利用する機能は API キーが必要です。API 利用量・コストに注意してください。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリへの書き込み権限を事前に確認してください。
- Monitoring の polling により監視・Kill Switch が動作します。重要な設定は validate_config で事前チェックしてください。
- データベーススキーマ変更（マイグレーション）は monitoring_db.init_monitoring_db 内で一部自動適用されますが、運用時の DB 管理には注意が必要です。

---

## 参考コマンド例（ systemd での常駐起動案）

例: run_execution を常駐化する場合（systemd のユニットファイル内で）
- 環境変数は EnvironmentFile=/path/to/.env を使って設定
- ExecStart=/path/to/venv/bin/python -m kabusys.run_execution

（運用環境に合わせてログローテーションやプロセス優先度調整を行ってください）

---

必要であれば、README に以下を追加できます:
- 既知の API 仕様（ブローカークライアントのインターフェース）
- DB スキーマの詳細ドキュメント
- systemd / Docker / Kubernetes 用のデプロイ例
- テストの実行方法・ユニットテスト方針

どの情報を追加したいか教えてください。