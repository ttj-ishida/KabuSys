# KabuSys

日本株自動売買システムのモジュール群（ライブラリ＋起動スクリプト群）。

概要、セットアップ、使い方、ディレクトリ構成などをこのリポジトリ内のコードに基づいて日本語でまとめた README です。

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたシステム群です。主な役割は以下の通りです。

- 発注エンジン（ExecutionEngine）による注文管理・発注・リスク制御
- 監視（Monitoring）コンポーネントによるシステム稼働・注文状況・リスク監視
- ポートフォリオ構築（候補選定、ウェイト計算、ポジションサイズ決定）
- リサーチ（ファクター計算、特徴量探索）
- AI 製のニュース NLP / レジーム判定（OpenAI API 経由）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証など）
- ペーパートレード用の分離された DB と Mock ブローカー対応

コアは Python で実装され、DuckDB（分析用）および SQLite（監視・ペーパートレード記録）を用います。

---

## 主な機能一覧

- Execution
  - ExecutionEngine：ブローカークライアント経由の注文発行・管理
  - RiskManager / OrderManager / Reconciler 等による安全運転
  - paper_trading モードでは MockBrokerClient による完全分離（data/paper_trading.db）
- Monitoring
  - SystemMonitor：CPU/メモリ/Disk、プロセス存在、データ鮮度監視
  - TradeMonitor：滞留注文や約定異常などの監視（trade_logs）
  - RiskMonitor：ドローダウン・ポジション上限監視と Kill Switch への連携
  - AlertManager 経由で通知（LINE 等のトークン設定で有効化）
- Portfolio
  - 銘柄候補選定、等分/スコア加重、リスクに基づく位置付け、セクター制限、レジーム乗数
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン・IC 計算、統計サマリ
- AI
  - news_nlp: OpenAI を使ったニュースセンチメント集計 → ai_scores に保存
  - regime_detector: ma200 とマクロニュースで市場レジーム判定、market_regime テーブルへ書き込み
- ツール
  - 環境設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report）

---

## 必要条件（例）

- Python 3.10+
- 依存ライブラリ（代表）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml 検証を行う場合）
- SQLite（標準ライブラリで使用）
- ネットワークアクセス（kabuステーション API / OpenAI 等を使用する場合）

必要なパッケージは pyproject.toml / requirements.txt があればそちらを参照してインストールしてください。

例（仮）:
pip install duckdb psutil openai pyyaml

---

## セットアップ手順

1. リポジトリをクローン / checkout して作業ディレクトリへ移動。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - requirements.txt がない場合は必要パッケージを個別にインストール（duckdb, psutil, openai, pyyaml など）

4. .env を作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants トークン、kabu API パスワード、DB パス、KABUSYS_ENV 等の設定を対話形式で保存します。
   - 生成された .env は Git にコミットしないでください（秘匿情報を含む）。

