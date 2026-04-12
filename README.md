# KabuSys

日本株自動売買システム（ライブラリ / 実行スクリプト群）のREADME。  
本リポジトリは売買実行、監視、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）等の主要コンポーネントを含みます。

---

## 概要

KabuSys は日本株の自動売買（Execution）とそれを支える監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント・レジーム判定）機能を持つモジュール群です。  
主要設計方針の一部：

- DB（SQLite / DuckDB）を用いたローカル永続化と分析
- 実行エンジンと監視エンジンを分離し、それぞれ独立して起動可能
- Paper Trading（検証用）と Live（本番）を環境変数で切替
- OpenAI（GPT 系）を用いたニュースセンチメント / レジーム判定を実装（API キー必須）
- シンプルな CLI / スクリプトと Streamlit ダッシュボードを提供

---

## 主な機能一覧

- Execution
  - ExecutionEngine を起動してブローカーへ発注（本番・Paper Trading 切替）
  - OrderManager / OrderRepository / Reconciler による注文管理と再同期間合
  - RiskManager による利用制限（例：ポジション比率、ドローダウン等）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、プロセス生存、データ鮮度を監視
  - TradeMonitor：滞留注文、約定の価格異常を検出
  - RiskMonitor：ドローダウンやポジション上限の監視とアラート記録
  - MonitoringEngine：各モニタを束ねてポーリング実行
  - AlertManager：LINE Push による通知（設定がある場合）
  - streamlit_dashboard：監視 DB を可視化するダッシュボード
- Portfolio（ポートフォリオ構築）
  - 候補選定（select_candidates）
  - 重み計算（等金額／スコア加重）
  - 単元株丸め・ポジションサイズ計算（リスクベース等）
  - セクターキャップ / レジーム乗数等のリスク調整
- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（情報係数）評価、統計サマリ
- AI（OpenAI 統合）
  - news_nlp.score_news: ニュース記事をまとめて LLM に投げ、銘柄別センチメントを ai_scores テーブルに保存
  - regime_detector.score_regime: ETF の MA200 乖離と LLM のマクロセンチメントを合成して市場レジーム判定を DB に保存
- 開発向けツール
  - tools.paper_verification_report: Paper Trading DB を集計して報告（PASS/FAIL 判定）
  - utils.process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順

前提：Python 3.10+ を推奨（typing の | 演算子を使用）。

1. リポジトリをクローン、作業ディレクトリへ移動

   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化（推奨）

   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール

   requirements.txt がない場合は下記パッケージをインストールしてください（プロジェクトで使用している主な外部依存）:

   ```
   pip install duckdb psutil requests openai streamlit
   ```

   - duckdb: 分析用 DB
   - psutil: プロセス情報・CPU/メモリ情報
   - requests: LINE API 通信など
   - openai: OpenAI API クライアント
   - streamlit: ダッシュボード

4. 環境変数設定（.env をプロジェクトルートに置くことができます）
   - 自動読み込み機構が組み込まれており、プロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を読み込みます。
   - 自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 必要に応じて data ディレクトリを作成

   ```
   mkdir -p data
   ```

---

## 重要な環境変数（主なもの）

- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
- SQLITE_PATH: 監視用 SQLite DB パス — デフォルト: data/monitoring.db
- DUCKDB_PATH: 分析用 DuckDB パス — デフォルト: data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（paper_trading 時に使用） — デフォルト: data/paper_trading.db
- PAPER_FILL_MODE: Paper Trading 時の約定モード（instant / partial / never / reject） — デフォルト: instant
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合は必須）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必要に応じて）
- KABU_API_PASSWORD: kabu ステーション API 用パスワード（実行時のブローカークライアントで必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知を有効化する場合に使用
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒） — デフォルト: 60
- PID_FILE_PATH: ExecutionEngine 用 PID ファイルパス — デフォルト: data/execution.pid
- KILL_FLAG_PATH: KillSwitch 用フラグファイルパス — デフォルト: data/kill.flag

（その他の細かい設定は `kabusys.config.Settings` を参照してください）

---

## 使い方（代表的なコマンド）

