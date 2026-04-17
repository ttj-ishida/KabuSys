# KabuSys

日本株向けの自動売買システム（小規模リサーチ / ポートフォリオ構築 / 実行 / 監視 / AI 補助）用のコードベース。  
このリポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築ロジック、リサーチ用ユーティリティ、OpenAI を使ったニュース NLP / レジーム判定などを含みます。

---

## プロジェクト概要

KabuSys は次のような機能を提供します。

- データ分析・リサーチ（DuckDB 経由）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- 注文管理・実行エンジン（実際のブローカーまたは Paper Trading 用のモック）
- 監視・アラート（システム状態、注文滞留、リスク・ドローダウン監視）
- ニュースの NLP によるセンチメントスコア生成（OpenAI）
- 市場レジーム判定（MA + マクロニュースの LLM 判定）
- 環境設定ウィザード・設定検証・検証レポートツール

設計上の要点：
- 設定は .env（もしくは環境変数）から読み込む
- Paper Trading は本番 DB と分離（Paper 専用 SQLite）
- 監視は監視用 DB（SQLite）へログを残す
- DuckDB は分析・リサーチ用データベースとして使用

---

## 主な機能一覧

- 実行（Execution）
  - BrokerClientFactory によるブローカークライアント作成（本番 or Mock）
  - OrderManager / RiskManager / Reconciler / ExecutionEngine による発注ロジック
  - 起動時にプロセス優先度を "high" に設定（可能な場合）
  - Paper Trading モードでは data/paper_trading.db に記録

- 監視（Monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存 / データ鮮度を監視
  - TradeMonitor: 滞留注文・約定価格の異常を検出
  - RiskMonitor: ドローダウン / ポジション上限を監視し risk_logs に記録
  - KillSwitch: しきい値超過時に data/kill.flag を書き込み ExecutionEngine 停止を誘発
  - AlertManager: LINE Messaging API 経由の通知（設定があれば）

- リサーチ / ファクター計算
  - calc_momentum / calc_volatility / calc_value：DuckDB の prices_daily/raw_financials を参照してファクター計算
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）、統計サマリー

- ポートフォリオ構築
  - 候補選定（スコアソート）
  - 等分配・スコア加重の重み計算
  - セクター上限の適用
  - ポジションサイズ決定（lot 単位、risk_based / equal / score）

- AI モジュール
  - news_nlp.score_news: ニュース記事を OpenAI で評価し ai_scores テーブルに書き込む
  - regime_detector.score_regime: ETF（1321）の MA200 とマクロニュースセンチメントを合成してレジーム判定

- ユーティリティ / ツール
  - config_setup: .env の対話式作成ウィザード
  - validate_config: 環境・config ファイルの事前検証 CLI
  - tools.paper_verification_report: Paper Trading の検証レポート生成

---

## 必要な依存関係（主なもの）

代表的な Python パッケージ（バージョンは実行環境に合わせてください）:
- duckdb
- psutil
- openai
- requests
- PyYAML（config YAML 検証を行いたい場合）
- sqlite3（標準ライブラリ）

インストール例（pip）:
```
pip install duckdb psutil openai requests PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン / 配置
2. 仮想環境を作成して依存関係をインストール
3. .env を作成
   - 対話式ウィザードで作る:
     ```
     python -m kabusys.config_setup
     ```
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 推奨・任意
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
     - OPENAI_API_KEY （AI モジュール使用時）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用）
     - LOG_LEVEL（DEBUG/INFO/..）

4. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合
   python -m kabusys.validate_config --strict
   ```

5. データベース初期化
   - 監視用 DB（monitoring.db）は起動時に自動でテーブルが作成（init_monitoring_db）。
   - DuckDB ファイルはリサーチ用に prices_daily / raw_financials 等のテーブルを準備してください（外部データ取り込みは別ツールで実行）。

---

## 使い方（起動・主なコマンド）

- ExecutionEngine（発注エンジン）起動
  ```
  python -m kabusys.run_execution
  ```
  動作のポイント:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading 用 SQLite に記録（settings.is_paper により切替）。
  - 起動前に data/stop_requested.flag が存在する場合は起動せず終了。
  - 実行中に data/stop_requested.flag が作られるとエンジンに停止シグナルを送り終了。

