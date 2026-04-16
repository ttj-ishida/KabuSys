# KabuSys

KabuSys は日本株の自動売買・研究・監視を目的とした小規模なフレームワークです。本リポジトリは戦略構築、実行エンジン、監視、リサーチ、AI（ニュースセンチメント・レジーム判定）などの主要コンポーネントを含みます。

以下はこのコードベースの概要、機能、セットアップ手順、使い方、ディレクトリ構成のまとめです。

---

## プロジェクト概要

- 日本株自動売買システムのプロトタイプ実装。
- 戦略（ファクター計算・ポートフォリオ構築）・実行（ブローカー接続、注文管理）・監視（システム状態、注文滞留、リスク）・リサーチ（ファクター・特徴量解析）・AI（ニュースセンチメント、市場レジーム判定）をモジュール化。
- データ永続化は DuckDB（価格・ファクターデータ等）と SQLite（監視ログ・発注ログ等）を併用。
- Paper Trading モードを持ち、本番 DB と分離して動作可能。

---

## 主な機能一覧

- Execution（注文発行 / OrderManager / Reconciler）
  - Broker クライアントの抽象化（本番 / モック切替）
  - Duplicate 注文検知、注文状態同期（再起動時のリコンシリエーション）

- Monitoring（監視サブシステム）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス存在チェック / データ鮮度チェック
  - TradeMonitor: 注文滞留（stale orders）・約定価格異常の検出
  - RiskMonitor: ドローダウン監視・ポジション上限チェック、Dashboard 更新
  - AlertManager: LINE Push での通知（クールダウンあり）
  - KillSwitch: リスクトリガーで `data/kill.flag` を書くことで ExecutionEngine を安全に停止

- Portfolio（ポートフォリオ構築ユーティリティ）
  - 候補選定、等配分 / スコア加重配分、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイジング（ロット丸め・aggregate cap）

- Research（ファクター・特徴量計算）
  - Momentum / Volatility / Value ファクター計算（DuckDB 上の prices_daily / raw_financials を利用）
  - 将来リターン計算、IC（情報係数）計算、統計サマリー

- AI（OpenAI を用いたニュース NLP / レジーム判定）
  - news_nlp: raw_news を集約して LLM に投げ、銘柄ごとのセンチメントを ai_scores に書込
  - regime_detector: ETF（例: 1321）の MA200 乖離とマクロニュースセンチメントを合成して market_regime を決定
  - OpenAI API 呼び出しはリトライ・バリデーション・フェイルセーフ実装あり（APIキー必須）

- ツール
  - paper_verification_report: Paper Trading DB を集計して検証レポートを標準出力に出力
  - Streamlit ダッシュボード: 監視 DB を読み取り専用で表示（ポートフォリオ / 注文 / システム状態 / リスクログ）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 本リポジトリに requirements.txt が無い場合、少なくとも以下が必要になります:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit  (ダッシュボードを使う場合)
   - 例:
     - pip install duckdb psutil openai requests streamlit

4. データディレクトリを作成
   - mkdir -p data

5. 環境変数の設定
   - .env / .env.local に設定可能（自動ロードはデフォルトで有効。無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）
   - 主要な環境変数（デフォルト値／説明）:
     - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必要な場合）
     - KABU_API_PASSWORD: kabuステーション API パスワード（実運用時）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時のモック約定挙動、デフォルト: instant）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）
     - LOG_LEVEL: DEBUG|INFO|...（デフォルト: INFO）
     - PID_FILE_PATH / KILL_FLAG_PATH: 実行時の PID/kill flag パス（デフォルト: data/execution.pid / data/kill.flag）

6. DB 初期化
   - Monitoring 用のテーブルは起動時 (init_monitoring_db) に自動で作成されます。
   - DuckDB 側は価格データや raw_financials / raw_news 等が必要な場合は別途投入してください（スキーマに依存）。

---

## 使い方

以下は主要な実行コマンド例です。プロジェクトルートから実行することを想定しています。

