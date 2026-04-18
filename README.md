# KabuSys

日本株自動売買システムのコードベース（簡易ドキュメント）。  
ここではプロジェクトの概要、主要機能、セットアップ手順、利用方法、ディレクトリ構成を記載します。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を行うシステムです。  
主な要素は以下です。

- エンジン（ExecutionEngine）: 発注・リスク管理・注文管理を行う実行コンポーネント
- 監視（Monitoring）: システム状態、注文、リスクをポーリングしてログ・アラート・Kill Switch を管理
- ポートフォリオ構築: 候補選定、配分重み計算、ポジションサイズ計算等の純粋関数群
- リサーチ: DuckDB 上でファクターや将来リターン、IC 計算等を実行
- AI モジュール: ニュースを LLM（OpenAI）でスコアリングして ai_scores に書き込む、レジーム判定等
- ユーティリティ: 設定読み込み、ログ設定、プロセス優先度設定など

コマンドラインスクリプトとして起動できるモジュールを複数提供しています（例: 実行エンジン起動、監視ループ、設定ウィザード、検証レポート生成など）。

---

## 機能一覧

- Execution（発注実行）
  - 本番 / ペーパートレードの切替（`KABUSYS_ENV=paper_trading` では MockBroker、別DB を使用）
  - リスク管理（最大ポジション比率、資金利用率、コールバック等）
  - 注文履歴やポジションの永続化（SQLite / DuckDB）

- Monitoring（監視）
  - CPU / メモリ / ディスク使用率、実行プロセスの生存確認
  - 注文の滞留・約定異常の検出、ドローダウン・ポジション上限監視
  - Kill Switch（条件に応じて `data/kill.flag` を書き込み、Execution を停止）
  - ログ永続化（SQLite）と日次ログローテーション（ログファイル）

- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額／スコア加重配分、リスクベースの発注量計算
  - セクター上限の適用、レジーム乗数

- Research（リサーチ）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン、IC（スピアマン）計算、特徴量サマリ

- AI（OpenAI）
  - ニュース記事のセンチメントを LLM で評価して `ai_scores` テーブルへ保存
  - マクロニュースとETF MA乖離の合成による市場レジーム判定

- ツール
  - 環境設定ウィザード（`.env` の対話的作成: `config_setup.py`）
  - 設定検証 CLI（`.env` と config/*.yaml の検証: `validate_config.py`）
  - Paper Trading 用検証レポート生成ツール

---

## セットアップ手順

前提: Python 3.10+（型注釈・Union|等を使用しているため）、git リポジトリがルートにある想定。

1. リポジトリをチェックアウト
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows (PowerShell 等)
   ```

3. 必要パッケージをインストール  
   主な依存:
   - duckdb
   - psutil
   - openai
   - PyYAML（任意：validate_config の YAML 検証に使用）
   ```
   pip install duckdb psutil openai pyyaml
   ```

4. 環境変数の設定（.env）  
   対話式ウィザードで `.env` を作成するのが簡単です：
   ```
   python -m kabusys.config_setup
   ```
   ウィザードで作成された `.env` は自動的にプロジェクトルートの `.env` として保存されます。
   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB。デフォルト: data/paper_trading.db）
   - OPENAI_API_KEY（AI 機能利用時に必要）
   - LOG_LEVEL（DEBUG/INFO/...）

   自動読み込み: 起動時に `.env` / `.env.local` を自動でロードします（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

5. DB 初期化  
   実行スクリプト（監視・実行）は起動時に監視用テーブル等を必要に応じて作成します。特別な事前処理は不要です。

---

## 使い方

- 実行エンジン起動（ExecutionEngine）
  - 本番またはペーパートレードいずれも `Settings` が KABUSYS_ENV を参照して DB を切り替えます。
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - 停止:
    - 外部からプロセスに SIGINT（Ctrl+C） を送る
    - またはプロジェクトルートの `data/stop_requested.flag` を作成すると監視側・実行側が検知して終了します。
  - ペーパートレード：
    - `KABUSYS_ENV=paper_trading` とすると MockBrokerClient を使用し、データは `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）へ保存します。

- 監視ループ起動（Monitoring）
  - 起動:
    ```
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は常に（env に関わらず）本番用の `SQLITE_PATH` を使用して監視ログを記録します。
  - 停止フラグ:
    - `data/stop_requested.flag` を作成すると監視ループが終了します。

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
  - `.env` や `config/*.yaml` の存在・基本整合性をチェックできます。
  - PyYAML がない場合、YAML 内容検証はスキップされ警告になります。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

- AI / リサーチ機能（プログラムから呼び出す）
  - ニューススコアリング:
    ```python
    from kabusys.ai import score_news
    # conn: duckdb connection, target_date: datetime.date, api_key: str|None
    score_news(conn, target_date, api_key="sk-...")
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="sk-...")
    ```
  - 注意: OpenAI API キー（OPENAI_API_KEY）を環境変数として設定しておくか、引数で渡してください。

- ロギング
  - 全スクリプトは共通の `kabusys.utils.logging_setup.setup_logging` を使ってログ設定を統一します。
  - ログは標準出力（stdout）と日次ローテーションされるファイル（デフォルト `logs/<app_name>.log`）に出力されます。ログディレクトリは環境変数 `LOG_DIR` または引数で変更可能。

- Kill Switch / 停止フラグ
  - `kabusys.monitoring.kill_switch` はリスク条件（ドローダウンなど）に応じて `data/kill.flag` を書き込みます。ExecutionEngine はこのフラグの存在を確認して安全停止します。
  - 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動削除します（本番では 0 を推奨）。

---

## 重要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

---

## ディレクトリ構成（主要ファイル）

（プロジェクトルートの `src/kabusys/` 下を抜粋）

- kabusys/
  - __init__.py — パッケージ定義・バージョン
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度・CPU affinity 設定
  - portfolio/
    - portfolio_builder.py — 候補選定・重み算出
    - position_sizing.py — 発注株数計算、キャップ処理
    - risk_adjustment.py — セクター上限、レジーム乗数
  - monitoring/
    - monitoring_db.py — SQLite の永続化層（テーブル初期化 + MonitoringDB クラス）
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度監視
    - trade_monitor.py —（注文監視ロジック。要参照）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — Monitor の束ね
  - execution/ — ExecutionEngine 周りの実装（OrderManager 等）
  - research/ — ファクター計算・特徴量探索
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py — 市場レジーム判定
  - data/ — 実行時に使用するデータ・フラグ（`data/kill.flag`, `data/stop_requested.flag`, `data/execution.pid` 等）

（上記は主要ファイルの要約です。詳細は各モジュールの docstring を参照してください。）

---

## 運用上の注意

- KABUSYS_ENV=live（本番）時は特に慎重に設定してください。`validate_config` は本番時のチェックを促す警告を出します。
- Kill Switch 機構は保護目的ですが、設定（例: KILL_FLAG_CLEAR_ON_START）を誤ると意図せぬ挙動になる可能性があります。本番では自動クリアを無効にすることを推奨します。
- データベース（SQLite / DuckDB）ファイルはデフォルトで `data/` に保存されます。運用時はバックアップ・適切な権限設定を行ってください。
- OpenAI 呼び出しはレート制限や API エラーを考慮してリトライやフェイルセーフ実装がありますが、API キー管理・コスト制御に注意してください。

---

この README はコードから読み取れる設計・起動方法の要点をまとめたものです。詳細な挙動や拡張、各戦略ロジックの仕様については各モジュールの docstring や設計ドキュメント（存在する場合）を参照してください。