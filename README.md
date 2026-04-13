# KabuSys

日本株自動売買システムの一部を含むコードベース向け README（日本語）。

この README は与えられたソースコードに基づき、プロジェクト概要・機能・セットアップ・使い方・ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を行うためのモジュール群です。本リポジトリには以下の主要領域が含まれます。

- 実行（Execution）：発注管理・リスク管理・ブローカー連携・再同期（Reconciler）
- 監視（Monitoring）：プロセス・システム資源・注文の滞留や約定異常、ドローダウン監視・アラート送信
- ポートフォリオ構築（Portfolio）：候補選定・重み算出・ポジションサイズ計算・リスク調整
- リサーチ（Research）：ファクター計算・特徴量探索（IC 等）
- AI（ai）：ニュースセンチメント（OpenAI を利用）・市場レジーム判定
- ユーティリティ（utils）：プロセス優先度や CPU affinity の設定等
- ツール（tools）：Paper Trading 検証レポート生成など

コア設計方針の例：
- DuckDB / SQLite をデータ格納に利用（DuckDB は時系列分析、SQLite は監視ログや注文ログ）
- 日時周りでルックアヘッドを避ける実装（テスト/後処理の安全性重視）
- フェイルセーフ：外部 API（OpenAI 等）失敗時は局所フォールバックして継続

---

## 主な機能一覧

- SystemMonitor：CPU/メモリ/ディスク・プロセス状態・データ鮮度を監視しログ格納
- TradeMonitor：滞留注文検出・約定価格異常の検出とログ化
- RiskMonitor：ドローダウンやポジション数上限の監視、kill.flag による停止指示
- AlertManager：LINE Messaging API での通知（クールダウン機能あり）
- MonitoringEngine：上記モニタ群のポーリングエンジン
- ExecutionEngine（起動スクリプトを含む）：ブローカー接続、OrderManager、RiskManager、Reconciler を組み合わせて実行
- Reconciler：再起動時の注文・ポジション差分の自動同期
- Portfolio：候補選定、等配分/スコア配分、ポジションサイズ計算、セクター上限適用、レジーム乗数計算
- Research：モメンタム/ボラティリティ/バリューなどのファクター計算、将来リターン、IC/統計サマリ
- AI：ニュースを OpenAI でセンチメント評価し ai_scores に保存、マクロセンチメントと MA200 によるレジーム判定
- Tools：paper_trading の検証レポート生成（集計と PASS/FAIL 判定）

---

## 要求環境 / 依存パッケージ

- Python 3.10 以上（タイプヒントで `X | Y` などを使用）
- 主な Python ライブラリ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード起動時）
- 推奨: 仮想環境（venv / poetry / pipenv 等）

※ requirements.txt はこのスニペットに含まれていません。上記パッケージを pip でインストールしてください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate
3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトの requirements.txt があれば pip install -r requirements.txt）
4. デフォルトのデータディレクトリを作成
   - mkdir -p data
5. 環境変数を設定（必須/任意は次章参照）
   - 例: export KABUSYS_ENV=development
   - .env / .env.local をプロジェクトルートに置くと自動で読み込まれる（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
6. DB 初期化は run_monitoring / run_execution 実行時に自動で行われる（monitoring DB の初期テーブル作成が行われる）

---

## 環境変数（主なもの）

必須（実行する機能により変わります）：
- JQUANTS_REFRESH_TOKEN：J-Quants API トークン（Settings.jquants_refresh_token）
- KABU_API_PASSWORD：kabuステーション API パスワード

一般／データベース：
- KABUSYS_ENV：environment（development / paper_trading / live）。デフォルト: development
- LOG_LEVEL：ログレベル（DEBUG, INFO, ...）、デフォルト: INFO
- DUCKDB_PATH：DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH：監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH：paper trading 用 SQLite（デフォルト: data/paper_trading.db）

監視・実行設定：
- PID_FILE_PATH：ExecutionEngine 用 PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH：kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START：起動時に kill.flag をクリアするか（"1" で有効）
- MONITOR_POLL_INTERVAL：SystemMonitor のポーリング間隔（秒、デフォルト: 60）。0 以下や不正値はデフォルトにフォールバック

Paper trading / AI：
- PAPER_FILL_MODE：paper trading の fill 動作（instant|partial|never|reject、デフォルト instant）
- OPENAI_API_KEY：OpenAI を使う機能（news_nlp / regime_detector）で必須

その他：
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化

---

## 使い方（主要スクリプト / コマンド）

以下は典型的な起動例です。プロジェクトルート（.git または pyproject.toml がある場所）で実行してください。

