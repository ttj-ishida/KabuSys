# KabuSys — 日本株自動売買システム（README）

以下はこのリポジトリ（src/kabusys）に含まれる主要モジュールの概要、セットアップ方法、使い方、ディレクトリ構成の説明です。開発者・運用者向けの簡易ドキュメントとして記載しています。

注意: 本プロジェクトは .env による環境変数駆動です。まず .env を作成してから各スクリプトを実行してください。

---

## プロジェクト概要
KabuSys は日本株向けの自動売買システムのコンポーネント群です。主な目的は以下：

- 売買シグナルの計算・銘柄選定・ポジションサイズ決定（Portfolio construction）
- 注文の発行および管理（ExecutionEngine）
- システム稼働監視・リスク監視・Kill Switch（Monitoring）
- Paper Trading の検証・レポート作成ツール
- 研究用モジュール（ファクター計算・特徴量解析）
- ニュースを使った AI（LLM）ベースのセンチメント評価 / レジーム判定

設計方針としては、DuckDB / SQLite をデータ層に使い、外部 API 呼び出し（kabuステーション, J-Quants, OpenAI 等）は設定に応じて使用します。Paper Trading は本番 DB と明確に分離されます。

---

## 主な機能一覧
- 環境設定ウィザード（.env 生成）: config_setup.py
- 設定検証 CLI（.env / config/*.yaml の整合性チェック）: validate_config.py
- ExecutionEngine 起動スクリプト（本番 / ペーパートレード対応）: run_execution.py
- Monitoring ポーリング（システム状態・注文状態・リスク監視）: run_monitoring.py
- Kill Switch 実装（条件に応じて data/kill.flag を書く）と停止フラグ連携
- Paper Trading 検証レポート出力ツール: tools/paper_verification_report.py
- Portfolio (候補選定, 重み計算, ポジションサイズ算出)
- Research（ファクター計算、forward returns、IC 計算、統計サマリー）
- AI モジュール
  - news_nlp: ニュース記事を LLM に投げて銘柄ごとのセンチメントを ai_scores テーブルへ書き込み
  - regime_detector: ma200 とマクロニュースの LLM センチメントを合成して市場レジーム判定
- ユーティリティ
  - logging_setup: 統一的なログ設定（コンソール + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定
- DB スキーマ管理（監視用 SQLite の初期化・マイグレーション）

---

## セットアップ手順

前提:
- Python 3.10 以上（型アノテーションの | 記法等を使用）
- SQLite（標準ライブラリ）・DuckDB（pip パッケージ）を利用
- OpenAI を使う機能を使う場合は OpenAI API キーが必要

1. リポジトリをクローン / checkout
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - 任意: PyYAML（config 検証で YAML 内容チェックを有効にする場合）
     - pip install pyyaml
   ※ requirements.txt は本リポジトリに含めていない想定のため、上記をプロジェクトに合わせて管理してください。

4. .env の作成
   - 対話式に生成する（推奨）:
     - python -m kabusys.config_setup
   - 手動編集でも可。最低限必要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - デフォルトファイルパス（Settings クラスのデフォルト）:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も failure 扱いにする場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリ・ログディレクトリ
   - 実行時に自動作成されますが、必要に応じて手動で作成できます:
     - data/
     - logs/

---

## 環境変数（主要なもの）
（.env に設定する想定。設定ウィザードでも入力可能）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーションベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト logs/）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）
- PAPER_FILL_MODE: paper_trading 時の MockBroker の fill モード（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

自動読み込み:
- プロジェクトルートに .env / .env.local がある場合、起動時に自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

---

## 使い方（主要スクリプト / コマンド）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱い

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
    - 起動時に data/stop_requested.flag が存在すると起動を中止します。
    - エンジンは別スレッドで run_session を実行。停止フラグ検知で Engine.stop() を呼び停止します。
    - 実行前に .env を設定し、必要な DB ファイル・設定を確認してください。

- Monitoring 起動（ポーリング監視）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - Monitoring は環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用します（監視ログは monitoring.db）。
  - 停止は data/stop_requested.flag を生成することで行います。

- Paper Trading 検証レポート（CLI）
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
  - 出力: 稼働率、注文成功率、送信率、レイテンシ（P95）等のサマリと PASS/FAIL 判定

- AI 機能（プログラム呼び出し）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)
    - OpenAI キーは引数または環境変数 OPENAI_API_KEY。結果は ai_scores テーブルへ書き込まれます。
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（duckdb.connect(...)）を受け取り、DB 内のテーブルを更新します。

- Research / Portfolio（ライブラリとして利用）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
  - これらは純粋関数群であり、DuckDB 接続やパラメータを渡して利用します。ユニットテストやオフライン解析に適しています。

---

## 停止・Kill Switch
- 停止フラグ（run_monitoring / run_execution が監視するもの）
  - data/stop_requested.flag : 実行スクリプトの外部停止フラグ。存在を検知するとループを抜けます。
- Kill Switch（監視が一定条件を満たした場合に作成）
  - data/kill.flag : KillSwitch による停止指示。ExecutionEngine は起動時にこのフラグの有無や設定に依存したガードを持ちます（KILL_FLAG_CLEAR_ON_START 設定の影響あり）。

---

## ログ
- 共通ロギングユーティリティで stdout と日次ローテートファイルを統一的に扱います。
  - デフォルトログディレクトリ: logs/
  - ログファイル名はアプリ名プレフィックス（例: execution → logs/execution.log）
  - ログの保持: 日次ローテーションで 30 日分

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要モジュール・ファイル構成です（抜粋）:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込みロジック
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート CLI
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 株数決定・丸め・上限処理
    - risk_adjustment.py       — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py       — Momentum/Volatility/Value 計算
    - feature_exploration.py   — forward returns / IC / summary
  - ai/
    - news_nlp.py              — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py       — レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py         — SQLite 監視 DB 初期化・CRUD ラッパ
    - system_monitor.py        — システム状態・データ鮮度監視
    - trade_monitor.py         — 注文監視（滞留注文、約定異常等） ※（実装あり）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — KillSwitch 実装
    - monitoring_engine.py    — 各モニタの束ね（ポーリング実行）
    - alert_manager.py        — 通知（LINE 等） ※（実装あり）
  - execution/
    - execution_engine.py     — ExecutionEngine 本体（注文ループ等） ※（実装あり）
    - broker_factory.py       — Broker クライアント生成（Mock / real）
    - order_manager.py        — 注文管理
    - order_repository.py     — 発注履歴等リポジトリ
    - reconciler.py           — 差分照合
    - risk_manager.py         — 発注時のリスク制御
  - data/                     — スキーマ / ETL / pipeline 等（prices_daily, raw_news 管理等） ※（実装あり）
  - utils/
    - logging_setup.py        — ログ設定
    - process_priority.py     — プロセス優先度 / CPU affinity

（注）実際の細かな実装（execution_engine の実装、broker client 等）は該当ファイルを参照してください。

---

## 実運用上の注意
- KABUSYS_ENV が `live` の場合は本番扱いです。LINE 通知や Kill Switch の設定等を必ず確認してください。
- .env を絶対に VCS にコミットしないでください（config_setup.py でも注意書きあり）。
- OpenAI API を利用する処理はコストが発生するため、テスト時はモックするかキーを用意した上で注意して実行してください。
- run_monitoring は監視ログ用の SQLite（設定次第で本番 DB）に書き込みます。設定に応じたパスを確認してください。
- process_priority.set_process_priority() は実行環境に応じた権限が必要な場合があります。失敗時は警告が出て処理は継続します。

---

## 参考コマンド例

- .env を生成（対話式）
  - python -m kabusys.config_setup

- 設定確認
  - python -m kabusys.validate_config

- ペーパートレードで実行（環境変数指定例）
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- 監視プロセス起動（60秒間隔）
  - python -m kabusys.run_monitoring
  - 60 秒間隔を変更する場合:
    - export MONITOR_POLL_INTERVAL=30

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - or 指定 DB:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

---

この README は利用開始に必要な基本情報をまとめたものです。各モジュールの詳細な仕様やアルゴリズム（PortfolioConstruction.md など）は別ドキュメントを参照してください。追加で README の改善点や、各スクリプトの引数・ログ例などを追記希望があれば教えてください。