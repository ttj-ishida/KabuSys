# KabuSys

日本株自動売買システムの軽量フレームワーク（部分実装）。  
本リポジトリには設定管理、監視モジュール、ポートフォリオ構築、研究用ファクター計算、AI を用いたニュース解析、ペーパートレード検証ツールなどの主要コンポーネントが含まれます。

## プロジェクト概要
- DuckDB（分析用）と SQLite（監視・注文ログ用）を併用する構成
- 実運用 / ペーパートレード / 開発の実行モードを環境変数で切替可能（KABUSYS_ENV）
- ExecutionEngine（発注エンジン）と Monitoring（監視）を分離した起動スクリプトを提供
- ニュースセンチメントやレジーム判定に OpenAI（gpt-4o-mini）を利用するモジュールを含む（APIキー必要）
- 設定ウィザード・設定検証用 CLI、ペーパートレード検証レポート生成ツールあり

## 主な機能一覧
- 環境設定管理
  - .env の自動読み込み（プロジェクトルート検出）と対話式ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行 / 監視用スクリプト
  - run_execution.py: ExecutionEngine 起動（KABUSYS_ENV=paper_trading のときは MockBroker を使用し paper DB に記録）
  - run_monitoring.py: SystemMonitor を定期ポーリングして監視ログを記録
- 監視サブシステム
  - system_monitor: CPU/メモリ/Disk やデータ鮮度、Execution プロセスの存在確認
  - trade_monitor: 注文の滞留・約定異常等の検出（モジュールあり）
  - risk_monitor: ドローダウン・ポジション上限の監視と Kill Switch（kill.flag）生成
  - monitoring_db: 監視用 SQLite テーブルの初期化・読み書き
  - monitoring_engine: 各 Monitor を束ねたポーリング実行ロジック
- ポートフォリオ構築ユーティリティ（純粋関数）
  - 候補選定、重み計算（等重/スコア重み）、セクター上限適用、レジーム乗数、ポジションサイズ計算
- 研究用モジュール
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB 経由）
  - feature_exploration: 将来リターン計算、IC 計算、ファクター統計
- AI モジュール
  - news_nlp: ニュースを LLM に投げて銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector: ETF とマクロニュースを組み合わせて市場レジーム判定（market_regime テーブルへ書き込み）
- ツール
  - tools.paper_verification_report: ペーパートレード DB を集計して検証レポートを出力

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローンして作業ディレクトリへ移動
   - プロジェクトルートに `.git` または `pyproject.toml` があると自動で .env を検出します。

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必須（主にコード中で参照されるもの）:
     - duckdb, psutil, openai
   - optional:
     - PyYAML（config 検証で YAML を検査する場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

   ※ requirements ファイルがない場合は上記を個別インストールしてください。

4. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または .env.example を参考にプロジェクトルートに `.env` を作成
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL, LOG_DIR 等

5. 設定検証
   - python -m kabusys.validate_config
   - 問題がある場合は出力される ERROR/WARNING を確認して .env を修正

## 使い方（よく使うコマンド）
- 環境ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）起動
  - 実運用（注意して使用）:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパートレード:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading では MockBrokerClient を使用し、データは paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）へ記録されます
  - 実行起動時は data/execution.pid（デフォルト）へ PID が書き込まれ、data/stop_requested.flag により停止できます

- 監視（Monitoring）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔の上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は本番用の sqlite_path を環境にかかわらず使用します（監視ログは共通）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ニューススコア・レジーム判定）
  - AI 機能を使うには OPENAI_API_KEY を設定
  - モジュール関数として呼び出し:
    - kabusys.ai.score_news(conn, target_date, api_key=...)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

## 重要な挙動・既定値
- KABUSYS_ENV:
  - development / paper_trading / live のいずれか
  - paper_trading は発注と DB を本番から分離するためのモード
- DB パス（デフォルト）
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
- ログ
  - デフォルトは logs/ 以下にアプリ名別（execution.log, monitoring.log 等）で出力（TimedRotatingFileHandler 日次）
  - 環境変数 LOG_DIR, LOG_LEVEL で上書き可能
- プロセス優先度
  - 起動スクリプトは最初に set_process_priority("high") を試みます（psutil に依存）
- Kill / Stop フラグ
  - data/kill.flag: KillSwitch が書き込むフラグ（ExecutionEngine に停止を指示）
  - data/stop_requested.flag: run_* スクリプト内で監視・終了判定に用いられるファイル
- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動ロード
  - 自動ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

## ディレクトリ構成
（主要なファイル／モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数・設定管理（自動 .env 読込）
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py           — ニュースセンチメント取得（OpenAI）
    - regime_detector.py    — 市場レジーム判定（LLM + MA200）
  - monitoring/
    - monitoring_db.py      — SQLite テーブル作成・CRUD ユーティリティ
    - system_monitor.py     — CPU/メモリ/データ鮮度監視
    - trade_monitor.py      — 注文監視（滞留／約定異常）※モジュールあり
    - risk_monitor.py       — ドローダウン／ポジション上限監視
    - kill_switch.py        — kill.flag 書込みロジック
    - monitoring_engine.py  — モニタを束ねるポーリングエンジン
    - alert_manager.py      —（アラート送信ラッパー、実装による）

  - portfolio/
    - portfolio_builder.py  — 候補選定・重み計算
    - position_sizing.py    — 株数決定・リスク制限
    - risk_adjustment.py    — セクターキャップ・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py    — Momentum/Value/Volatility 等ファクター計算（DuckDB）
    - feature_exploration.py— 将来リターン・IC・統計
    - __init__.py

  - monitoring/ (上記)
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
    - __init__.py

  - utils/
    - logging_setup.py      — ログ初期化ユーティリティ
    - process_priority.py   — プロセス優先度・CPU affinity 設定
    - __init__.py

注: data/、logs/ 等は実行環境で生成されます。

## 開発者向けメモ・注意点
- DuckDB コネクションを研究モジュールへ注入して SQL と Python を組み合わせた計算を行います。DuckDB のテーブルスキーマ（prices_daily, raw_financials, raw_news など）は期待どおりに用意する必要があります。
- AI を利用する部分は OpenAI SDK の仕様変更に影響されるため、API 呼び出しラッパーをテスト時にモックする設計になっています（_call_openai_api を patch など）。
- run_execution/run_monitoring は PID / flag ファイルによる簡易制御を行います。運用環境では systemd / supervisor 等でプロセス監視を推奨します。
- paper_trading モードは本番 DB と完全分離するよう設計されていますが、本番切替時は .env の設定と KILL_FLAG の状態を必ず確認してください。

---

問題点の報告や改善提案は issue を作成してください。README の記載や CLI の振る舞いを簡単にカスタマイズできます（例: デフォルトパスや閾値は config/*.yaml や環境変数で拡張することを想定しています）。