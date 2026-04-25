# KabuSys

日本株自動売買システムの一部（ライブラリ＋起動スクリプト群）。  
このリポジトリには、戦略の研究用モジュール、ポートフォリオ構築、実行エンジン起動スクリプト、監視・アラート、Paper Trading 用ツール、AI を用いたニュース NLP モジュールなどが含まれます。

---

## 概要

KabuSys は日本株の自動売買に必要な機能群をモジュール化したコードベースです。主な関心点は以下：

- 戦略研究（DuckDB を用いたファクター計算、特徴量解析）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ決定、セクター制限）
- 実行エンジン（BrokerClient 抽象化、Paper Trading と本番の分離）
- 監視（システム状態・注文の監視、Kill Switch）
- AI モジュール（ニュースのセンチメント評価、レジーム判定）
- 運用支援ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）

---

## 主な機能一覧

- 環境設定管理
  - .env の対話的作成/更新（kabusys.config_setup）
  - 起動前の設定検証（kabusys.validate_config）
  - 自動で .env を読み込む仕組み（プロジェクトルート検出）
- 実行関連
  - ExecutionEngine 起動スクリプト（run_execution.py）
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用 DB に記録
  - ExecutionEngine の停止はフラグファイル（data/stop_requested.flag）や Kill Switch で制御
- 監視関連
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（ポーリング）
  - run_monitoring.py で監視ループを起動（デフォルト 60 秒間隔、MONITOR_POLL_INTERVAL で上書き可）
  - 監視ログは SQLite（デフォルト `data/monitoring.db`）へ永続化（初回自動作成）
- ポートフォリオ構築
  - 候補選定（score に基づくソート）
  - 等重・スコア重み・リスクベース配分
  - セクター上限適用、レジーム乗数
  - 単元株丸め、aggregate cap によるスケーリング
- 研究用（DuckDB）
  - モメンタム・ボラティリティ・バリューファクター計算（prices_daily / raw_financials 利用）
  - 将来リターン計算、IC 計算、ファクター統計
- AI（OpenAI）
  - ニュース記事を LLM でスコアリングして ai_scores に書き込み
  - マクロニュース＋ETF MA を合成して市場レジーム（bull/neutral/bear）を判定
  - リトライ・バリデーション等の堅牢化ロジックを実装
- 運用ツール
  - Paper Trading の検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 必要条件（推奨）

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定 YAML の検証に任意）
- （開発用）pipenv/venv 等で仮想環境を推奨

※ 実際の requirements.txt はリポジトリに合わせて用意してください。例:
```
duckdb
psutil
openai
PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化する。
   - 例: python -m venv .venv && source .venv/bin/activate

2. 依存パッケージをインストールする。
   - 例: pip install -r requirements.txt
   - もし requirements.txt がない場合は上の主要依存を個別にインストールしてください。

3. 環境変数 (.env) を作成する。
   - 対話形式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは `.env.example` を参考に `.env` を作成してください。
   - 自動ロードはデフォルトで有効。無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

4. 設定を検証する（推奨）。
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告も失敗扱い（exit code 1）になります。

5. 必要に応じて DB ディレクトリ（`data/`）やログディレクトリ（`logs/`）を作成します。多くの起動スクリプトは自動で親ディレクトリを作成しますが、権限に注意してください。

---

## 環境変数（主要なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
- DB パス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 時の SQLite（デフォルト: data/paper_trading.db）
- ログ
  - LOG_LEVEL — ログレベル（DEBUG/INFO/…、デフォルト INFO）
  - LOG_DIR — ログ保存ディレクトリ（デフォルト logs/）
- AI / OpenAI
  - OPENAI_API_KEY — OpenAI API キー
- 監視・起動制御
  - PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
  - KILL_FLAG_PATH — kill.flag のパス（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に Kill Flag をクリアする（"1" 有効、デフォルト "0"）
- その他（監視閾値）
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

---

## 使い方（起動・主要スクリプト）

- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（`PAPER_TRADING_SQLITE_PATH`）へ記録します。
  - 起動時に data/stop_requested.flag が存在すると起動しません。
  - 停止は data/stop_requested.flag を作成するか、実行プロセスへ KeyboardInterrupt を送ることで行います。

- 監視ループ起動
  ```
  python -m kabusys.run_monitoring
  ```
  - デフォルトポーリング間隔: 60 秒。環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能。
  - 監視は常に「本番用の」sqlite_path を使用（環境に依らず monitoring DB は共通）。
  - 停止：data/stop_requested.flag を作成するか Ctrl+C 。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で DB を指定可能。

- AI バッチ処理（コード呼び出し例）
  - ニューススコアリング:
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026, 4, 10), api_key="YOUR_OPENAI_KEY")
    ```
  - レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026, 4, 10), api_key="YOUR_OPENAI_KEY")
    ```

---

## 停止・Kill Switch の仕組み

- run_execution / ExecutionEngine は停止フラグファイル（data/stop_requested.flag）を監視します。フラグが立っていると安全停止します。
- Kill Switch（kabusys.monitoring.kill_switch）はリスク条件（ドローダウンやポジション上限）に応じて `data/kill.flag` を書き込み、実行エンジンの強制停止トリガーとして使用できます。`.env` の `KILL_FLAG_CLEAR_ON_START` を使って起動時に自動クリアするか制御可能（本番では 0 推奨）。

---

## ロギング

- ログは標準出力（stdout）とファイル（logs/<app_name>.log）に出力されます。
- 日次ローテーション（TimedRotatingFileHandler）で 30 日分保持。
- ログ設定は全スクリプト共通のユーティリティ kabusys.utils.logging_setup.setup_logging を使用しています。

---

## ディレクトリ構成（主なファイル）

（src 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理、自動 .env 読み込み
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (参照あり)
    - alert_manager.py (参照あり)
    - kill_switch.py
  - execution/  (実行関連コンポーネント: Engine, BrokerFactory, OrderManager 等)
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/（実行時に DB / PID / flag が配置される想定）
  - logs/（ログ出力先）

---

## 開発・運用上の注意

- .env は機密情報を含むため Git にコミットしないでください（config_setup でも注意書きあり）。
- KABUSYS_ENV=live の場合は設定を慎重に確認してください（validate_config に本番向けチェックあり）。
- OpenAI API を利用する機能は API キーと通信コストが必要です。テスト時はモック化できる設計（内部の API 呼び出し関数を差し替え可能）。
- DuckDB / SQLite の接続はそれぞれのファイルパスを環境変数で指定できます。運用時のバックアップおよび容量管理に注意してください。
- process priority / CPU affinity はプラットフォーム依存の権限要件があります。権限不足では警告が出て設定がスキップされます。

---

## テスト／実験

- MonitoringEngine の単発実行（テスト）:
  - テストコードから MonitoringEngine のインスタンスを作成し `run_once()` を呼べます（ポーリングループを回さずに1回だけ実行可能）。
- OpenAI 関連の関数は API 呼び出しをラップしているため、ユニットテストではモックして振る舞いを検証してください（コード内でもテスト向けパッチを想定）。

---

## ライセンス・バージョン

- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

---

必要であれば、README に以下の追加情報も作成します：
- requirements.txt のサンプル
- systemd / Docker を使った運用手順（ユニットファイル例 / Dockerfile）
- よくあるトラブルシュート（DB 権限、ログ出力失敗、OpenAI の rate limit 対処）
ご希望があればどれを追加するか教えてください。