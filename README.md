# KabuSys

KabuSys は日本株向けの自動売買システム（研究・シミュレーション・実行・監視を含む）です。  
このリポジトリには注文実行エンジン、ポートフォリオ構築、リサーチ用ファクター計算、ニュースの NLP スコアリング（OpenAI 利用）、および稼働監視・アラート機能が実装されています。

主な設計方針：
- DuckDB / SQLite を利用したローカルデータ操作（外部ブローカー API への依存は抽象化）
- Paper trading（模擬取引）モードと本番モードの明確な分離（DB も分離）
- ルックアヘッドバイアス防止（日時参照の扱いに注意）
- フェイルセーフ（API 失敗時のフォールバック、冪等操作）

---

## 機能一覧（ハイライト）

- Execution（発注・注文状態管理）
  - OrderManager / ExecutionEngine による注文生成、送信、状態同期、リコンシリエーション
  - Broker クライアントの抽象化（本番 / Mock を切替可能）
  - RiskManager による発注前リスク判定

- Portfolio（銘柄選定・配分）
  - 候補選定、等配分 / スコア加重配分
  - ポジションサイズ計算（リスクベース、lot 単位丸め、aggregate cap）
  - セクター集中制限、レジーム乗数

- Research（因子計算・特徴探索）
  - Momentum / Volatility / Value ファクター計算（DuckDB 上の prices_daily/raw_financials）
  - 将来リターン計算、IC（スピアマン）計算、基本統計サマリ

- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント -> ai_scores 書込
  - マクロ記事を用いた市場レジーム判定（bull/neutral/bear）と DB への保存
  - API 呼び出しはリトライ・スコア検証・安全クリッピング実装

- Monitoring（監視・アラート）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（ポーリング）
  - SQLite ベースの監視ログ（system_status, trade_logs, positions, risk_logs, dashboard）
  - LINE へプッシュ通知（AlertManager）
  - kill.flag を書いて ExecutionEngine を停止させる KillSwitch
  - Streamlit ダッシュボード（read-only 接続）で監視情報表示

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
  - process priority / CPU affinity ユーティリティ

---

## 前提 / 必要環境

- Python 3.10 以上（PEP 604 の union 型、from __future__ annotations を使用）
- SQLite（標準ライブラリに同梱）
- 推奨依存パッケージ（requirements.txt がある場合はそちらを使用）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit

インストール例：
- 仮想環境作成（推奨）
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージのインストール（手動）
  - pip install duckdb psutil openai requests streamlit

（プロジェクトに requirements.txt を用意している場合は pip install -r requirements.txt を使用）

---

## 環境変数（主なもの）

アプリ設定は環境変数またはプロジェクトルートの .env / .env.local によって読み込まれます。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

重要な変数：
- KABUSYS_ENV: 起動環境。development / paper_trading / live（必須ではないが有効値チェックあり）
  - paper_trading の場合、MockBrokerClient が使用され、データベースは paper_trading 用に分離されます。
- JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
- KABU_API_PASSWORD: kabu ステーション API（必須）
- OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム検出で必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant / partial / never / reject）
- PID_FILE_PATH / KILL_FLAG_PATH: プロセス制御用ファイルパス
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用トークン・ユーザ ID

その他:
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）。0以下の値は無効扱いでデフォルトにフォールバック。

.env の読み込み優先度:
- OS 環境変数 > .env.local > .env

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存パッケージをインストール
   - pip install duckdb psutil openai requests streamlit

4. .env を作成（リポジトリに .env.example があれば参照）
   - 必要なキーを設定（最低: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY を状況に応じて設定）

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（起動コマンド例）

注意: ソースがパッケージとして配置されている場合は python -m kabusys.<module> で実行できます（repo のルートを PYTHONPATH に含めるか pip install -e . を行う）。

1. ExecutionEngine を起動（本番/模擬を自動判定）
   - python -m kabusys.run_execution
   - Paper trading モードで実行するには環境変数 KABUSYS_ENV=paper_trading を設定：
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - 実行開始時にプロセス優先度を "high" に設定します（set_process_priority）。

