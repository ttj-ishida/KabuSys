# KabuSys

軽量な日本株自動売買システムのコアライブラリ（モニタリング・実行エンジン・ポートフォリオ構築・リサーチ・AIユーティリティ群）。このリポジトリは主に内部ロジック（純粋関数・DB永続化・監視・実行制御）を提供します。

---

## 概要

KabuSys は次を目的としたモジュール群を含みます。

- 注文発行・状態管理の ExecutionEngine（ブローカー抽象化を介して実発注またはモックでの Paper Trading）
- システム／発注／リスクの監視（MonitoringEngine、LINE通知、ダッシュボード）
- ポートフォリオ構築（銘柄選定・重み付け・株数決定・セクター制約）
- リサーチ（ファクター計算・将来リターン・IC評価）
- AI 支援（ニュースのセンチメントスコアリング・市場レジーム判定）
- 運用支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード起動）

設計方針として「ルックアヘッドバイアスを避ける」「DB（DuckDB/SQLite）経由で自己完結する」「本番と paper_trading を明確に分離する（DB・クライアント）」が取られています。

---

## 主な機能一覧

- Execution
  - 注文生成 / ブローカー同期 / リコンシリエーション（再起動後の自動整合）
  - Paper Trading モード（モックブローカー、専用 SQLite DB）
- Monitoring
  - システムリソース監視（CPU / メモリ / ディスク）
  - データ鮮度チェック（価格データの最終更新日）
  - 注文滞留・約定異常検出
  - ドローダウン・ポジション上限監視と Kill Switch（停止フラグ生成）
  - LINE 通知（クールダウン付き）
  - Streamlit ダッシュボード（読み取り専用）
- Portfolio construction
  - 候補選定、等配分／スコア加重配分、リスクベースのポジション決定
  - セクターキャップ適用、レジーム乗数
- Research
  - モメンタム／ボラティリティ／バリューファクター計算（DuckDB 経由）
  - 将来リターン、IC（スピアマン相関）、統計サマリ
- AI
  - ニュースの LLM（OpenAI）によるセンチメント評価と ai_scores テーブルへの書込み
  - マクロニュース＋ETF MA200 に基づくレジーム判定と market_regime 書き込み
- ツール
  - Paper Trading 検証レポート生成スクリプト
  - Streamlit ダッシュボード起動スクリプト

---

## 必要条件（推奨）

- Python 3.10+
- パッケージ（インポート参照に基づく）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード使用時)
- SQLite（標準ライブラリ）

（プロジェクトには requirements.txt がないため、上記を個別にインストールしてください。）

例:
```bash
pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. レポジトリをクローン／配置する（またはパッケージとしてインストール）。
2. 必要パッケージをインストール（上記参照）。
3. .env ファイルをプロジェクトルートに配置して環境変数を設定（オプション）。
   - 自動読み込み順序: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
4. data ディレクトリ（デフォルト DB 等の格納先）を作成（実行時に自動生成されることもあります）。
5. 必須の環境変数を設定:
   - JQUANTS_REFRESH_TOKEN（J-Quants API）
   - KABU_API_PASSWORD（kabuステーション API）
   - OPENAI_API_KEY（AI 機能を使う場合）
   - KABUSYS_ENV（development / paper_trading / live。デフォルト: development）

推奨環境変数（一部デフォルトあり）:
- SQLITE_PATH (デフォルト: data/monitoring.db)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE: instant | partial | never | reject (デフォルト: instant)
- LOG_LEVEL (DEBUG/INFO/...)
- MONITOR_POLL_INTERVAL (監視ポーリング間隔秒。デフォルト 60)

例 (.env):
```
KABUSYS_ENV=paper_trading
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_password
JQUANTS_REFRESH_TOKEN=...
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
```

---

## 使い方（代表的な実行コマンド）

- ExecutionEngine を起動（本番では KABUSYS_ENV を適切に設定）
```bash
# デフォルト (development): 本番 DB を使用
python -m kabusys.run_execution

