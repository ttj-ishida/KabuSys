# KabuSys

日本株自動売買システムのコアライブラリ（読み取り専用ドキュメント）。  
この README はリポジトリ内の主要スクリプト・設定・モジュール構成に基づいた使用方法とセットアップ手順をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコア実装です。  
主に次の責務を持つモジュール群で構成されています:

- 実行エンジン（注文送信、オーダー管理、リスク管理、約定処理）
- 監視（システム状態・注文滞留・リスク監視、Kill Switch）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出、セクター制限）
- 研究用モジュール（ファクター計算・特徴量探索）
- AI 補助（ニュースセンチメント / レジーム判定：OpenAI を使用）
- 各種ユーティリティ（設定管理、プロセス優先度設定、レポート生成など）

本リポジトリは運用用/研究用の共存を考慮した設計になっており、paper_trading（ペーパートレード）モードでは本番 DB とは分離されます。

---

## 主な機能（抜粋）

- ExecutionEngine 起動スクリプト（run_execution）:
  - KABUSYS_ENV により paper_trading モードでは MockBrokerClient を使用し、ペーパートレード専用 DB に記録
  - プロセス優先度設定・PID ファイル管理・停止フラグ対応
- Monitoring（run_monitoring / MonitoringEngine）:
  - CPU / メモリ / ディスク / プロセス生存チェック
  - データ鮮度チェック（DuckDB の prices_daily ベース）
  - 注文滞留・約定異常の検知
  - リスク（ドローダウン・ポジション上限）の検出と Kill Switch 書き込み
  - アラート送信インフラ（LINE 等）へ接続可能
- ポートフォリオ構築:
  - 候補選定（スコア順）・等分配／スコア加重
  - セクター上限の適用
  - リスクベース／等分配等のポジションサイズ計算（単元株丸め等）
- 研究モジュール:
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）等の統計解析
- AI モジュール（OpenAI）:
  - ニュース記事のセンチメントを LLM でスコアリング（ai.score_news）
  - マクロニュース + ETF MA を組み合わせた市場レジーム判定（ai.regime_detector）
- ツール:
  - 対話式 .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード結果検証レポート生成ツール（tools/paper_verification_report）

---

## 必須要件（概略）

- Python 3.9+
- pip-installable パッケージ（主に）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML を検証する場合）
- SQLite（標準で Python に同梱）
- ネットワーク接続（本番の kabuステーション API / OpenAI を使用する場合）

※ requirements.txt は本リポジトリに含まれていない場合があります。上記パッケージを個別にインストールしてください。

---

## セットアップ手順

1. レポジトリをクローン / 配布パッケージを展開
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS) / .venv\Scripts\activate (Windows)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. `.env` の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - このウィザードで J-Quants トークン、Kabu API パスワード、DB パス等を設定します。
   - 重要: `.env` は機密情報を含むため Git にコミットしないでください。
5. 設定検証
   - python -m kabusys.validate_config
   - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict
6. データディレクトリを作成（必要に応じて）
   - デフォルトの DB / PID / フラグ等は `data/` 配下に作成されます。実行ユーザに書き込み権限があることを確認してください。

---

## 主要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API のパスワード
- 実行モード
  - KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DB 関連
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- OpenAI
  - OPENAI_API_KEY — AI モジュールで使用する API キー
- ログ / PID / Kill Switch
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
  - PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch フラグファイル（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" = 有効）
- Monitoring
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- Paper Trading
  - PAPER_FILL_MODE — ペーパートレード用の約定モード: instant | partial | never | reject

詳細は `src/kabusys/config.py` にプロパティごとの説明があります。`python -m kabusys.config_setup` で推奨値を対話的に設定できます。

---

## 使い方（主要コマンド）

- 実行エンジン（Engine）を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使用して `data/paper_trading.db`（または PAPER_TRADING_SQLITE_PATH）に記録します。
    - 起動時にプロセス優先度を "high" に設定します。
    - 停止は `data/stop_requested.flag` を作成するか ExecutionEngine 側からの停止処理に従います（または KeyboardInterrupt）。
    - PID はデフォルトで `data/execution.pid` に書き込まれます。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は sqlite_path（monitoring DB）を使用します（KABUSYS_ENV に依存しません）。
    - 停止は `data/stop_requested.flag` を作成することで検知して終了します。

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話式に作成・更新します。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで終了コード 1 を返します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可能）

- AI モジュール（プログラムから呼び出し）
  - kabusys.ai.score_news(duckdb_conn, target_date, api_key=None)
    - raw_news を集約して OpenAI に送信、ai_scores テーブルへ書き込みます。
    - api_key 未指定時は環境変数 OPENAI_API_KEY を使用。
  - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)
    - ETF MA とマクロニュースを組み合わせて market_regime テーブルを更新します。

---

## 停止・フラグの取り扱い

- 停止フラグ
  - run_execution / run_monitoring はプロジェクトルートの `data/stop_requested.flag` を参照して停止を検知します（スクリプト内でのパス定義に依存）。
- Kill Switch
  - RiskMonitor と KillSwitch により、所定のリスク条件（ドローダウン超過・ポジション上限超過等）で `data/kill.flag` が書き込まれます。ExecutionEngine は起動時にこのフラグを検査し、設定に応じて自動クリアすることも可能です（KILL_FLAG_CLEAR_ON_START）。
- PID ファイル
  - ExecutionEngine は PID を書き込み、SystemMonitor は PID ファイルの存在とプロセス生存を確認します。古い（stale）PID が見つかった場合は削除してリスクログに記録します。

---

## ディレクトリ構成（主要ファイル）

リポジトリは Python パッケージ `kabusys` を中心に構成されています。主要ファイルを簡略に示します:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 起動前設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py          — プロセス優先度・CPU affinity
  - execution/                      — 実行エンジン関連（order_manager 等）
  - monitoring/
    - monitoring_db.py             — SQLite 永続化層（監視用テーブル）
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
    - news_nlp.py                   — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py            — レジーム判定（MA + マクロセンチメント）
    - __init__.py
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
    - __init__.py
  - monitoring/                      — 監視関連（DB, monitors, engine）

（実際のサブモジュールは src/kabusys フォルダを参照してください）

---

## 開発上の注意点 / 運用時の注意

- 機密情報（API トークン・パスワード）は .env に保存しても Git/公開リポジトリにコミットしないでください。
- KABUSYS_ENV によって本番（live）モードでの危険な設定をチェックする仕組みがあります。validate_config で「本番」に関する警告を必ず確認してください。
- Monitoring は run_monitoring の docstring にある通り、KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。環境変数で path を分離する場合は SQLITE_PATH を明示的に変更してください。
- OpenAI を使う機能は API コストとレート制限に注意してください。API 呼び出しはリトライ・バックオフ等の保護を備えていますが、運用ポリシーを設けてください。
- process priority / cpu affinity の設定は OS 権限が必要になる場合があります（AccessDenied の場合はログに警告が出ますが処理は続行します）。

---

## よく使うコマンドまとめ

- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- ExecutionEngine 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、README に具体的な systemd ユニットや Dockerfile 例、詳細な設定項目説明（すべての環境変数の一覧と意味）、および各モジュールの API 使用例（コードスニペット）を追加できます。どの部分を詳しく書き加えるかを教えてください。