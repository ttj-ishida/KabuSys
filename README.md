# KabuSys

日本株向け自動売買システムの軽量実装（ライブラリ + 起動スクリプト群）

Version: 0.1.0

---

## プロジェクト概要

KabuSys は、日本株の自動売買に関するコア機能群（シグナル計算、ポートフォリオ構築、ポジションサイジング、実行エンジン、監視、AI を使ったニュース解析など）を提供する Python のコードベースです。  
設計方針として、以下を重視しています。

- モジュールごとの責務分離（純粋関数で計算する研究モジュール、IO/DB 層の分離等）
- 本番 / ペーパートレードの明確な分離（DB を分ける）
- ロギング・監視・Kill Switch による安全運用（停止フラグファイル、アラート）
- OpenAI を用いたニュースセンチメント解析やレジーム判定のサポート（オプション）

---

## 主な機能一覧

- 環境設定ウィザード（`.env` の作成 / 更新）: `kabusys.config_setup`
- 設定検証 CLI（.env / config/*.yaml のチェック）: `kabusys.validate_config`
- 実行エンジン起動スクリプト（ExecutionEngine）: `run_execution.py`
  - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し、ペーパートレード専用 DB に記録
- 監視ループ起動スクリプト（SystemMonitor）: `run_monitoring.py`
  - システム状況・データ鮮度・リスク監視、Kill Switch の評価
- Monitoring DB 層（SQLite）: `monitoring.monitoring_db`（テーブル作成 / 永続化 API）
- Risk / Trade / System の各監視コンポーネント
- ポートフォリオ構築（候補選定、重み付け、単元丸め）: `portfolio/*`
- 研究（ファクター計算、前方リターン、IC 計算）: `research/*`
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定）: `ai/*`
- 運用ツール: ペーパートレード検証レポート生成スクリプト `tools.paper_verification_report`

---

## 必要要件（主な依存パッケージ）

基本的な組み合わせ（環境によって適宜インストールしてください）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能使用時)
- PyYAML（設定検証で YAML ファイルのパースを行う場合に有用）

例（pip）:
```
pip install duckdb psutil openai PyYAML
```

（プロジェクトに requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順（ローカル）

1. リポジトリをクローン / ソースを入手
2. Python 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb psutil openai PyYAML
   ```
4. 環境変数 `.env` を作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動でルートに `.env` を置く（.env.example を参照して作成）
5. 設定検証
   ```
   python -m kabusys.validate_config
   # 厳密モード（警告を FAIL 扱い）:
   python -m kabusys.validate_config --strict
   ```

---

## 主要な環境変数（重要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API（戦略/研究で使用）
- KABU_API_PASSWORD — kabuステーション API パスワード（実行時のブローカ接続で使用）

その他重要な環境変数:
- KABUSYS_ENV — 実行環境: `development` | `paper_trading` | `live`（デフォルト: `development`）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite（デフォルト: `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: `data/paper_trading.db`）
- LOG_LEVEL / LOG_DIR — ログレベル・ログディレクトリ
- OPENAI_API_KEY — OpenAI を使う機能で必要（ai.score_news / score_regime）

監視に関するオーバーライド:
- MONITOR_POLL_INTERVAL — SystemMonitor のポーリング間隔（秒、デフォルト 60）

Kill / Stop フラグ（ファイル）:
- data/kill.flag — Kill Switch が書き込む停止フラグ（ExecutionEngine に停止シグナル）
- data/stop_requested.flag — 手動停止要求用（起動スクリプトがこのファイルを検出して終了）

---

## 使い方（起動 / 実行例）

基本的にはモジュール実行形式で起動します。

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- 実行エンジン起動（ExecutionEngine）
  - 本番 / 開発 / ペーパートレードは KABUSYS_ENV によって制御
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - ペーパートレード時は `.env` に `KABUSYS_ENV=paper_trading` を設定すると MockBroker が使用され、`data/paper_trading.db` に記録されます。

- 監視ループ起動（SystemMonitor）
  ```
  # ポーリング間隔を 30 秒にしたい場合
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 監視はデフォルトで本番 sqlite_path を使用（環境にかかわらず監視 DB は共通）

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # データベースを指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（ライブラリ関数として利用）
  - ニューススコアリング:
    ```py
    import duckdb
    from kabusys.ai import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, target_date=date(2026,4,1), api_key="SK-...")
    ```
  - レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,1), api_key="SK-...")
    ```

注意: AI 機能使用時は OPENAI_API_KEY の設定または api_key 引数の指定が必須です。

---

## 運用上の注意

- Kill Switch / Stop フラグ:
  - 監視モジュールは各種条件（ドローダウン超過、ポジション上限など）で `data/kill.flag` を書き込み、ExecutionEngine が停止する仕組みです。手動停止を行う場合は `data/stop_requested.flag` を作成すると起動スクリプトが検出して安全に終了します。
- ログ:
  - デフォルトで `logs/` にアプリ別ログファイル（例: `logs/execution.log`）が日次ローテーションで保存されます。`LOG_DIR` 環境変数で変更可能。
- 本番注意:
  - `KABUSYS_ENV=live` は即時実取引を行うため、設定や API 認証情報・Kill Switch の挙動を十分に確認してから運用してください。
- DB マイグレーション:
  - `monitoring_db.init_monitoring_db` は既存 DB に対する簡易マイグレーション（カラム追加など）を行います。バックアップ推奨。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトの `src/kabusys` 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py                       — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py                 — .env 対話ウィザード
  - validate_config.py              — 設定検証 CLI
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py              — ロギング設定ユーティリティ
    - process_priority.py           — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py              — SQLite 用永続化 API（テーブル初期化含む）
    - system_monitor.py             — システム・データ鮮度監視
    - trade_monitor.py              — （トレード監視ロジック）
    - risk_monitor.py               — ドローダウン・ポジション上限監視
    - monitoring_engine.py          — 各 Monitor を束ねる
    - kill_switch.py                 — kill.flag の書き込みロジック
    - alert_manager.py              — （アラート送信：LINE 等／実装に依存）
  - execution/
    - execution_engine.py           — 実行エンジン本体（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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
    - news_nlp.py                    — ニュースセンチメント生成（OpenAI）
    - regime_detector.py             — レジーム判定（MA + マクロセンチメント）
    - __init__.py
  - tools/
    - paper_verification_report.py   — ペーパートレード検証レポート

（上記は主要ファイルの抜粋です。細部はソースツリーを参照してください）

---

## 開発者向けメモ / 拡張ポイント

- DuckDB を使った研究処理は SQL + Python の混成で実装されており、データ投入後に即座に活用できます。
- Portfolio / Position sizing のアルゴリズムは将来的に lot_size を銘柄ごとに差し替えられる設計に拡張可能（TODO 注記あり）。
- OpenAI 呼び出しはリトライ / バックオフやレスポンス検証を行っており、失敗時はフェイルセーフ（スコア 0 など）で継続する実装です。
- validate_config は PyYAML がない場合 YAML 検証をスキップします。CI では PyYAML を入れて厳密検証を推奨します。

---

## サンプル .env（最小）

.example（参考）
```
# 実行環境
KABUSYS_ENV=development

# 必須
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

# ログ
LOG_LEVEL=INFO
```

.env はセキュリティ上 Git にコミットしないでください（config_setup でも注意文を出力します）。

---

必要であれば、README をさらに詳細化（例：API の関数仕様や ExecutionEngine / Broker の接続設定例、CI 用手順、例外ハンドリング方針）できます。どの部分を深掘りしますか？