# KabuSys

日本株向け自動売買システム（リサーチ・ポートフォリオ構築・発注・監視・AI 補助）  
このリポジトリは、戦略リサーチ、ポートフォリオ構築、発注エンジン、監視/アラート、ニュース NLP（OpenAI 利用）などのコンポーネントを含む統合システムです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローを構成するモジュール群です。主な目的は以下です。

- ファクター計算・特徴量探索によるシグナル生成（research）
- 候補選定・配分・株数決定（portfolio）
- 発注エンジン（ExecutionEngine）とブローカー抽象（execution）
- 監視（System / Trade / Risk）、Kill Switch による安全停止（monitoring）
- 新聞記事を用いた LLM ベースのセンチメント評価（ai.news_nlp）と市場レジーム判定（ai.regime_detector）
- ペーパートレード用検証レポート生成ツール（tools）

設計方針の一部:
- DuckDB / SQLite によるローカルデータ運用
- 環境依存設定は .env で管理
- OpenAI API 呼び出しはフェイルセーフ実装（リトライ・フォールバック）
- 本番とペーパートレードを分離（DB・モッククライアント等）

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、ペーパートレード用 DB に記録
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - システム資源・データ鮮度・滞留注文・ドローダウンの検出
  - Kill Switch（data/kill.flag）で ExecutionEngine を安全に停止
  - アラート通知フック（LINE 等の設定を通して利用可能）
- ポートフォリオ構築:
  - 候補選定（score / rank）
  - 重み計算（等金額・スコア加重）
  - ポジションサイズ計算（リスクベース、ロット丸め、aggregate cap）
  - セクター集中制限・レジーム乗数
- Research:
  - ファクター計算（Momentum, Volatility, Value 等）
  - 将来リターン計算、IC（スピアマンランク相関）、統計サマリー
- AI:
  - ニュース NLP による銘柄別センチメント（OpenAI を利用）
  - マクロニュース + ETF MA を用いた市場レジーム判定
- ツール:
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順

※ Python 3.10 以上を推奨します（型注釈の記法等に依存）。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .\.venv\Scripts\activate    # Windows（PowerShell/CMD）
   ```

3. 必要パッケージをインストール
   （requirements.txt が無い場合は以下をインストール）
   ```
   pip install duckdb psutil openai
   # オプション
   pip install PyYAML
   ```
   - duckdb: 分析用 DB
   - psutil: プロセス優先度・リソース計測
   - openai: ニュース NLP / レジーム判定で利用
   - PyYAML: config 検証時の YAML パース（無くても検証は一部スキップされます）

4. 初期設定（.env）
   - 対話式ウィザードで .env を作成:
     ```
     python -m kabusys.config_setup
     ```
   - 作成後、設定を検証:
     ```
     python -m kabusys.validate_config
     # 警告も FAIL にしたい場合
     python -m kabusys.validate_config --strict
     ```

5. データディレクトリの確認
   - デフォルト DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
   - ログ: logs/ ディレクトリが作成され、日次ローテーションでログが出力されます。

---

## 使い方

以下は主要スクリプト／機能の実行例です。

1. ExecutionEngine（発注エンジン）起動
   - デフォルト（.env の KABUSYS_ENV に従う）:
     ```
     python -m kabusys.run_execution
     ```
   - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、ペーパートレード用 DB に記録されます。
   - Engine は data/execution.pid を生成・管理し、停止は data/stop_requested.flag あるいは data/kill.flag によって制御されます。

2. Monitoring 起動
   - デフォルトポーリング間隔 60 秒（環境変数で変更可）
     ```
     MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
     ```
   - 停止はプロジェクトルート/data/stop_requested.flag を作成することで制御します。
   - Monitoring は監視ログを SQLite（settings.sqlite_path）に書き込みます。

3. Paper Trading 検証レポート
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   # DB を明示する場合:
   python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
   ```

4. AI（ニュース NLP / レジーム判定）
   - OpenAI API キーを .env または環境変数に設定してください: OPENAI_API_KEY
   - プログラムから呼ぶ場合の例:
     ```py
     import duckdb
     from kabusys.ai.news_nlp import score_news
     conn = duckdb.connect("data/kabusys.duckdb")
     # target_date は datetime.date オブジェクト
     count = score_news(conn, target_date, api_key=None)  # api_key None の場合 OPENAI_API_KEY を参照
     ```
   - regime_detector も同様に `score_regime(conn, target_date)` を呼び出して market_regime テーブルへ書き込みます。

5. その他ユーティリティ
   - 設定ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - 設定検証:
     ```
     python -m kabusys.validate_config
     ```

---

## 主要環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API 用

重要（デフォルトあり・任意で上書き）:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY — OpenAI 利用時に必要
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）※ run_monitoring 用

その他:
- PAPER_FILL_MODE — ペーパートレード時のフィル挙動（instant/partial/never/reject）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

詳しくは `kabusys.config.Settings` のプロパティ説明を参照してください。

---

## ディレクトリ構成（主要ファイル・モジュール）

（src/kabusys 以下の主要ファイルを抜粋）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py       — 統一ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py      — システム・データ鮮度チェック
    - trade_monitor.py       — （注文滞留や約定異常などの検出）※詳細は実装参照
    - risk_monitor.py        — ドローダウン / ポジション制限監視
    - kill_switch.py         — data/kill.flag 書き込みユーティリティ
    - monitoring_engine.py   — 各モニタを束ねるループ
    - alert_manager.py       — （LINE などへの通知ラッパー）※実装参照
  - execution/
    - execution_engine.py    — ExecutionEngine（注文実行ループ）※実装参照
    - broker_factory.py      — ブローカークライアント生成（本番 / モック）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注関連
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 発注株数計算（ロット丸め・aggregate cap）
    - risk_adjustment.py     — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py     — Momentum / Volatility / Value などのファクター
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）で銘柄別センチメント
    - regime_detector.py     — マクロ + ETF MA による市場レジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール

付属:
- data/                     — デフォルト DB / PID / flag を置く場所（実行時に生成）
  - monitoring.db
  - paper_trading.db
  - kabusys.duckdb
  - execution.pid
  - kill.flag / stop_requested.flag
- logs/                     — ログファイル（日次ローテーション）

---

## 運用上の注意

- KABUSYS_ENV を `live` に設定すると本番運用になります。Kill Switch / 通知設定（LINE）などを十分確認してください。
- .env は絶対にバージョン管理にコミットしないでください。
- OpenAI 利用部分は API キーとコストの管理が必要です。API 呼び出しはリトライやフォールバックを実装していますが、費用が発生します。
- ペーパートレード時はデータベースが本番 DB とは分離されます（PAPER_TRADING_SQLITE_PATH を確認）。
- ログディレクトリに書き込み権限がない場合、ファイル出力は無効化されコンソール出力のみになります。

---

## 開発・拡張ポイント（参考）

- strategy や execution コンポーネントは拡張可能。BrokerClientFactory を実装すれば新しいブローカーへ接続できます。
- portfolio/position_sizing は lot_size の銘柄別対応や手数料モデルを取り込む拡張が想定されています。
- research モジュールは DuckDB に投入される prices_daily / raw_financials に依存します。ETL パイプラインを整備してください。
- monitoring のアラート先（LINE 等）は AlertManager 経由で追加できます。

---

もし README に追加したい情報（インストール用 requirements.txt、CI 実行方法、より詳細なアーキテクチャ図など）があれば教えてください。必要に応じて追記します。