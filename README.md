# KabuSys

日本株向け自動売買システム（ライブラリ／起動スクリプト群）

本リポジトリは、データ処理・ファクター計算・ポートフォリオ構築・発注エンジン・監視および AI 補助機能を含む自動売買システムの主要コンポーネントを含みます。実運用（live）・ペーパートレード（paper_trading）・開発（development）で動作モードを切り替えられる設計です。

---

## 概要

- DuckDB / SQLite を用いたデータ格納・解析
- Strategy / Research モジュールでファクター計算・特徴量解析
- Portfolio モジュールで銘柄選定・配分・ポジションサイズ算出
- ExecutionEngine による発注処理（kabuステーション / MockBroker を切替）
- Monitoring 系でシステム状態・注文状態・リスクを定期監視
- AI モジュール（OpenAI）を利用したニュースセンチメント解析・市場レジーム判定
- 設定ウィザード・検証 CLI、紙上検証レポート生成ツール等のユーティリティ

---

## 主な機能一覧

- 設定管理
  - .env 自動ロード、対話式ウィザード（`kabusys.config_setup`）
  - 設定検証 CLI（`kabusys.validate_config`）
- 実行系
  - ExecutionEngine 起動スクリプト（`run_execution.py`）
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 専用 DB を利用
  - 監視ループ起動スクリプト（`run_monitoring.py`）
    - 定期的に System/Trade/Risk をチェックし、必要に応じて Kill Switch を発動
- 監視・アラート
  - system_status / trade_logs / risk_logs / dashboard 管理（`monitoring_db.py`）
  - リスク監視（ドローダウン・ポジション上限等）（`risk_monitor.py`）
  - Kill Switch（`kill_switch.py`）で data/kill.flag を書き込み ExecutionEngine 停止
  - MonitoringEngine（polling ループ）
- ポートフォリオ構築
  - 候補選定、等金額/スコア重み、リスク調整（セクター上限・レジーム乗数）、ポジションサイズ算出
- リサーチ
  - モメンタム／ボラティリティ／バリュー等のファクター計算（DuckDB を利用）
  - 将来リターン計算・IC（Information Coefficient）などの分析ユーティリティ
- AI（OpenAI）
  - ニュースの銘柄別センチメントスコア算出（`ai.news_nlp`）
  - マクロニュースと ETF の MA を合成したレジーム判定（`ai.regime_detector`）
- ツール
  - Paper Trading 検証レポート生成（`tools.paper_verification_report`）

---

## 前提 / 必要環境

- Python 3.10+（型記法（X | Y）等を使用）
- SQLite（標準ライブラリ）
- 以下の Python パッケージ（最低限）
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証を行う場合に必要）
- ネットワークアクセス（kabuステーション API / OpenAI / J-Quants を利用する場合）
- （任意）仮想環境の使用を推奨

必要パッケージ例（手動インストール）:
```
pip install duckdb psutil openai pyyaml
```

プロジェクトで requirements.txt があればそちらを使用してください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   ```
   pip install --upgrade pip
   pip install duckdb psutil openai pyyaml
   ```

4. 対話式で .env を作成（推奨）
   ```
   python -m kabusys.config_setup
   ```
   - J-Quants / kabu API / OpenAI キー等の必須値を入力してください。
   - 作成後、`python -m kabusys.validate_config` で検証します。

5. データディレクトリの準備（必要に応じて）
   - デフォルトでは `data/` 配下に DB やフラグファイルを作成します。自動作成されますが、権限に注意してください。
   - デフォルトパス:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db

---

## 使い方（主要コマンド）

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動
  - 本番/ペーパー切替は KABUSYS_ENV 環境変数で制御（`.env` で設定）
  - 起動コマンド:
    ```
    python -m kabusys.run_execution
    ```
  - 実行中は `data/execution.pid`（デフォルト）に PID を書き込みます。
  - 停止は `data/stop_requested.flag` ファイルを作成するか、ExecutionEngine 側の停止処理を呼ぶ形になります。

- 監視ループ起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）をオーバーライド可能（デフォルト 60 秒）。
  - 監視プロセスは `data/stop_requested.flag` を検知するとループを終了します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - オプション `--db` で DB パスを指定可能（デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- AI モジュール（プログラム的に呼び出す）
  - OpenAI API キーを環境変数 `OPENAI_API_KEY` に設定するか、関数引数で渡す必要があります。
  - 例（Python 内から）:
    ```py
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date, api_key="sk-...")
    ```

