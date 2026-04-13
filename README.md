# KabuSys

日本株向け自動売買システムのミニマル実装（リサーチ、ポートフォリオ構築、発注、監視、AI ツール群を含む）。

このリポジトリはモジュール群（execution / monitoring / research / portfolio / ai / tools）が含まれており、ローカル環境や Paper Trading モードでの動作を想定しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたライブラリ兼実行環境です。主な関心事は以下です。

- データ処理（DuckDB を利用した価格や財務データの集計）
- ファクター計算・リサーチ（モメンタム、バリュー、ボラティリティ等）
- ポートフォリオ構築（候補選定・重み決め・株数決定）
- 発注実行（Broker 抽象化、ExecutionEngine、OrderManager、Reconciler）
- 監視（System / Trade / Risk のモニタ、Alert via LINE、Streamlit ダッシュボード）
- AI 支援（ニュースのセンチメント解析、レジーム判定 - OpenAI API を利用）
- ツール（Paper Trading 検証レポート等）

設計方針として、以下が守られています：
- 本番 DB / Paper Trading DB を分離（paper_trading モード）
- ルックアヘッドバイアス防止（date.today()/datetime.today() を直接参照しない実装）
- フェイルセーフ（API 失敗時はデフォルト値で継続、部分失敗を許容）
- 単体関数は副作用が少ない「純粋関数」や明確に責務分離されたクラス化

---

## 主な機能一覧

- Execution
  - 発注の作成 / 送信 / 同期（OrderManager）
  - 再起動時の自動リコンシリエーション（Reconciler）
  - RiskManager による発注前リスク判定
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス存在確認 / データ鮮度監視
  - TradeMonitor: 滞留注文 / 約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: 条件到達時に flag ファイルを書いて Execution を停止させる仕組み
  - AlertManager: LINE Push による通知（クールダウンあり）
  - Streamlit ダッシュボード（監視データの可視化）
- Research / Portfolio
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算・IC（情報係数）・統計サマリー
  - 候補選定・重み付け・ポジションサイズ計算・セクターキャップ・レジーム乗数
- AI
  - news_nlp: ニュース記事を OpenAI でセンチメント評価し ai_scores に保存
  - regime_detector: ETF の MA200 とマクロニュースから日次レジーム判定
- Tools
  - paper_verification_report: Paper Trading の検証レポート生成

---

## セットアップ手順

前提
- Python 3.10 以上（Union 型表記 X | Y を使用しているため）
- sqlite3 は標準ライブラリ
- DuckDB, psutil, requests, openai, streamlit など外部ライブラリが必要

1. リポジトリをクローン／取得
2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（requirements.txt が無ければ下記をインストール）
   - pip install duckdb psutil requests openai streamlit
   - 必要に応じて追加ライブラリをインストールしてください
4. 環境変数設定
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を置くと自動で読み込まれます
   - 自動読み込みを無効化したい場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
5. データディレクトリ作成
   - data/ 配下に DB ファイル等を配置（例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）

推奨の環境変数（最低限）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能を使う場合は必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動、デフォルト: instant）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（Paper Trading 用 DB、デフォルト: data/paper_trading.db）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（LINE 通知を利用する場合）

例 .env（プロジェクトルート）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

---

## 使い方

いくつかのエントリポイント（スクリプト）を紹介します。

- ExecutionEngine 起動（本番/紙取引で DB を分離）
  - python -m kabusys.run_execution
  - 実装メモ:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（デフォルト data/paper_trading.db）に記録します。
    - 起動直後にプロセス優先度を "high" に設定します（psutil を使用）。
    - Engine は ExecutionEngine.run_session() を実行します。

- Monitoring の永続ポーリング起動
  - python -m kabusys.run_monitoring
  - 実装メモ:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用する注意点があります（run_monitoring の仕様）。
    - PID ファイルのチェックやデータ鮮度チェック、RiskMonitor/TradeMonitor 等を呼び出します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH を上書き）
  - 出力: 標準出力にレポートを表示。稼働率、注文成功率、送信率、レイテンシ等を集計して PASS/FAIL 判定します。

