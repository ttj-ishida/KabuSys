# KabuSys

日本株自動売買システムのコンポーネント群（ライブラリ＋起動スクリプト群）。  
本リポジトリはトレード実行エンジン、監視エンジン、リサーチ／ポートフォリオ構築、AI（ニュースNLP／レジーム判定）などの主要機能をモジュール化して提供します。

---

## プロジェクト概要

KabuSys は日本株向けの自動取引／リサーチ基盤です。主な設計方針は以下の通りです。

- モジュール化：実行（Execution）、監視（Monitoring）、リサーチ（Research）、ポートフォリオ（Portfolio）、AI（ニュース分析／レジーム判定）などを分離。
- 環境分離：`KABUSYS_ENV` により `development` / `paper_trading` / `live` を切替。ペーパートレードは本番 DB と分離して動作。
- フェイルセーフ：API 呼び出し失敗時はフォールバック（例: マクロセンチメント失敗時は中立扱い）し、部分失敗が他データを破壊しないよう設計。
- 設定は .env ファイルと環境変数で管理（自動読み込み機能あり）。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution: ExecutionEngine（発注エンジン）を起動。`KABUSYS_ENV=paper_trading` 時は MockBroker を使用し DB を分離。
  - run_monitoring: SystemMonitor のポーリングループを起動。監視結果を SQLite に記録。
- 設定管理
  - config_setup: 対話式ウィザードで `.env` を生成 / 更新。
  - validate_config: 起動前に環境変数 / 設定ファイルの妥当性チェックを行う CLI。
- 監視（Monitoring）
  - system_monitor: CPU / メモリ / ディスク / プロセスヘルス / データ鮮度を検査。
  - trade_monitor: 発注・約定ログの監視（滞留注文、約定異常などを検出）。
  - risk_monitor: ドローダウン・ポジション上限などを監視しリスクイベントを記録。
  - kill_switch: リスク条件に基づき `data/kill.flag` を書き込み ExecutionEngine を停止させる仕組み。
  - monitoring_engine: 各モニタを束ねポーリング・アラート発行。
  - monitoring_db: 監視用 SQLite のスキーマ作成 / 操作ユーティリティ。
- Execution 関連（発注）
  - BrokerFactory, ExecutionEngine, OrderManager, RiskManager, Reconciler 等（実装ファイルは別途）。
- ポートフォリオ構築
  - 銘柄選定、重み付け、リスク調整、ポジションサイズ計算（等重み／スコア重み／リスクベース等）。
- リサーチ（Research）
  - ファクター計算（モメンタム／バリュー／ボラティリティ等）
  - 特徴量探索、将来リターン計算、IC 計算、統計サマリ
- AI（OpenAI）
  - news_nlp: raw_news を LLM でスコアリングして ai_scores に書き込む。
  - regime_detector: ma200 とマクロセンチメントを合成して日次の市場レジームを判定。
- ユーティリティ
  - logging_setup: 統一的なログ設定（コンソール + 日次ローテーションファイル）。
  - process_priority: プロセス優先度／CPU affinity 設定ユーティリティ。
- ツール
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポートを生成。

---

## 動作前提 / 必要要件

- Python 3.10+
- SQLite（Python 標準ライブラリで利用）
- 外部ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証を行う場合）
- OS: Windows / Linux / macOS を想定。プロセス優先度や CPU affinity はプラットフォーム依存で一部機能制限あり。

インストール例（requirements.txt がある場合）:
pip install -r requirements.txt

必要最低限のインストール例:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. .env を作成
   - 対話式ウィザード（推奨）
     - python -m kabusys.config_setup
     - ウィザードは J-Quants / kabuAPI のトークンや DB パス、ログレベル等を入力して .env を生成します。
   - 手動で設定する場合は .env.example を参考に .env を作成（.env は絶対に Git にコミットしない）。

5. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば修正してください。--strict を付けると警告も失敗扱いになります。

6. データディレクトリ作成（必要に応じて）
   - デフォルト DB 等は `data/` を想定するため、必要に応じて作成されます（コードは起動時に自動作成を試みます）。

---

## 主要環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API リフレッシュトークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- KABUSYS_ENV: 実行環境（development | paper_trading | live） デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの fill 動作（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI を利用する場合に必要（news_nlp / regime_detector）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（開発時のみ 1 を推奨、 production は 0 推奨）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

注意:
- .env の自動ロード: デフォルトで .env と .env.local をプロジェクトルートから自動読み込みします。無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（主要コマンド）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し `data/paper_trading.db` に記録します。
    - 実行中に停止させるには `data/stop_requested.flag` または監視側が書き込む `data/kill.flag` を使用します。
    - プロセスの PID は `data/execution.pid` に保存されます。

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60）。
  - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI / レジームスコアリング（プログラム呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=...)  — news_nlp の呼び出し例
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...) — レジーム判定
  - これらを CLI から直接呼ぶユーティリティは用意されていないため、スクリプト/ジョブから呼び出してください。OpenAI API キーは OPENAI_API_KEY または引数で渡す必要があります。

---

## 停止／Kill シグナルの仕組み

- 手動停止（実行エンジン）
  - 起動プロセスは `data/stop_requested.flag` の存在を監視しており、存在すると安全に停止します。
- 自動 Kill Switch
  - 監視モジュールがドローダウン等の条件を満たすと `data/kill.flag` に理由を書き込みます。ExecutionEngine は起動時や定期チェックでこのフラグを検出して停止します。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定していると起動時に kill.flag を自動クリアします（生産環境では推奨されません）。

---

## ディレクトリ構成

（src 直下の kabusys パッケージを想定）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込みロジック（自動 .env ロード）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py        — ログ初期化ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py        — 監視用 SQLite スキーマ + DB 操作
    - monitoring_engine.py    — モニタを束ねるエンジン
    - system_monitor.py       — システム / データ鮮度監視
    - trade_monitor.py        — 発注 / 約定監視（ファイル中に参照あり）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — フラグ書き込みによる停止シグナル
    - alert_manager.py        — アラート（LINE 等）発行（実装参照）
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数決定・資金配分
    - risk_adjustment.py      — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py      — Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py             — ニュースを LLM でスコアリングし ai_scores へ書き込み
    - regime_detector.py      — ma200 + マクロセンチメント合成によるレジーム判定
  - execution/                — Execution 系のコンポーネント群（BrokerFactory 等）
  - data/                     — （実行時に使用されるデータ/DB/log 等の配置先）
  - logs/                     — ログファイル出力先（デフォルト）

---

## 運用上の注意 / ベストプラクティス

- .env は機密情報を含むため必ず .gitignore に追加し、リポジトリにコミットしないでください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にして、kill.flag の自動クリアを無効化してください。
- OpenAI や各 API のキーは権限と使用量に注意し、可能なら限定的なキー／監視を設定してください。
- モニタリング / ログを定期的に確認し、異常時は即時対応できる運用体制を整えてください。
- DuckDB / SQLite のバックアップ方針を運用に合わせて検討してください（分析 DB / 監視 DB は重要な履歴を含みます）。

---

何か特定のモジュール（たとえば ExecutionEngine の詳細、監視のアラート設定、AI スコアリングの挙動）について README に追記してほしい点があれば教えてください。必要に応じてコマンド例や図解も追加します。