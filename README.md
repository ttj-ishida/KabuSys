# KabuSys — README (日本語)

このドキュメントは、KabuSys コードベースの使い方・セットアップ方法・主要コンポーネントの概要をまとめた README です。

注意: 本リポジトリは Python パッケージ（src/kabusys）として実装されています。実行する際はプロジェクトルートを PYTHONPATH に含めるか、editable インストールを推奨します（例: pip install -e .）。

---

## プロジェクト概要

KabuSys は日本株自動売買システムの基盤ライブラリです。主な目的は以下の通りです。

- シグナルに基づく発注（ExecutionEngine / OrderManager）
- リスク管理・監視（MonitoringEngine, RiskMonitor, TradeMonitor, SystemMonitor）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 研究用ファクター計算・特徴量解析（research モジュール）
- AI を用いたニュースセンチメント評価（news_nlp）や市場レジーム判定（regime_detector）
- 運用用のユーティリティ（プロセス優先度設定、ステータス用 DB、Streamlit ダッシュボード等）

設計方針の一部:
- DuckDB / SQLite を用いたローカルデータ処理
- OpenAI API 呼び出し部は失敗時にフェイルセーフで続行
- モジュールは可能な限り純粋関数／副作用最小化で実装

---

## 主な機能一覧

- Execution（発注）
  - ExecutionEngine 起動スクリプト: kabusys.run_execution
  - Broker クライアントの抽象化と Mock 対応（paper_trading）
  - 再起動時のリコンシリエーション（Reconciler）

- Monitoring（監視）
  - SystemMonitor: プロセス稼働・CPU/メモリ/ディスク、データ鮮度の監視
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視
  - MonitoringEngine: 上記モニタを束ねるポーリングループ
  - AlertManager: LINE へのプッシュ通知（クールダウン付き）
  - kill.flag による ExecutionEngine 停止シグナル管理

- Portfolio（ポートフォリオ構築）
  - 候補選定、等率/スコア加重、ポジションサイズ決定、セクター上限やレジーム乗数の適用

- Research（調査/解析）
  - ファクター計算（Momentum, Volatility, Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI（OpenAI を利用）
  - news_nlp: ニュース記事群を LLM でスコアリングして ai_scores に保存
  - regime_detector: ETF の MA 乖離 + マクロニュースセンチメントで日次レジームを判定

- 管理ツール
  - Streamlit ダッシュボード（監視可視化）
  - Paper Trading 検証レポート生成スクリプト（tools.paper_verification_report）

---

## セットアップ手順

推奨 Python バージョン: 3.10+

1. リポジトリをクローンして移動
   - 例: git clone ... && cd <project-root>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（代表的な依存）
   - pip install duckdb psutil openai requests streamlit
   - 必要に応じて他の依存を追加してください（sqlite3 は標準ライブラリ）

   あるいは package を開発モードでインストール:
   - pip install -e .

4. 環境変数 / .env
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（既存 OS 環境変数は保護）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN — 必須（J-Quants API トークン）
     - KABU_API_PASSWORD — 必須（kabuステーション API パスワード）
     - OPENAI_API_KEY — AI 機能を使う際に必要
     - KABUSYS_ENV — "development" | "paper_trading" | "live"（default: development）
     - PAPER_FILL_MODE — paper_trading の約定挙動 ("instant"|"partial"|"never"|"reject")
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / LOG_LEVEL 等
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知用
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
   - .env の書式は shell 形式（コメントやクォート対応）で読み込まれます。

5. データディレクトリ作成
   - mkdir -p data

---

## 使い方（起動例）

前提: プロジェクトルートを PYTHONPATH に含める（例: export PYTHONPATH=./src）か、pip install -e . を行う。

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 補足: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視ログは production DB を参照する仕様）。

