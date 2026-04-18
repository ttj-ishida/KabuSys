# KabuSys

日本株自動売買システムの一部を含むライブラリ / 実行スクリプト群。  
このリポジトリには監視、実行エンジン起動スクリプト、ポートフォリオ構築ユーティリティ、リサーチ・ファクター計算、AI（ニュース NLP / レジーム判定）、および運用ツールが含まれます。

以下はこのコードベースの概要、機能一覧、セットアップ手順、基本的な使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォーム向けユーティリティ群です。  
主な目的は次の通りです。

- ExecutionEngine の起動 / 停止の管理（本番 / ペーパートレード切替）
- システム稼働監視（CPU / メモリ / ディスク / プロセス監視、データ鮮度）
- リスク監視（ドローダウン・ポジション上限検出）と Kill Switch
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- リサーチ用ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- ニュースを用いた NLP スコアリング（OpenAI を利用）
- ペーパートレード結果の検証レポート生成ツール

設計方針として、DB（DuckDB/SQLite）を用いたデータ参照・永続化、LLM 呼び出しのフェイルセーフ（エラー時はフォールバック）等を採用しています。

---

## 機能一覧

- 設定管理
  - `.env` 自動読み込み（プロジェクトルートを検出して `.env` / `.env.local` を読み込む）
  - `config_setup` による対話式 `.env` ウィザード
  - `validate_config` による起動前チェック（環境変数・config/*.yaml）

- 実行 / 監視
  - `run_execution.py`：ExecutionEngine を起動（`KABUSYS_ENV=paper_trading` 時は MockBroker を使用し DB を分離）
  - `run_monitoring.py`：SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔調整）
  - ログ設定ユーティリティ：コンソール + 日次ローテーションファイル（`kabusys.utils.logging_setup`）
  - プロセス優先度 / CPU affinity 設定（`kabusys.utils.process_priority`）

- 監視 / アラート
  - SystemMonitor（システムリソース・データ鮮度・Execution PID チェック）
  - TradeMonitor / RiskMonitor（注文滞留・約定異常・ドローダウン・ポジション上限監視）
  - KillSwitch（条件を満たしたら `data/kill.flag` を出力して Execution を停止）
  - MonitoringDB：SQLite を用いた監視ログ永続化（schema マイグレーション対応）

- ポートフォリオ構築（純粋関数）
  - 候補選定（score / rank による選出）
  - 重み付け（等配分 / スコア加重）
  - セクター上限適用（セクター集中を防ぐ）
  - ポジションサイズ計算（単元丸め / リスクベース / aggregate cap）

- リサーチ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）等の統計ユーティリティ

- AI（OpenAI）
  - ニュース NLP（raw_news → 銘柄別スコア → ai_scores に書き込み）
  - レジーム判定（ETF の MA200 乖離 + マクロニュースセンチメント）

- ツール
  - Paper Trading 検証レポート生成（期間指定可能）

---

## 必要な外部ライブラリ（主なもの）

主に以下のパッケージが必要です（バージョンはコードベースに依存します）:

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config の YAML 検証を行う場合、任意）

requirements.txt が無い場合は上記をインストールしてください。

例:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. .env の準備
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - または `.env.example` を参照して手動で `.env` を作成

   重要な環境変数（最低限設定が必要）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - OPENAI_API_KEY（AI 機能を使う場合）
   - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
   - その他：DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL, LOG_DIR など

5. ディレクトリ作成
   - data/ （SQLite DB、flag、pid ファイル用）
   - logs/ （ログファイル用）
   多くの処理は起動時に自動でディレクトリを作成しますが、権限に注意してください。

6. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります（exit 1）

---

## 使い方（主なコマンド）

パッケージモジュールとして実行します（プロジェクトルートで実行することを想定）。

- ExecutionEngine を起動（本番/ペーパー自動切替）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合: MockBroker を使い、DB は `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）を使用
    - PID ファイル: data/execution.pid（settings で上書き可）
    - 停止: data/stop_requested.flag が作成されるとエンジンを停止

- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
  - 監視は本番の sqlite_path（設定された SQLITE_PATH）を常に使用します（KABUSYS_ENV に依らず）
  - 停止: data/stop_requested.flag を作成するとループを終了

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話的に作成/更新します

- 設定検証
  - python -m kabusys.validate_config
  - --strict オプションで警告も FAIL として扱う

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプションで --db PATH を指定して DB ファイルを明示できます（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

- AI 機能（コードから呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キー: api_key 引数または環境変数 OPENAI_API_KEY
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- その他ユーティリティはモジュール関数としてインポートして利用可能です（例: portfolio.calc_position_sizes 等）。

---

## 重要な挙動メモ

- Monitoring は KABUSYS_ENV にかかわらず常に「本番」用の sqlite_path（Settings.sqlite_path）を使用します（run_monitoring の設計）。
- Execution は KABUSYS_ENV=paper_trading のとき専用の paper DB を使って完全分離します（PAPER_TRADING_SQLITE_PATH）。
- Kill Switch：
  - RiskMonitor が一定条件を満たすと KillSwitch が `data/kill.flag` に理由を書き込みます。
  - Execution 側は起動時に kill.flag の存在を確認します（停止フラグがある場合は起動しない）。
  - run_execution/run_monitoring は data/stop_requested.flag を見て終了します（停動時はこれを作ることができます）。
- ロギング：
  - setup_logging により stdout と日次ローテートファイル（logs/<app>.log）へ出力します。
  - 環境変数: LOG_LEVEL, LOG_DIR を使用して調整可能。

---

## ディレクトリ構成（主なファイル）

以下は src/kabusys 配下の主要ファイル / パッケージの一覧と簡単な説明です。

- src/kabusys/
  - __init__.py             — パッケージ定義（バージョン等）
  - config.py               — Settings クラス（環境変数 / .env 自動ロード）
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 起動前の設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py           — ニュース NLP（OpenAI を使う、ai_scores 書込み）
    - regime_detector.py    — 市場レジーム判定（MA200 + LLM）

  - monitoring/
    - monitoring_db.py      — SQLite 永続化層（テーブル作成・ログ関数）
    - system_monitor.py     — システム状態・データ鮮度監視
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - trade_monitor.py      — （注文監視、ソースに依存）
    - kill_switch.py        — Kill Switch（flag ファイルの書き込み / クリア）
    - alert_manager.py      — （アラート送信の抽象化、LINE 等）

  - execution/
    - broker_factory.py     — ブローカークライアント生成（Mock/実API 切替）
    - execution_engine.py   — ExecutionEngine（セッション実行）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py  — 候補選定 / 重み付け
    - position_sizing.py    — 株数決定・単元丸め・投下資金スケール
    - risk_adjustment.py    — セクターキャップ・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py    — momentum / volatility / value 等
    - feature_exploration.py— 将来リターン / IC / 統計サマリー
    - __init__.py

  - data/
    - pipeline.py           — prices_daily 等を扱うパイプライン（参照）
    - stats.py              — zscore_normalize など（research で利用）

  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading の検証レポート生成スクリプト

  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度・CPU affinity ユーティリティ
    - __init__.py

（注）一部モジュールはここに示した略称で参照しています。実際のファイルに実装が存在するかはリポジトリのソースを参照してください。

---

## よくある質問 / 運用上の注意

- Q: 本番とペーパートレードの DB は分離されていますか？  
  A: はい。Execution は paper_trading のとき専用 DB（PAPER_TRADING_SQLITE_PATH）を使用します。一方 Monitoring は常に `SQLITE_PATH` を使用します。

- Q: OpenAI を使う機能は安全ですか？  
  A: API 呼び出しはリトライ・フォールバックを備え、失敗時は安全なデフォルトを使用するよう設計されています。ただし API キーは `.env` 等で管理し、漏洩に注意してください。

- Q: kill.flag / stop_requested.flag の違いは？  
  A: `kill.flag` は KillSwitch が書くフラグで ExecutionEngine を停止させるためのものです。`stop_requested.flag` は run_* スクリプトの外部からの停止要求に使われます（どちらも data/ に置かれます）。

---

README はここまでです。実際の運用・拡張時は次の点を確認してください：

- config/*.yaml（テンプレート）やスキーマはプロジェクトのドキュメントに従って生成 / 編集すること
- データ（DuckDB / SQLite）とログのパス、権限設定を本番で十分に確認すること
- OpenAI 使用時のコストとレート制限対策を運用設計に反映すること

必要があれば、この README をベースに起動手順のスクリプト例（systemd / docker / supervisor 用）や .env.example を作成します。要望があれば教えてください。