# KabuSys

日本株自動売買システムのモノリポジトリ（軽量なトレーディングフレームワーク）です。  
この README はコードベース（src/kabusys 以下）に基づく簡易ドキュメントです。

※ 本ドキュメントはソースコードのコメント・仕様に基づいて作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を行うためのコンポーネント群を含むプロジェクトです。主な機能は以下のとおりです。

- 実際の発注（kabuステーション）またはペーパートレード（モック）による ExecutionEngine
- システム稼働状況、注文状態、リスク（ドローダウン等）の監視コンポーネント
- ポートフォリオ構築・ポジションサイジングの純関数群
- DuckDB を用いたファクター計算・リサーチモジュール
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント / レジーム判定（AI モジュール）
- 簡易レポート生成ツール（ペーパートレード検証レポート等）
- 環境設定ウィザード・設定検証 CLI

ライブラリのエントリポイントは Python パッケージ `kabusys` です。

---

## 機能一覧

- Execution
  - ExecutionEngine を起動して発注フローを実行
  - paper_trading モードでは MockBrokerClient を使用し、本番 DB と分離（data/paper_trading.db が既定）
  - 発注・注文管理・リスク管理・Reconciler 等のコンポーネントを含む

- Monitoring
  - SystemMonitor：CPU/Memory/Disk、プロセス生存、データ鮮度などを監視
  - TradeMonitor：滞留注文・約定価格異常を検知
  - RiskMonitor：ドローダウン・ポジション上限を監視、必要に応じて kill.flag を書き込む
  - AlertManager：LINE Messaging API を使ったプッシュ通知（オプション）

- Research / Data
  - DuckDB 接続でファクター計算（momentum / value / volatility 等）
  - 将来リターン、IC 計算、特徴量サマリー等の解析関数

- AI
  - news_nlp.score_news：ニュース記事を集約して OpenAI に投げ、銘柄ごとのセンチメントを ai_scores に格納
  - regime_detector.score_regime：ETF MA とマクロニュースの LLM スコアを合成して市場レジーム（bull/neutral/bear）を判定・保存

- Utilities
  - 環境設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ペーパートレード検証レポート生成ツール（tools/paper_verification_report.py）
  - Process 優先度／CPU affinity の設定ユーティリティ

---

## セットアップ手順

前提: Python 3.9+（typing, dataclass 等を使用）

1. リポジトリをクローン／配置
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須（最低限）:
     - duckdb
     - psutil
     - requests
   - AI 機能を使う場合:
     - openai（OpenAI SDK）
   - validate_config の YAML 検証を使う場合:
     - PyYAML
   例（pip）:
   - pip install duckdb psutil requests openai pyyaml

4. 環境変数（.env）の準備
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または .env を手動作成（例）:
     ```
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_kabu_password
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     ```
   - 重要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - モード:
     - KABUSYS_ENV = development | paper_trading | live

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする: --strict

6. データディレクトリ作成
   - デフォルトでは data/ 以下に DB・PID・フラグを作成します。必要に応じて作成してください。
   - 例: mkdir -p data

---

## 使い方

基本的にパッケージをモジュール実行します（`python -m kabusys.<module>`）。

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話式で生成／更新します。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- 実行エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作モード:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 用 SQLite （PAPER_TRADING_SQLITE_PATH 環境変数、デフォルト data/paper_trading.db）に記録します。
  - PID ファイル: data/execution.pid（Settings.pid_file_path で上書き可）
  - 停止フラグ: data/stop_requested.flag（存在すると起動しない／実行中は停止をトリガー）

- 監視ポーリング（SystemMonitor の単体起動）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60）
  - Monitoring は常に本番用 sqlite_path（Settings.sqlite_path）を参照します（環境に依らず）
  - 停止フラグ: data/stop_requested.flag

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 引数 --db で DB パスを指定でき、環境変数 PAPER_TRADING_SQLITE_PATH より優先されます

- AI 関連（ニュース・レジーム）
  - OpenAI API キー: 環境変数 OPENAI_API_KEY、または関数引数で指定
  - ニューススコア生成（DuckDB 接続が必要）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)
  - 注意: OpenAI 呼び出しはネットワーク／レート制限で失敗する可能性があり、内部でリトライやフォールバック処理を行います。

- ログ・通知
  - LOG_LEVEL 環境変数でログレベルを制御（デフォルト INFO）
  - AlertManager を用いて LINE へ通知可能（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID が必要）。未設定の場合はログのみ。

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定モード（instant|partial|never|reject、デフォルト instant）
- OPENAI_API_KEY — AI 機能利用時に必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — アラート通知用
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1）

---

## 停止・Kill フラグ / PID の扱い

- 停止フラグ:
  - data/stop_requested.flag — run_execution / run_monitoring が存在を検知して停止します（手動で作成／削除）。
  - data/kill.flag — KillSwitch が書き込み、ExecutionEngine に停止シグナルを送る用途。
- PID:
  - ExecutionEngine は起動時に PID ファイル（data/execution.pid）を使用／更新します。SystemMonitor はこの PID の存在とプロセス生存を確認します。

---

## トラブルシューティング / 注意点

- .env の自動読み込み:
  - パッケージ読み込み時に .env/.env.local を自動ロードします（プロジェクトルートが .git または pyproject.toml で検出される場合）。
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- validate_config:
  - PyYAML が未インストールだと YAML 検証はスキップされます（警告が出ます）。

- OpenAI 呼び出し:
  - API キーが無い場合、score_news / score_regime は ValueError を送出します（キーが必須）。
  - ネットワークエラーや 429 / 5xx 等は内部でリトライしますが、最終的に失敗すると一部処理がスキップされる場合があります。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は冪等でテーブルを作成します。既存テーブルにカラムがない場合は簡易マイグレーション（ALTER TABLE）を行います。

- 権限や OS 依存:
  - process_priority.set_process_priority はプラットフォーム差分を吸収しますが、権限不足で失敗する可能性があります（警告でスキップ）。

---

## ディレクトリ構成 (src/kabusys の主要ファイル)

- src/kabusys/
  - __init__.py
  - config.py                  — 環境設定 / .env ロード / Settings
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - execution/                 — 発注関連コンポーネント群（OrderManager 等）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - utils/
    - process_priority.py
  - data/                      — 既定の DB / PID / flag ファイルが置かれる想定ディレクトリ（プロジェクトルート）

（上記は主要ファイルのみ抜粋。execution/ 配下やその他ユーティリティはリポジトリを参照してください。）

---

## 開発者向けメモ

- モジュールは可能な限り副作用を抑えた設計（例: DuckDB 接続を引数で受ける、純粋関数群）になっています。
- テストのしやすさを考慮して OpenAI 呼び出し等は個別関数で抽象化されており、ユニットテスト時はモック可能です（関数を patch してください）。
- データ鮮度チェックや LLM を使った機能はルックアヘッドバイアスを避ける実装方針が採られています（target_date を明示して処理）。

---

必要であれば README にサンプル .env、実行例のコマンドライン例、より詳細なディレクトリツリーや API ドキュメントを追記します。どの部分を詳しく追加しますか？