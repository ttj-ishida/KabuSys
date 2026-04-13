# KabuSys

日本株向け自動売買フレームワーク（ライブラリ兼実行コンポーネント）。  
戦略のポートフォリオ構築、約定実行、監視・アラート、研究用ファクター計算、ニュースNLP（OpenAI）によるセンチメント評価などを備えています。

---

## プロジェクト概要

KabuSys は以下の責務を分離して実装した自動売買基盤です。

- Execution: 注文生成・送信・リコンシリエーション（Broker 抽象化）
- Monitoring: プロセス／リソース監視、注文滞留・約定異常検出、kill‑switch、LINE 通知、Streamlit ダッシュボード
- Portfolio: 候補選定、重み付け、ポジションサイズ計算、セクター制約、レジーム乗数
- Research: DuckDB を用いたファクター計算（momentum/value/volatility）と特徴量解析
- AI: OpenAI を使ったニュースセンチメント（ai_scores）および市場レジーム判定
- Utils/Config: 環境変数自動ロード、プロセス優先度設定などユーティリティ

設計方針の一部:
- DuckDB / SQLite をデータ層に使用（リサーチは DuckDB、監視は SQLite）  
- 環境変数ベースの設定（.env/.env.local の自動読込をサポート）  
- Paper Trading（KABUSYS_ENV=paper_trading）用に本番 DB と分離された挙動をサポート

---

## 主な機能一覧

- Execution
  - ExecutionEngine: ブローカークライアント経由で注文を発行・管理
  - Reconciler: 起動時の注文・ポジション同期
  - OrderManager / OrderRepository: 注文ライフサイクル管理（DB 永続化）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定価格異常を検出
  - RiskMonitor: ドローダウンおよびポジション数上限の監視 → risk_logs 登録
  - KillSwitch: 条件で kill.flag を書き込み Execution 停止指示
  - AlertManager: LINE Push によるアラート送信（クールダウン管理）
  - Streamlit ダッシュボード: 監視データの可視化
- Portfolio
  - 候補選定（スコア降順）、等配分/スコア重み、リスクベースの株数算出、セクター制約
- Research
  - momentum/value/volatility 等のファクター計算（DuckDB）
  - 将来リターン、IC 計算、統計サマリ
- AI
  - news_nlp.score_news: OpenAI でニュースをまとめて銘柄ごとのセンチメントを ai_scores に保存
  - regime_detector.score_regime: ETF + マクロニュースを合成して日次レジーム判定
- ユーティリティ
  - 環境変数自動ロード（.env / .env.local）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順

前提: Python 3.9+（パッケージがお使いの環境に依存する可能性あり）

1. リポジトリのクローン / ソース配置
   - コードは `src/kabusys` 下に配置されています。

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 依存パッケージのインストール
   - 必要な主なパッケージ（例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用してください）

4. 環境変数の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（デフォルト）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（例）:
   - KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須用途あり）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須用途あり）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能使用時に必須）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
   - SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB パス（デフォルト: data/kabusys.duckdb）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE: paper_trading 時の約定挙動 (instant | partial | never | reject)
   - PID_FILE_PATH, KILL_FLAG_PATH, その他しきい値（CPU_THRESHOLD_PCT 等）

   簡易 .env.example:
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

5. データディレクトリ作成
   - data ディレクトリを作成して DB ファイルを置く／作成できるようにします。
   - mkdir -p data

---

## 使い方

以下は主要な実行例です。いずれもプロジェクトルート（src を PYTHONPATH に含める）で実行してください。

- 実行モードの切替
  - KABUSYS_ENV によって動作が変わります。
    - development: 開発モード（デフォルト）
    - paper_trading: ブローカーは Mock を用い、DB は PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）を使用して本番と完全分離
    - live: 本番運用

1. Monitoring ポーリングを起動
   - python -m kabusys.run_monitoring
   - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60）
   - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用します（監視ログは常に本番 DB に保存）

2. ExecutionEngine を起動（実際の取引フローを実行）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合は mock broker を使用し、data/paper_trading.db を使用

