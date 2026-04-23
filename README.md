# KabuSys

日本株向け自動売買フレームワーク（参考実装）

このリポジトリは、注文実行エンジン、監視・アラート機構、ポートフォリオ構築・リスク制御、リサーチ（ファクター計算）、およびニュースNLP（OpenAI を使ったセンチメント評価）を含むモジュール群で構成されています。設計は本番環境とペーパートレード環境を分離し、運用時の安全装置（Kill Switch、リスクアラート）を備えています。

※ 本 README はソースコード（src/kabusys 以下）を元に作成しています。

---

## 主要機能

- Execution Engine
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアント抽象化（MockBroker を用いた検証可能なペーパー環境）
  - 発注・注文管理・約定ログの永続化
  - リスク管理（ポジション上限、最大利用率、ドローダウン等）

- Monitoring
  - システム指標（CPU / メモリ / ディスク）とプロセス生存チェック
  - 取引ログ監視（滞留注文、異常約定検出）
  - リスク監視（ドローダウン、ポジション数）
  - Kill Switch（条件に応じて data/kill.flag を作成し ExecutionEngine を停止）
  - 監視ループの起動スクリプト・DB永続化（SQLite）

- Portfolio Construction（純粋関数群・単体テストしやすい）
  - 候補抽出、等配分・スコア加重配分、セクター上限、ポジションサイズ計算（lot 単位丸め、資金スケーリング等）

- Research / Factor Calculation
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を用いて prices_daily/raw_financials を参照）
  - 将来リターン、IC（Spearman）や統計サマリー

- AI（OpenAI）
  - ニュースセンチメントスコアリング（news_nlp）
  - 市場レジーム判定（regime_detector）
  - いずれも API 呼び出しはフェイルセーフ設計（タイムアウト・リトライ・フォールバック）

- ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ロギングセットアップ（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

---

## セットアップ手順（開発・実行環境）

前提:
- Python 3.10 以上（型注釈や最新ライブラリ互換のため推奨）
- SQLite（標準で付属）
- DuckDB（Python パッケージ）

1. 仮想環境の作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージのインストール（最低限）
   ```bash
   pip install duckdb psutil openai
   ```
   - 追加で設定検証の YAML パーサを使う場合:
     ```bash
     pip install PyYAML
     ```
   - 実運用に合わせて他の依存が必要な場合があります（requirements.txt があればそちらを利用してください）。

3. 環境変数の準備
   - 対話式で .env を作る:
     ```bash
     python -m kabusys.config_setup
     ```
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数の一覧（抜粋）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
     - LOG_LEVEL: ログレベル（例: INFO）
     - OPENAI_API_KEY: OpenAI を使う場合必須

4. 設定検証（起動前に推奨）
   ```bash
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

---

## 使い方

主要な起動スクリプトと実行例。

- Execution Engine 起動
  - 本番/ペーパーは KABUSYS_ENV で切替（paper_trading なら paper 用 DB と MockBroker を使用）
  ```bash
  # 例: ペーパートレード環境で起動
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  - 実行中に data/stop_requested.flag を作成すると、起動済みエンジンが停止処理を受けます。
  - PID ファイル: data/execution.pid（設定により変更可）

- Monitoring 起動
  ```bash
  # ポーリング間隔を環境変数で上書き（秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 監視は本番 sqlite_path（KABUSYS_ENV にかかわらず）を参照します。
  - 監視中に data/stop_requested.flag を作成すると監視ループが終了します。
  - デフォルトポーリング間隔: 60 秒

- Paper Trading 検証レポート
  ```bash
  # デフォルト DB または明示的に --db を指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- AI 関連（プログラムから呼ぶ）
  - ニュースセンチメント集計:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key=...)
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key=...)

- .env ウィザード（初期設定）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証（必須項目・パス・YAML 解析のチェック）
  ```bash
  python -m kabusys.validate_config
  ```

---

## 主要設定（よく使う環境変数）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールを使う場合）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード時）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant/partial/never/reject）
- LOG_DIR / LOG_LEVEL: ログ出力先・レベル

---

## ログ / データファイルの既定

- ログ: logs/<app_name>.log（日次ローテーション、30日保持）
- 監視 DB: data/monitoring.db（SQLite）
- DuckDB: data/kabusys.duckdb
- ペーパートレード DB: data/paper_trading.db
- Kill / Stop フラグ:
  - data/kill.flag — Kill Switch（ExecutionEngine 停止要求）
  - data/stop_requested.flag — run_* スクリプトの停止要求フラグ
- PID ファイル: data/execution.pid（ExecutionEngine）

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/設定の読み込み・検証
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングスクリプト
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 取引ログ監視（存在）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の作成・クリア
    - monitoring_engine.py — 各モニタの統合ループ
    - alert_manager.py — アラート送信（LINE 等、実装参照）
  - execution/
    - execution_engine.py — 実行ロジック（EngineConfig など）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py 等
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算・資金配分
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum / volatility / value）
    - feature_exploration.py — IC / forward returns / 統計
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）
    - regime_detector.py — 市場レジーム判定（OpenAI + ma200）
  - utils/
    - logging_setup.py — 共通ログ設定
    - process_priority.py — プロセス優先度 / CPU affinity
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

---

## 運用上の注意 / 安全装置

- KABUSYS_ENV=live の場合は本番発注が行われます。設定（特に API キー・LINE 通知先・Kill Switch 設定）を十分確認してください。
- validate_config による事前チェックを必ず実行してください。
- Kill Switch（data/kill.flag）および stop_requested.flag を使った強制停止機構があります。起動時の自動クリア設定には注意（KILL_FLAG_CLEAR_ON_START）。
- OpenAI や外部 API 呼び出しはリトライとフォールバックを備えていますが、API 利用制限やコストに注意してください。

---

## 開発・拡張

- 多くのモジュールは「純粋関数」または I/O を分離した設計でテストしやすくなっています（例: portfolio / research）。
- DuckDB をデータソースとして使う設計のため、ローカルでデータを準備すればリサーチ機能を簡単に試せます。
- OpenAI 呼び出し部は単一のラッパー関数にまとめられており、テスト時はパッチ可能です（unittest.mock.patch）。

---

フィードバックや追加の説明が必要であれば、どの部分（起動フロー、環境変数、具体的な API 呼び出し方法、DB スキーマなど）を詳しく説明してほしいか教えてください。