2. Monitoring を単独で起動（ポーリング監視）
   - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
   - デフォルト 60 秒ごとに SystemMonitor.check_once() を呼び出します。
   - run_monitoring は monitoring DB（Settings.sqlite_path）を使用（環境にかかわらず本番 sqlite_path を使います）。

3. Streamlit ダッシュボード（監視データ閲覧）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 監視 DB を読み取り専用で開き、Overview/Positions/Orders/System タブを表示します。

4. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB: data/paper_trading.db。--db で別パス指定可。

5. AI スコアリング / レジーム判定（ライブラリ API）
   - kabusys.ai.score_news(...)
   - kabusys.ai.regime_detector.score_regime(...)
   - これらは DuckDB 接続および API キーを渡して呼び出します（CLI エントリポイントはなし）。

---

## 運用メモ / 重要ポイント

- Paper trading は本番 DB と完全分離（設定により paper_trading 用 SQLite を使用）。実データと混同しないよう注意。
- Monitoring は常に本番 sqlite_path を使用する設計（KABUSYS_ENV に依存しない）。
- kill.flag による停止シグナル：KillSwitch が kill.flag ファイルを書き込むと ExecutionEngine 側がそれをチェックして安全に停止する仕組みを想定。
- OpenAI 呼び出しでは 429/ネットワーク/5xx をリトライし、レスポンスのバリデーションとスコアクリッピングを行います。API キーが未設定の場合は ValueError を送出する箇所があります。
- プロセス優先度設定はプラットフォーム依存（psutil を用いる）。権限不足時は警告を出してスキップされます。
- .env のパースは独自実装されており、クォートや export 形式、コメント処理にある程度対応しています。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / 設定の読み込みと Settings クラス
  - run_execution.py — ExecutionEngine 起動スクリプト（KABUSYS_ENV による paper_trading 切替）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成ツール（CLI）
  - portfolio/
    - portfolio_builder.py — 候補選定・等重/スコア重み計算
    - position_sizing.py — 株数決定、aggregate cap、lot 単位調整
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py — raw_news を OpenAI でスコア化して ai_scores に書き込むロジック
    - regime_detector.py — マクロ＋ETF MA で市場レジーム判定（OpenAI 利用）
  - monitoring/
    - monitoring_db.py — SQLite スキーマ作成・読み書きユーティリティ（MonitoringDB）
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・PID チェック
    - trade_monitor.py — 注文滞留・約定異常価格検出
    - risk_monitor.py — ドローダウン・ポジション上限モニタ
    - kill_switch.py — kill.flag の読み書きと評価ロジック
    - alert_manager.py — LINE 通知ラッパ
    - monitoring_engine.py — 複数モニタを束ねたポーリング実行クラス
    - streamlit_dashboard.py — streamlit ベースの監視ダッシュボード（起動用スクリプト）
  - execution/
    - order_manager.py — 注文ワークフロー（作成・送信・キャンセルなど）
    - reconciler.py — 起動時の注文/ポジションリコンシリエーション
    - その他（broker, order_repository, order_record, execution_engine 等は存在が想定されます）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記はこの README で取り上げた主なモジュールの抜粋です。詳細な実装や未表示ファイルも含まれます。）

---

## 開発者向けメモ

- DuckDB / SQLite のスキーマやマイグレーションは monitoring_db.init_monitoring_db() 内で行われます（冪等）。
- テスト時に外部 API をモックしやすい設計（OpenAI 呼び出しはラッパー関数でまとめられ、テスト時に差し替え可能）。
- 時刻周りはルックアヘッドを避ける方針：関数呼び出し側で target_date を渡す設計が多いです。
- ログは標準 logging を使用。簡易にログレベルを変更するには LOG_LEVEL 環境変数を設定してください。

---

必要であれば、README にサンプル .env テンプレート、より詳しい実行例（systemd ユニットファイル例、Dockerfile、CI 設定）や開発者向けのテスト手順を追加できます。どの情報を優先して追加しますか？