# KabuSys

日本株自動売買システム（KabuSys）のソースリポジトリ向け README。  
このドキュメントはリポジトリ内の主要コンポーネントと、ローカルでのセットアップ・実行方法をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買／研究／監視を目的とした Python ベースのシステムです。  
主な関心事は以下です。

- 注文発行と状態管理（ExecutionEngine / OrderManager 等）
- Paper Trading（本番 DB と分離された模擬実行）
- 監視（System / Trade / Risk の定期チェック、LINE 通知、kill flag）
- ポートフォリオ構築（候補選定、重み、ポジションサイズ計算、セクター制限）
- 研究用モジュール（ファクター計算、特徴量探索、IC 計算）
- ニュースの NLP（OpenAI を用いたニュースセンチメント付与）
- DuckDB / SQLite を使った時系列・メタデータの集計・永続化
- Streamlit ベースの監視ダッシュボード

設計方針として、ルックアヘッドバイアスを避ける、外部 API 呼び出しの失敗時はフェイルセーフで継続する、冪等／クラッシュ耐性を重視する実装が施されています。

---

## 機能一覧

- Execution
  - 注文作成 → ブローカー送信 → 状態同期（Reconciler）
  - Paper Trading モード（MockBroker を使用して data/paper_trading.db に記録）
  - リスク管理（RiskManager）と注文リポジトリ
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス状態・データ鮮度の監視
  - TradeMonitor：滞留注文・約定価格異常の検知
  - RiskMonitor：ドローダウン・ポジション上限監視
  - KillSwitch：kill.flag による ExecutionEngine 停止指示
  - AlertManager：LINE Messaging API を使ったアラート送信（クールダウン付き）
  - Streamlit ダッシュボード（監視データ参照）
- Portfolio
  - 候補選定（スコア順ソート）
  - 重み計算（等配分・スコア加重）
  - セクター上限適用
  - ポジションサイズ算出（単元株丸め・aggregate cap・コストバッファ）
- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）や統計サマリー
- AI
  - ニュースセンチメント（OpenAI を用いて銘柄ごとに -1.0〜1.0）
  - 市場レジーム判定（ETF MA200 とマクロニュースセンチメントの合成）
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools.paper_verification_report）
- ユーティリティ
  - 環境設定読み込み (.env/.env.local 自動読み込み)
  - プロセス優先度・CPU affinity 設定ユーティリティ

---

## 必要条件 / 推奨環境

- Python 3.10+
- SQLite（標準ライブラリで利用）
- DuckDB（Python パッケージ）
- ネットワークアクセス（ブローカー API / OpenAI / LINE などを使う場合）
- インストール推奨パッケージ例:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit

例（venv 作成後）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

（実際の requirements.txt は本リポジトリに含まれていない場合があるため、必要に応じて追加してください）

---

## 環境変数（主な項目）

設定は環境変数またはプロジェクトルートの .env / .env.local から読み込みます。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（デフォルト値 / 必須性）:

- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - paper_trading の場合、Execution は paper 用 DB (PAPER_TRADING_SQLITE_PATH) を使用
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API 用）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- OPENAI_API_KEY — OpenAI 利用時に必要
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db （Monitoring が使用する DB）
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db（paper_trading 用）
- PAPER_FILL_MODE — Paper Trading の約定挙動（instant|partial|never|reject、デフォルト: instant）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager（LINE）用
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH — デフォルト: data/execution.pid
- KILL_FLAG_PATH — デフォルト: data/kill.flag
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag をクリアする場合に "1" を設定

注意:
- run_monitoring スクリプトは、KABUSYS_ENV に関わらず Monitoring 用に settings.sqlite_path（通常 data/monitoring.db）を使用します（監視ログは本番 DB に集約される想定）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して本番 DB と分離します。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. 必要パッケージをインストール
   ```bash
   pip install duckdb psutil requests openai streamlit
   ```

4. .env ファイル作成（リポジトリルート）
   - 例:
     ```
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     LINE_CHANNEL_ACCESS_TOKEN=
     LINE_USER_ID=
     ```
   - .env.example があれば参考にしてください。

5. データディレクトリを作成
   ```bash
   mkdir -p data
   ```

6. DuckDB / SQLite スキーマ準備
   - monitoring 用 SQLite は `init_monitoring_db()` により起動時に自動作成／マイグレーションされます。
   - DuckDB 側は prices_daily / raw_financials 等のテーブルが必要（データロードは別途）。

---