- Streamlit ダッシュボード（監視向け）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視用 SQLite を読み取り専用で開いてダッシュボード表示します。MonitoringEngine を動かした上で参照してください。

- AI 機能（ニューススコア・レジーム判定）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を duckdb 接続と date, API key などを指定して呼び出します。
  - OpenAI API キーが必要です（OPENAI_API_KEY 環境変数、または引数で渡す）。

注意点 / トラブルシューティング
- 必須環境変数が未設定だと Settings クラスで ValueError が送出されます（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
- monitoring DB が存在しないと Streamlit ダッシュボード起動時にエラーとなります（MonitoringEngine を先に起動して DB を作成してください）。
- MONITOR_POLL_INTERVAL に 0 以下を渡すと無効扱いでデフォルトにフォールバックします（ログで警告）。

---

## ディレクトリ構成

主要ファイル・ディレクトリ（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数/.env のロードロジック、Settings クラス（各種設定取得）
  - run_execution.py
    - ExecutionEngine の起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュース記事を OpenAI でセンチメントスコア化して ai_scores に書き込む
    - regime_detector.py
      - マクロセンチメントと ETF MA を合成して日次レジーム判定を行い market_regime に書き込む
  - monitoring/
    - __init__.py
    - monitoring_db.py
      - SQLite のスキーマ初期化と簡易 DB ラッパ（MonitoringDB）
    - system_monitor.py
      - CPU/メモリ/ディスク/データ鮮度/実行プロセスの監視
    - trade_monitor.py
      - 滞留注文・約定異常の検出
    - risk_monitor.py
      - ドローダウン / ポジション上限の監視
    - kill_switch.py
      - フラグファイルを書いて Execution を停止させるロジック
    - alert_manager.py
      - LINE Push による通知
    - monitoring_engine.py
      - 上記各 Monitor を束ねてポーリングを行うエンジン
    - streamlit_dashboard.py
      - Streamlit を使った監視 UI
  - execution/
    - order_manager.py
    - reconciler.py
    - （その他発注関連モジュール。Broker 抽象化や OrderRepository など）
  - portfolio/
    - portfolio_builder.py
      - 候補選定・重み付け（等重・スコア重み）
    - position_sizing.py
      - 株数決定（risk_based / equal / score）
    - risk_adjustment.py
      - セクターキャップ、レジーム乗数
  - research/
    - factor_research.py
      - モメンタム / ボラティリティ / バリューのファクター計算（DuckDB を利用）
    - feature_exploration.py
      - 将来リターン計算・IC（スピアマン）・統計サマリー
  - tools/
    - paper_verification_report.py
      - Paper Trading の検証レポート生成 CLI
  - utils/
    - process_priority.py
      - psutil を使ったプロセス優先度 / CPU affinity 設定ユーティリティ

data/（プロジェクトルートに想定されるディレクトリ - サンプル）
- data/kabusys.duckdb  (DuckDB ファイル)
- data/monitoring.db    (監視用 SQLite)
- data/paper_trading.db (Paper Trading 用 SQLite)
- data/execution.pid    (ExecutionEngine の PID ファイル)
- data/kill.flag        (KillSwitch 用フラグファイル)

---

## 開発・拡張のヒント

- DuckDB 接続を渡すことで Research モジュールを外部データセットで容易に試験できます。
- OpenAI 呼び出し部分はテストしやすいようにラップ／置換（_call_openai_api のモック化）しやすい設計になっています。
- MonitoringDB は単純な読み書き層に留められているため、監視ロジックはテストしやすいです（MonitoringEngine.run_once をユニットテストで利用可能）。
- Paper Trading 用 DB は本番 DB から分離されるため、シミュレーション実行が安全に行えます。

---

もし README に追加したい箇所（例: requirements.txt の自動生成、具体的な起動例、CI 設定、LICENSE 等）があれば教えてください。必要に応じて追記・修正します。