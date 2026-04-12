# KabuSys

日本株向け自動売買システムのコンポーネント群。戦略・ポートフォリオ構築、発注管理、監視、研究/リサーチ、AI を用いたニュースセンチメント評価などを含むモジュール群のサンプル実装です。

---

## 概要

このリポジトリは以下の責務を持つモジュールで構成されています（主なもの）:

- execution: 発注フロー（OrderManager / ExecutionEngine / Reconciler 等）
- monitoring: システム監視・アラート・kill-switch・Streamlit ダッシュボード
- portfolio: 候補選定・重み計算・ポジションサイズ計算・リスク調整
- research: ファクター計算・特徴量探索
- ai: ニュース NLP（OpenAI）による銘柄センチメント評価・市場レジーム判定
- utils: プロセス優先度・CPU affinity ユーティリティ
- tools: Paper Trading 用検証レポート生成スクリプト
- config: 環境変数 / .env 読み込み / 設定ラッパー

設計方針・注意点（抜粋）:
- DuckDB / SQLite を使ったローカル DB ベースの集計・永続化
- 本番データベースと Paper Trading（検証）データベースは分離
- LLM 呼び出し（OpenAI）はフェイルセーフで失敗時は無視／フォールバック
- ルックアヘッドバイアス防止のため日付参照は明示的に引数で渡す設計

---

## 主な機能一覧

- 監視（Monitoring）
  - システムリソース監視（CPU / メモリ / ディスク）
  - Execution プロセス稼働検出（PID ファイル）
  - データ鮮度チェック（DuckDB の prices_daily）
  - 注文滞留・約定異常検出
  - ドローダウン・ポジション上限検出（Kill Switch により execution を停止可能）
  - LINE へのアラート送信（AlertManager）
  - Streamlit ダッシュボード（read-only モードで SQLite を表示）

- 発注 / 実行（Execution）
  - OrderManager による注文作成 / 送信 / 同期
  - Engine 側のリスク管理（RiskManager）、OrderRepository / Reconciler による再起動後の整合性維持
  - Paper Trading モード: MockBrokerClient を使い、paper_trading 用 DB に記録（本番 DB と完全分離）

- ポートフォリオ構築
  - 候補選定（スコア順）
  - 等配分 / スコア加重配分
  - セクター集中制限（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - ポジションサイズ計算（単元株丸め、リスクベース等）

- リサーチ
  - Momentum, Volatility, Value ファクター計算（DuckDB 上の prices_daily / raw_financials を使用）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリー

- AI（OpenAI）
  - 銘柄単位のニュース集約と LLM によるセンチメントスコア化（ai_scores テーブルへ書き込み）
  - マクロニュース + ETF MA200乖離から市場レジーム（bull/neutral/bear）を判定して DB に書き込み

- ツール
  - Paper Trading 検証レポート生成スクリプト（期間指定可能）

---

## 要件 (主要パッケージ)

最低限必要な Python パッケージ（抜粋）:

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボードを使う場合)

pip インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

（実プロジェクトでは requirements.txt を用意して pip install -r で管理してください）

---

## セットアップ手順

1. リポジトリをクローン、作業ディレクトリへ移動。

2. 仮想環境作成（推奨）:
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール:
   ```
   pip install duckdb psutil requests openai streamlit
   ```

4. 環境変数の設定:
   - プロジェクトルートに `.env` / `.env.local` を置くと自動ロードされます（OS 環境変数が優先）。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 重要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY
     - KABUSYS_ENV (development | paper_trading | live)
     - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
     - DUCKDB_PATH (分析 DB, デフォルト: data/kabusys.duckdb)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
     - PAPER_FILL_MODE (paper_trading の動作: instant|partial|never|reject)
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知を使う場合）
     - LOG_LEVEL（DEBUG/INFO/...）

5. データディレクトリ作成:
   ```
   mkdir -p data
   ```

---

## 使い方

### Monitoring を起動する
- デフォルトでは監視ポーリング間隔は 60 秒。
- 上書きするには環境変数 `MONITOR_POLL_INTERVAL` を指定（秒）。1 未満や無効値は無視されデフォルトにフォールバックします。
- 起動:
  ```
  python -m kabusys.run_monitoring
  ```
  または
  ```
  python src/kabusys/run_monitoring.py
  ```
- 説明:
  - 実行時にプロセス優先度を "high" に設定し、monitoring 用の SQLite（settings.sqlite_path）と DuckDB（settings.duckdb_path）に接続します。
  - 監視ログは SQLite（デフォルト: data/monitoring.db）に永続化されます。
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使います（監視は本番 DB を参照するため）。

