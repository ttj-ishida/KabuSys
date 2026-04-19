# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買・研究・監視プラットフォームです。  
ExecutionEngine（発注エンジン）、Monitoring（監視・Kill Switch）、ポートフォリオ構成・ポジションサイジング、リサーチ（ファクター計算）や AI（ニュース NLP / レジーム判定）などのコンポーネントを含みます。

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（起動・コマンド例）
- 主要環境変数（.env）
- ディレクトリ構成
- 補足・トラブルシューティング

---

## プロジェクト概要

- 自動売買の実行基盤（ExecutionEngine）
- 実行状態・データ鮮度・リスク指標の監視（Monitoring）
- ポートフォリオ構築・配分（等重/スコア重み/リスクベース）
- ポジションサイジング（単元丸め、集約キャップ）
- ファクター計算・特徴量探索（DuckDB を使用）
- ニュースの LLM（OpenAI）を用いたセンチメントスコアリングと市場レジーム判定
- ペーパートレード用の分離 DB と MockBroker サポート
- 各種ツール（検証レポート、設定ウィザード、設定検証）

---

## 主な機能一覧

- Execution
  - ExecutionEngine を起動して発注処理を行う。KABUSYS_ENV により paper_trading / live / development の挙動を切り替え。
  - paper_trading 時は MockBrokerClient を使用し、paper_trading 専用 DB に記録（本番 DB と分離）。
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングし、system_status / trade_logs / risk_logs / dashboard などに永続化。
  - Kill Switch: ドローダウンやポジション上限に達した際に data/kill.flag を書き込み ExecutionEngine を停止させる仕組み。
  - AlertManager 経由で通知（LINE等の設定を行えば通知可能）。
- Portfolio
  - 候補選定、等重点配分・スコア加重配分、リスク調整（セクター制限）、ポジションサイズ計算。
- Research
  - DuckDB 上の prices_daily / raw_financials などを参照してモメンタム／ボラティリティ／バリュー等のファクター計算。
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ。
- AI
  - news_nlp: raw_news を OpenAI に投げて銘柄別センチメントを ai_scores テーブルに保存（batch 処理・リトライ・バリデーション含む）。
  - regime_detector: ETF (1321) の MA200 とマクロニュースの LLM スコアを合成して日次の market_regime を算出・永続化。
- ユーティリティ
  - logging 設定（コンソール + 日次ローテーションファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - .env 対話式設定ウィザード・設定検証 CLI
- ツール
  - Paper Trading 検証レポート生成スクリプト（paper_verification_report）

---

## セットアップ手順（開発用）

以下は一般的なセットアップ手順の例です。プロジェクトの要件に応じて適宜調整してください。

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repo>
   ```

2. Python 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要な依存パッケージをインストール  
   （requirements.txt があればそれを使用。なければ少なくとも以下が必要です）
   - duckdb
   - psutil
   - openai
   - pyyaml（config 検証で使用）
   ```
   pip install duckdb psutil openai pyyaml
   ```

4. .env の作成（ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードに従って J-Quants / kabu API などの設定を行い `.env` を生成します。

5. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリなどの準備
   - デフォルトでは `data/` に SQLite / DuckDB ファイルを置きます。必要なら環境変数でパスを上書きしてください。
   - `logs/` ディレクトリはログ出力用に自動作成されますが、権限を確認してください。

---

## 主要な環境変数（.env）

自動ロード: プロジェクトルート（.git または pyproject.toml がある場所）にある `.env` / `.env.local` は起動時に自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

重要なオプション（一部）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）  
  Monitoring は環境にかかわらず本番 sqlite_path を使用します（paper_trading でも監視 DB は別扱い）。
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading 時の約定挙動: instant | partial | never | reject（デフォルト: instant）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ出力先（デフォルト: logs）
- PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch のフラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1。production では 0 推奨）
- OPENAI_API_KEY — OpenAI を用いる機能で必要（news_nlp / regime_detector）

簡単な .env の例（ウィザードで生成できます）
```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

---

## 使い方（起動・コマンド例）

エントリポイントはモジュール実行です。プロジェクトルートで実行してください（.env 自動ロードのため）。

- 設定ウィザード（.env 作成・更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動時に data/stop_requested.flag があると起動を行わず終了します。
  - 実行中は data/execution.pid に PID が書き込まれます。停止は kill.flag / stop flag を利用します。

- Monitoring 起動（監視ループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で秒数を上書きできます（例: MONITOR_POLL_INTERVAL=30）。
  - Monitoring は KABUSYS_ENV にかかわらず production の sqlite_path を使用します（監視ログは共通 DB）。
  - 停止はプロジェクトルート/data/stop_requested.flag を作成すると検知してループを終了します。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または `--db` オプションで指定。

- AI モジュール（Python スクリプト/REPL から使用）
  - ニュース NLP スコアリング
    ```py
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    # target_date を指定してスコアを付与（例: date(2026,4,10)）
    count = score_news(conn, target_date, api_key="sk-...")
    ```
  - レジーム判定
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="sk-...")
    ```

備考:
- OpenAI を利用する機能は OPENAI_API_KEY または関数引数で API キーを渡してください。
- Monitoring の各種アラートは AlertManager を経由して通知されます（LINE 設定があれば通知可能）。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要なモジュール構成（src/kabusys）です。実際のツリーはプロジェクトで管理されます。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込み / Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）による銘柄スコアリング
    - regime_detector.py     — マクロ + MA200 による市場レジーム判定
  - monitoring/
    - monitoring_db.py       — SQLite を使った監視ログ永続化層
    - system_monitor.py      — システム状態・データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション上限チェック
    - trade_monitor.py       — 発注ログ監視（存在）
    - monitoring_engine.py   — Monitor 統合・ポーリングループ
    - kill_switch.py         — Kill Switch ロジック（kill.flag 制御）
    - alert_manager.py       — アラート送信ロジック（存在）
  - execution/               — Execution 関連（Engine, OrderManager, BrokerFactory 等）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定・資金配分
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - utils/
    - logging_setup.py       — 統一的なログ設定（console + 日次ローテーション）
    - process_priority.py    — プロセス優先度 / CPU affinity 設定

プロジェクトルートにある想定フォルダ/ファイル
- data/                      — SQLite / PID / フラグファイル 等（自動作成される）
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - execution.pid
  - kill.flag
  - stop_requested.flag
- logs/                      — ログファイル（例: logs/execution.log, logs/monitoring.log）
- config/                    — YAML テンプレート（system_config.yaml 等）

---

## 補足・トラブルシューティング

- モジュールが動作しない/インポートエラーが出る場合は依存ライブラリ（duckdb, psutil, openai, pyyaml 等）がインストールされているか確認してください。
- process_priority.set_process_priority は OS の権限に依存します。権限不足で WARNING が出る場合がありますが、フェールオープンで続行します。
- Monitoring は監視用 DB に永続化します。誤って kill.flag を置かないように注意してください（KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアしますが、本番では 0 推奨）。
- DuckDB の接続を複数スレッドで使う際は使用方法に注意してください（モジュール内での使用パターンに従ってください）。
- OpenAI API のエラー（429 等）は内部でリトライ処理が組み込まれていますが、API レートやキーの使用状況は注視してください。

---

必要であれば、README の実行コマンド部分を環境変数の具体例や systemd / docker でのデプロイ例に合わせて追記できます。どの形式（ローカル起動 / docker / systemd）の説明が欲しいか教えてください。