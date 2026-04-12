# KabuSys

日本株向け自動売買・リサーチ基盤の一部を実装した Python パッケージです。  
このリポジトリには実行エンジン、監視（Monitoring）、ポートフォリオ構築・リスク調整、リサーチ（ファクター計算）、および AI を使ったニュースセンチメント評価などのモジュールが含まれます。

---

## プロジェクト概要

KabuSys は、以下のような責務を持つモジュール群で構成された自動売買システムのコア実装です。

- ExecutionEngine：シグナルを受けてブローカーへ発注し、注文状態を管理する
- Monitoring：システム状態、注文状況、リスク（ドローダウン・ポジション上限）を定期的に監視・ログ化しアラートを投げる
- Portfolio Construction：候補選定、重み付け、ポジションサイズ計算などの純粋関数群
- Research：DuckDB 上の価格・財務データからファクター・将来リターン・IC 等を計算
- AI：ニュースを LLM（OpenAI）でスコアリングし銘柄別スコアや市場レジームを判定
- Tools：Paper Trading の検証レポート生成などのユーティリティ

設計方針の例：
- DuckDB / SQLite を利用したローカルデータ処理
- 本番と paper_trading 環境は DB を完全分離
- ルックアヘッドバイアス回避（日時を外部から与える設計）
- API 呼び出しはリトライ / フェイルセーフ実装

---

## 主な機能一覧

- System monitoring
  - CPU / メモリ / ディスク使用率の記録
  - データ鮮度チェック（prices_daily の最終日付）
  - PID ファイル監視（プロセス停止検出・stale PID 検出）
- Trade monitoring
  - 滞留注文（stale orders）検出
  - 約定異常（約定価格の大幅乖離）検出
- Risk monitoring
  - ドローダウン（ハイウォーターマーク追跡）監視とアラート
  - ポジション数上限監視
  - kill.flag による ExecutionEngine 停止シグナル発行
- Execution
  - Broker クライアント切替（本番 / paper_trading）
  - 再起動時のリコンシリエーション（注文状態 / ポジションの突合）
  - Order state machine（作成→送信→約定/却下 等）
- Portfolio
  - 候補選定（スコア順）、等配分・スコア重み・リスクベース配分
  - セクター制約、レジーム乗数、単元株丸め、集約キャップ
- Research
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマンランク相関）、ファクター統計
- AI（OpenAI）
  - ニュース記事の銘柄単位センチメントスコア化（ai_scores テーブルへ格納）
  - マクロニュース + ETF MA200乖離から市場レジーム判定（market_regime テーブルへ格納）
- ツール
  - Paper Trading 検証レポート生成（期間指定可）
  - Streamlit による監視ダッシュボード

---

## セットアップ手順

1. Python 環境（推奨: 3.10+）を用意します。仮想環境を作成する例：

   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate.bat  # Windows
   ```

2. 依存パッケージをインストールします（requirements.txt がある場合はそれを使ってください）。代表的な依存：

   ```
   pip install duckdb psutil requests streamlit openai
   ```

   実行環境により追加で必要なパッケージがある場合があります（例: SQLite は標準ライブラリに含まれます）。

3. 環境変数を設定します。
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（既存 OS 環境変数は保護されます）。
   - 自動読み込みを抑止する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（主なものを抜粋）：
   - JQUANTS_REFRESH_TOKEN: J-Quants 用トークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
   - KABUSYS_ENV: 起動モード（development / paper_trading / live）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: paper_trading 時の専用 SQLite（デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE: paper_trading の約定挙動 ("instant" / "partial" / "never" / "reject")
   - LOG_LEVEL, PID_FILE_PATH, KILL_FLAG_PATH, MONITOR_POLL_INTERVAL など

   例（.env）:
   ```
   KABUSYS_ENV=development
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=...
   JQUANTS_REFRESH_TOKEN=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

4. データディレクトリを作成します（必要に応じて）:

   ```
   mkdir -p data
   ```

5. 初回実行時に監視 DB のテーブルは自動作成されます（init_monitoring_db を呼び出すため、通常は手動で初期化不要です）。

---

## 使い方

以下は主要な実行エントリポイントと実行例です。

- ExecutionEngine（実取引 / PaperTrading を起動）

  - 実行:

    ```
    python -m kabusys.run_execution
    ```

  - 注意:
    - `KABUSYS_ENV=paper_trading` を設定すると MockBrokerClient を使い、paper 専用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。
    - 起動時にプロセス優先度を "high" に設定します（プラットフォームにより制限あり）。

