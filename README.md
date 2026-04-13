# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ＋実行スクリプト群）です。  
このリポジトリには以下の主要機能（監視・実行・ポートフォリオ構築・リサーチ・AIニュース解析など）が含まれます。

注意: この README はソースコード（src/kabusys 以下）に基づいて作成しています。

---

## プロジェクト概要

KabuSys は以下の責務を持つコンポーネントで構成されています。

- Execution Engine：発注・リスク管理・注文状態管理・リコンシリエーション
- Monitoring：システム稼働状態・注文滞留・リスク（ドローダウン等）の監視。LINE 通知・kill スイッチ機能を含む
- Portfolio Construction：候補選定・重み計算・ポジションサイズ計算・セクター制約適用
- Research：ファクター計算（モメンタム/ボラティリティ/バリュー）や特徴量探索、IC 計算
- AI モジュール：ニュースセンチメント（OpenAI 経由）、市場レジーム判定
- DB：DuckDB（時系列・リサーチ用）と SQLite（監視・注文ログ用）を併用

設定は環境変数（またはプロジェクトルートの `.env` / `.env.local`）で行います。自動で .env をロードする機能あり（無効化可能）。

---

## 主な機能一覧

- SystemMonitor：CPU/メモリ/ディスク/プロセス健全性・データ鮮度監視（monitoring/）
- TradeMonitor：滞留注文・約定価格異常の検出
- RiskMonitor：ドローダウン検出、ポジション上限監視、ダッシュボード更新
- KillSwitch：条件到達時にフラグファイルを作成して ExecutionEngine 停止シグナルを送出
- AlertManager：LINE Messaging API による通知（クールダウン管理）
- MonitoringEngine：上記モニタ群をポーリングするエンジン
- ExecutionEngine（起動スクリプト run_execution.py）：ブローカー接続、注文管理、リスク制御、リコンシリエーションを実行
- Paper Trading：`KABUSYS_ENV=paper_trading` でモックブローカーと分離 DB（data/paper_trading.db）を使用
- Research：DuckDB を使ったファクター計算、将来リターン、IC 計算等
- AI：OpenAI を利用したニュースセンチメント（ai.news_nlp.score_news）、市場レジーム判定（ai.regime_detector.score_regime）
- ツール：Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
- Streamlit ダッシュボード：監視 DB を可視化する UI（monitoring/streamlit_dashboard.py）

---

## セットアップ手順（ローカル）

前提
- Python 3.9+ 推奨（ソースは型注釈を使用）
- OS により psutil の一部機能（priority/affinity）で権限が必要になる場合があります

1. リポジトリをクローン／配置する
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（requirements.txt がないため代表的なパッケージを個別インストール）
   - pip install duckdb psutil openai requests streamlit
   - 必要に応じて他パッケージを追加
4. 環境変数を用意
   - プロジェクトルートに `.env` または `.env.local` を配置するか、直接環境変数を設定します
   - 主要な環境変数（抜粋）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能利用時に必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 時の専用 DB、デフォルト: data/paper_trading.db）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知）
     - PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject）
     - PID_FILE_PATH / KILL_FLAG_PATH（デフォルト: data/execution.pid, data/kill.flag）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト 60）

※ .env の自動ロードは、プロジェクトルート（.git または pyproject.toml を基準）から行われます。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（起動・ツール）

共通:
- 多くの起動スクリプトは `python -m kabusys.<module>` として実行できます
- 実行時に最初にプロセス優先度を "high" に設定する処理が入ります（psutil による設定。設定に失敗しても継続します）

1. 監視ループ起動（Monitoring）
   - デフォルトで本番 sqlite（Settings.sqlite_path）を使用して監視ログを書きます
   - 実行:
     - python -m kabusys.run_monitoring
     - ポーリング間隔を変更する: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 補足: KABUSYS_ENV の値に関わらず監視は本番 sqlite_path を参照します