1. 監視ループを起動（SystemMonitor 単体）
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
   - 監視は Settings に従い monitoring DB（SQLITE_PATH）に書き込みます

2. 実行エンジン（ExecutionEngine）を起動
   - export KABUSYS_ENV=paper_trading   # 本番と分離して Paper Trading モードで起動する例
   - python -m kabusys.run_execution
   - paper_trading の場合は MockBrokerClient が選ばれ、PAPER_TRADING_SQLITE_PATH に記録します
   - 実行前に必須な環境変数（KABU_API_PASSWORD 等）を設定してください

3. Streamlit 監視ダッシュボード（読み取り専用で監視 DB を参照）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 既存の monitoring.db を read-only モードで開き、Overview / Positions / Orders / System タブを表示

4. Paper Trading 検証レポート生成ツール
   - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-10
   - 引数 --db を省略すると PAPER_TRADING_SQLITE_PATH 環境変数またはデフォルト path を使用
   - レポートでは稼働率・注文成功率・送信率・P95 レイテンシ等を出力し PASS/FAIL を判定

5. AI 機能（ニューススコア・レジーム判定）
   - OpenAI API キー（OPENAI_API_KEY）が必要
   - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を Python から呼ぶ形で利用
   - 例（インタラクティブ）:
     - >>> from kabusys.ai.news_nlp import score_news
     - >>> import duckdb, datetime
     - >>> conn = duckdb.connect("data/kabusys.duckdb")
     - >>> score_news(conn, datetime.date(2026,4,10), api_key="sk-...")

注意点：
- monitoring DB の初期テーブルは run_monitoring/run_execution 実行時に init_monitoring_db により作成されます（冪等）。
- OpenAI 呼び出しはエラー耐性・リトライ実装あり（ただし API キーは必要）。

---

## 運用上の注意

- Process Priority 設定：
  - run_monitoring / run_execution 起動時に set_process_priority("high") を呼び出します。psutil による権限要求で失敗する場合は警告が出ますが処理は継続します。
- kill.flag：
  - RiskMonitor 等は条件を満たすと KILL_FLAG_PATH（デフォルト data/kill.flag）に理由を書き込みます。ExecutionEngine はこのフラグを検知して安全停止することが期待されます。
  - Execution 起動時に kill.flag をクリアしたい場合は Settings.kill_flag_clear_on_start を "1" に設定してください。
- DB 分離：
  - paper_trading モードでは paper_sqlite_path を使用して本番監視 DB と完全に分離されます。

---

## ディレクトリ構成（抜粋）

以下は `src/kabusys` 配下の主要ファイル / モジュール構成（与えられたソースに基づく抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                          — 環境変数 / Settings 管理（.env 自動ロード機構含む）
  - run_monitoring.py                  — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                   — ExecutionEngine 起動スクリプト（paper_trading 切替）
  - utils/
    - __init__.py
    - process_priority.py              — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py                 — SQLite ベースの監視ログ永続化層
    - system_monitor.py                — システム状態・データ鮮度監視
    - trade_monitor.py                 — 注文滞留・約定異常監視
    - risk_monitor.py                  — ドローダウン・ポジション上限監視
    - kill_switch.py                   — kill.flag の書き込み / 管理
    - alert_manager.py                 — LINE Push によるアラート送信
    - monitoring_engine.py             — 各 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py           — Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - (その他 execution 関連ファイルはコード内で参照)
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
    - news_nlp.py                       — ニュースセンチメント（OpenAI）
    - regime_detector.py                — レジーム判定（MA200 + マクロセンチメント）
  - tools/
    - __init__.py
    - paper_verification_report.py      — Paper Trading 検証レポート出力ツール

（注）上記は与えられたコードスニペットに基づく抜粋。実際のリポジトリにはさらにモジュール／ファイル（data、strategy、execution の詳細等）が存在する可能性があります。

---

## 開発・デバッグのヒント

- .env 自動ロード:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` / `.env.local` を自動読み込みします。テストで自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB / SQLite:
  - DuckDB は分析クエリ用、SQLite は監視・注文ログ用に使い分けられています。両方の接続は各スクリプトで初期化されます。
- テスト可能性:
  - OpenAI 呼び出しや外部 API 呼び出し部分は内部でラップされており、ユニットテスト時は該当関数をモックしやすい設計です（例: news_nlp._call_openai_api を patch）。
- ログレベル:
  - LOG_LEVEL 環境変数でログ出力を制御できます（INFO/DEBUG 等）。

---

必要であれば、README に含める具体的なコマンドや sample .env のテンプレート（.env.example 形式）も作成できます。どの情報を追加したいか教えてください。