- Monitoring（監視ループ）起動
  ```
  python -m kabusys.run_monitoring
  ```
  環境変数:
  - MONITOR_POLL_INTERVAL（秒）: ポーリング間隔を上書き（デフォルト 60）
  特記事項:
  - Monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使用する（監視データは一元管理）。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を直接指定
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI モジュールの利用（プログラムから呼ぶ）
  - ニュース NLP スコア生成:
    ```
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="YOUR_OPENAI_API_KEY")
    ```
  - レジーム判定:
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="YOUR_OPENAI_API_KEY")
    ```

---

## 主要な環境変数（抜粋とデフォルト）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- OPENAI_API_KEY: OpenAI を使う場合に必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- LOG_LEVEL: INFO（例: DEBUG/INFO/WARNING）
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH 等は Settings 経由でカスタマイズ可能（Defaults: data/execution.pid / data/kill.flag）

特殊設定:
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant | partial | never | reject）

---

## 停止・Kill Switch の流れ

- Monitoring の KillSwitch がしきい値（ドローダウン等）を満たすと data/kill.flag を作成します。ExecutionEngine は kill.flag を検知して安全に停止します。
- 管理者が手動で停止したい場合は data/stop_requested.flag を作成すると run_monitoring/run_execution の起動ループが終了します（run_monitoring は同ファイルをチェックして停止します）。

---

## DB / マイグレーション

- 監視用 SQLite（デフォルト: data/monitoring.db）
  - init_monitoring_db(conn) により以下テーブルが作られます（冪等）:
    - system_status, trade_logs, positions, risk_logs, dashboard
  - 既存 DB に新しいカラムが必要な場合は起動時に簡易マイグレーション（ALTER TABLE ... ADD COLUMN）を行います（例: dashboard.peak_value, trade_logs.latency_ms）。

- DuckDB（デフォルト: data/kabusys.duckdb）
  - prices_daily / raw_financials / raw_news / ai_scores / market_regime 等のテーブルを想定（リサーチ・AI モジュールが参照）。

---

## ディレクトリ構成

以下はソースの主要ファイル / ディレクトリ（src/kabusys 以下）の要約です。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理、自動 .env 読み込み機能
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py       — レジーム判定（MA + マクロニュース）
  - monitoring/
    - monitoring_db.py        — 監視用 SQLite 永続化層（初期化/CRUD）
    - system_monitor.py       — システム状態 / データ鮮度監視
    - trade_monitor.py        — 注文滞留・価格異常監視
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — Kill Switch（kill.flag 書き込み）
    - alert_manager.py        — LINE 通知マネージャ
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
  - execution/                — Execution 関連（OrderManager, RiskManager, Engine 等）
    - (実装ファイル群。ブローカーファクトリ、実行エンジン、注文リポジトリ等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - __init__.py
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
  - その他:
    - data/ (ランタイム生成されるディレクトリ。PID / flag / DB 等を置く)

（上記はリポジトリ内の主要モジュールの一覧です。実際のファイルはさらに細分化されています）

---

## よくある質問 / 注意点

- Paper Trading と本番 DB は分離されています。KABUSYS_ENV=paper_trading により paper_trading 用 SQLite を使用するので、データが混ざる心配はありません。
- Monitoring は KABUSYS_ENV にかかわらず指定の monitoring SQLite（settings.sqlite_path）を使用します。監視ログは一元化することを想定しています。
- OpenAI を使う機能は API キー（OPENAI_API_KEY）を必ず設定してください。API エラーは可能な限りフェイルセーフ（スコア 0.0 など）で処理されますが、キー未設定時は関数が例外を投げます。
- 実行時のプロセス優先度設定や CPU affinity は psutil に依存し、権限不足や未対応 OS の場合は警告を出してスキップします。
- .env は決してリポジトリにコミットしないでください（config_setup にもその注意書きがあります）。

---

## 開発 / テスト上のヒント

- unit テストでは環境変数の自動読み込みを抑止したい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。
- AI / ネットワーク呼び出しのテスト時は OpenAI クライアントの呼び出し部分（内部関数）を patch して外部通信をモックしてください（ソース内にその旨の注釈あり）。

---

README はここまでです。必要であれば次の追加情報を用意します:
- 詳細な設定項目 (.env.example 風の完全一覧)
- 起動例を含む systemd / supervisor のユニットファイル例
- DuckDB テーブルスキーマのサンプル（prices_daily, raw_financials, raw_news 等）