# KabuSys

日本株向け自動売買システムの一部サブコンポーネント群（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI補助など）。

この README はソースツリー（src/kabusys）に含まれる主要スクリプト／モジュールの概要、セットアップ方法、使い方、ディレクトリ構成をまとめたものです。

注意: 本 README はリポジトリ内のコード（src/kabusys 以下）を参照して作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。主な責務は次の通りです。

- ExecutionEngine: 発注ロジック・リスク管理・注文管理（paper_trading / live 切替対応）
- Monitoring: システム状態や発注状況のポーリング監視、Kill Switch による安全停止
- Portfolio: 候補選定・重み付け・ポジションサイズ計算・セクター制約などの純粋関数群
- Research: DuckDB 上でファクター計算・特徴量解析を実行
- AI: ニュース NLP（OpenAI）を使った銘柄別スコアリング、レジーム判定
- Tools: ペーパートレード検証レポート生成などユーティリティ

設計上のポイント:
- 環境変数（.env）ベースの設定管理
- paper_trading モードでは本番 DB と分離（専用 SQLite）
- DuckDB を分析基盤に利用
- OpenAI を用いたテキスト解析は API キー必須、失敗時はフェイルセーフで続行

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV による挙動切替）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定）
- 環境設定
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env / config/*.yaml の起動前検証 CLI
- 監視・安全停止
  - monitoring_engine.py / system_monitor.py / trade_monitor.py / risk_monitor.py / kill_switch.py
  - kill.flag による ExecutionEngine 停止シグナル実装
- ポートフォリオ構築
  - portfolio_builder.py / position_sizing.py / risk_adjustment.py
- リサーチ
  - research/factor_research.py / feature_exploration.py（DuckDB 上でファクター・IC 等を計算）
- AI（LLM）
  - ai/news_nlp.py: ニュース記事をまとめて OpenAI でセンチメント評価 → ai_scores へ書き込み
  - ai/regime_detector.py: ma200 乖離 + マクロニュースで市場レジーム判定
- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定（stdout + 日次ローテートファイル）
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定

---

## 動作環境・依存関係

推奨 Python バージョン: 3.10 以上（型ヒントで `|` を使用しているため）

主要依存パッケージ（例）:
- duckdb
- psutil
- openai
- PyYAML（config ファイル検証を行う場合）
- （標準ライブラリ: sqlite3, logging, threading, datetime 等）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（プロジェクトに requirements.txt があればそちらを使ってください）

---

## 環境変数（主要一覧）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主な任意／デフォルト値:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — デフォルト: INFO
- LOG_DIR — デフォルト: logs/
- OPENAI_API_KEY — AI 機能利用時に必須
- PAPER_FILL_MODE — paper_trading の約定挙動（instant|partial|never|reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など（監視・Kill Switch 関連）

.env 生成は対話式ウィザード（python -m kabusys.config_setup）を推奨します。

---

## セットアップ手順（手順例）

1. リポジトリをクローンして作業ディレクトリへ移動
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. .env を作成（推奨: 対話式ウィザード）
   - python -m kabusys.config_setup
5. 設定を検証
   - python -m kabusys.validate_config
6. データディレクトリ（data/）の確認。必要に応じて作成されますが、事前に用意しておくと安全です。
7. DuckDB/SQLite ファイルパスは .env で指定可能（デフォルトは data/ 以下）。

---

## 使い方（起動・主なコマンド）

※ 各スクリプトはパッケージモードで起動できます（カレントがプロジェクトルートであることを想定）。

- ExecutionEngine を起動
  - 本番/ペーパートレードは KABUSYS_ENV で切替。
  - 例（ペーパートレード）:
    ```bash
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 起動時に process priority を "high" に設定し、paper_trading なら MockBroker を使い PAPER_TRADING_SQLITE_PATH に記録します。
  - 実行中に data/stop_requested.flag を作成すると、起動スレッドは検知して停止します。

- Monitoring を起動
  - ポーリング実行（MONITOR_POLL_INTERVAL で秒数指定可。デフォルト 60 秒）
    ```bash
    python -m kabusys.run_monitoring
    ```
  - 監視は本番 sqlite_path を使って状態を永続化します（環境にかかわらず同じ sqlite_path を使用）。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いで exit(1) になります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定できます。

- AI モジュール（プログラム的に）
  - OpenAI API キーが環境変数 OPENAI_API_KEY に必要です。
  - 例（score_news を呼ぶ最小例）:
    ```python
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    # target_date: datetime.date オブジェクト
    count = score_news(conn, target_date, api_key="sk-...")
    ```
  - 同様に regime_detector.score_regime を呼んで market_regime テーブルへ書き込みます。

- ログ
  - ログは stdout と logs/<app_name>.log に日次ローテートで出力されます（LOG_DIR 環境変数で変更可）。
  - ログレベルは LOG_LEVEL で制御。

- Kill Switch / Stop フラグ
  - KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）を使って ExecutionEngine を停止させます。
  - 監視ループ停止用のフラグファイル: data/stop_requested.flag（run_execution/run_monitoring がそれを検知して終了する設計）。

---

## 注意点 / 運用メモ

- paper_trading モードは本番データベースと分離されます。PAPER_TRADING_SQLITE_PATH を適切に設定してください。
- OpenAI 呼び出しは失敗時にフォールバックする設計ですが、API キーは必須です（AI 機能を使う場合）。
- ログディレクトリ作成に失敗した場合は stdout のみで継続する実装になっています。
- process priority の変更はプラットフォームに依存し、権限不足では警告を出してスキップします。
- DuckDB / SQLite スキーマは init_monitoring_db 等で冪等に初期化・マイグレーションされます。
- データ鮮度やレジーム判定などはルックアヘッドを避ける設計（target_date 未満のデータのみ参照）になっています。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を抜粋）

- __init__.py
- config.py
- config_setup.py — .env 対話ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト

サブパッケージ / モジュール:
- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI）
  - regime_detector.py — 市場レジーム判定（ma200 + マクロニュース）
- monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - monitoring_engine.py — 各モニターを束ねるポーリング実行
  - system_monitor.py — システム状態・データ鮮度監視
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag 管理
  - alert_manager.py (参照箇所あり) — 通知管理（コードベースに存在）
  - trade_monitor.py (参照箇所あり) — 注文監視（コードベースに存在）
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py, ...（実行ロジック）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py — ログ設定
  - process_priority.py — 優先度 / CPU affinity
- data/ (実行時に利用するディレクトリ例)
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - execution.pid, kill.flag, stop_requested.flag

---

## 開発・拡張のヒント

- DuckDB 上のテーブル（prices_daily, raw_financials, raw_news 等）を整備すればリサーチ / AI 機能が動作します。
- AI 呼び出しや外部 API 絡みのコードはリトライやフォールバックを実装してあり、ユニットテストではネットワーク呼び出しをモックすることを想定しています（例: _call_openai_api を patch）。
- position sizing やリスク制御のパラメータは Engine/RiskConfig 側で調整できます。

---

README に書かれている内容やコードの挙動で不明点や、実行に必要な追加情報（requirements.txt の生成、config/*.yaml のテンプレート生成スクリプトなど）が必要であれば、具体的に教えてください。追加のセットアップ手順やサンプル .env テンプレートを作成します。