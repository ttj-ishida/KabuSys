# KabuSys — 日本株自動売買システム

このリポジトリは、日本株向けの自動売買・リサーチ・監視ツール群です。戦略のポートフォリオ構築、発注エンジン、監視・アラート、AIを用いたニュース解析、研究用ファクター計算などを含みます。

> 注意: .env は秘密情報を含むため絶対にリポジトリにコミットしないでください。

---

## プロジェクト概要

KabuSys は以下を目的とするモジュール群で構成されています。

- ExecutionEngine: ブローカーと連携して発注・注文管理を行う実行コンポーネント（paper/live 切替対応）。
- Monitoring: システム稼働状況、注文状況、リスク（ドローダウン・ポジション上限等）を定期的にチェックし、必要に応じて Kill Switch を発動。
- Portfolio: 候補選定・重み付け・ポジションサイズ計算・セクター制限などの純粋関数群。
- Research: DuckDB 上の価格・財務データからファクター（モメンタム、ボラティリティ、バリュー等）を計算。
- AI: OpenAI（gpt-4o-mini 等）を使ったニュースのセンチメント解析・市場レジーム判定（APIキー必須）。
- Tools: ペーパートレード検証レポート生成スクリプトなど。

---

## 主な機能一覧

- 実行環境の切替（development / paper_trading / live）
  - paper_trading 時は MockBroker を使用し、本番 DB と完全分離（デフォルト: `data/paper_trading.db`）。
- 監視機能
  - CPU/メモリ/ディスク、Execution プロセス存在確認、データ鮮度チェック
  - 滞留注文・約定異常・ドローダウン・ポジション上限の検出とログ記録
  - Kill Switch（`data/kill.flag`）による ExecutionEngine の停止シグナル
- ログ管理
  - コンソール（stdout）と日次ローテートファイル（`logs/<app>.log`）に出力
- ポートフォリオ構築
  - 候補選定、等比重・スコア比重配分、リスクベースの株数計算、セクター制限、レジーム乗数
- 研究ユーティリティ
  - DuckDB を介したファクター計算、forward returns、IC 計算、統計サマリ
- AI によるニュース解析
  - ニュースを銘柄毎に集約して LLM に送信、センチメントを ai_scores テーブルに保存
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの組合せ）
- ユーティリティ
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools/paper_verification_report）

---

## セットアップ手順

1. Python 環境を作成（推奨: venv）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 主要依存（抜粋）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML (config 検証で YAML をチェックする場合)
   - 例:
     - pip install duckdb psutil openai pyyaml

   ※ 実際の requirements.txt がある場合は `pip install -r requirements.txt` を使用してください。

3. .env の作成
   - 対話ウィザードで作成:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY を設定してください（score_news / score_regime）。

4. 設定検証（起動前の推奨チェック）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする（厳密チェック）:
     - python -m kabusys.validate_config --strict

5. データディレクトリ
   - デフォルトの DB / ファイルパス（.env で上書き可能）:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_DIR: logs/
     - PID / flag: data/execution.pid, data/kill.flag, data/stop_requested.flag
   - これらの親ディレクトリは起動時に自動作成されることが多いですが、権限等に注意してください。

---

## 使い方（主要スクリプト）

- 実行エンジン（Execution）
  - 通常起動:
    - python -m kabusys.run_execution
  - paper_trading モードで起動する場合:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - このとき paper_trading 用の DB を使用し、本番 DB と分離されます。

- 監視サービス（Monitoring）
  - 起動:
    - python -m kabusys.run_monitoring
  - ポーリング間隔の上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - デフォルト 60 秒。1 秒以上の整数を指定してください。

- .env 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（プログラム的に利用）
  - ニュースセンチメント付与:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key 指定が可能
  - 市場レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

- Kill Switch / 停止フラグ
  - 監視側が条件を満たすと `data/kill.flag` を書き込むことで ExecutionEngine に停止シグナルを送ります。
  - 手動で停止させたい場合は `data/stop_requested.flag` を作成すると実行ループが終了します。

---

## 環境変数（主要）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境:
  - KABUSYS_ENV (development / paper_trading / live) — デフォルト: development

- DB / ログ:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - LOG_DIR (default: logs/)
  - LOG_LEVEL (default: INFO)

- AI:
  - OPENAI_API_KEY (AI 機能使用時に必要)

- 監視関連:
  - MONITOR_POLL_INTERVAL (秒、default: 60)
  - PID_FILE_PATH / KILL_FLAG_PATH 等（.env でカスタマイズ可能）
  - KILL_FLAG_CLEAR_ON_START (0/1) — 起動時に kill.flag を自動クリアするか（本番では 0 推奨）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                  — 環境変数/.env の読み込みと Settings
- config_setup.py            — .env 対話ウィザード
- validate_config.py         — 設定検証 CLI
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — Monitoring ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py              — ニュースセンチメント付与（OpenAI 呼び出し）
  - regime_detector.py       — 市場レジーム判定（AI + MA200）
- monitoring/
  - monitoring_db.py         — SQLite テーブル定義・永続化
  - system_monitor.py        — システム状態・データ鮮度チェック
  - trade_monitor.py         — 注文関連の監視（注: ファイルに実装あり）
  - risk_monitor.py          — ドローダウン・ポジション上限監視
  - kill_switch.py           — kill.flag 管理
  - monitoring_engine.py     — 各 Monitor を束ねる
  - alert_manager.py         — アラート送信（LINE 等、実装に依存）
- execution/
  - execution_engine.py      — 実行エンジン本体（発注ループ）
  - broker_factory.py        — ブローカークライアント生成（Mock / Live 切替）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py       — momentum/volatility/value 等の計算
  - feature_exploration.py   — forward returns / IC / summary
- utils/
  - logging_setup.py         — ロギング初期化ユーティリティ
  - process_priority.py      — プロセス優先度 / CPU affinity 設定
- monitoring/monitoring_db.py (監視用の DB 層)
- tools/
  - paper_verification_report.py  — Paper Trading の検証レポート生成

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）では kill.flag や KILL_FLAG_CLEAR_ON_START の設定に特に注意してください。validate_config は本番設定の危険点を警告します。
- ログディレクトリ・DB の親ディレクトリ作成に失敗した場合、ファイル出力が無効になりコンソール出力のみになることがあります（権限等を確認してください）。
- OpenAI 等の外部 API を使う処理はエラー時にフェイルセーフ（スコア 0 やスキップ）で継続する設計ですが、APIキーの管理と利用制限には留意してください。
- .env に秘密情報を保存する際は、アクセス制御と Git 応答設定（.gitignore）を厳密に行ってください。

---

## 貢献・拡張のヒント

- broker client 実装を追加して複数ブローカーをサポート可能
- ポートフォリオ構築の重み付けアルゴリズムやリスクパラメータは外部設定化して試験・最適化可能
- monitoring のアラート送信先（LINE 以外）をプラグイン化して多様な通知チャネルに対応可能
- DuckDB のスキーマに合わせて research のクエリを拡張・最適化してください

---

必要があれば README にインストール用の requirements.txt 例、さらに詳しい起動手順や運用チェックリスト（systemd / Supervisor 設定例、ログローテート確認、バックアップ方針）などを追記します。どの情報を優先して追加しますか？