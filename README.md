# KabuSys

日本株向け自動売買システムのサンプル実装（ライブラリ／ツール群）。  
このリポジトリはトレード実行、監視、ポートフォリオ構築、ファクター計算、ニュースNLP（OpenAI）などの主要コンポーネントを含みます。

---

## 概要

KabuSys は以下の責務を持つモジュール群で構成されています。

- Execution（発注）: ブローカークライアントを介した注文作成・送信・状態管理、再起動時のリコンシリエーション
- Monitoring（監視）: プロセス生存・システムリソース・データ鮮度・滞留注文・リスク（ドローダウン等）の監視、アラート送信（LINE）
- Portfolio（ポートフォリオ構築）: 候補選定、重み計算、ポジションサイズ算出、セクター制約、レジーム乗数
- Research（ファクター・探索）: Momentum / Volatility / Value ファクター、将来リターン・IC 計算
- AI（ニュース NLP / レジーム判定）: OpenAI を用いたニュースセンチメント評価、日次レジーム判定
- Tools: Paper Trading 検証レポート生成、Streamlit ベースの監視ダッシュボード
- 設定管理: `.env` / 環境変数の読み込みと Settings API

設計方針（抜粋）
- DuckDB / SQLite を利用して金融時系列・監視ログを保存
- 本番/ペーパートレードを環境変数で切り替え（データ分離）
- OpenAI 呼び出しはフェイルセーフ（失敗時はフォールバック）で実装
- ルックアヘッドバイアス回避のため日付参照は明示的な引数ベース

---

## 主な機能一覧

- 発注管理（OrderManager、OrderRepository）
- 起動時リコンシリエーション（Reconciler）
- 実行エンジン（ExecutionEngine 起動用スクリプト）
- 監視ループ（SystemMonitor / TradeMonitor / RiskMonitor）とアラート（LINE）
- Kill Switch（条件を満たしたら ExecutionEngine を停止させるフラグファイル）
- 監視 DB の自動初期化・マイグレーション（init_monitoring_db）
- Paper Trading 検証レポート生成ツール
- Streamlit ダッシュボード（監視情報可視化）
- ファクター計算・特徴量探索（DuckDB 上で完結）
- ニュースの LLM ベースセンチメント解析（OpenAI）

---

## セットアップ手順（開発環境向け）

前提: Python 3.10+（PEP 604 の union 型 `X | Y` を使用しているため）

1. リポジトリをクローン／配置
2. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)
3. 依存パッケージをインストール（代表例）
   - pip install duckdb psutil openai requests streamlit
   - （プロジェクトに requirements.txt がある場合はそれを利用してください）
4. 環境変数 / .env を準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動ロードされます（既存 OS 環境変数は保護されます）。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
5. データディレクトリを作成
   - mkdir -p data

推奨の最低環境変数（.env 例）
- KABUSYS_ENV=development|paper_trading|live
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...  （AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...
- SQLITE_PATH=data/monitoring.db
- DUCKDB_PATH=data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

---

## 使い方

以下はよく使うスクリプト／コマンドの例です。パッケージとして実行することを想定しています（python -m kabusys.<module>）。

1. ExecutionEngine（発注エンジン）の起動
   - デフォルトは Settings に従い DB 等を接続します。
   - Paper Trading を使う場合:
     - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient が使われ、データは PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録され本番 DB と分離されます。
   - 実行例:
     - python -m kabusys.run_execution
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

2. Monitoring（監視ループ）の起動
   - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
   - 実行例:
     - python -m kabusys.run_monitoring
   - 注意:
     - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視ログは本番 DB に記録される設計）。
     - 起動時にプロセス優先度を "high" に設定しようとします（psutil の権限に依存）。

3. Paper Trading 検証レポート生成
   - ツール: kabusys.tools.paper_verification_report
   - 実行例:
     - python -m kabusys.tools.paper_verification_report
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - データベースを明示する場合: --db path/to/paper_trading.db

4. Streamlit ダッシュボード（監視 UI）
   - 実行例:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 監視 DB を読み取り専用モードで開くため、MonitoringEngine を先に起動してデータを作成してください。

