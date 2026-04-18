# KabuSys — 日本株自動売買フレームワーク

このリポジトリは日本株向けの自動売買／研究／監視基盤のコンポーネント群を含む小規模フレームワークです。  
主要機能は取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、ニュースNLP を使ったスコアリング等を想定しています。

以下はコードベース（src/kabusys/*.py）に基づいた README です。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（起動・ユーティリティ）
- 環境変数（主要）
- 停止・Kill スイッチ
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下の役割を持つコンポーネント群で構成されています。

- ExecutionEngine: ブローカークライアント経由で発注・注文管理・リスク管理を行う実行エンジン（paper_trading モードでは MockBroker を使用）
- Monitoring: システム状態・注文状態・リスク監視を行い、kill.flag による安全停止などを実現
- Portfolio: 候補選定、重み計算、ポジションサイズ計算、セクター制限・レジーム乗数などの純粋関数群
- Research: DuckDB を用いたファクター計算、将来リターン、IC（情報係数）計算など
- AI: OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価、レジーム判定
- Tools: ペーパートレード検証レポート生成や設定ウィザードなどのユーティリティ

設計方針の一部:
- DuckDB / SQLite をローカル DB として利用（分析用 / 監視用に分離）
- 実行モード（development / paper_trading / live）は環境変数 `KABUSYS_ENV` で制御
- AI 呼び出しは API キー（OPENAI_API_KEY）に依存。失敗時はフェイルセーフで継続する実装が多い

---

## 機能一覧

- 実行エンジン起動スクリプト: `run_execution.py`
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 SQLite に記録
  - 停止フラグ（data/stop_requested.flag）を検知して停止
- 監視プロセス起動スクリプト: `run_monitoring.py`
  - CPU/メモリ/ディスク、Execution プロセスの生存、データ鮮度などを定期記録
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で変更可（デフォルト 60 秒）
  - 監視用テーブルは常に本番用 `sqlite_path` を使用（環境に依存しない）
- 設定ウィザード: `config_setup.py`（対話式 .env 生成）
- 設定検証 CLI: `validate_config.py`（--strict オプションあり）
- Paper Trading 検証レポート: `tools/paper_verification_report.py`
- ニュース NLP（OpenAI）による銘柄別センチメントスコアリング: `ai/news_nlp.py`
- レジーム判定（MA200 + マクロセンチメント合成）: `ai/regime_detector.py`
- ポートフォリオ構築ユーティリティ（候補選定・重み・ポジションサイズ・セクター制限）
- 監視 DB 層（SQLite）: テーブル作成と永続化ロジック
- ロギングの共通セットアップ、プロセス優先度・CPU affinity 設定ユーティリティ

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境を作成・有効化
   - bash / zsh 例:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```

2. 必要なパッケージをインストール  
   （requirements.txt が無い場合は次の主要依存を手動でインストール）
   ```
   pip install duckdb psutil openai
   # 追加（任意）:
   pip install PyYAML
   ```

3. リポジトリルートで .env を作成  
   対話式で作成する:
   ```
   python -m kabusys.config_setup
   ```
   必要最低限必須値:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

4. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリの確認（デフォルト）
   - DuckDB: `data/kabusys.duckdb`
   - SQLite (monitoring): `data/monitoring.db`
   - Paper trading SQLite: `data/paper_trading.db`（KABUSYS_ENV=paper_trading 時）

---

## 使い方（起動例）

各スクリプトはパッケージモジュールとして起動できます。

- 実行エンジン（ExecutionEngine）を起動:
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合、MockBroker を使用して paper_trading 用 DB に記録します。
  - 起動前に `data/stop_requested.flag` が存在する場合は起動しません。

- 監視プロセスを起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更する場合:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は常に本番監視用の `SQLITE_PATH`（デフォルト `data/monitoring.db`）を使用します（環境にかかわらず）。

- Paper Trading 検証レポートを生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- 環境設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- AI モジュール（プログラムから使用）
  - ニューススコアリング:
    ```
    from kabusys.ai.news_nlp import score_news
    # DuckDB 接続と target_date を渡して呼ぶ
    ```
  - レジーム判定:
    ```
    from kabusys.ai.regime_detector import score_regime
    ```

ログ:
- 共通ロギング設定により標準出力にログが出力され、`logs/<app_name>.log` に日次ローテーションで保存されます（`LOG_DIR` 環境変数で変更可能）。

---

## 主要な環境変数

必須・重要なもの:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: `development` | `paper_trading` | `live`（デフォルト: development）
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector）が必要とする API キー

データベース関連:
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 時の SQLite（デフォルト: data/paper_trading.db）

監視関連:
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch 用フラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0。production では 0 推奨）

Paper トレード用:
- PAPER_FILL_MODE — MockBroker の約定モード: `instant` | `partial` | `never` | `reject`（デフォルト `instant`）

ログ関連:
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
- LOG_DIR — ログ保存ディレクトリ（デフォルト `logs/`）

---

## 停止・Kill スイッチ

- 実行停止フラグ: `data/stop_requested.flag`
  - `run_execution.py` / `run_monitoring.py` はこのファイルを検知するとループを抜けて終了します（手動停止用）。
- Kill Switch（自動停止判定）:
  - 監視ロジック（RiskMonitor など）が条件を満たすと `data/kill.flag` を書き込みます。
  - ExecutionEngine 起動時に `KILL_FLAG_CLEAR_ON_START=1` を指定すると起動時に自動で kill.flag をクリアしますが、本番では危険なため推奨されません。

---

## ディレクトリ構成（抜粋）

以下は本リポジトリの主要なソース配置（`src/kabusys/`）の簡易ツリーです。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - execution/  (発注・エンジン関連; BrokerFactory, ExecutionEngine 等)
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - data/ (想定されるデータディレクトリと DB ファイル)
    - tools/
      - paper_verification_report.py

注意: 実際のファイル構成や追加のサブモジュールはリポジトリ内の全ファイルを参照してください。

---

## 備考 / 運用メモ

- run_monitoring は「監視用 DB」を必ず本番の sqlite_path に書き込む設計になっています（KABUSYS_ENV に影響されません）。監視データは環境に関係なく一元管理される前提です。
- run_execution は `KABUSYS_ENV=paper_trading` の場合、paper_trading 専用の SQLite を使用して本番 DB とデータを分離します。
- OpenAI を使う機能は API レスポンスの失敗に対してリトライやフォールバックを備えていますが、API キーの管理やコストに注意してください。
- `validate_config.py` は起動前チェックとして有用です。`--strict` を指定すると警告もエラー扱いになります。

---

必要であれば、この README をベースに「運用手順書（デプロイ・監視・障害時対応）」「開発者向け Contribution ガイド」「requirements.txt」や CI 設定のテンプレートも作成できます。どれを優先して出力しましょうか？