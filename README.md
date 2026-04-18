# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README（日本語）

概要・機能・セットアップ・使い方・ディレクトリ構成をまとめています。開発者向けに起動方法や重要な環境変数の取り扱いも記載します。

注意: .env ファイルには機密情報（API トークン・パスワード等）が含まれます。絶対に Git 等へコミットしないでください。

---

目次
- プロジェクト概要
- 主な機能
- 前提条件
- セットアップ手順
- 使い方（主要スクリプト）
- 環境変数（主要）
- 停止・Kill スイッチ
- ログ
- ディレクトリ構成（抜粋）
- 補足・運用上の注意

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたシステム群です。戦略・ポートフォリオ構築・注文実行・監視・リスク管理・研究（ファクター計算）・ニュース NLP（LLM を使ったセンチメント）などを含むモジュール化された実装が含まれます。

パッケージのトップレベル説明:
- パッケージ名: kabusys
- バージョン: 0.1.0（src/kabusys/__init__.py）

---

## 主な機能

- ExecutionEngine（発注エンジン）:
  - 実口座・ペーパートレード分離（KABUSYS_ENV=paper_trading 時は専用 DB / MockBroker を使用）
  - リスクマネージャ、注文マネージャ、リコンシリエーション等を組み合わせて発注処理を行う
- Monitoring（監視）:
  - システム資源（CPU/MEM/DISK）・プロセス死活・データ鮮度・注文滞留や約定異常等を監視
  - kill.flag 書き込みによる ExecutionEngine 停止トリガー
- Portfolio construction:
  - 候補選定、等比率／スコア加重、リスク調整（セクター制限、レジーム乗数）、ポジションサイズ決定
- Research:
  - DuckDB を用いたファクター計算（Momentum, Volatility, Value 等）や IC 計算、統計サマリー
- AI (LLM):
  - ニュース記事の銘柄ごとセンチメント評価（OpenAI API 使用）
  - 市場レジーム判定（ETF MA とマクロ記事の LLM 判定を合成）
- ユーティリティ:
  - 環境変数ウィザード（.env 生成）、設定検証 CLI、Paper Trading レポート生成ツール 等
- 永続化:
  - SQLite（監視 / ペーパートレード用）と DuckDB（分析用）

---

## 前提条件

- Python 3.9+（ソースは型アノテーション等を使用）
- pip でインストールする Python パッケージ:
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config 検証で YAML を検査する場合）
- ネットワーク接続（OpenAI API を使う機能を利用する場合）
- kabuステーション等の外部 API 設定（本番運用時）

package 要件ファイルはリポジトリに含まれていないため、開発環境では少なくとも上記パッケージをインストールしてください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンしてチェックアウト
   (例)
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して依存をインストール（上記参照）

3. .env ファイルの作成（ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   - 対話式で必要な環境変数を入力し .env を生成します。
   - 生成後は設定検証を行ってください:
     ```bash
     python -m kabusys.validate_config
     ```
     --strict を付けると警告も失敗扱いになります。

4. データディレクトリ初期化
   - デフォルトでは各種ファイルは `data/` 配下に作られます（SQLite、pid/flag 等）。
   - 必要に応じて `DUCKDB_PATH` / `SQLITE_PATH` を .env で変更してください。

---

## 使い方（主要スクリプト）

基本的な実行はモジュール形式で行います（プロジェクトルートで実行してください）。

- ExecutionEngine を起動
  - 本番・開発切り替えは KABUSYS_ENV で行います（development / paper_trading / live）
  - ペーパートレード時は paper 用 DB に記録され、本番 DB とは分離されます。
  ```bash
  python -m kabusys.run_execution
  ```

- Monitoring を起動（常駐ポーリング）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）
  ```bash
  python -m kabusys.run_monitoring
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 環境設定ウィザード（.env 生成／更新）
  ```bash
  python -m kabusys.config_setup
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  オプションで `--db PATH` により DB ファイルを明示指定できます。環境変数 `PAPER_TRADING_SQLITE_PATH` でも指定可能です。

- 研究・AI 用 API（ライブラリ呼び出し）
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
  - ファクター計算:
    from kabusys.research import calc_momentum, calc_volatility, calc_value

---

## 環境変数（主要）

config.py・validate_config.py・config_setup.py を参照した主要な環境変数:

必須（最低限設定）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主要任意／設定
- KABUSYS_ENV — 実行環境（development, paper_trading, live）。デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）、デフォルト: INFO
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI を使う機能で使用される API キー
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — (任意) アラート通知用 LINE 設定
- PAPER_FILL_MODE — ペーパートレードのフィルモード（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（1: 有効、0: 無効。デフォルト 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

.env は config_setup で作成できます。自動読み込みはデフォルトで有効（プロジェクトルートに .env がある場合）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 停止・Kill スイッチ

- グローバル停止（run_execution / run_monitoring の起動ループ両方が参照）
  - ファイル: data/stop_requested.flag
  - 存在すると監視ループ / 実行エンジンは安全にシャットダウンします。

- Kill Switch（リスク発動による ExecutionEngine 停止）
  - KillSwitch モジュールが条件を満たすと `data/kill.flag` を作成します（Settings.kill_flag_path で上書き可）。
  - ExecutionEngine は起動時に `KILL_FLAG_CLEAR_ON_START` の設定に応じてこのフラグをクリアすることがあります（安全運用では 0 を推奨）。
  - kill.flag は作成済みなら再書き込みしません（冪等）。

---

## ログ

- logging_setup モジュールで統一的に設定されます（setup_logging）。
- デフォルト: stdout（StreamHandler） + 日次ローテーションされたファイル（logs/<app>.log）
- ログディレクトリは LOG_DIR 環境変数またはデフォルト `logs/` を使用します。
- 例: run_execution は `logs/execution.log` を使用します。

---

## ディレクトリ構成（抜粋）

（src/kabusys 配下の主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み／Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py     — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py      — システムリソース・データ鮮度監視
    - trade_monitor.py       — （注: trade_monitor 実装ファイルあり）※リポジトリ全体参照
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       —（通知管理）
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/ (プロジェクトルート)
    - monitoring.db (デフォルト)
    - paper_trading.db (ペーパートレード)
    - kill.flag / stop_requested.flag / execution.pid など

（実際のファイル一覧はリポジトリ全体を参照してください）

---

## 補足・運用上の注意

- 本番運用（KABUSYS_ENV=live）時は特に環境変数の検証とバックアップを徹底してください。validate_config の警告は無視しないでください。
- .env を絶対にリポジトリへコミットしないでください（README ヘッダにも注意喚起あり）。
- OpenAI API 利用部分は API キーの課金・レート制限に注意してください。リトライ処理やクリップ等の耐障害設計は組み込まれていますが、運用監視は必須です。
- run_monitoring は MONITOR_POLL_INTERVAL により間隔を変えられますが、小さく設定しすぎると負荷やログ膨張の原因になります。
- ペーパートレード（paper_trading）は実アカウントと DB を完全に分離する設計です。切り替えは KABUSYS_ENV を用いて行ってください。
- ログディレクトリやデータディレクトリの権限、ディスク容量なども監視対象に含めてください（monitoring がディスク使用率を監視します）。

---

必要に応じて README を拡張します（例: API ドキュメント、実運用のデプロイ手順、コンテナ化例、テストの書き方など）。ほしい追加情報があれば教えてください。