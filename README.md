# KabuSys — 日本株自動売買システム

このリポジトリは日本株自動売買システム KabuSys のコアライブラリと起動スクリプト群を含みます。本 README はプロジェクト概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

注意: ここに記載のコマンドはリポジトリを Python パッケージとしてインポートできる状態（例: 開発環境では `src` を PYTHONPATH に含めるか pip の editable インストール）を前提とします。簡単にはリポジトリ直下で `python -m kabusys.<module>` で実行できます。

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームです。戦略の研究・検証（DuckDB を用いたファクター計算）、ポートフォリオ構築、発注エンジン（ExecutionEngine）、システム監視・アラート、ペーパートレード環境、LLM を用いたニュースセンチメント解析など、アルゴリズム運用に必要な機能を備えています。

設計の特徴:
- DuckDB を分析用 DB、SQLite を監視／トレードログ用に利用
- 本番 / ペーパートレードを環境変数 `KABUSYS_ENV` で切替
- OpenAI を利用したニュース NLP / レジーム判定モジュール（フェイルセーフ設計）
- モジュールはできるだけ純粋関数・副作用を限定してテスト容易性を確保

## 主な機能一覧

- 設定管理
  - .env / 環境変数の自動読み込み（`kabusys.config`）
  - 対話式 .env 作成ウィザード（`kabusys.config_setup`）
  - 設定検証ツール（`kabusys.validate_config`）

- 実行系（Execution）
  - ExecutionEngine 起動スクリプト（`run_execution.py`）
  - Paper Trading 用の MockBroker をサポート（`KABUSYS_ENV=paper_trading` 時）
  - 発注ログ・状態を SQLite に記録

- 監視（Monitoring）
  - System / Trade / Risk の各種モニタと監視エンジン（`monitoring` パッケージ）
  - Polling スクリプト（`run_monitoring.py`）
  - Kill Switch（条件を満たすと `data/kill.flag` にフラグ書込して Execution を停止）
  - 監視 DB の永続化層（`monitoring_db`）

- ポートフォリオ構築
  - 候補銘柄選定、等重・スコア加重、ポジションサイズ計算、セクター制約、レジーム乗数

- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ等

- AI（OpenAI）
  - ニュースセンチメント解析（`ai.news_nlp`）
  - 市場レジーム判定（`ai.regime_detector`）
  - OpenAI API のエラーに対するリトライ・フォールバック実装

- ツール
  - ペーパートレード検証レポート生成（`kabusys.tools.paper_verification_report`）

## 前提・依存

推奨 Python バージョン: 3.10+

主な外部ライブラリ（例）:
- duckdb
- psutil
- openai
- PyYAML（config YAML の検証を行いたい場合）
- （標準ライブラリの sqlite3 等は不要なインストール）

インストール例:
```
pip install duckdb psutil openai PyYAML
```

（要件は運用環境に応じて requirements.txt を作成して管理してください）

## セットアップ手順

1. リポジトリをクローン / チェックアウト
2. Python 仮想環境を準備し、依存をインストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb psutil openai PyYAML
   ```
3. 初期 .env を作成（対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   - .env に J-Quants トークン、kabuステーション API パスワード、必要な DB パス等を設定します。
   - `KABUSYS_ENV` は `development` / `paper_trading` / `live` のいずれか。

4. 設定検証（任意だが推奨）
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告も失敗扱いで exit code 1 にする

5. データ・ログ用ディレクトリ作成（通常は自動作成されますが確認）
   - data/ （PID/フラグ、SQLite DB 等）
   - logs/ （ログファイル）

6. OpenAI を使う機能を利用する場合は環境変数 `OPENAI_API_KEY` を設定

## 使い方（主要スクリプト）

- 実行エンジン（ExecutionEngine）起動
  - 本番 / ペーパートレードは KABUSYS_ENV に依存
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - Paper トレードで起動する例:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 挙動:
    - プロセス優先度を high に設定
    - Paper 環境なら専用 SQLite（デフォルト: data/paper_trading.db）を使用し MockBrokerClient による記録
    - 起動時に data/stop_requested.flag が既にあると起動をキャンセル

- 監視ポーリング起動
  - ポーリング開始:
    ```
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔を環境変数で変更:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
    デフォルト: 60 秒。0 以下や不正値は 60 秒にフォールバック。
  - 挙動:
    - SystemMonitor / TradeMonitor / RiskMonitor を定期実行
    - 監視は常に本番用 sqlite_path を利用（環境によらず）
    - data/stop_requested.flag を作成するとループを終了

