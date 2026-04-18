# KabuSys

日本株向け自動売買システムのコードベース（ライブラリ + 起動スクリプト群）の README です。  
この README はリポジトリ内のソース（`src/kabusys`）から主要な機能や使い方、設定方法を抜粋してまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能群を持つモジュール群です。

- 戦略（ファクター計算・特徴量解析）
- ポートフォリオ構築（銘柄選定・重み付け・ポジションサイズ計算）
- 実行層（ExecutionEngine、注文管理、ブローカークライアント）
- 監視（システム状態・注文状態・リスク監視、Kill Switch）
- 研究用ユーティリティ（DuckDB 経由のファクター計算など）
- AI 支援（ニュースの NLP スコアリング、レジーム判定）
- CLI ユーティリティ（.env ウィザード、設定検証、検証レポート生成）

設計方針の一部:
- DuckDB / SQLite をローカル DB として利用（分析とログの分離）
- paper_trading モードでは本番 DB と分離（専用 SQLite）
- OpenAI を利用した NLP 機能は API キーで制御
- フラグファイルによる安全停止（kill.flag / stop_requested.flag）

---

## 主な機能一覧

- config 管理・自動読み込み（`.env`, `.env.local`）
- 対話式 .env 作成ウィザード（`config_setup.py`）
- 設定検証 CLI（`validate_config.py`）
- 実行エンジン起動スクリプト（`run_execution.py`）
  - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用し `data/paper_trading.db` に記録
- 監視用ポーリングループ起動（`run_monitoring.py`）
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング周期を変更可能（既定 60 秒）
- 監視エンジン（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）
- ポートフォリオ構築（等重み・スコア重み・リスクベース等）
- 研究モジュール（ファクター計算、IC 計算、forward returns）
- AI モジュール（ニュース NLP による銘柄別スコアリング、レジーム判定）
- ツール: Paper Trading 検証レポート生成（`tools/paper_verification_report.py`）

---

## セットアップ手順（開発・ローカル実行向け）

1. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール  
   少なくとも以下をインストールしてください（プロジェクトの requirements.txt がない場合は個別に）:
   - duckdb
   - psutil
   - openai
   - PyYAML（設定検証で YAML の検査を行う場合）
   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```

3. プロジェクトルートに `.env` を用意  
   - 対話式ウィザードを利用:
     ```
     python -m kabusys.config_setup
     ```
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主な環境変数（デフォルト値）:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
     - LOG_LEVEL — default: INFO
     - OPENAI_API_KEY — 必要に応じて AI 機能で利用
     - MONITOR_POLL_INTERVAL — 監視ポーリング秒（run_monitoring 用。デフォルト 60）

4. 設定検証（任意だが推奨）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も FAIL 扱い
   ```

---

## 使い方（主な実行例）

- 実行エンジンを起動
  ```
  python -m kabusys.run_execution
  ```
  - 起動時に `KABUSYS_ENV` により以下の振る舞いが変わります:
    - paper_trading: MockBroker を使用し、`PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）に記録
    - live: 本番 DB を使用（`SQLITE_PATH`）

  - 実行エンジンスクリプトはプロセス優先度を高く設定し、`data/stop_requested.flag` が存在すると停止します。
  - デフォルト PID ファイル: `data/execution.pid`（Settings.pid_file_path）

- 監視（System / Trade / Risk）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で指定（秒、正の整数）。
  - 監視は本番 sqlite_path（Settings.sqlite_path）を参照し、DuckDB は `DUCKDB_PATH` を使用します。
  - 停止は `data/stop_requested.flag` を作成することで行います（監視ループが検知して終了）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - オプション `--db` で DB パスを指定可能。環境変数 `PAPER_TRADING_SQLITE_PATH` も参照します。

- .env ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

---

## 重要なファイル・フラグについて

- data/stop_requested.flag  
  - run_execution と run_monitoring が存在を検知して終了処理を行うための停止フラグ（手動で作成/削除することでプロセスの停止制御が可能）。

- data/kill.flag  
  - KillSwitch が条件を満たした際に書き込むファイル。ExecutionEngine に対して外部停止要求を発行するためのフラグとして使用されます。`Settings.kill_flag_clear_on_start` が 1 の場合、起動時に自動でクリアされる設定が可能（本番では 0 推奨）。

- PID ファイル  
  - 実行エンジンは PID ファイル（既定 `data/execution.pid`）を使用して自己管理・二重起動抑止を行う場合があります。

- ログ  
  - デフォルトログディレクトリ: `logs/`。ログはアプリケーション名別に `logs/<app_name>.log`（日次ローテーション、30 日保持）に出力されます。`LOG_DIR` や `LOG_LEVEL` で制御可能。

---

## 環境変数（抜粋と説明）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行系 / 振る舞い
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading では MockBroker と専用 DB を使用
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト `data/paper_trading.db`）
  - SQLITE_PATH: 監視 DB（デフォルト `data/monitoring.db`）
  - DUCKDB_PATH: DuckDB ファイル（デフォルト `data/kabusys.duckdb`）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

- ログ・運用
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
  - LOG_DIR: ログ格納ディレクトリ（デフォルト logs/）

- AI 関連
  - OPENAI_API_KEY: OpenAI API キー（ai モジュールで必須）

その他の設定は `kabusys.config.Settings` を参照してください（コードで各プロパティのデフォルトや検証ロジックがあります）。

---

## ディレクトリ構成（主要ファイル）

リポジトリは Python パッケージ `kabusys` 配下に機能が整理されています。以下は `src/kabusys` の主要ファイルとサブパッケージの概要です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み・Settings 定義
  - config_setup.py
    - 対話式 .env 作成ウィザード
  - validate_config.py
    - 起動前の設定チェック CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py — 統一ロギング設定
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite による永続化層
    - system_monitor.py — システム状態 / データ鮮度監視
    - trade_monitor.py — 注文・約定監視（ファイル内の他モジュールと連携）
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - monitoring_engine.py — モニタ群をまとめるエンジン
    - alert_manager.py — アラート送信（LINE 等、実装に依存）
  - execution/
    - execution_engine.py — 実行エンジン本体
    - order_manager.py, order_repository.py, reconciler.py, etc.（注文管理関連）
    - broker_factory.py — ブローカークライアント生成（paper_trading 用 Mock 別）
    - risk_manager.py — 発注前リスク制御
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum/Value/Volatility ファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI 利用）
    - regime_detector.py — 市場レジーム判定（MA + マクロ NLP）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成

（上は主要モジュールのみを抜粋しています。詳細はソースツリーを参照してください。）

---

## 運用上の注意 / ベストプラクティス

- .env は絶対にバージョン管理にコミットしない（`config_setup.py` のヘッダにも警告あり）。
- 本番（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START=0` を推奨（自動クリアは危険）。
- Monitoring は本番 sqlite_path を使用するため、開発時に監視 DB を上書きしないよう注意。paper_trading は実行エンジンのみ専用 DB に分離。
- OpenAI API を使用する機能はネットワーク/料金依存のため、失敗時はフェイルセーフ（多くの箇所でゼロフォールバックやスキップ処理あり）。
- プロセス優先度設定や CPU affinity は OS により制限される（権限不足で警告が出る場合あり）。

---

## 参考コマンドまとめ

- .env 作成ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動:
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- 監視起動:
  ```
  python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば README に「各モジュールの詳細 API ドキュメント」「設定項目の完全リスト（.env.example 相当）」や「起動スクリプトのシステムd/service ユニット例」などを追記できます。どの情報を追加したいか教えてください。