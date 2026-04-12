# KabuSys — README

KabuSys は日本株の自動売買／研究／監視を支援する Python パッケージ群です。本リポジトリは、売買実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AI（ニュースセンチメント／レジーム判定）など複数のモジュールで構成されています。

この README ではプロジェクト概要、主な機能、セットアップ手順、利用方法、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

- 目的: 日本株の自動売買システム（ExecutionEngine）と、それを支える監視・検証・研究ツール群を提供する。
- 設計方針:
  - 実行ロジックとデータ永続化（SQLite / DuckDB）を分離。
  - Paper Trading（模擬口座）モードをサポートし、本番 DB と完全に分離して検証可能。
  - 外部 LLM（OpenAI）を利用したニュースセンチメント・レジーム判定機能を提供（API キー必要）。
  - 監視は独立したプロセス（monitoring）として動作し、監視 DB を通じて状態を記録／アラート送信する。

---

## 主な機能一覧

- Execution（実行系）
  - OrderManager / ExecutionEngine による発注・状態管理・リスク制御
  - Broker クライアントの抽象化（本番 / Mock / Paper Trading の切替）
  - 起動時のリコンシリエーション（Reconciler）による自動復旧

- Monitoring（監視系）
  - SystemMonitor: プロセス生存、CPU/メモリ/ディスク、データ鮮度を監視
  - TradeMonitor: 注文滞留・約定価格異常を検出
  - RiskMonitor: ドローダウン / ポジション上限を監視し、リスクログ記録
  - KillSwitch: 条件到達時にフラグファイルを書き、ExecutionEngine 停止をシグナル
  - AlertManager: LINE Messaging API による通知（クールダウン管理）
  - Streamlit ダッシュボード（監視データ閲覧用）

- Research / Portfolio（研究・ポートフォリオ）
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算 / IC（Information Coefficient）評価
  - 銘柄選定・等配分／スコア配分・リスク調整・ポジションサイズ計算

- AI（LLM 統合）
  - ニュースを LLM でセンチメント化して銘柄別スコアを DuckDB に保存
  - マクロニュース + ETF MA200 を使った市場レジーム判定（bull/neutral/bear）

- ユーティリティ
  - .env 自動読み込み（プロジェクトルートを探索）
  - プロセス優先度・CPU affinity 設定ユーティリティ（psutil ベース）
  - Paper Trading 検証レポート生成ツール

---

## セットアップ手順

前提: Python 3.9+ を想定（実際のサポートは pyproject.toml 等を参照してください）。

1. リポジトリをクローン / プロジェクトルートへ移動
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）
3. 依存パッケージをインストール（例）
   - pip install duckdb psutil openai requests streamlit
   - （必要なら開発用にその他のパッケージをインストール）
4. data ディレクトリを作成
   - mkdir -p data
5. 環境変数 / .env を準備
   - プロジェクトルートに `.env`（および任意で `.env.local`）を置くと自動で読み込まれます。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 重要な環境変数（一部）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合に必要）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信用）
     - SQLITE_PATH（監視 DB のパス。デフォルト: data/monitoring.db）
     - DUCKDB_PATH（DuckDB のパス。デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB。デフォルト: data/paper_trading.db）
     - PID_FILE_PATH（実行プロセス PID ファイル, デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（kill フラグ, デフォルト: data/kill.flag）
     - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject、デフォルト: instant）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
6. DB 初期化
   - 監視用 DB は起動時に init_monitoring_db() が呼ばれて自動作成／マイグレーションされます。事前準備は不要です。
   - DuckDB 側のテーブル（prices_daily / raw_financials など）は別途データ投入が必要です（研究・AI 機能を使う場合）。

注意:
- psutil ベースでプロセス優先度／CPU affinity を設定します。権限により設定が失敗する場合は警告を出してスキップされます。
- OpenAI を利用する機能は API キーが必須です。API 呼び出しはリトライ・フォールバック設計になっていますが、キー未設定時はエラーを返す関数もあります。

---

## 使い方

以下は代表的な起動・実行コマンド例です。パッケージはモジュールとして実行可能に設計されています（トップから python -m で呼ぶ想定）。

1. 監視ループを起動（Monitoring）
   - デフォルトのポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で秒数を上書き可能（1 秒以上）。
   - MONITOR_POLL_INTERVAL に不正な値を設定するとデフォルトにフォールバックします。
   - 実行:
     - python -m kabusys.run_monitoring
   - 備考:
     - run_monitoring は Monitoring 用の SQLite DB（Settings.sqlite_path）を常に使用します（KABUSYS_ENV に関係なく本番監視 DB を参照）。

