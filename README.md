# KabuSys — README

このリポジトリは日本株自動売買システム「KabuSys」の一部実装を含みます。ここではプロジェクトの概要、主要機能、セットアップ手順、使い方、およびディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は、日本株の自動売買・検証・監視を目的としたモジュール群です。主な機能は以下の領域に分かれています。

- Execution: 注文生成・ブローカー連携・リコンシリエーション
- Monitoring: システム稼働状況・注文状況・リスク監視、LINEによるアラート送信、Streamlit ダッシュボード
- Portfolio: 銘柄選定・配分・ポジションサイズ計算・リスク調整
- Research: ファクター計算・特徴量探索・IC計算
- AI: ニュースの NLP スコアリング（OpenAI API 利用）、市場レジーム判定
- Tools: Paper Trading の検証レポート作成などのユーティリティ

設計方針として、可能な限り「フェイルセーフ（API失敗時はスキップして継続）」や「ルックアヘッドバイアス排除（date.today() などの直接参照を避ける）」が採用されています。

---

## 機能一覧

- 実運用 / Paper Trading 切替（KABUSYS_ENV）
  - production (live)、paper_trading、development をサポート
  - paper_trading は本番 DB と分離して `data/paper_trading.db` に記録
- ExecutionEngine
  - ブローカー抽象化（Factory）
  - 注文状態管理 / OrderManager / OrderRepository
  - リコンシリエーション（再起動後の自動同期）
- Monitoring
  - SystemMonitor: CPU・メモリ・ディスク・プロセス監視、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン監視、ポジション上限監視、dashboard 更新
  - KillSwitch: 条件到達時に `data/kill.flag` を書いて Execution を停止
  - AlertManager: LINE Messaging API による通知（クールダウン機能あり）
  - Streamlit ダッシュボード：監視情報の可視化
- Portfolio
  - 候補選定、等重・スコア重み、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元丸め・aggregate cap・利用可能現金を考慮）
- Research
  - momentum / volatility / value 等のファクター計算（DuckDB 経由）
  - forward returns、IC、統計サマリー、ランク関数
- AI
  - ニュース記事を OpenAI（gpt-4o-mini）でセンチメント評価 → `ai_scores` 書き込み
  - 市場レジーム判定（ETF ma200 とマクロニュースの LLM センチメントの合成）
  - API エラーはリトライ・フォールバックして安全動作
- Tools
  - paper_verification_report: Paper Trading DB を読みレポートを標準出力に生成

---

## セットアップ手順

前提
- Python 3.10+（typing の | 演算子などを使用）
- 仮想環境を推奨（venv / pipenv / poetry 等）

1. リポジトリをクローンし、仮想環境を作成・有効化
   ```bash
   git clone <repo>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要なパッケージをインストール（最小限の例）
   ```bash
   pip install duckdb psutil requests openai streamlit
   ```
   実際の開発・運用では依存バージョン固定の requirements.txt / Poetry を使用してください。

3. データディレクトリを作成
   ```bash
   mkdir -p data
   ```
   デフォルト DB ファイル:
   - Monitoring SQLite: data/monitoring.db
   - Paper Trading SQLite: data/paper_trading.db
   - DuckDB: data/kabusys.duckdb

4. 環境変数の設定
   - プロジェクトルートの .env / .env.local をサポート（自動読み込みあり）
   - 自動読み込みを無効にする場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
   - 必須（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY
   - 主要な環境変数（デフォルトあり）
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時の Mock 動作）
     - PAPER_TRADING_SQLITE_PATH: paper trading 用 DB パス（デフォルト: data/paper_trading.db）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - LOG_LEVEL, PID_FILE_PATH, KILL_FLAG_PATH 等

   例 .env:
   ```
   KABUSYS_ENV=paper_trading
   OPENAI_API_KEY=sk-...
   PAPER_FILL_MODE=instant
   ```

5. （任意）LINE 通知を有効にする場合は以下を設定
   - LINE_CHANNEL_ACCESS_TOKEN
   - LINE_USER_ID

---

## 使い方

主要な起動スクリプトとツールの使用例。

- 実行エンジン（ExecutionEngine）を起動
  - デフォルトで高優先度に設定し、KABUSYS_ENV によって Paper Trading 用 DB を切り替えます。
  ```bash
  python -m kabusys.run_execution
  ```
  - 停止: プロセスを正常終了するか、プロジェクトルートの `data/stop_requested.flag` を作成すると監視プロセスが検知して終了します。
  - Execution の PID ファイル: `data/execution.pid`（既定）

- 監視ループを起動（SystemMonitor 単体）
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト: 60）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 監視は本番 sqlite_path を利用（KABUSYS_ENV に依存せず本番 DB を参照する実装になっている点に注意）

- Streamlit ダッシュボード
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - ダッシュボードは監視 DB を読み取り専用で開きます。データがない場合はメッセージが表示されます。

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: `data/paper_trading.db`。`--db` で指定可能。

- AI モジュール（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要です（OPENAI_API_KEY または関数引数で指定）
  - 例: スクリプトから呼ぶ / 単体で import して利用する
    - `kabusys.ai.score_news(conn, target_date, api_key=...)`
    - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)`