- Kill Switch（監視から Execution 停止シグナル）
  - 条件（例: ドローダウン or ポジション上限）が満たされると `data/kill.flag` を書き込み
  - ExecutionEngine 側は `Settings.kill_flag_path` を見て停止を受け入れる
  - 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると kill flag を自動クリア（本番では 0 推奨）

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` で SQLite パスを明示するか、環境変数 `PAPER_TRADING_SQLITE_PATH` を使う（デフォルト: data/paper_trading.db）
  - 稼働率、注文成功率、P95 レイテンシ等を計算して PASS/FAIL 判定を出力

- AI モジュール（ニュース NLP / レジーム判定）
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OpenAI API キーを `OPENAI_API_KEY` または引数で指定
  - 失敗時のフォールバック（スコア 0.0 等）が組み込まれており、API エラーでプロセス全体が停止しない設計

- 設定自動ロードの制御
  - デフォルトでプロジェクトルートの `.env` と `.env.local` を自動で読み込みます
  - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

## 主な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 sqlite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/...）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（0/1）

## プロセス制御・フラグファイル

- data/stop_requested.flag: run_monitoring / run_execution の外部停止用（存在を監視して処理を終了）
- data/kill.flag: KillSwitch が書き込む停止シグナル（ExecutionEngine による受信で停止）
- data/execution.pid: ExecutionEngine が PID を書き込む可能性あり

これらのパスは Settings でカスタマイズ可能です。

## ディレクトリ構成（抜粋）

以下はリポジトリ内の主要ファイルとディレクトリの説明です（src/kabusys 配下）。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env 自動ロード / Settings クラス
  - config_setup.py
    - 対話式 .env 作成ウィザード
  - validate_config.py
    - 設定検証 CLI（.env と config/*.yaml のチェック）
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングスクリプト
  - monitoring/
    - monitoring_db.py
      - SQLite ベースの監視 DB 初期化・操作クラス（MonitoringDB）
    - system_monitor.py
      - システム状態・データ鮮度監視（SystemMonitor）
    - trade_monitor.py
      - 発注ログ監視（TradeMonitor）※コードベースに含まれている想定
    - risk_monitor.py
      - ドローダウン・ポジション上限監視（RiskMonitor）
    - kill_switch.py
      - kill.flag の作成・評価（KillSwitch）
    - monitoring_engine.py
      - 各 Monitor を束ねる MonitoringEngine
    - alert_manager.py
      - アラート通知の取りまとめ（LINE 等）※実装が存在する前提
  - execution/
    - execution_engine.py
      - ExecutionEngine のコア（EngineConfig, run_session 等）
    - broker_factory.py
      - 実 / モック BrokerClient の生成（環境に応じて切替）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py
      - 発注管理・リポジトリ・リスク制御
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
      - ニュースの LLM ベースセンチメント解析
    - regime_detector.py
      - マクロ + ETF MA を合成したレジーム判定
  - tools/
    - paper_verification_report.py
      - ペーパートレードの指標集計・レポート生成
  - utils/
    - logging_setup.py
      - 統一的なログ設定ユーティリティ
    - process_priority.py
      - プロセス優先度設定（Windows / POSIX 対応）
    - その他ユーティリティ

※実際のリポジトリではさらに細分化されたファイルや追加モジュールがあります。上は主要な構成の概要です。

## 運用上の注意点

- 本番環境で `KABUSYS_ENV=live` を設定する場合は `.env` の値（特に API パスワードや通知設定）を慎重に確認してください。`validate_config` は本番向けの追加チェックを行います。
- `KILL_FLAG_CLEAR_ON_START=1` は本番では危険です（kill flag が自動クリアされるため）。本番では `0` を推奨します。
- OpenAI を利用する機能は API 呼び出しに費用が発生します。利用ポリシーとコストを確認してください。
- ログディレクトリが作成できない場合、ファイル出力をスキップしてコンソールのみで動作します（`kabusys.utils.logging_setup` の挙動）。

## さらなる開発・拡張

- strategy（シグナル生成）や execution の細部は本 README に全て網羅していません。各モジュールの docstring と実装を参照してください。
- テスト・CI を整備すると安全に本番デプロイできます。モジュールは純粋関数を多用しているためユニットテストを書きやすい設計です。
- DuckDB のスキーマ（prices_daily, raw_financials 等）に合わせた ETL パイプラインを用意すると研究・運用がスムーズになります。

---

必要であれば、README に含める環境変数のサンプル .env.example、systemd / service ファイルの起動例、デプロイ手順（Dockerfile / docker-compose）や運用チェックリスト（アラート閾値の推奨値）などを追加で作成します。どの内容を優先して追加しますか？