### Execution（発注エンジン）を起動する
- Paper Trading モードでは `KABUSYS_ENV=paper_trading` を指定すると、MockBrokerClient が使われ、専用の paper_trading DB に記録されます（本番 DB と完全分離）。
- 起動:
  ```
  KABUSYS_ENV=live python -m kabusys.run_execution
  ```
  Paper Trading:
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
- 説明:
  - 起動時にプロセス優先度を "high" に設定、必要な依存コンポーネント（BrokerClient, OrderRepository, RiskManager, Reconciler 等）を組み立てて ExecutionEngine を実行します。
  - Engine は pid_file（デフォルト data/execution.pid）を使いプロセス存在を管理します。

### Streamlit ダッシュボード
- 監視 DB を読み取り専用で表示します。
- 起動コマンド例:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
- DB が存在しない／読めない場合はエラーメッセージが表示されます。

### Paper Trading 検証レポート生成
- ツール:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```
- 引数:
  - --from / --to : YYYY-MM-DD 形式で期間指定
  - --db : SQLite DB パス（指定がない場合は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

### AI / LLM 機能（プログラム的に使用）
- 銘柄ニューススコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
- 市場レジームスコア: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- いずれも OpenAI API キーが必要（引数で渡すか環境変数 OPENAI_API_KEY を設定）。
- LLM 呼び出しはリトライ・フェイルセーフロジックを備えていますが、API キーが無い場合は例外を投げます。

---

## 主要環境変数（要約）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、Execution は MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録する
- SQLITE_PATH: 監視 DB（data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用挙動）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用
- KABU_API_PASSWORD: kabuステーション API 用
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager の LINE 通知用
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH: ExecutionEngine 用 pid ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: KillSwitch の flag ファイルパス（デフォルト data/kill.flag）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）

---

## 実装上の注意 / 動作ポリシー

- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を検出）を起点に `.env`（優先度低）→ `.env.local`（優先）を読み込みます。
  - OS 環境変数はデフォルトで保護され、.env の値で上書きされません（`.env.local` は override=True だが OS 環境変数は protected）。
  - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

- データベース:
  - monitoring 用の SQLite と research/price 用の DuckDB を併用する設計です。
  - Paper Trading モードでは SQLite を別ファイルに分け、本番データを汚染しないようにしています。

- フェイルセーフ:
  - LLM（OpenAI）呼び出しはレート制限・ネットワーク障害に対して指数バックオフでリトライしますが、最終的に失敗した場合は 0.0（中立）やスキップで継続する実装になっています。
  - 監視コンポーネントは個別に例外をキャッチして他の監視を続行します。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数 / .env 読み込み / Settings ラッパー
- run_monitoring.py — SystemMonitor のポーリング起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

src/kabusys/monitoring/
- monitoring_db.py — SQLite テーブル初期化・CRUD（MonitoringDB）
- system_monitor.py — システム・データ鮮度監視
- trade_monitor.py — 注文滞留・約定異常監視
- risk_monitor.py — ドローダウン・ポジション上限監視
- kill_switch.py — kill.flag ファイルによる停止トリガー
- alert_manager.py — LINE プッシュ通知
- monitoring_engine.py — 各 Monitor を束ねるエンジン
- streamlit_dashboard.py — Streamlit による監視ダッシュボード

src/kabusys/execution/
- order_manager.py — 注文作成／送信管理（OrderManager）
- reconciler.py — 起動時のリコンシリエーション（注文・ポジション整合性）
- （他: broker_factory, order_repository, execution_engine 等が想定される）

src/kabusys/portfolio/
- portfolio_builder.py — 候補選定・重み計算
- position_sizing.py — 株数決定・投下資金制御
- risk_adjustment.py — セクターキャップ・レジーム乗数

src/kabusys/research/
- factor_research.py — Momentum / Volatility / Value ファクター計算
- feature_exploration.py — 将来リターン・IC・統計サマリー

src/kabusys/ai/
- news_nlp.py — ニュースの銘柄別センチメント評価 / ai_scores への書き込み
- regime_detector.py — ETF MA200 とマクロニュースで日次レジーム判定

src/kabusys/tools/
- paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

src/kabusys/utils/
- process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

---

## よくある操作例

- 監視を 30 秒間隔で実行:
  ```
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- Paper Trading レポート（過去 10 日）:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- Streamlit ダッシュボードの起動:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

---

## 開発メモ / 拡張ポイント

- パフォーマンスや運用上の要件に応じて、DuckDB / SQLite テーブルのインデックスや VACUUM 等を検討してください。
- BrokerClient の実装（実際の証券会社 API との接続）は抽象化されています。実運用時は認証やレート制限、注文エラー取り扱いの堅牢化が必要です。
- LLM 出力のバリデーションは行っているものの、挙動変化に備えた監視・スキーマ検証を強化してください。
- 単体テスト用に OPENAI 呼び出しや psutil など外部依存をモックする仕組みがあると便利です（既にコード内で差し替え可能な設計を採用しています）。

---

この README はコードベースの主要部分を抜粋して整理したものです。各モジュールの詳細な API や更なる使用例は該当ソースコード（src/kabusys 以下）を参照してください。必要であれば README 内のコマンド・環境変数のテンプレートや、requirements.txt の作成を支援します。