## 使い方（実行例）

- ExecutionEngine（本番 / paper_trading）
  - モジュールとして起動:
    ```bash
    python -m kabusys.run_execution
    ```
  - KABUSYS_ENV=paper_trading にすると paper_trading DB を使用し MockBroker を利用します:
    ```bash
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```

- Monitoring（ポーリングループ）
  - デフォルトポーリング間隔 60 秒。MONITOR_POLL_INTERVAL で上書き可能。
    ```bash
    python -m kabusys.run_monitoring
    # ポーリング間隔を 30 秒にする例
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

- Streamlit 監視ダッシュボード
  - read-only モードで SQLite を開く想定:
    ```bash
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```

- Paper Trading 検証レポート生成
  - コマンドラインで日付レンジ指定が可能:
    ```bash
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    # DB パスを指定
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
    ```

- AI モジュール（ニューススコア / レジーム判定）
  - OpenAI API キーが必要。DuckDB 接続を渡して呼び出します（スクリプト例はモジュール関数を参照）。
  - 例（score_news を呼ぶ際の概念）:
    ```py
    from kabusys.ai.news_nlp import score_news
    # conn: duckdb connection, target_date: datetime.date
    score_news(conn, target_date, api_key="sk-...")
    ```

---

## 主要スクリプト説明

- src/kabusys/run_execution.py
  - ExecutionEngine の起動スクリプト。起動時にプロセス優先度を設定し、DB 接続→コンポーネント組み立て→セッション実行を行います。
  - KABUSYS_ENV=paper_trading の場合は paper 用 DB を使用します。

- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL で間隔を制御（デフォルト 60 秒）。
  - 監視テーブルは settings.sqlite_path に書き込まれます（環境に関係なく本番 sqlite_path を使用）。

- src/kabusys/tools/paper_verification_report.py
  - paper_trading DB を元に稼働率、注文成功率、レイテンシ等を集計してレポート出力します。

- src/kabusys/monitoring/streamlit_dashboard.py
  - Streamlit を使ったブラウザベースの監視ダッシュボード。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数読み込み・Settings クラス
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - monitoring/
    - monitoring_db.py — monitoring 用 SQLite のテーブル作成・読み書き
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py — 注文滞留・約定価格異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の作成/管理
    - alert_manager.py — LINE push 通知ユーティリティ
    - monitoring_engine.py — 各 Monitor を束ねる実行ループ
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py, reconciler.py, ...（注文関連）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - research/
    - factor_research.py, feature_exploration.py
  - ai/
    - news_nlp.py, regime_detector.py
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - data/ （実行時に使用される DB ファイル等 / デフォルトパス: data/*.db）

---

## 注意点・運用上の補足

- init_monitoring_db() は起動時に呼ばれ、テーブル作成／簡易マイグレーションを行います（冪等）。
- Process priority（set_process_priority）はプラットフォーム依存の差を吸収しますが、権限不足等で設定できない場合は警告ログが出て動作は継続します。
- kill.flag による停止は冪等で、既存ファイルがある場合は上書きしません。Execution 起動時に KILL_FLAG_CLEAR_ON_START を使ってクリーンアップできます。
- OpenAI / LINE / ブローカー API などは外部サービス依存なので、運用環境では API キーやレート制限、エラーハンドリングに注意してください。モジュール側でもリトライやフェイルセーフ実装がありますが、運用設定（レート・コスト・しきい値）は各プロジェクト固有のチューニングが必要です。
- Paper Trading モードは本番 DB と分離されますが、監視ログは別に管理する設計を確認してください（run_monitoring は sqlite_path を直接使用します）。

---

## 開発者向けメモ

- コード内ドキュメント（docstring）に多くの設計意図や注意点が書かれています。特に AI 関連（news_nlp / regime_detector）は JSON モード・レスポンス検証・リトライ戦略など詳細が明記されています。
- DuckDB を用いたファクター計算は SQL と Python の組合せで実装され、prices_daily / raw_financials 等のテーブルが前提です。データロードパイプラインは別モジュール（kabusys.data.pipeline 等）を参照してください。
- テストを行う際は Settings の自動 .env ロードを `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

---

この README はコードベースの主要点をまとめた概要です。詳細な API 仕様や DB スキーマ、運用手順（バックアップ、監視閾値調整、障害対応フロー等）は別ドキュメントで管理することを推奨します。必要であれば、README に追記したい具体的な運用手順や .env.example のテンプレートを作成しますのでお知らせください。