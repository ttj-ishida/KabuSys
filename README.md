# KabuSys

日本株向け自動売買システムのパッケージ（ライブラリ／実行スクリプト群）。

このリポジトリは、シグナル生成・ポートフォリオ構築・注文実行・監視・研究用ユーティリティを含むモジュール群を整理しています。  
本 README はプロジェクト概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下の役割をもつモジュール群から成る日本株自動売買システムです。

- データ解析・リサーチ（DuckDB を用いたファクター計算、特徴量解析）
- ポートフォリオ構築（候補選定、重み算出、リスク調整、株数決定）
- 実行エンジン（注文作成・ブローカークライアント経由で発注。ペーパートレード対応）
- 監視（システム状態、注文状況、リスク監視、Kill Switch）
- AI 補助（ニュース NLP によるセンチメント評価、レジーム検出）
- ツール群（ペーパートレード検証レポート等）
- 設定管理（.env のウィザード、検証 CLI）

設計上の特徴:
- 環境変数ベース設定（`.env` 自動読み込み対応）
- 本番 DB とペーパートレード DB の分離
- DuckDB を使った分析・リサーチ
- OpenAI（gpt-4o-mini）を用いる AI モジュール（API キー必要）
- 監視は SQLite に記録し、必要に応じて kill.flag を書いて実行エンジン停止を促す

---

## 主な機能一覧

- 設定管理
  - 対話式ウィザード: `kabusys.config_setup`
  - 構成検証 CLI: `kabusys.validate_config`
- 実行
  - ExecutionEngine 起動スクリプト: `kabusys.run_execution`
  - Paper trading をサポート（KABUSYS_ENV=paper_trading）
- 監視
  - SystemMonitor 起動スクリプト: `kabusys.run_monitoring`
  - 監視用 DB（SQLite）へのログ記録（system_status, trade_logs, risk_logs, positions, dashboard）
  - Kill Switch（drawdown やポジション上限で kill.flag を生成）
- ポートフォリオ
  - 候補選定、等金額/スコア重み、ポジションサイズ計算、セクターキャップ、レジーム乗数
- 研究（research）
  - モメンタム／ボラティリティ／バリュー等のファクター計算
  - 将来リターン計算、IC（情報係数）計算、統計サマリー
- AI
  - ニュース NLP による銘柄別センチメント（`kabusys.ai.news_nlp`）
  - レジーム判定（`kabusys.ai.regime_detector`）
- ツール
  - Paper Trading 検証レポート生成: `kabusys.tools.paper_verification_report`

---

## 必要要件（依存パッケージ）

主に以下が必要です（バージョンは使用環境で調整してください）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config 検証で YAML 構文チェックを行う場合）

例（venv を作ってインストール）:
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# requirements.txt がない場合:
pip install duckdb psutil openai pyyaml
```

（requirements.txt がなければ上記個別インストールを参照してください）

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード

よく使う（省略時はデフォルトあり）:
- KABUSYS_ENV (development | paper_trading | live) — 実行環境（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時に使用、デフォルト: data/paper_trading.db）
- LOG_LEVEL — (DEBUG|INFO|WARNING|ERROR|CRITICAL)（デフォルト: INFO）
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使用する場合）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（1=yes。production では 0 推奨）

推奨: `.env` をプロジェクトルートに作成して管理（絶対に Git にコミットしないでください）。

.config_setup で対話的に `.env` を作成できます。

---

## セットアップ手順（ローカルでの簡易手順）

1. リポジトリをクローンして作業ディレクトリへ移動
2. Python 仮想環境を作成し有効化
3. 依存パッケージをインストール（上記参照）
4. `.env` を作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動で `.env` を用意（以下は最小例）:
     ```
     JQUANTS_REFRESH_TOKEN=your_token
     KABU_API_PASSWORD=your_kabu_password
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     ```
5. 設定検証（任意）:
   ```
   python -m kabusys.validate_config
   ```
   `--strict` を付けると警告もエラー扱いになります:
   ```
   python -m kabusys.validate_config --strict
   ```
6. DB ディレクトリ（data）やログディレクトリを作成（多くのスクリプトが自動作成しますが、権限に注意）:
   ```
   mkdir -p data logs
   ```

---

## 使い方（主要スクリプト）

- Execution（発注エンジン）起動:
  - 本番または開発に合わせて KABUSYS_ENV を設定してください。
  - Paper trading の場合、環境変数 KABUSYS_ENV=paper_trading をセットすると、MockBrokerClient を使用しペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  ```
  python -m kabusys.run_execution
  ```
  実装上、起動時に data/stop_requested.flag が存在すると起動を中止します。エンジンは data/execution.pid を生成します。

- Monitoring（監視ループ）起動:
  - MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（デフォルト 60 秒）。
  - 実行例:
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```
  監視は常に本番 sqlite_path を使用（環境に依らず監視 DB は本番 DB を想定）。停止させるにはプロジェクトルートの data/stop_requested.flag を作成します。

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- 環境設定ウィザード（.env 作成）:
  ```
  python -m kabusys.config_setup
  ```

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間を指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # 別 DB を指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI / Research モジュールはプログラム的に利用:
  - OpenAI を使う機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要です。例:
    ```py
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    from datetime import date
    score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```
  - research モジュールは DuckDB 接続を受け取り純粋関数的に動作します。

注意点:
- run_monitoring/run_execution は stop フラグ（data/stop_requested.flag）や kill.flag（監視の Kill Switch による data/kill.flag）を扱います。運用時はこれらのファイルの取り扱いに注意してください。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリに書き込み権限が必要です。

---

## ディレクトリ構成

主要なファイル／パッケージ（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック（.env 自動読み込み）
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
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
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py    (※コードベースに存在)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py    (※コードベースに存在)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py

（上記は主要ファイルの概略。詳細は各モジュールの docstring を参照してください）

---

## 運用メモ / 実装上の注意

- 本番運用時は必ず `KABUSYS_ENV=live` を意図的に設定し、LINE 通知等の設定を確認してください。validate_config によるチェックを推奨します。
- .env は機密情報を含むため、絶対にバージョン管理に含めないでください。
- ペーパートレードは production DB と分離されます（PAPER_TRADING_SQLITE_PATH）。ペーパートレードの約定挙動は PAPER_FILL_MODE で制御できます。
- AI 機能は外部 API（OpenAI）に依存します。API キーとレート制限を考慮してください。API 失敗はフェイルセーフでスコア 0.0 やスキップとする実装になっていますが、運用時の挙動は確認してください。
- ロギングは `kabusys.utils.logging_setup.setup_logging` を通じて統一されています。ログディレクトリの作成に失敗した場合、コンソール出力のみになります。

---

## 開発者向け情報 / テスト

- モジュールは比較的純粋関数的に設計されている箇所が多く、ユニットテストが書きやすい構造です（research / portfolio 等）。
- 外部依存（OpenAI 呼び出し、psutil、DB）についてはモック可能なように内部呼出しを切り分けています（例: news_nlp._call_openai_api をテストでパッチ）。
- DuckDB/SQLite を使った統合テストを用意するとリサーチ・監視機能の検証が容易です。

---

README は以上です。  
追加で、特定の機能（例: ExecutionEngine の起動パラメータや OrderManager の使い方、monitoring の詳細アラート設定）について詳しくまとめる必要があれば、どの項目を拡張するか教えてください。