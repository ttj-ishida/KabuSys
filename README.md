# KabuSys

日本株向けの自動売買システム（ライブラリ／実行コンポーネント群）のリポジトリ。  
この README は、リポジトリに含まれる主要コンポーネントの概要、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は、取引エンジン（ExecutionEngine）・監視（Monitoring）・ポートフォリオ構築・リサーチ・AI（ニュース NLP / レジーム判定）など、自動売買に必要な主要機能をモジュール化したシステムです。  
設計方針の特徴：

- 本番用と Paper Trading を明確に分離（DB 等を分ける）。
- DuckDB を用いたバッチ／リサーチ処理（価格・財務データ参照）。
- SQLite を用いた監視ログ・トレードログの永続化。
- OpenAI を利用したニュースセンチメント評価（AI モジュール）。
- モジュールは純粋関数設計または薄い永続化層で分離。

---

## 主な機能一覧

- ExecutionEngine
  - ブローカークライアント経由での発注・注文管理
  - 起動時のリコンシリエーション（reconciler）で不整合の自動復旧
  - Paper Trading モード（MockBrokerClient + 分離された SQLite）

- Monitoring
  - SystemMonitor（CPU/メモリ/Disk、プロセス監視、データ鮮度）
  - TradeMonitor（滞留注文、約定価格の異常検出）
  - RiskMonitor（ドローダウン / 保有上限）
  - KillSwitch（条件成立時に停止フラグを書き込み、ExecutionEngine 停止）
  - AlertManager（LINE Push で通知）
  - Streamlit ダッシュボード（監視 UI）

- Portfolio（銘柄選定・重み付け・ポジションサイズ）
  - 候補選定、等金額/スコア加重、リスクベースのポジション決定
  - セクター上限、レジーム乗数適用

- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC 計算、特徴量サマリー

- AI
  - news_nlp: ニュース記事を LLM（OpenAI）でスコアリング → ai_scores へ書込
  - regime_detector: ETF MA とマクロニュースを合成して market_regime を判定

- CLI / ツール
  - Monitoring ポーリング起動スクリプト
  - ExecutionEngine 起動スクリプト（paper_trading をサポート）
  - Paper Trading 検証レポート (tools.paper_verification_report)
  - Streamlit ベースの監視ダッシュボード

---

## 前提 / 必要環境

- Python 3.9+（型ヒント等の記述から）
- 必要な外部パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボード利用時)
- SQLite は標準ライブラリで利用
- ネットワーク（ブローカー API / OpenAI / LINE API を利用する場合）

必要パッケージはプロジェクトに requirements.txt があればそちらを利用してください。なければ上記パッケージをインストールしてください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit

3. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（自動読み込みはデフォルトで有効）。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 主要な環境変数（例・必須 / 推奨）
   - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須な箇所あり）
   - KABU_API_PASSWORD — kabuステーション API パスワード（必須な箇所あり）
   - OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知を有効にする場合
   - KABUSYS_ENV — 実行環境（"development" / "paper_trading" / "live"、デフォルト: development）
   - PAPER_FILL_MODE — paper_trading の約定モード（instant / partial / never / reject、デフォルト: instant）
   - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
   - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - PID_FILE_PATH / KILL_FLAG_PATH など（デフォルトは data 以下）

   例 (.env):
   ```
   KABUSYS_ENV=paper_trading
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_pass
   JQUANTS_REFRESH_TOKEN=...
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   ```

---

## 実行方法（主要コマンド）

- ExecutionEngine を起動（デフォルト環境）
  - python -m kabusys.run_execution
  - Paper Trading で起動する場合:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
    - Paper Trading では `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に発注履歴が保存され、本番 DB と分離されます。

- Monitoring（ポーリング）を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を秒で指定する（環境変数）:
    - export MONITOR_POLL_INTERVAL=30
  - 監視は Settings に従い、監視ログは SQLITE_PATH（デフォルト: data/monitoring.db）へ書き込みます。
  - 監視は常に本番 sqlite_path を利用する点に注意（run_monitoring の設計）。

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュールの利用（プログラム内 API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 停止・フラグ機構

- 停止フラグ（run_monitoring / run_execution）
  - プロジェクト内の data/stop_requested.flag（run_* スクリプト内で参照）を作成すると起動中ループは検知して安全に終了します。
- Kill Switch（自動停止）
  - 条件（ドローダウン超過等）により `KillSwitch` が `data/kill.flag` を書き込みます。
  - ExecutionEngine は起動時に kill.flag を検出すると起動しない設計（paper_trading 時も同様）。
  - Settings.kill_flag_clear_on_start を使って起動時に kill.flag を自動クリアする運用も可能（環境変数 KILL_FLAG_CLEAR_ON_START=1）。

---

## 設定の自動読み込みについて

- config.Settings モジュールはプロジェクトルート（.git または pyproject.toml のある場所）を基準に `.env` と `.env.local` を自動で読み込みます。
- 読み込み優先順位:
  - OS 環境変数（最優先）
  - .env.local（override=True）
  - .env（override=False）
- 自動読み込みを無効化する:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイルと説明）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定管理（.env 自動読み込み、Settings クラス）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

- src/kabusys/execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, broker_factory など
  - Reconciler — 起動時のリコンシリエーション（broker と local の突合）
  - OrderManager — 発注フローの外向き API

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite テーブル（system_status, trade_logs, positions, risk_logs, dashboard）初期化・永続化層
  - system_monitor.py — CPU/メモリ/Disk、プロセス、データ鮮度の監視
  - trade_monitor.py — 滞留注文・約定異常の検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の書込ロジック
  - alert_manager.py — LINE Push 通知
  - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み算出（等金額 / スコア）
  - position_sizing.py — 発注株数計算（risk_based / equal / score）
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- src/kabusys/research/
  - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン、IC、統計サマリー

- src/kabusys/ai/
  - news_nlp.py — ニュース NLP（OpenAI）で銘柄別センチメントを ai_scores に書き込む
  - regime_detector.py — ETF MA とマクロニュースを使って市場レジーム判定、market_regime 書き込み

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成 CLI

- data/
  - デフォルトの DB や PID / flag ファイルが置かれる想定ディレクトリ（例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag, data/stop_requested.flag）

---

## 運用上の注意・ベストプラクティス

- Paper Trading と Live を混同しない:
  - KABUSYS_ENV=paper_trading の場合、発注履歴等は PAPER_TRADING_SQLITE_PATH に保存され、本番監視 DB と分離されます。
- プロセス優先度:
  - 起動スクリプトは最初に set_process_priority("high") を呼びます。psutil の権限により設定できない場合は警告でスキップされます。
- データ鮮度チェック:
  - SystemMonitor は DuckDB の get_last_price_date を参照してデータ鮮度を判定します。DuckDB の prices_daily が更新されていることを確認してください。
- フラグファイル
  - data/stop_requested.flag による安全停止、および data/kill.flag による自動停止（KillSwitch）を運用ルールに含めてください。
- OpenAI 使用時
  - API 呼び出しはリトライ・バックオフ・レスポンスバリデーション等のフェイルセーフを実装していますが、API キーや使用量の管理は運用者が行ってください。

---

## よく使うコマンドまとめ

- Execution 起動
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Monitoring 起動（ポーリング）
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- Streamlit Dashboard
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

問題があれば、どの機能の README をより詳細化したいか（例: ExecutionEngine の設計、OrderManager API、AI モジュールの入力/出力仕様など）を教えてください。必要に応じてサンプル .env、起動手順の詳しい例、運用チェックリストも作成します。