- Monitoring（SystemMonitor のポーリングループ起動）

  - 実行:

    ```
    python -m kabusys.run_monitoring
    ```

  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書きできます（デフォルト 60 秒）。0 以下の値は無視されデフォルトに戻ります。
  - 監視は常に本番用の sqlite_path を使用します（環境に依らず監視用 DB を共通化する設計）。

- Paper Trading 検証レポート生成（ツール）

  - 実行例:

    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```

  - オプション:
    - --from YYYY-MM-DD : 期間開始
    - --to YYYY-MM-DD : 期間終了
    - --db PATH : SQLite DB ファイルパス（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- Streamlit ダッシュボード（監視）

  - 実行:

    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```

  - ダッシュボードは監視 DB を read-only で開き、ポートフォリオ・ポジション・最近の注文・最新システム状態・最近のリスクイベントを表示します。

- AI 機能（プログラム呼び出し）

  - ニューススコアリング（例: プログラム内部から呼ぶ）:

    ```python
    from kubusys.ai import score_news
    import duckdb
    from datetime import date

    conn = duckdb.connect("data/kabusys.duckdb")
    written = score_news(conn, target_date=date(2026, 4, 11), api_key="sk-...")
    print(f"書き込み件数: {written}")
    ```

  - レジーム判定:

    ```python
    from kubusys.ai.regime_detector import score_regime
    written = score_regime(conn, target_date=date(2026,4,11), api_key="sk-...")
    ```

  - 注意: API キーは引数で渡すか環境変数 `OPENAI_API_KEY` を設定してください。失敗時は多くの箇所でフェイルセーフ（0.0やスキップ）動作をします。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要なファイル・モジュールの概要です。

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

- src/kabusys/execution/
  - execution_engine.py — 実行エンジン（EngineConfig 等）
  - order_manager.py — Order 管理（Order 状態遷移・送信フロー）
  - order_repository.py — SQLite ベースの注文永続化（参照）
  - reconciler.py — 起動時の同期・リコンシリエーション
  - broker_factory.py / broker_api.py — ブローカークライアント抽象と生成

- src/kabusys/monitoring/
  - monitoring_db.py — 監視ログの永続化層（SQLite テーブル初期化・CRUD）
  - system_monitor.py — システム監視（CPU/メモリ/ディスク・PID・データ鮮度）
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書き込み・判定ロジック
  - alert_manager.py — LINE 通知プッシュ
  - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・スコアソート
  - position_sizing.py — 株数算出ロジック（risk_based / equal / score）
  - risk_adjustment.py — セクター制約・レジーム乗数
  - __init__.py — 主要関数を再エクスポート

- src/kabusys/research/
  - factor_research.py — momentum / volatility / value ファクター計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - __init__.py — 主要関数を再エクスポート

- src/kabusys/ai/
  - news_nlp.py — ニュースを LLM でセンチメントスコア化する処理
  - regime_detector.py — マクロ + MA200 を使った市場レジーム判定
  - __init__.py — API のエクスポート

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

- src/kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 運用上の注意点 / トラブルシューティング

- .env 読み込み
  - config.py はプロジェクトルート（.git または pyproject.toml を探索）を元に .env/.env.local を自動読み込みします。CI やテストで自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等設計で、既存 DB に対して必要なカラム追加（簡単な ALTER）を行う仕組みを持ちます。

- Paper Trading（分離）
  - `KABUSYS_ENV=paper_trading` のときは broker が Mock となり書き込み先 SQLite が paper_trading 用に切替わります。これにより本番 DB と完全に分離できます。

- OpenAI API
  - API 呼び出しは 429 / タイムアウト / 5xx 等に対して指数バックオフでリトライしますが、API キーが不正・未設定の場合は例外になります。AI 機能を使う際は `OPENAI_API_KEY` を設定してください。

- LINE 通知
  - channel token / user id が未設定の場合、AlertManager は送信をスキップしてログのみ記録します。

---

## 開発メモ

- 単体テストを書く際は、外部 API 呼び出し（OpenAI / ブローカー / requests）をモックすることを推奨します。news_nlp / regime_detector は内部の API 呼び出し関数を patch しやすい設計になっています。
- DuckDB のクエリは日付範囲を明示的に与え、ルックアヘッドを防ぐ設計になっています。research モジュールは副作用を持たない純粋関数群を目指しています。

---

必要であれば README にサンプル .env.example、requirements.txt の推奨内容、CI / systemd ユニットファイル例、デプロイ手順（Docker / コンテナ化）などを追加できます。どの情報を優先して追加しますか？