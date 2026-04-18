# KabuSys — 日本株自動売買システム

このリポジトリは、日本株向けの自動売買／リサーチ／監視ツール群を集めたプロジェクトです。  
純粋関数型のポートフォリオ構築、Research 向けのファクター計算、Execution（発注）・Monitoring（監視）・AI ベースのニュース解析などを含みます。

---

## プロジェクト概要

- 名前: KabuSys
- バージョン: 0.1.0（`src/kabusys/__init__.py`）
- 目的: 日本株の自動売買パイプラインを構築・運用するためのモジュール群
- 主な技術:
  - SQLite / DuckDB（データ永続化・分析）
  - psutil（プロセス／リソース監視）
  - OpenAI（ニュース NLP / レジーム判定）
  - Python 標準ライブラリ中心（外部依存は最小限）

---

## 機能一覧

- Execution（発注）関連
  - ExecutionEngine 起動スクリプト（`run_execution.py`）
  - BrokerClientFactory を用いて本番・ペーパートレードを切り替え可能
  - OrderRepository / OrderManager / Reconciler / RiskManager 等のコンポーネント

- Monitoring（監視）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス状態 / データ鮮度の監視
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新・リスクログ書き込み
  - KillSwitch: 条件に応じた停止フラグ（`data/kill.flag`）書き込み
  - MonitoringEngine: 各モニタを組み合わせて定期実行

- Portfolio（銘柄選定・配分）
  - 候補選定、等配分／スコア加重の重み計算
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、リスク制限、aggregate cap）

- Research（ファクター・解析）
  - Momentum / Volatility / Value ファクター計算（DuckDB ベース）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー

- AI（ニュース NLP / レジーム判定）
  - news_nlp: raw_news を集約して LLM（gpt-4o-mini）でセンチメントを算出・ai_scores へ保存
  - regime_detector: ETF（1321）MA とマクロニュースの LLM センチメントを合成して市場レジーム判定

- ツール
  - 環境設定ウィザード（`config_setup.py`）: 対話式で `.env` を作成
  - 設定検証 CLI（`validate_config.py`）: .env / config/*.yaml の事前チェック
  - Paper Trading 検証レポート生成（`tools/paper_verification_report.py`）

---

## セットアップ手順

1. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

2. 依存ライブラリをインストール
   - pip install duckdb psutil openai
   - 追加（オプション）: PyYAML（`pip install pyyaml`） — `validate_config` が YAML パースチェックを行う場合に必要

3. .env の初期作成（対話式推奨）
   - python -m kabusys.config_setup
   - 対話ウィザードに従って必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を入力してください。

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 本番前は `--strict` を付けて警告も失敗扱いにすることを検討してください。

5. データディレクトリ作成
   - デフォルトの DB 等は `data/` 配下に作られます。自動作成される場合もありますが、適切なパーミッションの確認を推奨します。

注意: OpenAI を用いる機能（news_nlp / regime_detector）は環境変数 `OPENAI_API_KEY` を設定しておく必要があります。

---

## 重要な環境変数（主なもの）

デフォルト値は `src/kabusys/config.py` ならびに `config_setup.py` 内の定義を参照しています。主要なものを抜粋します:

- JQUANTS_REFRESH_TOKEN (必須)
  - 説明: J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD (必須)
  - 説明: kabuステーション API パスワード
- KABU_API_BASE_URL
  - デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH
  - デフォルト: data/kabusys.duckdb
- SQLITE_PATH
  - デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH
  - デフォルト: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）
- KABUSYS_ENV
  - 値: development | paper_trading | live
  - デフォルト: development
- LOG_LEVEL
  - デフォルト: INFO
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
  - 任意。アラート通知に使用
- OPENAI_API_KEY
  - AI 機能使用時に必須（news_nlp / regime_detector）
- PAPER_FILL_MODE
  - デフォルト: instant
  - 有効値: instant | partial | never | reject
- KILL_FLAG_CLEAR_ON_START
  - 0 または 1（本番では 0 推奨）
- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔（秒）。デフォルト 60 秒

参考: `python -m kabusys.config_setup` を実行すると対話式で .env を生成できます。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env を生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 本番前: python -m kabusys.validate_config --strict

- ExecutionEngine（実行／ペーパートレード対応）
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、`data/paper_trading.db` に記録されます（本番 DB と分離）。
    - 起動時に `data/stop_requested.flag` が存在する場合は起動しません。
    - 実行中に停止したい場合は `data/stop_requested.flag` を作成してください（Monitoring 側と同様の停止フラグ）。

- Monitoring（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60）。
  - 監視プロセスは Settings に従い、本番の sqlite_path を使用して監視ログを残します（環境にかかわらず同じ sqlite を参照）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能（プログラムから利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーを引数で渡すか、環境変数 OPENAI_API_KEY を使います。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 停止・キルスイッチ

- stop フラグ
  - `data/stop_requested.flag` を作成すると、`run_monitoring.py` と `run_execution.py` のループが検知して終了します（監視・実行スクリプトの安全シャットダウン用）。

- kill フラグ（Kill Switch）
  - `KillSwitch` コンポーネントにより条件（ドローダウン超過など）で `data/kill.flag` が書き込まれます。ExecutionEngine はこれを検知して停止する設計です。
  - `Settings.kill_flag_clear_on_start` を 1 にすると起動時に自動クリアされますが、本番では 0 を推奨します。

---

## ディレクトリ構成（抜粋）

リポジトリの主要なファイル・ディレクトリと目的:

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / 設定管理（.env 自動ロード含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py — ニュース NLP（OpenAI を利用したセンチメントスコア生成）
    - regime_detector.py — 市場レジーム判定

  - monitoring/
    - monitoring_db.py — SQLite ベースの監視 DB レイヤー
    - system_monitor.py — システム監視（CPU/メモリ/データ鮮度）
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション数監視
    - kill_switch.py — kill.flag 書き込み / 解除
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — （アラート送信管理; 実装はファイル参照）

  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - position_sizing.py — 発注株数計算

  - research/
    - factor_research.py — Momentum / Volatility / Value 等の計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート

  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- config/
  - system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
  - （`validate_config.py` はこれらの存在・パースを確認します。欠けている場合は警告。）

- data/
  - デフォルトの DB / PID / フラグファイルを格納（例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag）

---

## 実行上の注意点 / ベストプラクティス

- 本番（KABUSYS_ENV=live）の場合は必須環境変数を必ず設定し、`validate_config.py --strict` を推奨します。
- `.env` は機密情報を含むため、絶対に Git にコミットしないでください（`config_setup.py` のヘッダにも注意書きあり）。
- OpenAI を用いる処理はネットワーク遅延・API エラーを考慮してリトライ設計されていますが、API キーとコスト管理に注意してください。
- `run_execution` 実行時は `data/stop_requested.flag` の存在に注意（既に立っていると起動しない）。
- `monitoring` は監視ログやリスクイベントを SQLite に書き込みます。監視 DB のバックアップや容量管理を行ってください。
- process priority は起動時に `high` に設定されます（OS によっては権限不足で失敗することがあります）。

---

## 参考コマンド一覧

- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate

- 依存インストール
  - pip install duckdb psutil openai

- .env 作成（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 起動
  - python -m kabusys.run_execution

- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードベースの主要なコンポーネントと運用手順をまとめたものです。詳細な設計（PortfolioConstruction.md、StrategyModel.md 等）や追加の実行・テスト手順はリポジトリ内のドキュメントを参照してください。必要であれば、導入手順や運用フローをさらに細かくまとめたドキュメントを作成します。