# KabuSys

日本株向け自動売買システムのコアライブラリ群・起動スクリプト群です。  
本リポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視機能・研究用ツール・AI（ニュースNLP / レジーム判定）を含む実用的な構成を想定しています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の主要機能を持ちます。

- 戦略（ファクター計算 / 特徴量探索）
- ポートフォリオ構築（候補選定、重み付け、株数計算）
- 発注実行エンジン（本番/ペーパー取引を分離）
- リスク管理・監視（ドローダウン・ポジション上限・プロセス死活監視）
- AI モジュール（ニュースセンチメント、レジーム判定） — OpenAI API を利用
- 運用支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）
- ログ出力（コンソール + 日次ローテーションファイル）

設計方針の一部：
- DB は DuckDB（分析用）と SQLite（監視 / 発注ログ）を併用
- 環境ごとに挙動を切り替え（KABUSYS_ENV: development / paper_trading / live）
- 本番とペーパー取引は DB を分離して影響を回避
- 外部 API（OpenAI / kabuステーション / J-Quants）は設定により有効化

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine 起動（発注エンジン）
  - run_monitoring.py — SystemMonitor のポーリングループ起動（監視 daemon）
- 設定関連
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — .env と config/*.yaml の起動前検証
  - config.Settings — 環境変数集約・取得ユーティリティ
- 監視（monitoring）
  - monitoring_engine.py — 各モニタの統合ポーリング
  - system_monitor.py / trade_monitor.py / risk_monitor.py — 各種チェック
  - kill_switch.py — 条件に基づく kill.flag 発行（実行エンジン停止）
  - monitoring_db.py — SQLite テーブル定義 + 永続化 API
- 発注・実行（execution）関連
  - BrokerClientFactory / ExecutionEngine / OrderManager / RiskManager 等（実行系）
  - ペーパートレード時は MockBrokerClient と専用 DB を使用
- ポートフォリオ（portfolio）
  - 銘柄選定、重み付け、ポジションサイズ決定、セクター制限、レジーム乗数
- 研究（research）
  - factor_research.py / feature_exploration.py — ファクター計算・IC 等
- AI（ai）
  - news_nlp.py — ニュースを使ったセンチメントスコアリング（OpenAI）
  - regime_detector.py — マクロ + ETF MA を合成した市場レジーム判定
- ツール
  - tools/paper_verification_report.py — ペーパートレード検証レポート生成
- ユーティリティ
  - utils.logging_setup — 統一ログ設定
  - utils.process_priority — プロセス優先度 / CPU affinity 設定

---

## セットアップ手順

前提
- Python 3.9+（コードは型注釈とモダンな標準ライブラリを使用）
- 任意で仮想環境を推奨

1. リポジトリをクローン / コピー
2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存ライブラリをインストール
   - requirements.txt がある場合: pip install -r requirements.txt  
     （本リポジトリでは主要ランタイム依存: duckdb, psutil, openai, PyYAML（検証用）などが想定されます）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env の準備
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または .env.example をコピーして手動で編集（.env.example を用意している前提）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI 機能を使う場合:
     - OPENAI_API_KEY を設定

5. データディレクトリ作成
   - デフォルトで data/ 以下に DB・フラグファイルなどが格納されます。ログは logs/ に出力されます。
   - 必要に応じて以下の環境変数でパスを変更可能:
     - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, LOG_DIR

注意: Settings モジュールはプロジェクトルートにある .env / .env.local を自動ロードします（自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

## 使い方（主要コマンド）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告を厳格扱いにする場合: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - 本番 / ペーパーは KABUSYS_ENV に依存:
    - 本番: export KABUSYS_ENV=live
    - ペーパー: export KABUSYS_ENV=paper_trading
  - 起動:
    - python -m kabusys.run_execution
  - 停止:
    - run_execution は data/stop_requested.flag を監視しており、該当ファイルが存在するとエンジンを停止します。
    - また監視側が kill.flag を書き込むと ExecutionEngine に停止シグナルを送れます（kill_switch）。

- 監視ループ起動（SystemMonitor）
  - ポーリング間隔は環境変数で上書き可:
    - export MONITOR_POLL_INTERVAL=30  （秒）
  - 起動:
    - python -m kabusys.run_monitoring
  - run_monitoring は data/stop_requested.flag を存在チェックして停止します。
  - 監視は監視用 SQLite（Settings.sqlite_path）を使用（監視は常に本番 monitoring.db を参照します）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キーを設定（OPENAI_API_KEY）
  - news_nlp.score_news / regime_detector.score_regime を呼び出して DuckDB に書き込みます（主にバッチ処理として想定）。

- ログ
  - ルートロガーはコンソール（stdout）とファイル（logs/<app_name>.log、日次ローテート）を出力します。
  - ログレベルは環境変数 LOG_LEVEL で指定（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN —（必須）J-Quants API トークン
- KABU_API_PASSWORD —（必須）kabuステーション API パスワード
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）

---

## 運用上のファイル・フラグ

- data/stop_requested.flag — 各起動スクリプトはこのファイルを監視して優雅に終了します
- data/kill.flag — KillSwitch が書き込み、ExecutionEngine に停止を促す
- data/execution.pid — ExecutionEngine の PID ファイル（設定でパス変更可）
- logs/ — ログ出力先（日次ローテーション）

---

## ディレクトリ構成

以下は主要ファイル・ディレクトリの概要（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py            — ニュース NLP / OpenAI 統合
    - regime_detector.py     — 市場レジーム判定
  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義 + DB API
    - monitoring_engine.py   — 監視エンジン（各 Monitor の統合）
    - system_monitor.py
    - trade_monitor.py       — （コード中に参照あり）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py       — （アラート送信管理、コード参照）
  - execution/
    - execution_engine.py    — 発注エンジン（EngineConfig, run_session 等）
    - broker_factory.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                    — 実行時に使用される default path（例: data/*.db, flags）
  - logs/                    — ログ出力先（デフォルト）

---

## 開発・拡張メモ

- DuckDB 接続を渡す設計により、研究コードは本番 DB に直接アクセスせずに分析可能です（安全性向上）。
- AI 呼び出しは再試行・バックオフ・レスポンス検証を実装しており、フォールバック動作を用意しています（失敗してもシステム継続）。
- process_priority や CPU affinity は psutil を用いており、プラットフォーム（Windows / POSIX）差分を吸収します。権限不足時は警告を出してスキップします。
- config/ 以下の YAML 設定は validate_config により存在・パースをチェックします（PyYAML がインストールされている場合）。

---

## よくある操作例

- .env を作成して検証:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- ペーパートレードレポート（直近デフォルト DB）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- 監視（デフォルト 60 秒間隔）をデバッグ的に 10 秒ごとに:
  - MONITOR_POLL_INTERVAL=10 python -m kabusys.run_monitoring

---

必要があればセクション（API 詳細、DB スキーマ説明、設定項目の完全一覧、運用手順）を追加で作成します。どの部分を詳しくしたいか指示してください。