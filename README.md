# KabuSys

日本株向けの自動売買システム（ライブラリ & 実行ツール群）

このリポジトリは、約定・リスク管理・監視・ポートフォリオ構築・リサーチ・AI ベースのニュース解析などを統合した自動売買基盤の主要コンポーネントを含みます。

---

## プロジェクト概要

- 実行エンジン（ExecutionEngine）による発注・注文管理・リスク管理の実装
- 監視（Monitoring）モジュール：システム状態・注文異常・ドローダウン等の検出とログ化
- ポートフォリオ構築ユーティリティ（候補選定、重み計算、ポジションサイズ計算、セクター制約）
- リサーチ用モジュール（ファクター計算・将来リターン・IC・統計サマリ）
- AI モジュール：ニュースのセンチメントスコアリング（OpenAI）、市場レジーム判定
- 運用用ツール：Paper Trading 検証レポート、Streamlit ダッシュボード など
- 設定管理（環境変数と .env の自動読み込み）

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine の起動スクリプト
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper DB（data/paper_trading.db）に記録
  - プロセス優先度設定、PID 管理、停止フラグ監視（data/stop_requested.flag）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動
  - MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視ログは SQLite（monitoring.db）へ永続化（環境に関わらず本番 sqlite_path を使用）
- 監視コンポーネント
  - SystemMonitor：CPU/メモリ/ディスク・プロセス稼働・データ鮮度チェック
  - TradeMonitor：滞留注文、約定価格異常検出
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch：条件に応じて data/kill.flag を書き込み、ExecutionEngine 停止シグナル送出
  - AlertManager：LINE Push を用いた通知（クールダウン管理あり）
  - Streamlit ダッシュボード（監視 UI）
- ポートフォリオ
  - 候補選定（スコア降順）、等金額／スコア加重の重み付け
  - ポジションサイズ計算（risk_based、等配分、スコア配分）、単元（lot）丸め、集約キャップ調整
  - セクター集中制限、レジーム乗数（bull/neutral/bear）
- リサーチ
  - ファクター計算：モメンタム / ボラティリティ / バリュー
  - 特徴量探索：将来リターン、IC（Spearman）、統計サマリ等（DuckDB ベース）
- AI（OpenAI）
  - ニュース NLP による銘柄単位センチメント算出（ai_scores テーブルへ書込）
  - レジーム判定（ETF 1321 の MA とマクロニュースを LLM 評価で合成）
- 運用ツール
  - paper_verification_report：Paper Trading DB の検証レポート生成（稼働率、成功率、レイテンシ等）

---

## 前提条件 / 推奨環境

- Python 3.10 以上（PEP 604 の union 型表記等を使用）
- SQLite（標準ライブラリ）
- DuckDB（Python パッケージ）
- External packages:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボード利用時)
- ネットワーク接続（OpenAI 呼び出しや LINE API を使用する場合）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai requests streamlit

   （必要に応じて requirements.txt を用意している場合はそれを利用してください）

4. data ディレクトリを作成
   - mkdir -p data

5. 環境変数の設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（.env.local もサポート）。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

6. 必須の環境変数（例）
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=... (AI モジュール利用時必須)
   - KABUSYS_ENV=development|paper_trading|live
   - その他（任意）: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL, PAPER_FILL_MODE, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

---

## 重要な環境変数（主なもの）

- KABUSYS_ENV: development / paper_trading / live
  - paper_trading の場合、run_execution は paper 用 DB（PAPER_TRADING_SQLITE_PATH）と MockBrokerClient を利用
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector を呼ぶ際に必要）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用
- KABU_API_PASSWORD: kabuステーション API 用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: PaperTrading 用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60）
- PID_FILE_PATH, KILL_FLAG_PATH: ファイルパス（Settings でデフォルト設定あり）
- LOG_LEVEL: ログレベル（DEBUG|INFO|...）

---

## 実行方法（代表例）

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL を設定してポーリング間隔を変更可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は Settings に定めた sqlite_path を使用（環境にかかわらず本番 sqlite_path を使用する点に注意）

- 実行エンジンを起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と分離）
  - 起動時に PID ファイル（data/execution.pid デフォルト）を生成、停止は data/stop_requested.flag により行える

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db /path/to/paper_trading.db（指定がない場合は環境変数 PAPER_TRADING_SQLITE_PATH あるいは data/paper_trading.db）

---

## ライブラリ（モジュール）利用例

- AI スコア付与（ニュース）
  - from kabusys.ai import score_news
  - score_news(conn=duckdb_conn, target_date=date(2026,4,1), api_key="...")

- レジームスコア（AI + MA）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn=duckdb_conn, target_date=date(2026,4,1), api_key="...")

- ポートフォリオ構築ユーティリティ
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
  - candidates = select_candidates(buy_signals, max_positions=10)
  - weights = calc_score_weights(candidates)
  - sizes = calc_position_sizes(weights=weights, candidates=candidates, portfolio_value=..., ...)

- 研究用（ファクター）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - momentum = calc_momentum(duckdb_conn, target_date)

---

## ファイル / ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
  - Settings クラス：環境変数の解決・自動 .env 読み込み
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 分離機能あり）
- monitoring/
  - monitoring_db.py — SQLite スキーマ定義・簡易マイグレーション・永続層
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 制御
  - alert_manager.py — LINE Push 通知（クールダウン）
  - monitoring_engine.py — 各 Monitor をまとめる
  - streamlit_dashboard.py — Streamlit ベースの監視 UI
- execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py (エンジン本体は一部のみ)
  - broker_factory.py / broker_api.py — ブローカー抽象化
- portfolio/
  - portfolio_builder.py — 候補選定・重み生成
  - position_sizing.py — 株数計算・丸め・集約キャップ
  - risk_adjustment.py — セクター制限・レジーム乗数
- research/
  - factor_research.py — Momentum/Volatility/Value
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- ai/
  - news_nlp.py — ニュースセンチメント算出（OpenAI）
  - regime_detector.py — ETF MA + マクロニュースでレジーム判定
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください）

---

## 運用時の注意 / 実装上の補足

- run_monitoring は Settings.sqlite_path（監視用 DB）を用います。環境にかかわらず本番 sqlite_path を使用する旨はソースに明記されています。
- run_execution は paper_trading モード時に paper 用 DB を使用して本番 DB からの切り離しを行います。
- .env の読み込み順は: OS 環境変数 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
- MonitoringDB.init_monitoring_db() は冪等でテーブル作成・簡単なマイグレーション（カラム追加）を行います
- OpenAI 呼び出しは API エラーや 5xx、429、タイムアウト等に対してリトライやフォールバック処理を実装（モジュール内参照）
- プロセス優先度設定（set_process_priority）は psutil を用いて OS に合わせて処理を行い、権限不足時は警告ログを出してスキップします
- stop フラグ / kill フラグのデフォルトパスは data ディレクトリ直下（実行スクリプト内で解決）

---

## 開発メモ

- Python 型ヒント（PEP 604 等）を用いているため Python 3.10 以上を推奨
- 単体テストや CI のハーネスはこの README に含まれていません。テストを実行する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して環境依存を切ると安定します
- DuckDB / SQLite のスキーマはコード中に SQL で埋め込まれているため、DB バージョンの互換性に注意してください

---

必要に応じて README に追加してほしい内容（API 仕様の詳細、より詳しい環境変数一覧、運用手順書など）があれば指示ください。