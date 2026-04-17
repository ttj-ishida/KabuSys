# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買・研究・監視ツール群です。  
スクリプト群は発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント／レジーム判定）などの機能を提供します。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
- 主要な環境変数（.env）
- ディレクトリ構成
- 実行時の注意点 / トラブルシューティング

---

## プロジェクト概要

KabuSys は下記のような目的で設計されたモジュール群です。

- 市場ファクターの計算・リサーチ（DuckDB を使った時系列処理）
- ポートフォリオ構築（候補選定・重み算出・ポジションサイズ計算）
- ExecutionEngine による発注（本番 / ペーパートレードの分離）
- 監視サブシステム（システム状態・注文の滞留・リスク監視、Kill Switch）
- AI を使ったニュースのセンチメント評価と市場レジーム判定
- ペーパートレードの検証レポート生成ツール
- 環境設定ウィザード / 設定検証ツール

コードは主に純粋関数・DB 操作・監視ループなどに分離され、外部 API 呼び出しは明示的な箇所に限定しています（OpenAI / kabuステーション / J-Quants 等）。

---

## 機能一覧

主な機能

- Execution
  - ExecutionEngine による取引セッション実行（本番 / paper_trading 切り替え）
  - BrokerClientFactory による本番 / モックブローカーの選択（KABUSYS_ENV に依存）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / Execution プロセスの死活監視
  - TradeMonitor: 滞留注文チェック・約定価格の異常検出
  - RiskMonitor: ドローダウン・ポジション数上限監視（Kill Switch トリガ）
  - MonitoringEngine / run_monitoring スクリプトで定期ポーリング
- Portfolio
  - 候補選定（スコア順）/ 等配分・スコア加重配分 / セクター制限適用 / ポジションサイズ計算
- Research
  - ファクター計算（Momentum, Volatility, Value 等）
  - 将来リターン計算・IC（Information Coefficient）計算・統計サマリ
- AI
  - news_nlp: OpenAI（gpt-4o-mini）を用いたニュースセンチメント集計と ai_scores への書き込み
  - regime_detector: ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成して市場レジーム判定
- Tools
  - Paper Trading 検証レポート生成スクリプト（paper_verification_report）
- 設定関連
  - config_setup: 対話式 .env 生成ウィザード
  - validate_config: 起動前の設定検証 CLI

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - Python 3.10+ を想定（duckdb / psutil / openai 等のサポートを確認してください）。

2. 依存パッケージをインストールします（例）:
   - requirements.txt が用意されている想定:
     pip install -r requirements.txt
   - 必要な主要パッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証時に YAML 検証をする場合に推奨）
   - SQLite は Python 標準ライブラリで利用可能です。

3. 環境変数を用意する:
   - 対話式ウィザードで .env を生成できます:
     python -m kabusys.config_setup
   - あるいはプロジェクトルートに .env を手動で作成してください（下記「主要な環境変数」を参照）。
   - .env はリポジトリにコミットしないでください（機密情報を含みます）。

4. 設定を検証（任意）:
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. データフォルダ作成:
   - 多くのデフォルトパスは data/ 以下を参照します。必要に応じて作成してください:
     mkdir -p data

---

## 使い方（代表的なコマンド）

- 環境設定ウィザード（.env を生成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 実行エンジンの起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV 環境変数で制御（development / paper_trading / live）
  - paper_trading モードでは MockBrokerClient を使用し、ペーパートレード用 DB（data/paper_trading.db）に記録します。

- 監視ループの起動（SystemMonitor 単体）
  - python -m kabusys.run_monitoring
  - ポーリング間隔の上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - デフォルト 60 秒
  - 監視は KABUSYS_ENV にかかわらず production sqlite_path（SQLITE_PATH）を使用します（監視ログの永続性のため）。

- Paper Trading 検証レポートの生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数またはデフォルト）

- AI 関連（プログラムから呼び出す）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime
  - OpenAI API キーは環境変数 OPENAI_API_KEY に設定するか、関数呼び出し時に api_key 引数で指定します。

---

## 主要な環境変数（.env）

必須（少なくとも実行検証でチェックされるもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

推奨 / 主要
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)。デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視（monitoring）用 SQLite（monitoring.db）デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（例: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- OPENAI_API_KEY — OpenAI を利用する機能で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番通知用（任意）

その他
- PAPER_FILL_MODE — paper_trading モードでの約定挙動（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア (0|1)
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると自動で .env を読み込まない（テスト等）

注意:
- .env の自動読み込みはプロジェクトルートの検出（.git か pyproject.toml）に依存します。
- .env をVCSにコミットしないでください（シークレットを含みます）。

---

## 振る舞い上の重要点 / 実行時の注意

- run_monitoring は監視用 DB（SQLITE_PATH）を使用します。KABUSYS_ENV に依存せず本番 SQLite を参照します（監視ログは分離しない仕様）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離されます。
- 停止フラグ:
  - data/stop_requested.flag — run_execution / run_monitoring がこのファイルを検知すると安全停止します（存在確認だけ）。
  - data/kill.flag — KillSwitch が書き込むことで ExecutionEngine 停止をトリガできます。
- PID ファイル:
  - 実行エンジンは pid ファイルを data/execution.pid（デフォルト）に書きます。SystemMonitor はこの PID を見てプロセス生存チェックを行います。
- process priority / CPU affinity:
  - 起動時に set_process_priority("high") を呼び出します。psutil が必要で、権限不足の場合は警告を出してスキップされます。
- OpenAI 呼び出し:
  - news_nlp / regime_detector は OPENAI_API_KEY が必要です。API 呼び出しはリトライやフォールバック（失敗時の安全値）を内蔵しています。
- PyYAML:
  - validate_config は PyYAML があると config/*.yaml のパースチェックを行います。未インストール時は警告のみ。

---

## ディレクトリ構成（src/kabusys の主なファイル）

以下は主要モジュールのツリー（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込み
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - execution/               — 発注関連（OrderManager, ExecutionEngine など）
    - (複数モジュール参照)
  - monitoring/
    - monitoring_db.py       — SQLite ベースの永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信ロジック）
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
    - news_nlp.py            — ニュースセンチメント (OpenAI)
    - regime_detector.py     — 市場レジーム判定 (OpenAI + MA)
    - __init__.py
  - data/ (実行時に作成される想定)
    - monitoring.db (など)
    - paper_trading.db
    - kabusys.duckdb

---

## よくあるトラブル / デバッグヒント

- ImportError / モジュール不足:
  - duckdb / psutil / openai / PyYAML 等が必要です。requirements.txt があればそこからインストールしてください。
- OpenAI 関連が動かない:
  - OPENAI_API_KEY を設定してください。API 呼び出しはネットワークやレート制限で失敗することがあるため、ログとリトライ挙動を確認してください。
- PID / kill.flag / stop flag の取り扱い:
  - data/stop_requested.flag が存在すると起動スクリプトは安全に起動/継続しません。開発時にすでにフラグが残っていると起動しないので注意してください。
  - KILL_FLAG_CLEAR_ON_START=1 を本番で使うと危険です（validate_config でも警告があります）。
- DuckDB / SQLite パス:
  - デフォルトは data/ 以下です。config_setup でパスを変更できます。親ディレクトリがなければ警告が出ますが起動時に自動生成されることもあります。

---

以上がリポジトリの簡潔な README です。必要であれば次の内容を追記します：
- 各モジュールの API（関数・クラス一覧）詳細
- 実行例（実際の .env の雛形 / サンプルコマンド）
- 開発用ユニットテストの書き方／テスト実行手順

ご希望があれば追記します。