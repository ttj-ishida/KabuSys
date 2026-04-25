# KabuSys — 日本株自動売買システム (README)

このリポジトリは日本株の自動売買・研究・監視を目的とした軽量フレームワークです。  
README ではプロジェクト概要、主な機能、セットアップ手順、起動・使い方、およびディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は次の目的を持つモジュール群で構成されたシステムです。

- 注文実行エンジン（ExecutionEngine） — ブローカークライアントを経由して発注・注文管理を行う。
- 監視（Monitoring） — システム稼働状況・注文データ・リスク指標を定期的にチェックし、必要時に通知／Kill Switch を発動する。
- ポートフォリオ構築（Portfolio） — 候補選定・重み計算・ポジションサイズ計算・セクター制約適用など純粋関数群。
- 研究・ファクター計算（Research） — DuckDB 上の時系列データからファクターや将来リターン・IC 計算を行う。
- AI 補助（AI） — ニュース NLP によるセンチメント評価、レジーム判定など（OpenAI API 利用）。
- ユーティリティ群 — ロギング設定、プロセス優先度設定、設定ウィザード、設定検証、ツール類。

設計上のポイント:
- 設定は .env（環境変数）で管理。自動ロード機能あり（プロジェクトルートに .env がある場合）。
- DB: DuckDB（分析用）と SQLite（監視・発注ログ用）を併用。
- Paper Trading モードでは本番 DB と分離してペーパートレード用 DB を使用可能。
- LLM 呼び出し部はフェイルセーフで、API エラー時は代替挙動（スコア 0 等）で継続。

---

## 機能一覧

- run_execution: ExecutionEngine を起動（本番 / paper_trading 対応）
  - Paper Trading 時は MockBrokerClient を使用し、data/paper_trading.db に記録
- run_monitoring: SystemMonitor のポーリングループを起動
  - MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能
- monitoring:
  - system_status / trade_logs / positions / risk_logs / dashboard の永続化（SQLite）
  - RiskMonitor: ドローダウン／ポジション上限の監視とログ化
  - KillSwitch: 条件を満たした場合に kill.flag を書き込み Execution を停止
  - MonitoringEngine: 各モニタの統括とアラート送出
- portfolio:
  - 候補選定（select_candidates）
  - 等金額/スコア重みの計算
  - ポジションサイズ計算（リスクベース・等配分など）、ロット丸め、集約上限のスケーリング
  - セクター制約・レジーム乗数
- research:
  - momentum / volatility / value 等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- ai:
  - news_nlp: ニュース記事を OpenAI に送って銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector: ETF の ma200 乖離 + マクロニュースの LLM スコアで market regime を判定・保存
- utils:
  - logging_setup: コンソール + 日次ローテートファイルの共通ロギング設定
  - process_priority: プロセス優先度 / CPU affinity の簡易設定
