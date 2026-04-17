# KabuSys

KabuSys は日本株向けの自動売買・研究基盤です。バックテスト・ポートフォリオ構築・発注・監視・AI（ニュースセンチメント／レジーム判定）などの機能をモジュール化して提供します。

以下はこのコードベースの概要・セットアップ・使い方・ディレクトリ構成のまとめです。

---

## プロジェクト概要

- 目的: 日本株の自動売買システムと研究ツール群を提供する。
- 主な役割:
  - 注文実行エンジン（ExecutionEngine）
  - 監視（Monitoring） — システム状態・注文滞留・リスク監視・Kill Switch
  - ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）
  - リサーチ（ファクター計算・特徴量探索）
  - AI モジュール（ニュースセンチメント、マーケットレジーム判定：OpenAI を利用）
  - 各種ユーティリティ（プロセス優先度設定、設定管理など）
  - ツール: ペーパートレード検証レポート生成など

---

## 機能一覧（抜粋）

- 設定管理
  - .env 自動読み込み（プロジェクトルートの `.env` / `.env.local`）
  - 対話式設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
- 実行 / 発注
  - run_execution.py: ExecutionEngine を起動
  - paper_trading 環境では MockBrokerClient を使用し、本番 DB と分離（data/paper_trading.db）
- 監視
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）
  - MonitoringEngine: System / Trade / Risk モニタを統合してアラート・Kill Switch を評価
  - Kill Switch: data/kill.flag により ExecutionEngine を停止
- ポートフォリオ構築
  - 候補選定（スコア順）、等配分・スコア配分、セクター上限適用、ポジションサイズ計算（単元丸め、リスクベース等）
- リサーチ
  - ファクター計算（Momentum / Volatility / Value 等）
  - 特徴量探索、将来リターン計算、IC（Information Coefficient）
- AI
  - ニュースの NLP による銘柄別スコアリング（OpenAI API）
  - マクロニュース＋ETF MA で市場レジーム判定（OpenAI API）
- ツール
  - paper_verification_report: ペーパートレード DB から検証レポートを生成

---

## セットアップ手順

1. Python 環境
   - Python 3.9+ を推奨（プロジェクトで使用している構文・型注釈に準拠）
2. 依存ライブラリのインストール（最小例）
   - pip install duckdb psutil openai PyYAML
   - （SQLite は標準ライブラリに含まれます）
   - 必要に応じて requirements.txt を作成して pip install -r requirements.txt
3. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 役立つ環境変数
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
     - OPENAI_API_KEY — OpenAI を利用する場合必須
     - LOG_LEVEL — DEBUG/INFO/...
   - 自動読み込みを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1
4. データディレクトリ作成
   - デフォルトでは data/ に DB やフラグファイルを置きます。必要に応じてディレクトリを作成してください:
     - mkdir -p data
5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告を厳密に FAIL にしたい場合は --strict を付ける

注意: 本番（KABUSYS_ENV=live）では .env に機密情報を含むため Git 管理対象から除外してください（config_setup も README に指示あり）。

---

## 使い方（主要コマンド）

- 設定ウィザード（.env 作成／更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録して本番 DB と分離
    - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了
    - 実行中は data/execution.pid に PID を書きます
    - 停止は data/stop_requested.flag の作成でシグナル送信（および Kill Switch により data/kill.flag が発行される場合があります）

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    - MONITOR_POLL_INTERVAL（秒。デフォルト 60）
  - Monitoring は常に本番用の sqlite_path（Settings.sqlite_path）を参照して監視データを記録します
  - 停止条件: data/stop_requested.flag の存在を検知するとループ終了

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 関連（プログラム API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - api_key が None の場合は環境変数 OPENAI_API_KEY を参照
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意点:
- OpenAI 関連関数は api_key 未設定だと ValueError を出します。環境変数 OPENAI_API_KEY をセットしてください。
- MONITOR_POLL_INTERVAL は 1 未満や無効値のとき 60 秒にフォールバックします。

---

## 主要設定項目（よく使うもの）

- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - paper_trading: 発注はモック、DB は data/paper_trading.db に分離
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（分析用）
- SQLITE_PATH: 監視用 SQLite（monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading.db）
- OPENAI_API_KEY: OpenAI API を利用するなら必須
- LOG_LEVEL: ログ出力レベル（INFO 等）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（開発用。0/1）

---

## ディレクトリ構成（抜粋）

（リポジトリ内の src/kabusys 配下を記載）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数／.env 読み込みロジックと Settings
  - config_setup.py            — 対話式 .env 作成ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py
  - monitoring/
    - monitoring_db.py         — SQLite による監視ログ永続化
    - system_monitor.py        — システム・データ鮮度監視
    - trade_monitor.py         — 注文滞留・約定異常監視
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - monitoring_engine.py     — 各モニタをまとめるエンジン
    - kill_switch.py           — kill.flag 書き込みロジック
    - alert_manager.py         — （アラート送信役、実装箇所）
  - execution/                  — Execution（発注・注文管理）関連モジュール群
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - execution_engine.py
    - order_record.py
    - ...
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 株数算出・サイズ調整
    - risk_adjustment.py       — セクター上限・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py      — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py  — 将来リターン計算・IC・統計サマリー
    - __init__.py
  - ai/
    - news_nlp.py             — ニュースを OpenAI でスコアリング
    - regime_detector.py      — マクロ + ETF MA によるレジーム判定（OpenAI 併用）
    - __init__.py
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
    - __init__.py
  - data/                      — デフォルトデータディレクトリ（DB・PID・flag 等を配置）

---

## 運用上の注意 / ベストプラクティス

- 本番環境では KABUSYS_ENV=live を使う前に必須環境変数と LINE 通知設定を確認してください（validate_config.py のライブガードを参照）。
- Kill Switch（data/kill.flag）や stop_requested.flag を利用して安全に実行系を停止できます。KILL_FLAG_CLEAR_ON_START は本番で 1 にしないことを推奨します。
- OpenAI API を使用する機能は API レート制限やネットワーク障害に備えたリトライ実装がありますが、API キー管理に注意してください。
- paper_trading モードは本番 DB と完全分離するよう設計されています。ペーパートレード用 DB は PAPER_TRADING_SQLITE_PATH を指定してください。
- DuckDB / SQLite のファイルパスは .env で明示することを推奨します（デフォルトは data/*.db）。

---

## トラブルシューティング（よくある問題）

- 「環境変数が設定されていません」エラー:
  - 必須の環境変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）を .env に設定するか、環境にエクスポートしてください。
- OpenAI 呼び出しで Key エラー:
  - OPENAI_API_KEY が設定されているか確認してください。関数は引数で api_key を受け取るものもあります。
- run_monitoring のポーリング間隔を変更したい:
  - 環境変数 MONITOR_POLL_INTERVAL=<秒> を設定（1 以上の整数）。不正値はデフォルト 60 秒にフォールバック。

---

この README はコードベース内のモジュール実装に基づく要約ドキュメントです。詳細な実装や追加オプションは各モジュールの docstring / コメントを参照してください。必要であれば各サブモジュールの使用例や API ドキュメントを別途作成できます。