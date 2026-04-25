# KabuSys

日本株自動売買のための内部ライブラリ群および起動スクリプト群です。取引エンジン、監視、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などを含みます。

> 注意: この README はソースコード（`src/kabusys`）の実装に基づいて作成しています。実際の環境で運用する前に `python -m kabusys.validate_config` で設定検証を行ってください。

---

## プロジェクト概要

KabuSys は以下の責務を持つコンポーネント群で構成されています。

- ExecutionEngine（発注エンジン）: broker クライアントを通じて発注を行う。
- Monitoring（監視）: システム稼働状況、約定／注文ログ、リスク（ドローダウン・ポジション上限）を監視し、必要に応じて Kill Switch を発動。
- Portfolio（ポートフォリオ構築）: 候補選定、配分重み計算、ポジションサイズ決定、セクター制限など。
- Research（リサーチ）: ファクター計算（Momentum / Value / Volatility）や特徴量解析（IC 等）。
- AI（ニュース NLP / レジーム判定）: OpenAI を用いたニュースのセンチメント解析や市場レジーム判定。
- ユーティリティ: 設定読み込み、ログ設定、プロセス優先度設定など。

実行モードは `KABUSYS_ENV` で切り替え可能（`development` / `paper_trading` / `live`）。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（`KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し DB は分離）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（ポーリング間隔は環境変数で上書き可）
- 設定管理
  - config_setup.py: 対話式ウィザードで `.env` を生成・更新
  - validate_config.py: 起動前に環境設定と config/*.yaml を検証
- 監視
  - monitoring_engine.py 等で System / Trade / Risk の各 Monitor を束ねて定期実行
  - KillSwitch によるフラグファイル（`data/kill.flag`）で ExecutionEngine 停止
- ポートフォリオ構築
  - 候補選定（スコア・ランク基準）、等分配・スコア加重配分、リスクベースのポジションサイズ算出
- リサーチ
  - DuckDB を用いたファクター計算（momentum / value / volatility）や将来リターン、IC 計算
- AI（OpenAI）
  - ニュース記事をまとめてセンチメントスコアを生成し `ai_scores` に格納
  - マクロニュース + ETF MA200 による市場レジーム判定を DB に書き込み
- ツール
  - paper_verification_report: Paper Trading 用の検証レポート生成

---

## セットアップ手順（開発 / テスト向け）

前提: Python 3.9+ を推奨（typing 機能や型注釈の記載があるため）。プロジェクトルートで作業してください（`.env` 自動ロードや相対パス解決のため）。

1. リポジトリをクローン / 配布パッケージを展開
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - 必須パッケージ（最低限）:
     - duckdb
     - psutil
     - openai
   - 追加（任意／機能に応じて）:
     - PyYAML（`validate_config` の YAML 内容検証で使用）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - 実運用ではバージョン固定の requirements.txt を用意してください。

4. .env の作成
   - 対話ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは `.env.example` を参考に `.env` を手動で作成
   - 重要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY を設定

5. 設定検証
   - python -m kabusys.validate_config
   - `--strict` を付けると警告も失敗扱いになります

6. データディレクトリの準備（ログ・DB 等）
   - デフォルトでは以下のファイル/ディレクトリが使われます:
     - data/kabusys.duckdb (DUCKDB_PATH)
     - data/monitoring.db (SQLITE_PATH)
     - data/paper_trading.db (PAPER_TRADING_SQLITE_PATH, paper_trading モード)
     - logs/（ログファイル保存先）
   - 起動スクリプトが必要に応じてディレクトリを作成しますが、パーミッションに注意してください。

---

## 主要環境変数（代表）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行制御 / 環境
  - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- データベースパス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（monitoring.db）パス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- Paper Trading 固有
  - PAPER_FILL_MODE — instant / partial / never / reject（デフォルト: instant）
- AI
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で必要）
- Monitoring
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
- Kill / 停止フラグ
  - KILL_FLAG_PATH — KillSwitch が書き込む flag ファイル（デフォルト: data/kill.flag）
  - PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
  - KILL_FLAG_CLEAR_ON_START — 起動時に Kill Flag を自動クリアするか（0/1、デフォルト: 0）

詳しくは `src/kabusys/config.py` の `Settings` を参照してください。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告もエラー扱い）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（注文エンジン）
  - python -m kabusys.run_execution
  - 振る舞い:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper 用 DB（PAPER_TRADING_SQLITE_PATH）に記録
    - data/stop_requested.flag が存在すると起動せず終了
    - 実行中は data/execution.pid を使う

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 監視は常に `Settings.sqlite_path`（監視 DB）を使用（環境にかかわらず本番の path を参照する仕様）
  - Stop フラグ: プロジェクトルートの data/stop_requested.flag を検出すると監視ループを終了

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH で SQLite ファイルを指定（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

- AI 関連（プログラムから利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも `OPENAI_API_KEY` または引数 `api_key` が必要

- ログ
  - デフォルトは logs/<app_name>.log（TimedRotatingFileHandler、日次ローテート、30日保持）と stdout に出力
  - ログ設定は kabusys.utils.logging_setup.setup_logging で統一

停止 / Kill
- 運用上の停止指示:
  - ExecutionEngine を安全に停止させたい場合は KillSwitch が書き込む `data/kill.flag`（通常は Monitoring が自動的に書き込む）
  - 手動停止を行う場合はプロジェクトルートの `data/stop_requested.flag` を作成すると run_execution/run_monitoring が検知して終了します。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 以下の主なモジュールの構成例です（抜粋）。

- kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照されるが実装ファイルが存在する場合)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (上記)
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に使用されるディレクトリ、DB やフラグファイルを格納)
  - logs/ (ログ出力先)

※ 上記はリポジトリに含まれているソースの一覧を要約したものです。実際のリポジトリではさらに細かい実装ファイルやテスト、スクリプト等が存在する可能性があります。

---

## 実運用上の注意点

- KABUSYS_ENV が `live` のときは設定ミスが重大な影響を及ぼします。`validate_config` の警告を十分に確認してください。
- OpenAI を利用する機能は API コストとレイテンシに注意し、API キーの管理を厳重に行ってください。
- DB（特に production 用）へのアクセスは権限やバックアップ方針を検討してください。Paper Trading は本番 DB と分離する設計です。
- ログ/DB ディレクトリの権限や容量管理を行ってください。
- PID / flag ファイル（data/execution.pid, data/kill.flag, data/stop_requested.flag）を適切に運用してください（誤った削除や誤検出に注意）。

---

## 開発・拡張のヒント

- 設定は `kabusys.config.Settings` から集中管理されています。新しい設定を追加する場合はここを変更してください。
- ロギングは `kabusys.utils.logging_setup.setup_logging` を全起動スクリプトで呼び出して統一してください。
- DuckDB を用いたリサーチ系処理は SQL と Python を組み合わせる設計です。テスト時は小さな DuckDB ファイルを用意すると高速です。
- AI モジュールの外部 API 呼び出しは `_call_openai_api` や `_score_chunk` を patch/mocking することで単体テストを容易にできます。

---

必要があれば README に含めるサンプル .env のテンプレートや、よくあるトラブルシューティング（依存関係、権限、DB マイグレーション例）を追加します。どの項目を詳しく追記しましょうか？