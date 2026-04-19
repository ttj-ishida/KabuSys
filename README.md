# KabuSys

日本株自動売買システムのリポジトリ（モジュール群のみ）。  
この README はコードベースの主要コンポーネント、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買／リサーチ／監視を行うためのモジュール群です。  
主な役割は以下のとおりです。

- 実行エンジン（ExecutionEngine）による発注ロジック（本番 / ペーパー）
- 監視サブシステム（System / Trade / Risk）による稼働監視と Kill Switch
- ポートフォリオ構築（銘柄選定・重み付け・ポジションサイズ計算）
- リサーチ（ファクター計算・特徴量解析）
- AI モジュール（ニュースセンチメント、レジーム判定） — OpenAI を利用
- 開発用ユーティリティ（.env ウィザード、設定検証、レポート生成 等）

設計上の特徴：
- DuckDB を分析用 DB、SQLite を監視／発注履歴用 DB（ペーパートレード時は分離）として利用
- .env または環境変数で設定を管理（自動ロード機能あり）
- ログはコンソール + 日次ローテーションのファイル出力
- フェイルセーフ（API失敗時はフォールバックして継続する設計）

---

## 主な機能一覧

- 実行
  - run_execution.py：ExecutionEngine の起動スクリプト（KABUSYS_ENV により本番／ペーパーを切替）
  - ペーパートレード時は MockBrokerClient を使用し DB を分離（`data/paper_trading.db`）
  - 停止はフラグファイル（`data/stop_requested.flag` / `data/kill.flag` 等）で制御

- 監視
  - run_monitoring.py：SystemMonitor のポーリング起動（デフォルト 60 秒）
  - System / Trade / Risk モニタでログを記録し、Kill Switch を評価
  - MonitoringDB（SQLite）に system_status / trade_logs / positions / risk_logs / dashboard を保持

- ポートフォリオ構築
  - 候補選定、等金額／スコア重み付け、セクター制限、レジーム乗数、ポジションサイズ算出

- リサーチ
  - ファクター（Momentum / Volatility / Value）計算（DuckDB 上の prices_daily, raw_financials 参照）
  - 将来リターン、IC 計算、統計サマリ等のユーティリティ

- AI（OpenAI）
  - news_nlp.score_news：ニュース記事を LLM でセンチメント評価し ai_scores に書き込む
  - regime_detector.score_regime：ETF の MA とマクロ記事の LLM スコアを合成して市場レジームを判定

