# KabuSys — 自動売買システム（README）

このリポジトリは日本株の自動売買/調査/監視を目的とした軽量なフレームワークです。  
以下はコードベース（src/kabusys 以下）の概要、機能、セットアップ手順、使い方、ディレクトリ構成の説明です。

## プロジェクト概要
KabuSys は以下の主要機能を備えたモジュール群で構成されています。
- シグナルに基づく発注エンジン（ExecutionEngine）
- 発注のライフサイクル管理（OrderManager / OrderRepository）
- 起動時のリコンシリエーション（Reconciler）
- ポートフォリオ構築・ポジションサイズ計算（portfolio）
- ファクター計算・研究ユーティリティ（research）
- ニュース NLP を用いた銘柄センチメント評価・レジーム判定（ai）
- システム稼働状況、注文・リスク監視およびアラート（monitoring）
- 環境設定管理（config）とプロセス優先度ユーティリティ（utils）

設計方針の要点：
- DB は DuckDB（時系列/ファクターデータ等）と SQLite（監視用/注文用）を併用
- Paper trading と Live は DB を分離（KABUSYS_ENV に依存）
- OpenAI（LLM）を使った NLP 機能は環境変数で API キーを注入
- フェイルセーフ設計（API失敗時のフォールバック、部分失敗を許容）

---

## 機能一覧（代表的なもの）
- Execution
  - Signal → Order 作成 → ブローカー送信の安全な 2 相永続化フロー
  - リコンシリエーション（再起動時の同期）
  - リスクゲート（レートリミット、最大ポジション、ドローダウン等）
- Portfolio
  - 候補選定（score / rank に基づく）
  - 等重・スコア加重配分
  - ポジションサイズ計算（risk_based / equal / score）
  - セクターキャップ適用、レジーム乗数
- Research
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）等の解析ツール
- AI
  - news_nlp: OpenAI を用いたニュースセンチメントの銘柄別スコア化（ai_scores テーブルへ記録）
  - regime_detector: ETF とマクロニュースを組み合わせた市場レジーム判定
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/データ鮮度/プロセス存在チェック
  - TradeMonitor: 滞留注文・約定価格異常の検出
  - RiskMonitor: ドローダウン / ポジション数の監視とログ・アラート
  - KillSwitch: 条件に応じて kill.flag を書き込み、ExecutionEngine に停止を促す
  - AlertManager: LINE push による通知（クールダウン付き）
  - Streamlit ダッシュボード（data/monitoring.db を読み取り専用で可視化）
- Utilities
  - 環境変数の自動ロード（.env / .env.local）
  - プロセス優先度・CPU affinity 設定ユーティリティ

---

## 必要環境 / 依存パッケージ（例）
- Python 3.9+（typing の一部記法に依存）
- pip install で導入する主要パッケージ例:
  - duckdb
  - psutil
  - requests
  - streamlit
  - openai
  - （標準ライブラリ: sqlite3 等）

（requirements.txt は本リポジトリに含めてください。上記は最低限の例です）

---

## 環境変数（主なもの）
config.py で扱う主要な環境変数（一部）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合は必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PID_FILE_PATH, KILL_FLAG_PATH 等の監視関連パス
- PAPER_FILL_MODE: paper_trading 時の模擬約定挙動（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、既定 60）

注意: .env/.env.local をプロジェクトルートに置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

---

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローンし、プロジェクトルートを決める
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb psutil requests streamlit openai
   - （requirements.txt を用意している場合は pip install -r requirements.txt）
4. データディレクトリを作成
   - mkdir -p data
5. 環境変数を設定（.env を作成）
   - 例（.env）:
     - KABUSYS_ENV=development
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
6. DuckDB / SQLite の初期テーブル
   - monitoring 用テーブルは起動スクリプトが自動で init します（init_monitoring_db）。
   - DuckDB の prices_daily / raw_financials 等のテーブルはデータ投入手順に従って準備してください（外部データ取り込みが必要）。

---

## 使い方（起動方法 / コマンド例）

注意: パッケージをインストールしていない開発環境では PYTHONPATH を指定して直接実行できます。
例: PYTHONPATH=src python -m kabusys.run_execution

1. ExecutionEngine（発注エンジン）を起動
   - 本番/デバッグ:
     - PYTHONPATH=src python src/kabusys/run_execution.py
   - モジュール実行:
     - PYTHONPATH=src python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に書き込まれます。

2. MonitoringEngine（監視ループ）を起動
   - PYTHONPATH=src python src/kabusys/run_monitoring.py
   - ポーリング間隔を環境変数で上書き:
     - MONITOR_POLL_INTERVAL=30 PYTHONPATH=src python src/kabusys/run_monitoring.py
   - 監視は常に production 用の sqlite_path を参照（KABUSYS_ENV にかかわらず監視 DB は本番 path を使用する設計）。