- ツール:
  - config_setup: 対話的に .env を生成／更新するウィザード
  - validate_config: .env / config/*.yaml 等の起動前チェック
  - paper_verification_report: ペーパートレード DB から検証レポートを生成

---

## セットアップ手順

前提
- Python 3.9+（ソースで typing | None の記法や modern API を使用）
- システムに sqlite3 が含まれていること（通常の Python に同梱）
- ネットワーク接続（OpenAI を使う場合）

1. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール
   推奨パッケージ（主要依存）:
   - duckdb
   - psutil
   - openai
   - （任意）PyYAML（config/*.yaml の検証を行う場合）

   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```

3. プロジェクトルートに .env を用意
   - 対話式に作る:
     ```
     python -m kabusys.config_setup
     ```
   - または直接 .env を作成し、最低限必須な環境変数を設定:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 重要: .env は Git にコミットしないでください。

4. 設定検証（任意だが推奨）
   ```
   python -m kabusys.validate_config
   ```
   --strict オプションを付けると警告も FAIL 扱いになります。

5. データディレクトリ・ログディレクトリ
   - デフォルトでは以下を想定します。必要に応じて .env で上書きしてください。
     - data/ （SQLite DB・PID・flag 保存用）
     - logs/（ログファイル）
   - ログディレクトリは環境変数 LOG_DIR で変更可能。

6. （OpenAI を使う場合）API キーの設定
   - 環境変数 OPENAI_API_KEY を設定するか、該当関数に api_key を渡してください。

---

## 使い方

重要な実行エントリポイントはモジュールとして実行できます（パッケージ内のスクリプト）。

- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  # --strict を指定すると警告があると exit(1) になります
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine（発注エンジン）起動
  - Paper Trading（ペーパートレード）:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
    Paper Trading の SQLite は PAPER_TRADING_SQLITE_PATH（.env の PAPER_TRADING_SQLITE_PATH）で指定可能（デフォルト: data/paper_trading.db）。
  - Live / Development など:
    ```
    export KABUSYS_ENV=live
    python -m kabusys.run_execution
    ```
  - エンジンは data/stop_requested.flag の存在を監視しており、存在すると安全に停止します。実行中は data/execution.pid に PID が書き出されます。

- Monitoring（監視ループ）起動
  ```
  # ポーリング間隔を秒で上書き（デフォルト 60 秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - Monitoring は常に（KABUSYS_ENV にかかわらず）本番 sqlite_path を使用します（監視用 DB）。
  - 停止は data/stop_requested.flag を作成することで行えます。

- ペーパートレード検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは --db オプション、または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

- AI / 研究関数のプログラム的利用例
  - DuckDB 接続を作成して関数を呼び出します（OpenAI を使う場合は OPENAI_API_KEY を環境変数で設定するか api_key を渡す）。
  - 例（ニュース NLP を呼ぶ場合の概略）:
    ```
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```
  - research モジュール:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

- Kill Switch / 停止フラグ
  - kill.flag（Settings.kill_flag_path / デフォルト data/kill.flag）を書き込むと ExecutionEngine に停止シグナルを送れます。KillSwitch はリスク条件（例: ドローダウン閾値やポジション数上限）に応じてこれを書き込みます。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨します。

- ログ
  - setup_logging により stdout と logs/<app_name>.log に日次ローテーションで出力されます。
  - ログレベルは環境変数 LOG_LEVEL または .env 設定で調整できます。

---

## 主要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- OPENAI_API_KEY（AI 機能を使う場合）
- LOG_LEVEL（例: INFO / DEBUG）
- MONITOR_POLL_INTERVAL（run_monitoring の間隔、秒）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: 1/0）

---

## ディレクトリ構成（抜粋）

リポジトリはパッケージ化されており、主要なソースは `src/kabusys/` 以下にあります。主要ファイルを抜粋して示します。

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数/.env の自動ロードと Settings クラス
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 起動前チェック CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor 起動スクリプト
    - utils/
      - logging_setup.py       — 共通ログ設定
      - process_priority.py    — プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py       — SQLite テーブル初期化と永続化 API
      - system_monitor.py      — CPU / メモリ / データ鮮度監視
      - trade_monitor.py       — （注文滞留/約定異常等の監視）※実装あり
      - risk_monitor.py        — ドローダウン / ポジション上限監視
      - kill_switch.py         — kill.flag 管理
      - monitoring_engine.py   — 各 Monitor を束ねる
      - alert_manager.py       —（通知管理：LINE 等。実装が存在する可能性あり）
    - execution/
      - execution_engine.py    — ExecutionEngine（エンジン本体）
      - broker_factory.py      — Broker クライアント生成（Mock/Live 切替）
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
    - ai/
      - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py     — レジーム判定
    - tools/
      - paper_verification_report.py
    - data/                    — 実行時に使用される DB / pid / flag を想定するディレクトリ（生成される）

（注）上記は主なファイルのみを抜粋しています。実際のファイル構成は src/kabusys 以下をご確認ください。

---

## 運用上の注意

- 本番運用 (KABUSYS_ENV=live) の場合は必ず設定を慎重に確認してください。validate_config の警告を確認し、LINE 通知等のアラート設定を整備してください。
- kill.flag / stop_requested.flag / execution.pid 等のフラグ / PID ファイル管理に注意してください。誤って残ると意図しない停止や起動不能を招きます。
- OpenAI API を利用する箇所は外部依存であり、APIの利用料金とレートリミット/エラーを考慮してください。API エラー時はフォールバック動作をとる設計ですが、頻繁な失敗は機能低下を招きます。
- DuckDB / SQLite ファイルのバックアップ・保護を行ってください（特に本番）。

---

## 追加情報 / 開発者向け

- config/*.yaml（system_config.yaml など）は設定テンプレートとして使用します。validate_config はこれら YAML の存在／パース検証を行います（PyYAML 必須）。
- 単体テストや CI に関する記述はここでは省略していますが、モジュールは比較的関数分割されておりユニットテストを追加しやすい設計です。
- LLM 呼び出し部分のテストは、モック（unittest.mock.patch）で _call_openai_api を差し替えて実施できます（ソース内にその旨の注記あり）。

---

必要であれば README に実際の .env.example のテンプレート、さらに詳細なコマンド例や systemd / supervisor 用のサービスユニット例、実際の DB スキーマ・サンプルデータの生成手順などを追加できます。希望があれば教えてください。