2. 実行エンジンを起動（Execution）
   - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使い、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）へ書き込みます（本番 DB と完全分離）。
   - 実行:
     - python -m kabusys.run_execution
   - 起動時に Reconciler による照合、自動復旧処理が行われます。

3. Paper Trading 検証レポート（ツール）
   - SQLite の Paper Trading DB から検証レポートを生成します。
   - 実行例:
     - python -m kabusys.tools.paper_verification_report
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - オプション `--db PATH` で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

4. 監視ダッシュボード（Streamlit）
   - Streamlit を使った簡易ダッシュボードで monitoring DB を閲覧できます。
   - 実行:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

5. AI 機能（ニュースセンチメント / レジーム判定）
   - OpenAI API キー（OPENAI_API_KEY）が必要です。
   - コード上の関数を呼び出すことで動作します（例: kabusys.ai.score_news は DuckDB 接続と target_date を受け取り ai_scores に書き込む）。
   - LLM 呼び出しはリトライ／フォールバックロジックを備えていますが、API 利用量には注意してください。

6. 主要な設定と挙動
   - 環境自動読み込み:
     - プロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を読み込みます。
     - OS 環境変数は保護され、.env.local は既存環境変数を上書き可能（ただし OS 環境は保護）。
   - ログレベル:
     - LOG_LEVEL 環境変数で制御（DEBUG/INFO/...）。
   - kill.flag:
     - KillSwitch は監視結果に応じて `KILL_FLAG_PATH`（デフォルト data/kill.flag）へ理由を記したファイルを書きます。ExecutionEngine 側でこれを検知して安全に停止できます。

---

## 代表的な環境変数（まとめ）

- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants 用トークン）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- OPENAI_API_KEY — OpenAI 利用時に必要
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知
- SQLITE_PATH — data/monitoring.db（監視 DB、デフォルト）
- PAPER_TRADING_SQLITE_PATH — data/paper_trading.db（paper_trading モード時）
- DUCKDB_PATH — data/kabusys.duckdb（DuckDB ファイル、デフォルト）
- PID_FILE_PATH — data/execution.pid（ExecutionEngine PID）
- KILL_FLAG_PATH — data/kill.flag（KillSwitch 用フラグ）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — instant | partial | never | reject（paper_trading の約定挙動）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると自動 .env ロードを無効化

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル／モジュールと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数／Settings 管理（.env 自動読み込み含む）
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite ベースの監視ログ永続化（テーブル作成／CRUD）
  - system_monitor.py — CPU/メモリ/ディスク / データ鮮度 / PID チェック
  - trade_monitor.py — 注文の滞留・約定異常検出
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — Kill フラグの書き込み / 管理
  - monitoring_engine.py — 各 monitor を束ねるループ（テスト用 run_once あり）
  - alert_manager.py — LINE への通知ラッパ
  - streamlit_dashboard.py — Streamlit による監視ダッシュボード

- src/kabusys/execution/
  - order_manager.py — 発注フローと状態遷移（OrderRecord を操作）
  - reconciler.py — 起動時や再開時の注文／ポジション照合（自動復旧）
  - その他: broker_factory, execution_engine, order_repository 等（発注関連）

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定、スコア順ソート
  - position_sizing.py — 発注株数計算（リスクベース／等配分等）
  - risk_adjustment.py — セクター上限、レジーム乗数

- src/kabusys/research/
  - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB を参照）
  - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー

- src/kabusys/ai/
  - news_nlp.py — ニュースを LLM に投げて銘柄別センチメントを算出・保存
  - regime_detector.py — ETF MA200 とマクロセンチメントを合成して市場レジーム判定

- src/kabusys/utils/
  - process_priority.py — プロセス優先度・CPU アフィニティ設定ユーティリティ

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成

---

## 注意事項・運用上のヒント

- Paper Trading と本番 DB は分離して運用すること（設定で paper_trading モードを利用）。
- OpenAI（LLM）を使う際は API キーの管理と利用量に注意してください。失敗時はフォールバック処理が働く実装ですが、コスト管理は重要です。
- process priority / cpu affinity の設定は OS 権限に依存します。権限不足時は警告が出てスキップされます。
- monitoring のポーリング間隔や kill flag の挙動は環境変数で柔軟に調整可能です。
- DB（DuckDB）の prices_daily / raw_financials / raw_news などのテーブルは研究／AI 機能が正しく動作するために事前にデータを用意してください。

---

もし README に追加してほしい項目（例: より詳しいセットアップ手順、Docker 化、CI 設定、テスト実行方法、各モジュールの API 仕様書など）があれば教えてください。必要に応じて追記・詳細化します。