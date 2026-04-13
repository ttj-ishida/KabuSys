# KabuSys

KabuSys は日本株向けの自動売買・研究・監視を目的とした軽量なPythonライブラリ/アプリケーション群です。  
このリポジトリには取引実行エンジン、モニタリング、ポートフォリオ構築、ファクター計算、LLM を用いたニュースセンチメント評価などのコンポーネントが含まれます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 必要条件 / 依存パッケージ
- セットアップ手順
- 環境変数（主なキー）
- 使い方（主要コマンド）
- ディレクトリ構成（主要ファイルと概要）
- 付録（運用上の注意）

---

## プロジェクト概要

KabuSys は以下の用途を想定したモジュール群を提供します。

- Execution: ブローカーと接続して発注・状態管理（ExecutionEngine / OrderManager 等）
- Monitoring: システム稼働状況、注文滞留、ドローダウン等の監視とアラート（LINE 連携・kill flag 等）
- Portfolio: 銘柄候補選定、重み付け、ポジションサイズ算出、セクター上限処理
- Research: DuckDB を用いたファクター計算（Momentum, Volatility, Value）と統計解析
- AI: ニュースの NLP スコアリング + 市場レジーム判定（OpenAI APIを利用）
- Tools: Paper Trading の検証レポート生成や Streamlit ダッシュボードなど

設計方針の一部：
- DuckDB/SQLite によるデータ永続化（監視ログは SQLite、分析は DuckDB）
- 実行・監視は環境変数で切替（development / paper_trading / live）
- LLM 呼び出しは失敗時にフェイルセーフ（スコア 0 やスキップ）で継続

---

## 主な機能一覧

- Execution
  - ブローカー抽象化（Mock/実ブローカーを切替）
  - 起動時リコンシリエーション（未確定注文・ポジション整合）
  - リスク管理（制限値、サーキットブレーカー等）

- Monitoring
  - システムリソース監視（CPU/メモリ/ディスク）
  - データ鮮度チェック（DuckDB の最終価格日）
  - 注文滞留・約定異常検出
  - ダッシュボード（Streamlit）
  - kill.flag による ExecutionEngine 強制停止シグナル
  - LINE へのプッシュ通知（クールダウン管理）

- Portfolio
  - 候補選定（スコア順）
  - 等金額・スコア加重配分
  - セクター上限適用
  - ポジションサイズ計算（リスクベース等）

- Research
  - モメンタム / ボラティリティ / バリューの日次計算
  - 将来リターン（forward returns）と IC 計算
  - 統計サマリー（count/mean/std/min/max/median）

- AI (OpenAI)
  - ニュース記事を銘柄単位に集約して LLM でセンチメント評価（ai_scores に書込）
  - マクロニュースと ETF ma200 を組合せた市場レジーム判定

- Tools
  - paper_verification_report: Paper Trading 用 DB から検証レポートを生成
  - streamlit_dashboard: 監視データの可視化

---

## 必要条件 / 依存パッケージ

推奨 Python バージョン: 3.10+

主な依存ライブラリ（例）:
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード利用時)

※ 本リポジトリには requirements.txt は含まれていません。必要に応じて pip install を行ってください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動:
   ```
   git clone <repo_url>
   cd <repo_root>
   ```

2. 仮想環境の作成と依存パッケージのインストール:
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb psutil requests openai streamlit
   ```

3. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. データディレクトリ作成（必要に応じて）:
   ```
   mkdir -p data
   ```

5. 初期 DB 作成
   - run_monitoring / run_execution を起動すると、monitoring 用 SQLite テーブルは自動で作成（init_monitoring_db が実行）されます。

---

## 環境変数（主なキー）

以下は主要な環境変数の抜粋と説明。必須のものは明記します。

- KABUSYS_ENV (デフォルト: development)
  - 有効値: development | paper_trading | live
  - paper_trading の場合、MockBroker を使用し paper_trading 用 DB に記録

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants API 用トークン

- KABU_API_PASSWORD (必須)
  - kabuステーション API 用パスワード

- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)

- OPENAI_API_KEY
  - OpenAI を利用する機能（news_nlp / regime_detector）で必要

- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
  - LINE 通知を有効にする場合に設定

- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (paper trading の約定動作: instant | partial | never | reject, default: instant)

- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (1/0): Execution 起動時に kill.flag をクリアするか

- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - Risk / Monitoring で使用する閾値（パーセンテージ）

- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

- MONITOR_POLL_INTERVAL
  - run_monitoring.py のポーリング間隔（秒、デフォルト 60）。0以下は無効でデフォルトにフォールバック。

その他、各モジュールに固有の設定があるため、エラーメッセージや Settings クラスのプロパティを参照してください。

---

## 使い方（主要コマンド / 実行例）

- 実行モジュールを用いた起動

  - Monitoring ポーリングループを起動:
    ```
    python -m kabusys.run_monitoring
    ```
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で上書き可能（例: 30）
    - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用します（監視ログは本番 DB に保存）

  - ExecutionEngine を起動:
    ```
    python -m kabusys.run_execution
    ```
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し `data/paper_trading.db` に記録（本番 DB と分離）

- Paper Trading 検証レポート（ツール）:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` オプションで別 DB を指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

