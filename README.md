# KabuSys

日本株自動売買システム（ライブラリ & 実行スクリプト群）

このリポジトリは、システム監視・発注エンジン・ポートフォリオ構築・リサーチ・AI 補助モジュール等を含む自動売買基盤のコードベースです。本 README ではプロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は日本株向けの資産運用自動化フレームワークです。主な役割は次の通りです。

- マーケットデータ（DuckDB）を使ったファクター計算・特徴量分析（research）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ決定）
- 発注ロジックを担う ExecutionEngine（本番 / ペーパートレード対応）
- 実行状況・システム状態を記録する監視（Monitoring）
- ニュースを LLM(OpenAI) で解析してスコア化する AI モジュール
- 簡易ツール群（例: ペーパートレード検証レポート生成）
- 環境設定ウィザード・設定検証ツール等の CLI 補助

設計方針として、DB 操作や外部 API 呼び出しは明示的に分離され、ユニットテストしやすい純粋関数と薄い IO 層で構成されています。

---

## 機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - paper_trading モード時は MockBrokerClient を使い専用 SQLite に書き込み
  - 停止用フラグ検出（data/stop_requested.flag）や PID ファイル管理

- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた監視エンジン
  - システムリソース／データ鮮度／滞留注文／ドローダウン検出
  - Kill Switch（条件で data/kill.flag を書き込み Execution を停止）
  - run_monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL によるポーリング間隔上書き

- Portfolio
  - 候補選定（score 降順）
  - 重み計算（等額・スコア加重）
  - ポジションサイズ計算（リスクベース / 等分配）、単元株丸め、資金スケーリング
  - セクター上限・レジーム乗数の適用

- Research
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI
  - ニュース NLP（OpenAI）で銘柄別センチメントを ai_scores に書き込み
  - レジーム判定（ETF の MA200 乖離とマクロニュースの LLM スコア合成）

- Utilities
  - 統一的なログ設定（logs/ 日次ローテーション）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - .env ウィザード（config_setup）と設定検証（validate_config）
  - tools: ペーパートレード検証レポート生成

---

## 必要な依存パッケージ（例）

コード中で使われている主要依存ライブラリは次の通りです。環境に応じて適宜インストールしてください。

- Python 3.9+（型ヒント等を想定）
- duckdb
- psutil
- openai
- PyYAML（設定検証で YAML パースを行う場合に任意）
- （SQLite は標準ライブラリで利用可能）

例:
pip install duckdb psutil openai PyYAML

※ 実際の requirements.txt がある場合はそちらを使ってください。

---

## セットアップ手順（ローカル実行向け）

1. リポジトリをクローンし、Python 仮想環境を作成・有効化します。

   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールします。

   - pip install duckdb psutil openai PyYAML
   - （必要に応じて他のパッケージもインストール）

3. .env の作成（対話式ウィザード推奨）

   - python -m kabusys.config_setup
   - ウィザードに従って必要な環境変数を入力します（J-Quants / kabuAPI など）

   重要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   任意 / 設定例
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
   - LOG_LEVEL — デフォルト: INFO
   - OPENAI_API_KEY — AI 機能を使う場合に必須

4. 設定検証（推奨）

   - python -m kabusys.validate_config
   - 警告を厳密に扱う場合は --strict を付ける

5. 必要なディレクトリを作成（.env の値に応じて）
   - data/, logs/ などは自動作成されますが、権限に注意してください。

---

## 使い方（主要スクリプト / モジュール）

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - オプション: --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - ポイント:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、MockBrokerClient を使って発注をシミュレーション
    - 起動時に data/stop_requested.flag が存在すると起動を中止
    - 停止は data/stop_requested.flag を作成することで行えます（Kill Switch は別に data/kill.flag を使う）

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 監視は Settings.sqlite_path を使って永続化（監視 DB は環境に依らず本番 sqlite_path を使います）
  - 停止は data/stop_requested.flag の作成で行います（同フラグ）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH が未設定の場合）