---

## 重要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード

- 運用関連
  - KABUSYS_ENV: 実行環境（development / paper_trading / live） デフォルト: development
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...） デフォルト: INFO
  - LOG_DIR: ログ保存先（`logs/` がデフォルト）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
  - SQLITE_PATH: 監視用 SQLite（デフォルト `data/monitoring.db`）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（`data/paper_trading.db`）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒） — run_monitoring で使用
  - PAPER_FILL_MODE: ペーパートレードの約定挙動（instant|partial|never|reject）

- 停止 / キルスイッチ
  - data/stop_requested.flag: run_execution / run_monitoring はこのファイルの有無を見て終了・停止
  - data/kill.flag: KillSwitch が検出した場合に書き込まれ、ExecutionEngine に停止指示を与える

---

## 停止・リカバリ

- 正常停止（監視側を止めたい場合）
  - プロセス内からは KeyboardInterrupt（Ctrl+C）で終了可能
  - 外部から監視・実行ループを止めるにはプロジェクトルートの `data/stop_requested.flag` を作成してください（両スクリプトが検知して安全に終了します）。

- Kill Switch
  - RiskMonitor 等が条件を満たすと `data/kill.flag` を書き込み、ExecutionEngine の即時停止トリガーになります。
  - 本番環境では `KILL_FLAG_CLEAR_ON_START=0` を推奨（自動クリアさせない）。

---

## ディレクトリ構成（主要ファイル）

（リポジトリルートに `src/kabusys` がある想定）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み・Settings クラス
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py : Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py : ニュースセンチメント算出（OpenAI）
    - regime_detector.py : 市場レジーム判定（OpenAI + MA）
  - monitoring/
    - monitoring_db.py : SQLite テーブル初期化・読み書きラッパ
    - system_monitor.py : システム状態・データ鮮度監視
    - trade_monitor.py : （注文関連監視、ソース内参照）
    - risk_monitor.py : ドローダウン・ポジション上限監視
    - kill_switch.py : kill.flag の生成
    - monitoring_engine.py : 複数モニタのポーリング統括
    - alert_manager.py : （アラート送信ロジック）
  - portfolio/
    - portfolio_builder.py : 候補選定・重み計算
    - position_sizing.py : 株数計算・scale down
    - risk_adjustment.py : セクター上限・レジーム乗数
  - research/
    - factor_research.py : ファクター計算（momentum/value/volatility）
    - feature_exploration.py : 将来リターン・IC・統計サマリー
  - utils/
    - logging_setup.py : ログ設定ユーティリティ
    - process_priority.py : プロセス優先度 / CPU affinity ユーティリティ
  - execution/ (発注関連コンポーネント、BrokerFactory 等)
  - data/ (実行時生成される: DB ファイル、pid/flag ファイル 等)

（注）上記は主要モジュールの抜粋です。実際のリポジトリではさらに細分化されたファイルが存在する可能性があります。

---

## サンプル .env（最小例）

こちらは例示です。実運用では必須値を正確に設定してください（.env を Git にコミットしないこと）。

```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
KILL_FLAG_CLEAR_ON_START=0
```

---

## 開発・拡張のヒント

- DuckDB はデータ解析用に用い、ファクター計算や AI 前処理に適しているため、prices_daily / raw_financials / raw_news 等のテーブル整備が重要です。
- AI 周りは OpenAI SDK を直接利用しているため、テスト時は `_call_openai_api` のパッチやモックを使うと良いです（news_nlp.py / regime_detector.py にその旨が記載されています）。
- run_execution は KABUSYS_ENV=paper_trading の場合、Paper DB（data/paper_trading.db）を使用し、本番 DB と分離する設計です。ペーパー検証の実行・解析に便利です。
- 監視・Kill Switch 周りは冪等性を重視して実装されています。運用時は `validate_config` を実行して設定ミスやパス権限を事前にチェックしてください。

---

この README はコードベースの主要機能と運用手順の要約です。さらに詳しい API 利用法や内部設計は各モジュールのドキュメント・関数コメントを参照してください。必要ならセクションの追記・具体例（設定例、起動スクリプトの systemd ユニット例 等）も作成しますので指示ください。