5. AI（ニューススコア・レジーム判定）
   - OpenAI API キーが必要: OPENAI_API_KEY 環境変数または関数引数で渡す
   - 関数:
     - kabusys.ai.score_news(conn, target_date, api_key=None)
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - 実行は DuckDB 接続を渡して呼び出します。失敗時はフォールバック動作（スコア＝0）があります。

環境変数の主な一覧（重要なもの）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）デフォルト 60（0以下は無効）
- SQLITE_PATH: 監視 DB（SQLite）デフォルト data/monitoring.db
- DUCKDB_PATH: 時系列 DB（DuckDB）デフォルト data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（paper_trading 時に使用）デフォルト data/paper_trading.db
- PID_FILE_PATH: execution.pid のパスデフォルト data/execution.pid
- KILL_FLAG_PATH: kill.flag のパスデフォルト data/kill.flag
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用

設定読み込みの挙動
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` が自動ロードされます。
- OS 環境変数は保護され、.env の値が上書きされないよう配慮されています。
- 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 監視（Monitoring）に関する補足

- init_monitoring_db(conn) が監視用テーブル群（system_status / trade_logs / positions / risk_logs / dashboard）を作成・マイグレーションします。実行前に明示的な初期化は不要です。
- SystemMonitor は PID ファイルを確認し、プロセスが存在しない stale PID を検出すると削除してリスクログに記録します。
- RiskMonitor は dashboard を参照してハイウォーターマーク・ドローダウンを管理し、必要に応じて risk_logs にリスクイベントを書き込み、KillSwitch が kill.flag を作成します。
- AlertManager は LINE の Push API を使って通知します。トークン・ユーザID が未設定の場合はログに残し送信はスキップします。

---

## ディレクトリ構成（主要ファイルと説明）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定読み込み・Settings クラス
  - run_execution.py — ExecutionEngine 起動スクリプト（メインエントリ）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - process_priority.py — psutil を使ったプロセス優先度 / CPU affinity ユーティリティ
  - execution/
    - order_manager.py — 注文マネージャ（OrderState マシン外向き API）
    - reconciler.py — 起動時の同期・リコンシリエーション
    - (その他: broker_factory, execution_engine, order_repository など: 発注関連)
  - monitoring/
    - monitoring_db.py — SQLite への読み書き（テーブル作成・CRUD ラッパー）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 滞留注文・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — フラグファイルによる停止シグナル
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit 監視ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定・スコアソート
    - risk_adjustment.py — セクター制限・レジーム乗数
    - position_sizing.py — 発注株数計算（単元丸め・集約上限）
  - research/
    - factor_research.py — momentum / volatility / value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py — raw_news を OpenAI でスコアリングして ai_scores に書き込む
    - regime_detector.py — レジーム判定（ma200 + macro sentiment 合成）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - data/ （実行時に作成される想定）
    - kabusys.duckdb （DuckDB default）
    - monitoring.db / paper_trading.db （SQLite）

（注）上記はリポジトリ内の主要ファイルを抜粋した一覧です。実際の実装にはさらに補助モジュールや broker API 周りのコードが含まれます。

---

## 運用上の注意点

- Paper Trading と Live は DB を分離して運用してください（PAPER_TRADING_SQLITE_PATH が有効）。
- OpenAI を利用する機能は API 呼び出しのレート制限・失敗を考慮しており、失敗時はフォールバックしますが、API キーの管理は慎重に行ってください。
- プロセス優先度の変更や CPU affinity 設定は OS 権限に依存します。権限不足だと設定に失敗して警告が出力されますが処理は継続します。
- MONITOR_POLL_INTERVAL を極端に短く設定するとシステム負荷やログ肥大化を招きます。デフォルト 60 秒を推奨します。

---

## ライセンス / 貢献

この README はコードベースに基づく簡易ドキュメントです。実際の商用利用や配布を行う場合はライセンスや責任範囲を明記してください。機能修正・改善のプルリクエストは歓迎します。

---

必要であれば README の英語版や、各モジュール（ExecutionEngine の起動フロー、OrderRepository のスキーマ、AI のプロンプト仕様など）について詳細なドキュメントを追加できます。どの部分を優先して充実させるか教えてください。