- Kill / Stop の仕組み
  - `KillSwitch` は内部評価で `data/kill.flag` を書き、Execution 停止を促します。
  - 管理者から強制停止する場合は `data/stop_requested.flag` を作成すると起動済み run_monitoring / run_execution が検知して終了します。

---

## 重要な挙動メモ

- .env の自動読み込み
  - プロジェクトルートを .git または pyproject.toml から検出し、`.env` → `.env.local` の順で読み込みます。
  - OS 環境変数は保護され、`.env.local` は上書き可能だが OS 環境変数は上書きされません。
  - 自動読み込みを無効化する: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- DB 初期化
  - run_monitoring / run_execution は起動時に監視テーブルを作成する `init_monitoring_db()` を呼びます（冪等）。
  - DuckDB / SQLite のパスは Settings から取得され、省略時は data 以下を使います。

- Paper Trading と本番の分離
  - `KABUSYS_ENV=paper_trading` のときは Paper 用 SQLite を使用し、ブローカークライアントはモックを使う想定です（実装に応じた Factory が生成）。

- OpenAI コール
  - リトライや JSON 検証、スコアのクリッピングなど堅牢化がされていますが、APIキーが未設定の場合は例外・ValueError が発生します（呼び出し前に環境変数をセットしてください）。

---

## ディレクトリ構成（抜粋）

リポジトリ内の主要ファイル / モジュール構成（`src/kabusys` 以下）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env の自動ロードを含む）
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト
  - execution/
    - order_manager.py
    - order_repository.py
    - execution_engine.py
    - reconciler.py
    - broker_factory.py
    - broker_api.py
    - ... （注文・ブローカー関連）
  - monitoring/
    - monitoring_db.py        — SQLite テーブル定義 / 永続化
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
    - streamlit_dashboard.py
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
  - data/                      — デフォルトで使われる DB/flag ファイル格納場所（ローカル）
  - utils/
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ

（上記は抜粋です。詳細はソースコードをご参照ください。）

---

## よくある操作・トラブルシュート

- 監視・実行プロセスが起動しない / PID 関連ログ
  - 実行中に生成される PID ファイルを参照、古い PID（プロセス死）であれば SystemMonitor が検出して削除します（stale PID）。
- DB にテーブルがない / スキーマ差異
  - run_* スクリプトは監視テーブルのマイグレーション（列追加等）を冪等で行います。
- OpenAI のレート制限（429）や一時エラー
  - モジュール内で指数バックオフのリトライ実装があります。完全に失敗した場合は該当チャンクをスキップして続行します。
- Paper 検証レポートで DB が見つからない
  - `data/paper_trading.db` の存在を確認、`--db` オプションでパスを指定できます。

---

## 開発上の注意事項

- DuckDB を使用して大規模時系列データ（prices_daily, raw_financials 等）を扱う設計です。DuckDB ファイルは適切に作成・バックアップしてください。
- 多くのモジュールは「外部 API 呼び出しを行う箇所」と「純粋関数」の分離を意識して実装されています。ユニットテストでは外部呼び出しをモックすることが推奨されます。
- セキュリティ上の注意: API キーやパスワードは .env / OS 環境変数で管理し、ソース管理に直接含めないでください。

---

必要があれば README のセクションを追記（例：API仕様、DBスキーマ詳細、運用手順、例 .env.example）します。どの情報を追加したいか教えてください。