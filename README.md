# KabuSys

日本株自動売買システムの Python パッケージ（抜粋）。本リポジトリは戦略・発注・監視・リサーチ・AI 補助などの主要コンポーネントを含みます。

以下はこのコードベースに対する簡易 README（日本語）です。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。主な機能は次の通り：

- 発注エンジン（ExecutionEngine）：ブローカークライアントを通じた注文発行・管理
- 監視（Monitoring）：システム状態、注文状態、リスク（ドローダウン・保有数）を定期チェックしアラート／Kill Switch を扱う
- ポートフォリオ構築：候補選定、重み計算、ポジションサイズ計算、セクター上限制御など
- リサーチ／ファクター計算：DuckDB の価格・財務データを用いたファクター計算・統計解析
- AI 補助：ニュース記事を LLM（OpenAI）でスコアリングし、レジーム判定やニュースセンチメントに利用
- ユーティリティ：ログ設定、プロセス優先度設定、設定ウィザード、設定検証ツールなど
- ツール：Paper Trading の検証レポート生成等

設計方針として「ルックアヘッドバイアス防止」「DB は明示的に切り分ける（本番 / paper）」等に配慮しています。

---

## 機能一覧（抜粋）

- 設定管理
  - .env ファイル自動読み込み（プロジェクトルート検出）
  - 対話式設定ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行 / 発注
  - ExecutionEngine（paper_trading 時は Mock ブローカーを使用、DB 分離）
  - BrokerClientFactory によるブローカー抽象化
  - OrderRepository / OrderManager / RiskManager / Reconciler 等のコンポーネント
- 監視
  - SystemMonitor: CPU/MEM/DISK、プロセス生存、データ鮮度チェック
  - TradeMonitor: 注文滞留・約定異常チェック
  - RiskMonitor: ドローダウン監視、ポジション上限監視
  - KillSwitch: 条件成立時に data/kill.flag を書き込む
  - MonitoringEngine: 上記をまとめてポーリング、AlertManager 経由で通知
- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 重み計算（等金額 / スコア重み）
  - ポジションサイズ計算（risk_based, equal, score）
  - セクターキャップ、レジーム乗数
- リサーチ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC 計算、統計サマリ
- AI
  - ニュース NLP（OpenAI）で銘柄ごとのセンチメントを ai_scores に書き込み
  - レジーム判定（MA200 + マクロニュースセンチメントの合成）
- ツール
  - paper_verification_report: Paper Trading DB を解析して PASS/FAIL レポートを出力

---

## セットアップ手順

前提：Python 3.9+（コードは型アノテーションを使用）、SQLite は標準ライブラリで利用可能。

1. リポジトリをクローンしてカレントに移動
   - 例: git clone ... && cd <repo>

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix)
   - .venv\Scripts\activate     (Windows)

3. 依存ライブラリをインストール
   - 必要なパッケージ例（最低限）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - pyyaml (config 検証で YAML を検査したい場合)
   - 例:
     - pip install duckdb psutil openai pyyaml

4. 環境変数（.env）を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
   - 推奨設定:
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能使用時）
     - LOG_LEVEL（DEBUG/INFO/...）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。production では 0 推奨）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict オプションを付けると警告も失敗扱い（exit 1）

注意:
- .env は絶対に Git にコミットしないでください（config_setup にも警告あり）。
- デフォルトの DB は data/ 以下に作成されます。ディレクトリ作成は自動で行われることが多いですが権限に注意してください。

---

## 使い方（主要スクリプト）

以下のスクリプトはパッケージとして実行可能です（プロジェクトルートで実行）：

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
    - 起動時に data/stop_requested.flag が既に存在すると起動せず終了
    - エンジンは実行中に同フラグを検知すると停止する
    - 実行時に data/execution.pid を使用 / 更新

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 挙動:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒数で上書き（デフォルト 60 秒）
    - Monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（監視 DB）を使用（常に本番 DB を参照）
    - 停止は data/stop_requested.flag の作成で行う

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH より優先）

環境変数の例（.env）
- KABUSYS_ENV=development
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- OPENAI_API_KEY=...  (AI 機能を使う場合)
- LOG_LEVEL=INFO
- MONITOR_POLL_INTERVAL=60
- KILL_FLAG_CLEAR_ON_START=0
- PAPER_FILL_MODE=instant  (instant|partial|never|reject)

停止・Kill スイッチについて
- ExecutionEngine / Monitoring の停止用フラグ:
  - data/stop_requested.flag : 外部から起動済みプロセスに「優雅に停止」を要求するために使用（run_* がチェック）
  - KillSwitch は条件を満たすと data/kill.flag を書き込み、ExecutionEngine は起動時にこのフラグの存在を検査して起動を防止したり、実行中に検知して停止する
- KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアする（本番環境では危険）

ログ
- ログは logs/<app_name>.log に日次ローテーションで書き出されます（デフォルト logs ディレクトリ）
- ログ出力の設定は kabusys.utils.logging_setup.setup_logging を通じて行います

---

## ディレクトリ構成（主要ファイル・モジュール）

以下はリポジトリの主要なモジュール構成（抜粋）です。実際のファイルツリーは多少異なる場合があります。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env ロード & Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - execution/               — 発注関連（BrokerFactory, Engine, OrderManager 等）
  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB ラッパー
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
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
  - tools/
    - paper_verification_report.py

---

## 補足・運用上の注意

- 本番環境で KABUSYS_ENV=live を設定する場合は、LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や kill flag の扱い等を慎重に確認してください。validate_config は Live ガードチェックを含みます。
- Paper Trading は本番 DB と完全分離する設計になっており、settings.is_paper により専用 SQLite DB を使用します。
- Monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path を使用するため、監視 DB の運用方針に注意してください（監視は常に同一の DB を参照します）。
- OpenAI を使う機能は API キーの管理と利用料に注意してください。API 呼び出しはリトライとフェイルセーフ実装がありますが、コストとレート制限に気を付けてください。

---

この README はコードベースの主要な使い方と設計上のポイントを簡潔にまとめたものです。各モジュールの詳細な挙動（引数や返り値、内部ロジック）については該当ソースファイルの docstring / コメントを参照してください。必要であれば、README に追記する形で「サービス起動手順」「運用プレイブック」「DB スキーマ詳細」等も作成できます。必要な項目を教えてください。