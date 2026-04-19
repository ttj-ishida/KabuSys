# KabuSys

日本株向けの自動売買システムのコアライブラリ群です。本リポジトリは取引エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュース解析／レジーム判定）などの主要コンポーネントを含みます。

## 概要

- Python パッケージとして設計されたモジュール群（src/kabusys/**）。
- DuckDB を分析用 DB に、SQLite を監視・注文ログ等の永続化用に使用。
- 本番（live）とペーパートレーディング（paper_trading）を分離（ペーパートレードは専用 SQLite を使用）。
- OpenAI を用いたニュースセンチメント解析やマクロセンチメント評価の仕組みを備える（APIキー必須）。
- 監視コンポーネントはシステム状態、注文滞留、リスク（ドローダウン・ポジション上限）を監視し、Kill Switch により実行エンジン停止を行える。

## 主な機能一覧

- 実行エンジン起動スクリプト（run_execution）
  - KABUSYS_ENV に応じて実ブローカまたは MockBroker を利用
  - paper_trading 時は専用 DB に記録して本番 DB と完全分離
  - プロセス優先度設定 / PID 管理 / stop flag による停止

- 監視ループ起動スクリプト（run_monitoring）
  - システム（CPU/メモリ/ディスク・データ鮮度・プロセス生存）監視
  - 注文・約定・リスク監視（滞留注文・約定異常・ドローダウン等）
  - kill.flag 書き込みによる ExecutionEngine 停止
  - MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）

- 設定管理 / ウィザード / 検証
  - config_setup: 対話式で .env の作成・更新を支援
  - validate_config: .env と config/*.yaml の事前検証（--strict で警告も FAIL）

- ポートフォリオ構築
  - 候補選定、等金額／スコア重み、リスクベースのポジションサイズ計算
  - セクターキャップ、レジーム乗数（市場レジームに応じた資金調整）

- リサーチ
  - ファクター計算（モメンタム／ボラティリティ／バリュー）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー

- AI（OpenAI）機能
  - news_nlp: ニュースを集約して LLM に投げ、銘柄別センチメントを ai_scores に書き込み
  - regime_detector: ma200 とマクロセンチメントを合成して market_regime を判定

- ツール
  - tools/paper_verification_report.py: ペーパートレードの検証レポート生成（稼働率・成功率・レイテンシ等）

- ユーティリティ
  - ロギングの統一設定（logs/<app>.log、日次ローテーション）
  - プロセス優先度・CPU affinity の簡易設定

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境の作成（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - 以下はコード内で使用されている主要ライブラリの例です。実際はプロジェクトの requirements.txt に従ってください。
     - duckdb
     - psutil
     - openai (OpenAI SDK)
     - PyYAML（config YAML 検証時に必要）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants トークン、kabu API パスワード、DB パス、KABUSYS_ENV などを対話式で作成します。
   - 生成された .env をプロジェクトルートに置きます（.env は絶対に VCS にコミットしないでください）。

4. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります。

5. 初回の DB 準備／ディレクトリ
   - data/ ディレクトリや指定した DB の親ディレクトリは自動作成されますが、必要に応じて手動作成してください。
   - デフォルト DB パス:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db

6. （OpenAI を使う機能を試す場合）
   - OPENAI_API_KEY を環境変数または .env に設定してください。

---

## 使い方（起動・実行例）

- 監視ループを起動
  - 簡単に実行: python -m kabusys.run_monitoring
  - ポーリング間隔の変更（秒単位）:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を参照します（KABUSYS_ENV に依らず）。

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）に記録されます。
  - 起動時に data/stop_requested.flag が存在すると起動を行わず終了します。
  - 実行エンジンの PID は data/execution.pid に書かれます。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 機能（スコア算出・レジーム判定）
  - news_nlp.score_news や regime_detector.score_regime をコード経由で呼び出します（OpenAI API Key が必要）。

- 強制停止 / Kill Switch
  - KillSwitch は条件を満たしたときに data/kill.flag を書き込み、ExecutionEngine 側が検出して安全にシャットダウンします。
  - kill.flag の自動クリア設定は KILL_FLAG_CLEAR_ON_START（.env）で制御できます（本番では 0 推奨）。

---

## 主要な環境変数（抜粋とデフォルト）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 動作環境
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）

- DB / ファイルパス
  - DUCKDB_PATH — data/kabusys.duckdb
  - SQLITE_PATH — data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — data/paper_trading.db
  - PID_FILE_PATH — data/execution.pid
  - KILL_FLAG_PATH — data/kill.flag

- ログ
  - LOG_LEVEL — INFO（DEBUG/INFO/...）
  - LOG_DIR — デフォルト logs/

- 監視
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）

- Paper Trading 動作
  - PAPER_FILL_MODE — instant / partial / never / reject（デフォルト: instant）

- OpenAI
  - OPENAI_API_KEY — LLM 機能（news_nlp/regime_detector）で必要

---

## ログとPID・フラグファイル

- ログ
  - デフォルトは logs/ ディレクトリに出力され、アプリ名ごとに日次ローテーション（例: logs/execution.log, logs/monitoring.log）
  - ログ設定は kabusys.utils.logging_setup.setup_logging で統一管理

- PID/フラグ
  - data/execution.pid — ExecutionEngine の PID（設定により変更可能）
  - data/stop_requested.flag — run_* スクリプトが検知するとループを抜ける（デプロイ停止用）
  - data/kill.flag — KillSwitch が作成すると ExecutionEngine 側がシャットダウン

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env の自動ロード・Settings 定義
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
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
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (参照あり)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照あり)
  - execution/  (注文関連モジュール群: broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager)
  - utils/
    - logging_setup.py
    - process_priority.py

注: 一部ファイル（たとえば execution 以下や data.pipeline 等）はここにリストしたもの以外にも存在し、実動作に必要な実装を含みます。

---

## 開発メモ / 注意事項

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で使用）。
- 本番環境（KABUSYS_ENV=live）では kill.flag 自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。デフォルトは 0。
- Paper trading は本番 DB と完全分離するよう設計されています。ペーパートレード実行前に PAPER_TRADING_SQLITE_PATH を確認してください。
- OpenAI 呼び出しはネットワークエラー・レートリミット等に対してリトライロジックが実装されていますが、APIキーと利用制限には注意してください。
- DuckDB / SQLite のスキーママイグレーションは一部で簡易処理（ALTER TABLE 追加）を行っています。破壊的変更は避ける設計を心がけていますが、バックアップを推奨します。

---

必要があれば以下の内容も追加します（依頼してください）：
- 具体的な .env のサンプル（安全なデフォルトと例示）
- 各 CLI / モジュールの API 使用例（コードスニペット）
- 開発用 Dockerfile / docker-compose の雛形

ご希望の追加情報があれば教えてください。