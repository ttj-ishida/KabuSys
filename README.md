# KabuSys

日本株自動売買プラットフォームのコアライブラリ群です。ポートフォリオ構築・ポジションサイジング・発注管理・監視・AIによるニュースセンチメント評価など、一連のコンポーネントを含みます。

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群で構成されています。

- execution: 発注エンジン、ブローカーAPIラッパー、注文状態管理、リコンシリエーション
- monitoring: システム稼働監視、注文監視、リスク監視、アラート（LINE）や kill flag による停止制御、監視DB（SQLite）/ダッシュボード（Streamlit）
- portfolio: 銘柄選定・重み付け・ポジションサイズ計算・セクター制限・レジーム乗数
- research: ファクター計算（モメンタム／ボラティリティ／バリュー）、特徴量探索（IC・将来リターン等）
- ai: ニュースNLP（OpenAI）を使った銘柄別センチメント評価、レジーム判定のためのマクロセンチメント
- tools: 運用用ユーティリティ（例: Paper Trading 検証レポート生成）
- utils / config: 環境変数・設定管理、プロセス優先度・CPU affinity 設定など

設計方針の一例：
- DuckDB/SQLite を使ったローカルデータ処理（外部API呼び出しは最小限）
- ルックアヘッドバイアスを避ける（日時参照の取り扱いに注意）
- フェイルセーフ（API失敗時のフォールバックや部分失敗保護）
- テスト容易性を考慮したインターフェース設計

---

## 主な機能一覧

- Execution
  - OrderManager（注文生成・送信・同期）
  - Reconciler（再起動時の自動復旧）
  - RiskManager（発注時の各種制約・制限）
  - Broker client ファクトリ（paper_trading で MockBroker を利用）

- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、プロセス生存チェック、データ鮮度チェック
  - TradeMonitor：滞留注文・約定価格異常検知
  - RiskMonitor：ドローダウン・ポジション上限監視、dashboard 更新
  - KillSwitch：flag ファイルによる ExecutionEngine 停止トリガ
  - AlertManager：LINE push によるアラート送信（クールダウン管理）
  - MonitoringEngine：上記監視をまとめてポーリング
  - Streamlit ダッシュボード（読み取り専用で監視状況を可視化）
  - monitoring.db の自動初期化とマイグレーション

- Portfolio
  - 銘柄候補選定、等重／スコア加重、リスクベースのポジションサイズ計算
  - セクターキャップ・レジーム乗数

- Research
  - Momentum/Volatility/Value ファクター計算（DuckDB を用いた SQL+Python 実装）
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計

- AI
  - ニュースの銘柄別センチメント評価（OpenAI API 呼び出し、バッチ化・リトライ・レスポンス検証）
  - マクロニュース + ETF MA200 を使った市場レジーム判定

- Tools
  - Paper Trading 検証レポート生成（期間指定可）

---

## セットアップ手順

前提
- Python 3.10+（モダンな型注釈（|）を使用）
- SQLite（標準で同梱）
- 推奨：venv を使った仮想環境

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate    # POSIX
   .venv\Scripts\activate       # Windows
   ```

3. 必要なパッケージをインストール（代表的な依存）
   pip install duckdb psutil requests openai streamlit
   - 実運用では requirements.txt を用意して `pip install -r requirements.txt` を推奨します。
   - `psutil` の一部機能は管理者権限や特定プラットフォームで制限される場合があります。

4. データディレクトリを作成
   ```
   mkdir -p data
   ```
   デフォルトの DB パス:
   - DuckDB: data/kabusys.duckdb
   - Monitoring SQLite: data/monitoring.db
   - Paper trading SQLite: data/paper_trading.db

5. 環境変数の設定
   - .env / .env.local をプロジェクトルートに置くと自動でロードされます（OS 環境を上書きしないよう配慮）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

代表的な環境変数（主要なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須な箇所あり）
- KABU_API_PASSWORD: kabuステーションAPIパスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- KABUSYS_ENV: 起動環境（development | paper_trading | live）
- PAPER_FILL_MODE: paper_trading の fill 挙動（instant | partial | never | reject）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite パス
- DUCKDB_PATH, SQLITE_PATH: DB ファイルパス
- PID_FILE_PATH, KILL_FLAG_PATH: 実行監視用ファイルパス
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）

.env の例（プロジェクトルート）
```
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=...
JQUANTS_REFRESH_TOKEN=...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

---

## 使い方

主要な起動スクリプト / ツールの実行例。

- 監視ループを起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 実行開始時にプロセス優先度を "high" に設定しようとします（psutil を使用、権限不足時は警告）。

- ExecutionEngine を起動（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の DB に記録します（本番 DB と分離）。
  - 実行開始時に監視テーブルの存在を保証するため init_monitoring_db() を呼びます。

- Streamlit ダッシュボード（監視 UI）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - read-only モードで SQLite を開きます。MonitoringEngine でデータが更新されている必要があります。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - 環境変数 PAPER_TRADING_SQLITE_PATH または --db オプションで DB パスを指定可能。

- AI（ニューススコア）を実行するプログラム側の呼び出し例（Python スニペット）
  ```py
  import duckdb
  from kabusys.ai import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  from datetime import date
  score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
  ```
  - score_regime（レジーム判定）も同様に呼び出せます（kabusys.ai.regime_detector.score_regime）。

注意点：
- OpenAI 呼び出しは API キーと通信環境を要します。失敗時はフォールバック挙動（0.0 等）をとる設計です。
- monitoring / execution は DB の永続化や kill.flag を使った停止に依存します。運用時は PID ファイル / kill flag のパス設定に注意してください。

---

## 主要ファイル・ディレクトリ構成

以下はコードベースの主要ファイル/パッケージ（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理（.env 自動ロード含む）
  - run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - __init__.py
    - process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py           — monitoring SQLite のスキーマ初期化・操作
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他: broker_factory, execution_engine, order_repository, order_record 等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP（OpenAI）
    - regime_detector.py        — マクロ+ETF MA200 によるレジーム判定
  - data/ (想定されるデータディレクトリ)
    - kabusys.duckdb
    - monitoring.db
    - paper_trading.db

---

## 運用上の注意 / ヒント

- KABUSYS_ENV の値は "development" | "paper_trading" | "live" が有効です。無効値は例外になります。
- paper_trading モードは本番 DB と完全に分離され、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
- Process priority / CPU affinity の設定はプラットフォーム依存です。psutil の権限エラー等が発生した場合はログに警告が出ますが、実行自体は継続します。
- monitoring_db.init_monitoring_db は冪等で何度呼んでも安全です。既存 DB へ必要なカラム追加マイグレーションを行います。
- OpenAI を使う機能は API コストとレート制約があるため、実運用では適切なレート管理と API キーの管理を行ってください。
- Streamlit ダッシュボードは監視DBを読み取り専用で開きます。MonitoringEngine が起動していることを確認してください。

---

必要であれば下記の追加を作成できます：
- requirements.txt（依存 pinned バージョン）
- docker-compose / systemd ユニット例（運用用）
- サンプル .env.example
- CLI ラッパーや管理用スクリプト群

ご希望があれば README をさらに拡張して、運用手順（systemd ユニット例・ログ管理）やデプロイ手順を追加します。