- Streamlit ダッシュボード起動:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - `--db` で監視 DB パスを指定（既存の monitoring.db を read-only で開きます）

- AI / レジーム判定・ニューススコアリングは関数 API として提供されます（OpenAI APIキーが必要）
  - 例: kabusys.ai.news_nlp.score_news / kabusys.ai.regime_detector.score_regime を呼び出して DuckDB 接続と target_date を渡す

---

## 主要ファイル / ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
  - パッケージエクスポート
- config.py
  - 環境変数読み込み・Settings クラス（.env 自動ロード機能を含む）

run スクリプト
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading での Mock 切り替えをサポート）

monitoring/
- monitoring_db.py
  - SQLite を使った監視ログ/テーブル初期化 / 読み書きラッパー
- system_monitor.py
  - リソース / データ鮮度 / PID チェック
- trade_monitor.py
  - 注文滞留・約定価格異常検出
- risk_monitor.py
  - ドローダウン・ポジション上限監視
- kill_switch.py
  - kill.flag 書込み・クリア用ユーティリティ
- alert_manager.py
  - LINE 通知ラッパー（クールダウン付き）
- monitoring_engine.py
  - 複数モニタを束ねるエンジン
- streamlit_dashboard.py
  - Streamlit ベースの監視 UI

execution/
- reconciler.py
  - 起動時の注文 / ポジション照合ロジック
- order_manager.py
  - 発注ワークフロー（OrderRecord と OrderRepository の上位）

portfolio/
- portfolio_builder.py
  - 候補選定・重み付け
- risk_adjustment.py
  - セクター制限・レジーム乗数
- position_sizing.py
  - 株数算出・単元丸め・aggregate cap

research/
- factor_research.py
  - Momentum / Volatility / Value の計算（DuckDB を利用）
- feature_exploration.py
  - 将来リターン、IC、統計サマリー

ai/
- news_nlp.py
  - ニュース記事をまとめて OpenAI に投げ、銘柄ごとのスコアを ai_scores テーブルに書き込む
- regime_detector.py
  - ETF ma200 とマクロニュースを LLM で評価して日次レジームを決定

tools/
- paper_verification_report.py
  - Paper Trading DB から検証レポート生成

utils/
- process_priority.py
  - クロスプラットフォームでのプロセス優先度 / CPU affinity 設定

data/
- （実行時に作成される SQLite / DuckDB ファイル等を配置。デフォルト: data/monitoring.db, data/kabusys.duckdb, data/paper_trading.db）

---

## 運用上の注意 / ベストプラクティス

- 環境ごとに DB を分離すること（特に Paper Trading と Live は分離）。
- OpenAI API 使用時はレート制限・コストに注意。news_nlp はバッチ/チャンク処理とリトライを実装済みだが運用上の監視は必要。
- kill.flag による停止は冪等的（既存ファイルがあれば上書きしない）なので、手動でのクリアが必要な場合がある（ExecutionEngine 起動時に clear を行う設定があります）。
- PID ファイル管理: SystemMonitor は PID ファイルの staleness を検出して削除するロジックがあるため、PID ファイルパス設定は適切に行ってください。
- Streamlit ダッシュボードは監視 DB を read-only で開きます。MonitoringEngine が DB を作成/更新していることを前提とします。
- .env の自動読み込みはリポジトリのルート (.git または pyproject.toml を基準) を参照して行います。CI環境等で読み込みを制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使用してください。

---

必要に応じて README を拡張します。特定の起動手順や各モジュールの詳細ドキュメント（Engine 設計、StrategyModel / PortfolioConstruction の参照文書など）を追加したい場合はお知らせください。