- ツール
  - config_setup.py：対話式 .env ウィザード
  - validate_config.py：環境変数 / config/*.yaml の検証 CLI
  - tools.paper_verification_report：Paper Trading 検証レポート生成

- ユーティリティ
  - logging_setup：統一されたロギング設定（コンソール + 日次ファイルローテーション）
  - process_priority：プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順（開発 / ローカル実行向け）

前提：Python 3.10+（型注釈などを利用）。必要ライブラリは requirements.txt 等を参照してインストールしてください（例: duckdb, psutil, openai, PyYAML が該当することがあります）。

1. リポジトリをクローン／展開する。

2. 仮想環境を作成して依存をインストール：
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. データ／ログ用ディレクトリを作成（デフォルトは `data/` と `logs/`）:
   ```
   mkdir -p data logs
   ```

4. 環境変数設定
   - 対話式ウィザードで .env を生成する：
     ```
     python -m kabusys.config_setup
     ```
     あるいは手動で `.env` を作成してください（以下の主要キーは必須）：
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development | paper_trading | live） — デフォルト development
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI モジュール使用時に必要）
     - LOG_LEVEL（DEBUG/INFO/...）

   - 自動ロードはプロジェクトルートに `.env` / `.env.local` がある場合に有効（無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

5. 設定検証（起動前チェック）：
   ```
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合
   python -m kabusys.validate_config --strict
   ```

6. ログディレクトリや data のパーミッション設定を確認。

---

## 使い方（起動方法・主要コマンド）

- 実行エンジン起動（ExecutionEngine）
  - 本番／ペーパーは KABUSYS_ENV に依存：
    ```
    # python -m でモジュールとして起動
    python -m kabusys.run_execution
    ```
  - 注意：起動時に `data/stop_requested.flag` が存在すると起動しません。
  - ペーパートレード時は `.env` で `KABUSYS_ENV=paper_trading` を設定し、`PAPER_TRADING_SQLITE_PATH` を確認します。
  - ExecutionEngine の PID はデフォルトで `data/execution.pid` に保存されます。

- 監視プロセス起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は常に本番の sqlite_path（`SQLITE_PATH`）を参照します（環境に関係なく監視 DB は本番 DB を使う設計）。

- .env ウィザード（対話式）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI モジュール（プログラムから利用）
  - news_nlp.score_news(conn, target_date, api_key=None) — OPENAI_API_KEY を環境変数または api_key 引数で渡す
  - regime_detector.score_regime(conn, target_date, api_key=None)

- Kill Switch / 停止
  - KillSwitch は `data/kill.flag` を書き込むことで ExecutionEngine 停止を促します（Settings.kill_flag_path でパスが設定可能）。
  - 手動で停止する場合は `data/stop_requested.flag` を作成すると run_* スクリプトがループを脱して終了します。

---

## 環境変数（主要）

- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーションのベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時に必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視）ファイルパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（INFO 等）
- LOG_DIR: ログファイル格納ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant | partial | never | reject）

---

## ロギング

- ログは `kabusys.utils.logging_setup.setup_logging` で統一的に設定されます。
- コンソール（stdout）出力と、日次でローテートするファイルハンドラ（logs/<app_name>.log）を追加。
- ファイル出力は `LOG_DIR` 環境変数 またはデフォルト `logs/` を使用。

---

## OpenAI（AI モジュール）について

- news_nlp と regime_detector は OpenAI（gpt-4o-mini）を利用します。利用には `OPENAI_API_KEY` が必要です。
- 実行中に 429 / ネットワーク断 / タイムアウト / 5xx 発生時は指数バックオフでリトライする実装です（最大リトライ回数はモジュールごとに定義）。
- AI 呼び出しはフェイルセーフ設計で、失敗時はフォールバック（0.0 等）で処理継続します。

---

## ディレクトリ構成（主要ファイル／モジュール）

リポジトリの `src/kabusys` 以下の主要構成：

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動ロードと Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポートツール
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI 利用）
    - regime_detector.py     — 市場レジーム判定（OpenAI 利用）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル作成・読み書き API）
    - system_monitor.py      — システム状態 / データ鮮度監視
    - trade_monitor.py       — （trade 監視、コード内参照）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 管理
    - monitoring_engine.py   — 複数モニタを束ねる実行エンジン
    - alert_manager.py       — （アラート送信の管理、コード内参照）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み付け
    - position_sizing.py     — 株数決定・スケール調整
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py — Forward returns / IC / 統計
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度・CPU affinity 設定
  - execution/               — ExecutionEngine, BrokerFactory, OrderManager 等（実行関連）
  - data/                    — デフォルトの DB ファイル / フラグファイル保存場所（実際はリポジトリ外で運用）
  - その他（modules によって細分化）

（※ 上記はコードベースの抜粋説明です。詳細な API は各モジュール内の docstring を参照してください。）

---

## よくある操作例

- 監視ループを 10 秒間隔で実行（環境変数で上書き）:
  ```
  MONITOR_POLL_INTERVAL=10 python -m kabusys.run_monitoring
  ```

- ペーパートレード用 Execution を実行:
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- Kill Switch を手動でクリア（開発者向け）:
  ```
  # Python スクリプト等で KillSwitch.clear() を呼ぶか、
  rm data/kill.flag
  ```

---

## 注意事項 / 運用上の留意点

- 本リポジトリには実際の ExecutionEngine 実装やブローカーインテグレーションの詳細が含まれます。`KABUSYS_ENV=live` 設定では実際に発注が行われるため、設定・資格情報管理は慎重に行ってください。
- `.env` は絶対に Git にコミットしないでください（`config_setup.py` のヘッダにも注意書きあり）。
- 本番環境では `KILL_FLAG_CLEAR_ON_START=0` を推奨します（誤って Kill Flag がクリアされることを防止）。
- OpenAI の API 利用はコストとレイテンシに注意してください。API キーの取り扱いも慎重に。
- ログディレクトリやデータディレクトリの権限を適切に設定してください。監視 DB は永続化されます。

---

この README はコードベース（src/kabusys/*.py）を基にまとめています。より詳細な使い方や内部設計（StrategyModel.md / PortfolioConstruction.md 等の設計ドキュメント）があればそちらも参照してください。質問や追加で README に含めたい内容があれば教えてください。