- Execution（発注エンジン）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録され、本番 DB と分離されます。
  - 起動時にプロセス優先度を "high" に設定します（可能な場合）。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - DB を読み取り専用で開いて監視情報を可視化します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH より優先）
  - 例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- AI / LLM 用関数（プログラムから呼ぶ例）
  - news_nlp.score_news(conn, target_date, api_key=...)
  - regime_detector.score_regime(conn, target_date, api_key=...)
  - どちらも OPENAI_API_KEY（引数または環境変数）が必要。API 呼び出しは冗長な失敗でもフェイルセーフに続行する実装になっています。

- kill.flag による Execution 停止
  - KillSwitch は検知条件（ドローダウン、ポジション上限等）で data/kill.flag を書き込みます。ExecutionEngine は起動時にこのフラグを確認し停止処理を行う設計です。

---

## 設定の挙動・注意点

- データベース:
  - DuckDB: デフォルト data/kabusys.duckdb（prices_daily, raw_financials 等のリサーチ用テーブル想定）
  - Monitoring SQLite: data/monitoring.db（監視ログ、trade_logs、positions、risk_logs、dashboard）
  - Paper Trading SQLite: data/paper_trading.db（paper_trading を選択した場合に利用）

- .env の自動読み込み:
  - プロジェクトルートは .git または pyproject.toml を探索して決定されます。見つからない場合は自動ロードをスキップします。
  - OS 環境変数は優先され、.env.local は .env を上書きします。

- MONITOR_POLL_INTERVAL:
  - run_monitoring では環境変数 MONITOR_POLL_INTERVAL を参照。デフォルトは 60 秒。1 未満や無効な値はデフォルトにフォールバックします。

- process priority / CPU affinity:
  - utils/process_priority.py で OS に応じて優先度を設定します。設定に失敗しても警告を出してスキップします（権限・未実装 OS など）。

- AI 呼び出しの堅牢性:
  - news_nlp, regime_detector は 429 / network / timeout / 5xx を指数バックオフでリトライします。
  - API の結果は厳密にバリデーションされます。失敗時はゼロや空の結果でフォールバックし、処理全体の停止を避けます。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主なファイル／モジュール構成です（抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数/設定管理 (.env 自動読み込み含む)
    - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - utils/
      - __init__.py
      - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
    - monitoring/
      - __init__.py
      - monitoring_db.py             — SQLite 監視 DB 層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - alert_manager.py
      - kill_switch.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - order_repository.py (参照)
      - execution_engine.py (参照)
      - broker_factory.py (参照)
      - broker_api.py (参照)
      - ... (発注周りの実装)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/ (データ処理周り)
      - pipeline.py (get_last_price_date 等)
      - stats.py (zscore_normalize 等)
    - tools/
      - __init__.py
      - paper_verification_report.py

各ファイルに詳細な docstring / コメントがあり、関数・クラスごとに振る舞いが記載されています。実装の意図やエッジケースの扱いもソース内コメントで説明されています。

---

## よくある操作例

- 開発環境で実行（ソースを直接利用）
  - export PYTHONPATH=./src
  - python -m kabusys.run_monitoring

- package をインストールして実行
  - pip install -e .
  - python -m kabusys.run_monitoring

- Paper Trading で Execution をテスト
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
  - データは data/paper_trading.db に保存されます（デフォルト）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 開発上の注意 / 今後の拡張ポイント（簡単に）

- position_sizing の lot_size は現在全銘柄共通。将来的に銘柄別単元対応が検討可能。
- apply_sector_cap の価格欠損時の挙動に改善余地（前日終値などのフォールバック）。
- DuckDB / SQLite のバージョン差異により executemany の空リスト扱い等の互換性注意。
- OpenAI SDK の変更に備えてエラーハンドリングや status_code の扱いは保守が必要。

---

この README は概要をまとめたものです。各モジュールの詳細な仕様や引数の説明はソースコード内の docstring を参照してください。追加のドキュメント（設計メモ、仕様書）がある場合はそちらも合わせて参照することを推奨します。