- 監視ループ（Monitoring）を起動

  Monitoring は常に本番の monitoring DB パス（Settings.sqlite_path）を使用します（環境に関係なく）。

  ```
  python -m kabusys.run_monitoring
  ```

  オプション:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（例: 30秒）

  例:

  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- 実行エンジン（ExecutionEngine）を起動

  KABUSYS_ENV が `paper_trading` の場合はモックブローカーを使用し、Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録されます。Live では本番ブローカーを使用する想定です。

  ```
  python -m kabusys.run_execution
  ```

- Paper Trading 検証レポートを生成

  tools.paper_verification_report は CLI を提供します。

  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

  または DB を直接指定:

  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- Streamlit 監視ダッシュボードを起動

  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

  ※ `-- --db` の形式で Streamlit に渡す引数を指定します（ダッシュボードの docstring に記載）。

- AI 機能（ニューススコア / レジーム判定）をコードから呼び出す

  Python プログラム内から DuckDB 接続と target_date を渡して呼び出します（OpenAI API キーが必要）。

  例（概念）:

  ```
  from openai import OpenAI
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, target_date=date(2026, 4, 10), api_key="YOUR_OPENAI_KEY")
  ```

  同様に regime_detector.score_regime を使って market_regime テーブルに書き込みができます。

---

## 注意事項 / 運用メモ

- プロセス優先度：run_monitoring / run_execution は開始直後に set_process_priority("high") を呼び出します。OS の権限によっては設定に失敗する場合があります（ログに警告が出ます）。
- DB 初期化：init_monitoring_db は冪等でテーブルを作成し、軽微なマイグレーション（カラム追加）も行います。起動時に DB が自動で準備されます。
- Kill Switch：RiskMonitor 等の結果により kill.flag が書き込まれると、ExecutionEngine 停止判定を行う想定の機構があります。flag ファイルのパスは Settings.kill_flag_path で設定します。
- Paper Trading：Paper Trading は本番 DB と分離された専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用します。PAPER_FILL_MODE を調整して約定の振る舞いを変更できます。
- OpenAI：API 呼び出しは外部依存であり、レート制限やネットワーク障害に対してリトライ・フォールバック処理が実装されていますが、API キー管理とコストに注意してください。
- 自動 .env 読込：プロジェクトルート（.git または pyproject.toml による探索）にある `.env` / `.env.local` を自動で読み込みます。OSの既存環境変数は保護されます。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル / モジュールのツリー（src/kabusys 以下）です。実際のリポジトリには他のモジュールやファイルが存在する可能性があります。

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理
  - run_monitoring.py                 — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py    — Paper Trading 検証レポート生成
  - portfolio/
    - __init__.py
    - portfolio_builder.py            — 候補選定・重み計算
    - position_sizing.py              — 株数計算・丸め・aggregate cap
    - risk_adjustment.py              — セクターキャップ・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py              — ファクター計算（momentum/value/volatility）
    - feature_exploration.py          — 将来リターン / IC / 統計
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュース NLP（OpenAI 統合）
    - regime_detector.py              — マクロ + MA200 を合成したレジーム判定
  - monitoring/
    - __init__.py
    - monitoring_db.py                — monitoring DB の読み書き層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - reconciler.py
    - order_manager.py
    - (その他 broker / engine / risk manager 等のモジュール — リポジトリによる)
  - utils/
    - __init__.py
    - process_priority.py             — プロセス優先度 / affinity ユーティリティ

---

## 開発 / テスト

- 各モジュールは可能な限り純粋関数化しており、ユニットテストのしやすさを意識しています。
- news_nlp / regime_detector の OpenAI 呼び出しは小さなラッパー関数を通しているため、テストではそれらをモック（patch）して動作検証が可能です。
- MonitoringDB 等は SQLite を直接使用しているため、テスト用にメモリ DB（:memory:）や一時ファイルを使って単体テストを作成できます。

---

## 参考 / 補足

- 設計書（PortfolioConstruction.md、StrategyModel.md 等）が存在する想定のコメントがコード内にあります。詳細なアルゴリズムや推奨値はそちらを参照してください（リポジトリ内にあれば）。
- 不明点や設定の詳細は `kabusys.config.Settings` を読み、必要な環境変数を確認してください。

---

以上。必要であれば、README にサンプル .env のテンプレートやデプロイ手順（systemd ユニットファイル例など）を追加しますか？