- 監視プロセスの起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可（秒、例: export MONITOR_POLL_INTERVAL=30）
  - 監視は Settings.sqlite_path を使って監視ログを記録します（Monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使用）

- 実行エンジン（ExecutionEngine）の起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に書き込みます。本番 DB と完全分離されます。
  - 実行中は data/execution.pid に PID を書きます（設定でカスタマイズ可）

- 停止方法（安全停止）
  - 例えば停止要求ファイルを作る: touch data/stop_requested.flag
  - run_monitoring / run_execution はこの stop_requested.flag を検知して終了します
  - 監視側の KillSwitch は重大リスク時に data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります（ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START を参照して初期化します）

- Streamlit ダッシュボード（監視可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視用 SQLite を読み取り専用で開きます

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を指定するか、環境変数 PAPER_TRADING_SQLITE_PATH を設定

- AI 機能の実行（例）
  - kabusys.ai.score_news や kabusys.ai.regime_detector.score_regime をスクリプトや REPL から呼び出せます。OpenAI API キーが必要です。
  - 例: from kabusys.ai.news_nlp import score_news

---

## 重要な挙動・設計ノート

- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）を検出して `.env` / `.env.local` を自動読み込みします。
  - OS 環境変数は上書きされません。`.env.local` は上書き可能。
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

- Paper Trading 分離:
  - KABUSYS_ENV=paper_trading のときは broker のモックと専用 SQLite（PAPER_TRADING_SQLITE_PATH）が使われます。実働データと分離されます。

- OpenAI 呼び出し:
  - news_nlp / regime_detector は OpenAI を用います。API キーは OPENAI_API_KEY（または関数引数）で指定してください。
  - レスポンスのバリデーションやリトライ、スコアクリップ（±1.0）などが組み込まれています。

- 監視・停止フロー:
  - run_monitoring, run_execution はプロセス優先度を「high」へ設定しようとします（psutil が必要）。権限によっては失敗して警告が出ますが継続します。
  - stop_requested.flag と kill.flag の両方が存在します。用途は次の通り:
    - stop_requested.flag: 手動で監視・実行ループを停止させる（両スクリプトでチェック）
    - kill.flag: KillSwitch が危険と判断したときに作成。ExecutionEngine に停止シグナルを送るために使用

---

## 環境変数一覧（主要なもの）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う際に必須）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用
- KABU_API_PASSWORD: kabuステーション API パスワード
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- LOG_LEVEL: ログレベル（DEBUG|INFO|...、デフォルト: INFO）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                  — 設定/環境変数読み込み（Settings クラス）
- run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py           — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py              — ニュースセンチメント（OpenAI）
  - regime_detector.py       — 市場レジーム判定（MA200 + マクロセンチメント）
- monitoring/
  - monitoring_db.py         — SQLite ベースの永続化レイヤ
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - alert_manager.py
  - kill_switch.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - reconciler.py
  - （その他：broker_factory, execution_engine, order_repository 等）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py

その他:
- data/                      — 実行時に利用するファイル群（監視 DB / paper DB / pid / flag 等）
  - monitoring.db (デフォルト)
  - paper_trading.db (paper_trading モード)
  - kabusys.duckdb
  - execution.pid
  - stop_requested.flag
  - kill.flag

---

## 開発・運用に関する補足

- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は冪等にテーブル・インデックスを作成します。また既存スキーマに対する簡易マイグレーション（カラム追加）を行う箇所があります。

- テスト・モック:
  - OpenAI 呼び出しや外部 API コールはテスト時に差し替え可能に設計されています（内部関数を patch）。

- ログ:
  - 各スクリプトは logging.basicConfig(level=logging.INFO) を行います。LOG_LEVEL 環境変数で挙動を制御できます。

---

この README はコードベースに含まれる実装をもとに作成しています。具体的な運用手順（証券会社接続の設定、DuckDB データ投入方法など）は環境や実運用要件に依存するため、別途運用ドキュメントを作成することを推奨します。必要であれば、各サブモジュール（ExecutionEngine、Broker 実装、DB スキーマ、テスト手順など）の詳細ドキュメントも作成します。