5. 設定検証（必須環境変数のチェックや config/*.yaml の存在確認）
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにするには --strict を付ける

6. （任意）OpenAI を使う場合は環境変数 OPENAI_API_KEY を設定する
   - export OPENAI_API_KEY="sk-..."（Unix）
   - WINDOWS: setx OPENAI_API_KEY "sk-..."

7. ディレクトリ（data, logs 等）の作成
   - 多くは自動作成されますが、権限等で失敗する場合は手動で作成してください。
   - デフォルトの DB ファイル:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db

---

## 重要な環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 推奨 / オプション
  - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
    - paper_trading の場合、Execution は MockBrokerClient を使用し paper_trading DB に記録
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（任意）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1。デフォルト 0。本番では 0 推奨）
  - PAPER_FILL_MODE — ペーパートレードの約定動作（instant / partial / never / reject）
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、run_monitoring で使用。デフォルト 60）

---

## 起動方法（代表的なスクリプト）

すべての起動スクリプトはモジュールとして実行できます（パッケージルートで実行）。

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し data/paper_trading.db に記録
  - 起動時に data/stop_requested.flag が存在すると起動しません
  - 実行中に data/stop_requested.flag が作成されるとエンジン停止を試みます
  - プロセス PID は data/execution.pid に書き込まれます（設定に依存）

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定可能（デフォルト 60）
  - 監視は Settings.sqlite_path にある SQLite DB（monitoring DB）へ書き込みます（環境にかかわらず本番 sqlite_path を使用）
  - 停止フラグ: project_root/data/stop_requested.flag を検知してループを終了します

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict で警告も失敗扱いにできます

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数でも可）

- AI 機能（例）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、ai_scores / market_regime 等のテーブルを書き込みます
  - OPENAI_API_KEY が必要（引数で渡すことも可能）

---

## ログ / フラグ / PID

- ログ
  - ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます（30 日保持）。
  - setup_logging() を各スクリプトが使っています（console 出力は stdout）。

- 終了 / 停止制御
  - data/stop_requested.flag：run_execution/run_monitoring の短期停止フラグ（スクリプトが存在を検知して終了）
  - data/kill.flag：KillSwitch が作成するフラグ（ExecutionEngine に対する致命的停止シグナル）
  - KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に kill.flag を自動クリアします（本番では危険なので 0 推奨）

- PID ファイル
  - ExecutionEngine は PID を data/execution.pid 等に書き込みます（Settings.pid_file_path で指定）

---

## ディレクトリ構成（主要ファイル）

以下は主要モジュールの構成（src/kabusys 下）。実際のファイル数はこれより多いことがあります。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env ロード機能含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ（Stream + TimedRotatingFile）
    - process_priority.py    — プロセス優先度・CPU affinity 設定
  - execution/               — 実行エンジン関連（Engine, OrderManager, BrokerFactory 等）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義・永続化ラッパー
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文ログ監視（滞留・約定異常）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch ロジック（flag 書込）
    - monitoring_engine.py   — 複数 Monitor を束ねる実行ループ
    - alert_manager.py       — 通知送信（LINE などをつなぐ想定）
  - portfolio/
    - portfolio_builder.py   — 銘柄候補選定、等分/スコア加重
    - position_sizing.py     — 発注株数計算（単元丸め・aggregate cap 等）
    - risk_adjustment.py     — セクター上限・レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum / volatility / value）
    - feature_exploration.py — 将来リターン・IC / 統計サマリ
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）を使った銘柄スコアリング
    - regime_detector.py     — マクロ+MA200 を組み合わせたレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

---

## 開発時の注意 / 動作設計のポイント

- Settings は .env を自動ロードしますが、テストなどで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- paper_trading モードは本番 DB と完全分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- AI 関連は外部 OpenAI API に依存するため、APIキーやレート制限、JSON バリデーション等に注意してください。失敗時はフェイルセーフ（スコア 0・スキップ）を取る設計です。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します（設定ミスで静かに失敗しないよう配慮）。
- process_priority はプラットフォーム（Windows / POSIX）に合わせて適切に処理されますが、権限不足で設定に失敗する場合があります（警告が出ます）。

---

## よく使うコマンド例

- .env を作る（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジンを起動
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 監視ループを起動（ポーリング間隔 30 秒に変更して起動）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート（期間指定）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## サポート / 拡張ポイント

- BrokerClient の実装差し替えで任意のブローカーに対応可（kabu API 実装 / Mock 実装など）
- portfolio / research モジュールは純粋関数群で設計されており、テスト・差し替えが容易
- AI モジュールはエラーハンドリングと冪等性を重視（部分失敗時の DB 保護）
- config/*.yaml に基づく追加設定やパラメータ化が想定されています（validate_config が存在）

---

もし特定のスクリプトの実行例や .env の推奨テンプレート（.env.example）などが必要であれば、追加で用意します。どの部分を深掘りしますか？