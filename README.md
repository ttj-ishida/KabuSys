# KabuSys

日本株向け自動売買システムのコードベース README（日本語）

このリポジトリは、シグナル生成 → ポートフォリオ構築 → 発注実行までを含む自動売買システム（リサーチ／ペーパートレード／本番運用を想定）です。主要コンポーネントにモニタリング、リスク管理、発注エンジン、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント／レジーム判定）があります。

---

## プロジェクト概要

- 名前: KabuSys
- 目的: 日本株の自動売買を行うための一連のモジュール群
  - 発注エンジン（ExecutionEngine）
  - 監視・アラート（MonitoringEngine、Kill Switch）
  - リスク管理（RiskManager / RiskMonitor）
  - ポートフォリオ構築（候補選定・重み付け・株数決定）
  - リサーチ（ファクター計算 / 特徴量解析）
  - AI モジュール（ニュースセンチメント、レジーム判定：OpenAI利用）
  - ペーパートレード用ツール（レポート生成等）
- 実装言語: Python 3.10+
- 永続化:
  - DuckDB: 分析用（デフォルト `data/kabusys.duckdb`）
  - SQLite: 監視用 / 発注履歴（デフォルト `data/monitoring.db`、ペーパートレードは `data/paper_trading.db`）

---

## 主な機能一覧

- 起動 / 実行
  - run_execution.py: ExecutionEngine 起動（KABUSYS_ENV により paper_trading / live を切替）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
- 設定管理
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env および config/*.yaml の事前検証 CLI
  - Settings クラスにより環境変数を集中管理
- モニタリング
  - system_monitor: CPU/メモリ/ディスク / データ鮮度 / 実行プロセス監視
  - trade_monitor: 注文ログ監視（滞留注文、約定異常など）
  - risk_monitor: ドローダウン・ポジション上限チェックとリスクログ記録
  - monitoring_engine: 各モニターを束ねてポーリング、アラート送出、Kill Switch 評価
  - monitoring_db: SQLite スキーマの初期化・読み書きユーティリティ（冪等）
- 発注系
  - execution パッケージ（BrokerFactory、OrderManager、ExecutionEngine、Reconciler、RiskManager 等）
  - ペーパートレード時は MockBrokerClient を使用し、本番 DB と分離
- ポートフォリオ構築
  - 候補選定、等配分／スコア加重、セクターキャップ、レジーム乗数、ポジションサイズ計算（単元株丸め・aggregate cap）
- リサーチ
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリ
- AI（OpenAI）
  - news_nlp: ニュース記事を LLM（gpt-4o-mini 等）でセンチメント評価し ai_scores に書込
  - regime_detector: ETF MA とマクロ記事の LLM スコアを合成して市場レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポート生成
- ユーティリティ
  - logging_setup: stdout + 日次ローテートファイルロギング設定
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順（ローカル開発向け）

前提:
- Python 3.10 以上
- git が使える環境

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（requirements.txt が無い場合の例）
   - pip install duckdb psutil openai PyYAML
   - （実行環境によっては追加パッケージが必要です）
4. 初期設定ファイル作成
   - python -m kabusys.config_setup
     - 対話式に .env を生成します（.env は Git にコミットしないこと）
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 問題がある場合は .env / config/*.yaml を修正
6. ディレクトリ作成（必要な場合）
   - data/ と logs/ は自動作成されますが、権限等で失敗する場合は手動で作成してください。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能利用時に必要)
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- LOG_DIR: ログ出力先（デフォルト logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 本番で Kill Flag を自動クリアするか（0/1、本番では 0 推奨）

注意:
- run_monitoring（監視）は KABUSYS_ENV にかかわらず本番の `SQLITE_PATH` を使用します。
- run_execution は KABUSYS_ENV=paper_trading の場合、`PAPER_TRADING_SQLITE_PATH` を使用して本番 DB と隔離します。

---

## 使い方（代表的コマンド）

1. 設定ウィザード（.env 生成）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit(1)）

3. ExecutionEngine を起動（本番 / ペーパー共通）
   - 環境変数を設定（例）
     - export KABUSYS_ENV=paper_trading
     - export OPENAI_API_KEY=...
   - 起動:
     - python -m kabusys.run_execution
   - 動作:
     - paper_trading の場合は MockBrokerClient が使用され、記録先は `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）
     - 実行中は `data/execution.pid`（PID ファイル）や `data/stop_requested.flag` による停止シグナリングを参照

4. Monitoring を起動
   - 環境変数で間隔変更:
     - export MONITOR_POLL_INTERVAL=30
   - 起動:
     - python -m kabusys.run_monitoring
   - 備考:
     - 監視は常に本番の SQLite (`SQLITE_PATH`) を使用する点に注意

5. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db で DB パスを明示可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

6. AI モジュールを手動で実行（例）
   - kabusys.ai.score_news(conn, target_date, api_key=...)
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
   - これらは DuckDB 接続を受け取り、テーブル（raw_news / prices_daily 等）を参照します

---

## 停止・Kill Switch

- Kill Switch は `data/kill.flag` を作成することで ExecutionEngine を停止させる仕組みです（kill_switch.py）。
- 実行停止の外部フラグ: `data/stop_requested.flag` が存在すると run_execution/run_monitoring は停止します。
- 本番で KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag が自動クリアされますが、本番環境では推奨されません。

---

## ロギング

- 共通のロギング設定 utility: kabusys.utils.logging_setup.setup_logging(app_name="execution" 等)
- デフォルトで stdout と日次ローテートのファイル出力（logs/<app_name>.log）を行います。
- ログレベルは引数・環境変数 LOG_LEVEL で制御可能。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — Settings / .env 自動読み込みロジック
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - execution/                — 発注関連（broker, engine, order_manager 等）
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ & DB 操作
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
  - data/ (実行時に使用する SQLite / PID / flag など)
  - config/ (yaml テンプレート等)

---

## 注意事項 / 実運用上のガイド

- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup にもその旨の注意書きがあります）。
- KABUSYS_ENV=live は本番です。validate_config は本番向けのガード（LINE 通知設定・Kill Switch 設定等）を警告します。
- OpenAI を利用する機能は API コストとレイテンシを伴います。API キーと利用ポリシーに注意してください。
- run_monitoring は監視用 DB を直接変更します。モジュール init_monitoring_db は後方互換性のための簡易マイグレーションを実行しますが、運用前にバックアップを取ってください。
- process_priority / cpu_affinity 設定は環境により権限が必要になる場合があります（Linux の nice 値、Windows の PRIORITY_CLASS 等）。

---

## 参考コマンド一覧（まとめ）

- .env 生成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行開始 (Execution): python -m kabusys.run_execution
- 監視開始 (Monitoring): python -m kabusys.run_monitoring
- ペーパーレポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

README の内容はコードのコメント・ドキュメントに基づいて作成しています。追加で詳しい設計ドキュメント（API 仕様、DB スキーマの詳細、運用手順、systemd ユニット例 等）が必要であればお知らせください。