3. Streamlit ダッシュボード（監視 UI）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - Dashboard は読み取り専用で SQLite DB を開きます。MonitoringEngine がデータを書き込む必要があります。

4. AI 機能（ニューススコアリング / レジーム判定）の手動実行（例: Python REPL）
   - from datetime import date
     import duckdb
     from kabusys.ai.news_nlp import score_news
     conn = duckdb.connect("data/kabusys.duckdb")
     score_news(conn, date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
   - レジーム:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(conn, date(2026,3,20), api_key="YOUR_OPENAI_KEY")

5. kill.flag 操作
   - KillSwitch により生成される停止フラグはデフォルト data/kill.flag（Settings.kill_flag_path）
   - ExecutionEngine は起動時にこのファイルが存在すると即座に停止をトリガーする設計になっています。
   - 起動前にフラグをクリアする例:
     - rm -f data/kill.flag
   - Monitoring の KillSwitch は条件検知時にファイルを書き込みます（理由をファイルに保存）。

---

## 設定の注意点 / 運用上のポイント
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかを指定。Paper trading は発注系を安全に模擬するため DB を分離します。
- OpenAI を利用する機能は API キーが必須。失敗時はフォールバック動作（ニュースがない場合はスコア 0.0 等）を行いますが、API キーは設定してください。
- Execution と Monitoring の両プロセスは pid_file にプロセス ID を書くことで互いにプロセス存在を確認します（SystemMonitor の監視対象）。
- プロセスの優先度は起動時に set_process_priority("high") が呼ばれます。権限によっては設定に失敗するのでログで確認してください。
- LINE 通知は channel token と user id が未設定のときは送信せずログに残します。

---

## ディレクトリ構成（src/kabusys）
以下は主要ファイル／ディレクトリのツリー（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数/.env ロード & Settings
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor 単体のポーリングスクリプト
  - utils/
    - __init__.py
    - process_priority.py          — プロセス優先度 / CPU affinity
  - execution/
    - execution_engine.py          — ExecutionEngine 本体
    - order_manager.py             — 発注状態マネージャ
    - order_repository.py          — SQLite への注文保存（実装ファイルあり）
    - order_record.py              — OrderRecord と状態遷移（実装ファイルあり）
    - reconciler.py                — 起動時リコンシリエーション
    - broker_factory.py            — Broker クライアント生成
    - broker_api.py                — Broker API プロトコル / 例外定義
    - risk_manager.py              — 実行時リスク管理
  - portfolio/
    - portfolio_builder.py         — 候補選定・スコアソート
    - position_sizing.py           — 株数/ラウンド/aggregate cap ロジック
    - risk_adjustment.py           — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py           — momentum / volatility / value 等
    - feature_exploration.py       — 将来リターン / IC / summary
    - __init__.py
  - ai/
    - news_nlp.py                  — ニュースセンチメント（OpenAI）
    - regime_detector.py           — 市場レジーム判定（ETF + macro news）
    - __init__.py
  - monitoring/
    - monitoring_db.py             — SQLite schema + MonitoringDB ラッパー
    - system_monitor.py            — CPU/メモリ/データ鮮度/プロセス監視
    - trade_monitor.py             — 注文滞留/約定異常検出
    - risk_monitor.py              — DD / position_limit の監視
    - kill_switch.py               — kill.flag 書き込みロジック
    - alert_manager.py             — LINE push
    - monitoring_engine.py         — 各 monitor を束ねるループ
    - streamlit_dashboard.py       — Streamlit ダッシュボード起動スクリプト
    - __init__.py
  - monitoring/monitoring_db.py    — SQLite テーブル初期化・操作
  - research/..., portfolio/...    — その他の補助モジュール

（実際のファイルは src/kabusys 以下の各サブディレクトリを参照してください）

---

## 開発 / デバッグのヒント
- DuckDB のクエリは開発時に直接接続して結果を確認できます（duckdb.connect("data/kabusys.duckdb")）。
- MonitoringDB の init_monitoring_db() は冪等なので何度呼んでも安全です。起動スクリプトが自動で呼び出します。
- LLM 呼び出し部（kabusys.ai.news_nlp, kabusys.ai.regime_detector）の API コールはテスト可能なように内部関数をモックできる作りです（ユニットテスト時は _call_openai_api を patch）。

---

## ライセンス / 貢献
- README に含まれていないライセンス情報・貢献ガイドラインはリポジトリルートに追記してください（LICENSE, CONTRIBUTING.md 等）。

---

以上がこのコードベースの README.md です。必要であれば以下の追記を作成できます：
- requirements.txt の推奨内容
- .env.example のテンプレート
- データ投入（prices_daily / raw_financials 等）手順書
- 運用手順（systemd / supervisor 用の unit ファイル例）