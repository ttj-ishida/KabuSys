# KabuSys

KabuSys は日本株向けの自動売買 / 研究 / 監視ツール群です。  
このリポジトリには、戦略のリサーチ用ファクター計算、ポートフォリオ構築ロジック、実運用向けの ExecutionEngine、監視コンポーネント、AI（ニュースセンチメント/レジーム判定）連携などが含まれます。

---

## 主な特徴（機能一覧）

- Execution
  - 発注状態管理 (OrderManager / OrderRepository)
  - ブローカークライアントの抽象化（本番 / Paper Trading 切替）
  - 再起動時のリコンシリエーション（Reconciler）
  - リスク管理（RiskManager）
- Monitoring
  - システム状態監視（CPU / メモリ / ディスク / プロセス）
  - 注文滞留・約定価格異常の検出
  - ドローダウン・ポジション上限監視（Kill Switch）
  - 監視ログ永続化（SQLite）
  - LINE によるアラート通知（AlertManager）
  - Streamlit ダッシュボード
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- Portfolio Construction
  - 候補選定、等重/スコア重み計算
  - セクター集中制限、レジーム乗数適用
  - 株数算出（単元丸め、リスクベース配分、スケールダウンロジック）
- AI 連携
  - OpenAI を用いたニュースセンチメント（ai_scores）
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定
- ツール
  - Paper Trading の検証レポート生成スクリプト

---

## 前提条件 / 依存関係

- Python 3.10+（型ヒントで | 演算子を使用しているため）
- 推奨パッケージ（examples — 実際は requirements.txt を用意してください）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite（標準ライブラリで利用）
- ネットワーク（LINE API / OpenAI API を使う場合）

例: 仮想環境作成・パッケージインストール
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動。
2. Python 仮想環境を作成して有効化（上記参照）。
3. 必要パッケージをインストール。
4. 環境変数を設定（.env ファイルをプロジェクトルートに置くことが可能。詳細は下の「環境変数」参照）。
5. data/ フォルダを作成（デフォルト DB ファイル等がここに置かれます）。
```
mkdir -p data
```

---

## 環境変数（主な設定）

Settings（kabusys.config）で定義される主な環境変数:

- 基本
  - KABUSYS_ENV: 起動モード。`development` / `paper_trading` / `live`（デフォルト: development）
  - LOG_LEVEL: ログレベル（"DEBUG", "INFO", ...）
- API
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須で使用箇所あり）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須で使用箇所あり）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- データベース / ファイルパス
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: ExecutionEngine 用 PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: Kill Switch 用フラグファイル（デフォルト: data/kill.flag）
- Paper Trading
  - PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定モード）
- Monitoring 閾値（任意）
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- 自動 .env 読み込み
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env 読み込みを無効化

.env ファイル読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` / `.env.local` を順に読みます。OS 環境変数が優先されます。

---

## 実行方法（使い方）

以下は主要なエントリポイントの実行方法例です。プロジェクトルートで実行してください。

- 監視ループを起動（SystemMonitor のポーリング）
```
python -m kabusys.run_monitoring
```
オプション:
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）。
- run_monitoring は Settings に従い sqlite_path を使用（Monitoring は環境にかかわらず本番 sqlite_path を参照）。

- 実行エンジン（ExecutionEngine）を起動
```
python -m kabusys.run_execution
```
ポイント:
- KABUSYS_ENV=paper_trading とすると MockBrokerClient を使用し、Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に書き込みを行います。本番 DB と分離されます。
- 起動時にプロセス優先度を "high" に設定します（OS により無視される場合あり）。

- Paper Trading 検証レポート生成
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
```
オプション:
- --db で SQLite ファイルを指定。未指定の場合は環境変数 PAPER_TRADING_SQLITE_PATH、さらに未設定なら `data/paper_trading.db` が使用されます。

- Streamlit 監視ダッシュボード
（起動前に MonitoringEngine を稼働させ、データベースが存在すること）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- AI 機能（ニューススコア / レジーム判定）
  - kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime を呼び出して DuckDB 接続と target_date, api_key を渡すことで動作します。
  - OpenAI API キーは引数で与えるか環境変数 OPENAI_API_KEY を設定してください。

---

## 運用上の注意

- kill.flag
  - KillSwitch は data/kill.flag に理由を書き込むことで ExecutionEngine 停止指示を行います。ExecutionEngine 側はこのフラグを検知して安全に停止する設計を想定しています。
  - 実行前に KILL_FLAG_CLEAR_ON_START を 1 にしておくと起動時にフラグを自動クリアできます（Settings.kill_flag_clear_on_start）。
- PID ファイル
  - ExecutionEngine は PID を pid_file に書きます。SystemMonitor はこの PID を見てプロセス生存チェックを行います。
- Paper Trading
  - `KABUSYS_ENV=paper_trading` を使うとブローカーはモックになり、本番 DB と分離された paper DB に注文ログを残します。実運用の誤操作を防げます。
- .env の取り扱い
  - .env 読み込み実装はかなり柔軟で、クォートやコメント、`export KEY=val` 形式に対応します。
  - テスト等で自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / Settings 管理、.env 自動読み込みロジック
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト
  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込むロジック
    - regime_detector.py — マクロ + ETF MA を使った市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化と簡易永続化 API（MonitoringDB）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウンやポジション上限の監視（RiskMonitor）
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - alert_manager.py — LINE Push によるアラート通知
    - monitoring_engine.py — 各 Monitor をまとめるループ
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数算出・スケーリング・単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算、IC、統計サマリ
  - execution/
    - order_manager.py — 発注ワークフロー（OrderManager）
    - reconciler.py — 起動時の注文・ポジション照合（自動復旧）
    - （※そのほか broker_factory, execution_engine, order_repository, order_record 等のモジュールが想定）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- data/
  - data/kabusys.duckdb（デフォルト DuckDB）
  - data/monitoring.db（監視用 SQLite）
  - data/paper_trading.db（Paper Trading 用 SQLite）
  - data/execution.pid, data/kill.flag など

---

## 開発メモ / テストに関して

- Settings クラスは多数のプロパティを通して設定を取得します。ユニットテスト時は環境変数をモックするか、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化してください。
- OpenAI / 外部 API を呼ぶ箇所（news_nlp, regime_detector）は API 呼び出しラッパーが分離されているため、unit test では _call_openai_api 等を patch して振る舞いをシミュレートできます。
- DuckDB を本番データで叩く処理は副作用が出ないように read-only 接続やテスト用の小さなデータセットでテストしてください。

---

必要なら、README に追記してほしい「使用例（CLI のスクリーンショットや実行ログ）」「requirements.txt」「デプロイ手順（systemd / docker）」なども作成できます。どれを補足しますか？