2. ExecutionEngine 起動（発注系）
   - Paper Trading モード: KABUSYS_ENV=paper_trading とすると MockBroker を利用し、data/paper_trading.db に記録して本番 DB と分離されます
   - 実行:
     - python -m kabusys.run_execution
   - 起動時にリコンシリエーション（未確定注文の同期など）を実行します

3. Paper Trading 検証レポート生成
   - ツール:
     - python -m kabusys.tools.paper_verification_report
     - 期間指定例:
       - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB パスを指定する場合:
       - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

4. Streamlit 監視ダッシュボード
   - 実行:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 引数 --db で監視用 SQLite DB を読み込み（読み取り専用）し、Overview/Positions/Orders/System タブを提供します

5. AI モジュール（プログラム的に利用する例）
   - ニューススコア付与:
     - from kabusys.ai.news_nlp import score_news
     - score_news(conn, target_date, api_key="...")  — DuckDB 接続と target_date（datetime.date）を渡す
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(conn, target_date, api_key="...")

---

## 重要な動作・ポリシー

- 環境設定の優先順位: OS 環境変数 > .env.local > .env
- Paper Trading は本番 DB と完全分離（別 SQLite ファイル）
- OpenAI を用いる処理は API エラー時にフェイルセーフ（多くはデフォルト値にフォールバック）を採用
- 監視用 DB の初期化関数 init_monitoring_db は冪等（起動時に呼び出して構いません）
- KillSwitch は条件成立時にファイル（デフォルト data/kill.flag）を出力し ExecutionEngine 側で検知して停止させる運用を想定
- プロセス優先度・CPU affinity は utils/process_priority.py で抽象化（権限不足時は警告を出してスキップ）

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env ロード / Settings クラス
  - run_monitoring.py — SystemMonitor のポーリング起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（OpenAI 経由）
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント合成）
  - monitoring/
    - __init__.py
    - monitoring_db.py — SQLite テーブル定義と永続化ロジック
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py — 滞留注文・約定異常の検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py — LINE Push 通知
    - kill_switch.py — kill.flag 制御
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py — 注文状態遷移の外向き API
    - order_repository.py — SQLite を使った注文永続化（省略箇所あり）
    - reconciler.py — 起動時のリコンシリエーション
    - ...（ブローカー関連・エンジン本体等）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数計算・単元丸め・aggregate cap
    - risk_adjustment.py — セクター制約・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
    - __init__.py
  - data/
    - pipeline.py, stats.py など（DuckDB からのデータ取得・正規化ユーティリティ）
  - utils/
    - __init__.py
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記は主要ファイルの抜粋です。実装の詳細は各ファイルの docstring / コメントを参照してください）

---

## 例：簡単な起動例

1. 環境変数を最低限設定（例: Bash）
   - export JQUANTS_REFRESH_TOKEN="..."
   - export KABU_API_PASSWORD="..."
   - export OPENAI_API_KEY="..."  # AI 機能利用時
   - export KABUSYS_ENV=paper_trading

2. paper_trading 実行（モックブローカーで安全に動作確認）
   - python -m kabusys.run_execution

3. 監視を並行起動
   - python -m kabusys.run_monitoring

4. 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

5. Dashboad（別ターミナル）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

## 開発・運用時の注意点

- 本番運用時は KABUSYS_ENV=live を設定してください。paper_trading は必ず専用 DB を使用します。
- ファイルパス（duckdb/sqlite/pid/kill flag）は Settings で管理され、環境変数で上書き可能です。
- OpenAI API を利用する処理はレート制限や API 障害を考慮したリトライ／フォールバックロジックを持ちますが、API キー漏洩等には注意してください。
- SQLite / DuckDB のファイルはバックアップや排他アクセスに注意（特に複数プロセスが同一ファイルに書き込む運用時）。

---

必要であれば、README に使い方のデモコマンドや .env.example のテンプレート、詳細な設定解説（各環境変数の完全リスト）を追加できます。どの情報を追加したいか教えてください。