3. Streamlit 監視ダッシュボード
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - または streamlit run -m kabusys.monitoring.streamlit_dashboard -- --db data/monitoring.db

4. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     - --from YYYY-MM-DD
     - --to YYYY-MM-DD
     - --db PATH （PAPER_TRADING_SQLITE_PATH を上書き）
   - 例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

5. AI (ニューススコア / レジーム判定)
   - news_nlp.score_news(conn, target_date, api_key=None)
     - DuckDB 接続と target_date（日付）を渡して実行すると ai_scores テーブルへ結果を書き込みます。
     - api_key を省略すると環境変数 OPENAI_API_KEY が使われます。
   - regime_detector.score_regime(conn, target_date, api_key=None)
     - ETF とマクロニュースを元に market_regime テーブルへ日次判定を書き込みます。

6. プロセス優先度設定
   - run_monitoring/run_execution は起動時に set_process_priority("high") を呼びます。
   - utils.process_priority.set_process_priority(level) を個別に利用可能（Windows / POSIX を吸収）。

注意事項:
- 実行中に ExecutionEngine を強制停止したい場合は kill_switch が有効になっていると Monitoring が kill.flag を書き、Execution 側で検出して停止できます（flag は Settings.kill_flag_path で制御）。
- Paper Trading は本番データベースと分離されるため、検証時の DB 汚染を避けられます。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動ロード、Settings クラス（アプリ設定の集中管理）
  - run_monitoring.py
    - SystemMonitor をポーリングする起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するスクリプト（paper_trading の分離対応）
  - tools/
    - paper_verification_report.py
      - Paper Trading の検証レポート出力用 CLI
  - monitoring/
    - monitoring_db.py
      - SQLite に対するテーブル初期化・読み書きラッパー（MonitoringDB）
    - system_monitor.py
      - システム状態・データ鮮度をチェック
    - trade_monitor.py
      - 注文滞留・約定異常検出
    - risk_monitor.py
      - ドローダウン・ポジション数監視
    - kill_switch.py
      - kill.flag 制御（Execution 停止トリガー）
    - alert_manager.py
      - LINE Push によるアラート通知
    - monitoring_engine.py
      - 各モニタを束ねるエンジン
    - streamlit_dashboard.py
      - Streamlit を用いたダッシュボード
  - execution/
    - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, broker_factory.py, broker_api.py, ...
    - 注文管理・ブローカー抽象化・起動時リコンシリエーション等
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - ポートフォリオ選定・重み付け・単元丸め・セクターキャップ等
  - research/
    - factor_research.py
      - momentum/value/volatility の DuckDB SQL 実装
    - feature_exploration.py
      - 将来リターン、IC、統計サマリ等
  - ai/
    - news_nlp.py
      - ニュースをまとめて OpenAI に投げ、ai_scores に書き込む
    - regime_detector.py
      - ETF MA とマクロニュースを用いたレジーム判定
  - data/  （期待される出力・DB 保存先：プロジェクトルートに作成）
    - kabusys.duckdb (DuckDB)
    - monitoring.db or paper_trading.db (SQLite)
    - kill.flag / execution.pid など

---

## 実運用上の注意点・設計上のポイント

- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を起点に行います。プロジェクト配布後も動作するよう設計されています。
- Monitoring の DB 初期化（init_monitoring_db）は冪等であり、既存 DB に対するマイグレーション（カラム追加）も実装されています。
- Paper Trading は本番 DB と明確に分離されるよう配慮されています（設定に応じて sqlite_path を切り替え）。
- OpenAI 呼び出しは再試行・バックオフ・レスポンスバリデーションを行い、失敗時はフォールバック（例: スコア＝0.0）するなどフェイルセーフ設計です。
- プロセス優先度や CPU affinity の設定は OS に依存するため、権限不足や未対応 OS の場合は警告を出してスキップします。

---

もし README に追加したい内容（例: requirements.txt の自動生成、systemd ユニットのサンプル、Dockerfile、さらなる環境変数の詳細、API スペック）や、特定モジュールの詳細ドキュメント化をご希望であれば教えてください。