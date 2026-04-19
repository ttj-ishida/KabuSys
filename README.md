# KabuSys

日本株向け自動売買システムのコードベース。  
この README はリポジトリ内の主要スクリプト／モジュールの概要、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買フレームワークです。主な目的は以下のとおりです。

- シグナル生成・ポートフォリオ構築・ポジションサイズ計算（research / portfolio）
- 注文管理、実行エンジン（execution）
- システム監視、アラート、Kill Switch（monitoring）
- ニュースの NLP スコアリング & レジーム判定（ai）
- ペーパートレーディング用の検証ツール（tools）

設計方針の一部：
- DuckDB を分析用に使用、SQLite を運用ログ／監視に使用
- Paper trading（ペーパートレード）と Live（本番）で DB を分離
- 環境変数と .env を使用して設定管理（対話式ウィザードあり）
- OpenAI（LLM）を使ったニュースセンチメント評価やレジーム判定機能を提供

---

## 主な機能一覧

- Execution（発注エンジン）
  - BrokerClientFactory による本番/モッククライアント切替
  - OrderManager / RiskManager / Reconciler / ExecutionEngine の構成
  - Paper trading 用 DB 分離（data/paper_trading.db）

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス健全性、データ鮮度チェック
  - TradeMonitor / RiskMonitor: 注文滞留、異常約定、ドローダウン監視
  - KillSwitch: 閾値到達時に data/kill.flag を書き込み Execution を停止
  - MonitoringDB: SQLite で監視ログを永続化

- Research（研究用）
  - ファクター計算（momentum/value/volatility）
  - 将来リターン／IC 計算、特徴量サマリ

- Portfolio（ポートフォリオ構築）
  - 候補選定、等分/スコア重み、リスクベースのポジションサイズ算出
  - セクター上限適用、レジーム乗数

- AI（LLM 統合）
  - news_nlp: ニュース記事をバッチで OpenAI に投げて銘柄別スコアを生成
  - regime_detector: ma + マクロニュースで market_regime を判定

- ユーティリティ
  - 対話式 .env ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ログ設定ユーティリティ（utils.logging_setup）
  - プロセス優先度 & affinity 設定（utils.process_priority）
  - Paper Trading 検証レポート生成ツール（tools.paper_verification_report）

---

## 前提・依存（代表例）

プロジェクト内のコードから推測される代表的な依存パッケージ（requirements.txt にまとめてください）:

- python >= 3.9
- duckdb
- psutil
- openai
- PyYAML（config 検証で任意）
- その他実行環境に応じたライブラリ（J-Quants, kabu API クライアント等はプロジェクト固有）

※ 実際の依存関係はプロジェクトの requirements.txt / pyproject.toml を参照してください。

---

## セットアップ手順（ローカル手順例）

1. リポジトリをクローンして作業ディレクトリに移動
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・有効化（例: venv）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate.bat  # Windows
   ```

3. 依存パッケージをインストール
   ```bash
   pip install -r requirements.txt
   ```
   （requirements.txt がない場合は duckdb, psutil, openai, pyyaml などを個別にインストール）

4. 初期ディレクトリ作成
   ```bash
   mkdir -p data logs
   ```
   既定の DB/ログパスは `data/kabusys.duckdb`, `data/monitoring.db`, `logs/` です。

5. 環境変数設定（.env の作成）
   - 対話式ウィザードを使う（推奨）:
     ```bash
     python -m kabusys.config_setup
     ```
   - または `.env` を直接作成。必要な主な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視用: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading の場合の専用 DB: data/paper_trading.db)
     - PAPER_FILL_MODE (instant|partial|never|reject) — デフォルト: instant
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR)

6. 設定検証（任意）
   ```bash
   python -m kabusys.validate_config
   # 警告をエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

---

## 使い方（主要スクリプト）

- 実行エンジン（ExecutionEngine）を起動
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します。
  - 起動時に停止フラグ（data/stop_requested.flag）が存在すると起動せずに終了します。
  - 実行中は PID を data/execution.pid に書きます。

- 監視ループを起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能。デフォルト 60 秒。
  - 監視は Settings.sqlite_path（通常 data/monitoring.db）を使用します（環境にかかわらず本番 sqlite_path を使用する仕様）。
  - 停止はプロジェクトルートの `data/stop_requested.flag` ファイルを作成することで行えます（監視ループはフラグ検知で終了）。

- .env の対話式作成
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート（ツール）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

- AI 機能（プログラムから呼び出す）
  - news_nlp のスコア生成:
    ```python
    from kabusys.ai import score_news
    # conn: duckdb connection, target_date: datetime.date, api_key: str (任意)
    score_news(conn, target_date, api_key=None)
    ```
  - regime_detector の実行:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key=None)
    ```

---

## 停止 / Kill Switch に関する運用メモ

- ExecutionEngine を強制停止させる（監視側からの停止）には `data/kill.flag` を利用します。KillSwitch が書き込むとエンジンは停止処理を行います。
- 監視・エンジン停止用のシンプルなフラグは `data/stop_requested.flag`（run_monitoring / run_execution がチェック）です。
- `KILL_FLAG_CLEAR_ON_START=1` を .env に設定すると起動時に kill.flag を自動クリアします（本番では危険。デフォルトは 0）。

---

## ログ

- ロギングは共通ユーティリティ `kabusys.utils.logging_setup.setup_logging()` を介して行われます。
- デフォルトでは標準出力（stdout）と日次ローテートのファイル出力（logs/<app_name>.log）を併用します。ログディレクトリは `LOG_DIR` 環境変数や引数で指定可能。
- ログレベルは `LOG_LEVEL` で制御できます（デフォルト INFO）。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内 `src/kabusys` を中心に記載します（抜粋）。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env の自動読み込み・Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度／CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ & 永続化 API
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文滞留などの監視（存在）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - kill_switch.py         — kill.flag の管理
    - alert_manager.py       — 通知管理（存在）
  - execution/
    - execution_engine.py    — ExecutionEngine 本体（存在）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - research/
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — IC / 統計サマリ等
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI 統合）
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
  - data/                    — 実行時に使用するファイル（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, flags, pid 等）

（上記はファイル群の要約です。細かいファイルは実際のツリーを参照してください。）

---

## 運用上の注意 / ベストプラクティス

- 本番（KABUSYS_ENV=live）では kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）にしないことを推奨します。
- OpenAI API キーは機密情報です。.env を絶対にリポジトリへコミットしないでください。
- Paper trading 用 DB は本番 DB と物理的に分離（デフォルトで data/paper_trading.db）されています。テスト時はペーパートレードモードを使って安全に検証してください。
- 監視プロセスは既定で高優先度（set_process_priority("high")）で起動します。必要に応じてプロセス優先度を変更してください。
- Logging のファイル出力が失敗しても標準出力には出力される設計です（フォールバック）。

---

## よく使うコマンド例

- .env 作成
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Execution 起動（開発）
  ```bash
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- Monitoring 起動
  ```bash
  python -m kabusys.run_monitoring
  # ポーリング間隔を 30 秒にする例
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README に書いた内容はコード内の docstring／コメントを参照してまとめています。  
さらに詳細な API 使用法や実稼働向けの運用手順・テスト指針は別途ドキュメント（設計書 / 運用手順書）を用意することを推奨します。