# Paper Trading モード例
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```
- Monitoring（常駐）を起動
```bash
# ポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能（秒）
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- Paper Trading 検証レポート生成（ツール）
```bash
# デフォルト DB は data/paper_trading.db。--db で別パス指定可
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
```
- Streamlit ダッシュボード（読み取り専用で SQLite を URI で開く）
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- AI 機能（ライブラリ関数呼び出し）
  - ニューススコア付け:
    - Python から呼び出す例:
      from kabusys.ai.news_nlp import score_news
      score_news(duckdb_conn, target_date, api_key=os.environ["OPENAI_API_KEY"])
  - レジーム判定:
      from kabusys.ai.regime_detector import score_regime
      score_regime(duckdb_conn, target_date, api_key=os.environ["OPENAI_API_KEY"])

停止・制御:
- 実行中スクリプトはプロセス優先度を high にセットし、フラグファイルを監視します。
  - 停止（外部から）: プロジェクトルートの data/stop_requested.flag を作成するとポーリングループが終了します。
  - Execution 停止トリガー: KillSwitch が data/kill.flag を書き込み → 実行側が検出して安全停止します。
  - 実行中の PID は data/execution.pid に書かれます。

---

## 環境変数（主要）

- KABUSYS_ENV: development | paper_trading | live（必須ではないが妥当な値を使用）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う機能に必要
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（paper_trading 時）
- PAPER_FILL_MODE: instant | partial | never | reject
- MONITOR_POLL_INTERVAL: 監視ポーリング秒（デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / その他閾値（CPU_THRESHOLD_PCT 等）は Settings クラスで参照

Settings の振る舞い:
- .env 自動読み込み（プロジェクトルートは .git または pyproject.toml から検出）
- OS 環境変数は保護され .env によって上書きされない（デフォルト）。.env.local は override する。

---

## よく使うファイル / フラグ

- data/monitoring.db — 監視ログ SQLite（デフォルト）
- data/paper_trading.db — Paper Trading 用 SQLite（KABUSYS_ENV=paper_trading）
- data/kabusys.duckdb — DuckDB データファイル
- data/stop_requested.flag — デーモンを停止させる外部フラグ（存在すれば監視ループが終了）
- data/kill.flag — KillSwitch による ExecutionEngine 停止トリガー
- data/execution.pid — 実行エンジンの PID（存在確認によりプロセス生存チェックを行う）

注意: フラグはファイルシステムベースの単純フラグです。作成／削除は手動または外部ツールで行えます。

---

## 開発メモ / 実装ノート

- DB 初期化: run_execution/run_monitoring の起動処理内で init_monitoring_db() を呼んでスキーマ作成・簡易マイグレーションを行います。
- Paper Trading は本番 DB から完全に分離されており、専用 SQLite を使用します。
- AI（OpenAI）呼び出しは堅牢化されており、429 やネットワーク断、5xx に対して指数バックオフでリトライします。APIキー未設定時は ValueError を送出する関数が多いので注意してください。
- モジュールは可能な限り外部副作用を抑え、duckdb 接続や sqlite3 接続を呼び出し元から注入する設計になっています（ユニットテストが容易）。
- process_priority ユーティリティは Windows / POSIX の差分を吸収します。権限不足時は警告でスキップします。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数/設定管理（Settings クラス）
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - ai/
    - news_nlp.py                — ニュースセンチメント（OpenAI）処理
    - regime_detector.py         — 市場レジーム判定（MA200 + macro sentiment）
  - monitoring/
    - monitoring_db.py           — SQLite 永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - execution_engine.py        — 実行エンジン（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - (その他 broker 抽象 / order_record 等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py
  - data/                         — 実行時に使用する DB/フラグ等（プロジェクトルートに置く）

（上記は主なファイルのみ抜粋しています。細かいユーティリティや補助モジュールが多数あります。）

---

## トラブルシューティング

- OpenAI 関連で KeyError / ValueError が出る場合:
  - OPENAI_API_KEY を設定してください。テスト時は関数引数で明示的に渡せます。
- DB が見つからない／読み取り専用で開けない:
  - パス確認（デフォルト: data/*.db）。streamlit は読み取り専用で URI を使って開いています。
- プロセスが再起動しても以前の注文状態を回復したい:
  - Reconciler が OrderSent 状態の同期とポジション差分照合を行います（ログを参照）。

---

## ライセンス / 貢献

この README はコードベースの説明目的です。ライセンスや貢献ルールはリポジトリのトップレベルの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

質問や補足してほしいドキュメント（例: セットアップスクリプト、requirements.txt、運用手順書など）があれば教えてください。README の内容を運用環境向けにカスタマイズして拡張できます。