- AI モジュール呼び出し（ライブラリとして）
  - from kabusys.ai.news_nlp import score_news
  - from kabusys.ai.regime_detector import score_regime
  - OpenAI API キーが必要（引数 or 環境変数 OPENAI_API_KEY）

- ライブラリ利用例（ポートフォリオ）
  - from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes

---

## 重要な動作・制約メモ

- run_monitoring は KABUSYS_ENV に関わらず Settings.sqlite_path（監視用 DB）を使用します。監視 DB と発注用ペーパートレード DB は分離できます（paper_trading モード）。
- run_execution は paper_trading モード時に PAPER_TRADING_SQLITE_PATH を使用します（本番 DB と完全分離）。
- 停止手段:
  - 一時停止／安全停止用フラグ: data/stop_requested.flag（run_monitoring / run_execution が監視）
  - Kill Switch: data/kill.flag（監視側から条件トリガで書き込むと ExecutionEngine 停止を促す）
- ロギング: kabusys.utils.logging_setup.setup_logging を使用。logs/<app_name>.log に日次ローテーションで保存（デフォルト 30 日保持）。
- OpenAI を用いる機能は API 呼び出しの失敗に対して冗長性（リトライ・フォールバック）を持つ設計ですが、API キーが未設定だと動作しません。
- validate_config で PyYAML がない場合、config/*.yaml の中身検証はスキップされます（警告）。

---

## ディレクトリ構成（主なファイル）

以下はこのリポジトリの主要なモジュールとファイル群の抜粋です（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - config_setup.py               — .env 対話式ウィザード CLI
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト

  - execution/                     — 発注関連（実装詳細は別ファイル）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py

  - monitoring/
    - monitoring_db.py             — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard 等）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py

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
    - news_nlp.py                   — ニュース NLP（OpenAI）
    - regime_detector.py            — 市場レジーム判定（OpenAI）
    - __init__.py

  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成ツール
    - __init__.py

- data/                             — データ・フラグ・PID・DB 等（実行時に作成）
  - monitoring.db (default)
  - paper_trading.db (paper_trading 用)
  - kill.flag
  - stop_requested.flag
  - execution.pid

- logs/                             — ログ出力先（デフォルト）

---

## よくある運用コマンド例

- 初期設定（ウィザード）
  - python -m kabusys.config_setup

- 設定チェック
  - python -m kabusys.validate_config

- 監視プロセス起動（バックグラウンドで起動する場合は OS のサービス化を推奨）
  - python -m kabusys.run_monitoring

- 実行エンジン起動
  - python -m kabusys.run_execution

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

---

## トラブルシューティング / 運用上の注意

- 権限: logs/ や data/ ディレクトリに書き込み権限があることを確認してください。ログディレクトリ作成失敗時はコンソール出力のみになります。
- OpenAI: API 呼び出しに関するエラーはリトライやフォールバックロジックがありますが、API キーが未設定だと例外が発生します（モジュール使用時に明示的にキーを渡すことも可）。
- データ鮮度: SystemMonitor は DuckDB の prices_daily 等のデータ鮮度をチェックします。prices_daily の更新が必要な場合はデータパイプライン側を確認してください。
- 停止: run_execution / run_monitoring を安全に停止したい場合は data/stop_requested.flag を作成してください（プロセスは定期的にこのファイルをチェックして自発終了します）。監視側による強制停止は data/kill.flag が利用されます。

---

## 貢献 / 開発メモ

- コードは、DBアクセス層・ビジネスロジック・IO 層を分割する設計を意識しています。ユニットテストは各純粋関数（portfolio/*.py、research/*.py 等）に対して書きやすい構造です。
- 追加依存やバージョン管理は requirements.txt を用意して管理することを推奨します。
- 本 README は現状のソースコードから抽出した情報に基づく概要です。実行前に python -m kabusys.validate_config で環境変数・ファイルパスの整合性を確認してください。

---

もし README に追記してほしい例（docker 化手順、systemd サービス定義、CI/CD の設定例、より詳細な構成図など）があれば教えてください。必要に応じて追記します。