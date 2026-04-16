# KabuSys

日本株自動売買システムのミニマム実装（ライブラリ + 実行スクリプト群）

このリポジトリは、戦略計算（リサーチ）、ポートフォリオ構築、発注/実行エンジン、監視・アラート、AI を使ったニュースセンチメント判定などを含む自動売買システムの構成要素を集めたコードベースです。

---

## 概要

- DuckDB を用いた時系列データや財務データの研究・特徴量計算モジュール
- SQLite（monitoring DB / paper trading DB）による監視ログ、注文ログの永続化
- ExecutionEngine（発注エンジン）と OrderManager / Reconciler による発注管理と再同期
- MonitoringEngine によるプロセス・データ鮮度・注文滞留・リスク監視、LINE 通知
- OpenAI（gpt-4o-mini 等）を使ったニュース NLP（銘柄別センチメント）と市場レジーム判定
- Streamlit ダッシュボード、検証レポート生成ツールなど運用・検証用ユーティリティ

設計上のポイント：
- 多くのモジュールは「純粋関数」または副作用を限定した実装（テスト容易性重視）
- 環境ごと（development / paper_trading / live）の設定切替をサポート
- Paper Trading モードは本番 DB と分離（専用 SQLite ファイル）

---

## 主な機能一覧

- research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン・IC 計算、特徴量統計
- portfolio
  - 候補選定、重み算出（等金額・スコア加重）
  - ポジションサイズ計算（リスクベース、ラウンド単元処理、利用可能現金によるスケール）
  - セクター上限・レジーム乗数の適用
- execution
  - OrderManager（発注・状態遷移管理）
  - Reconciler（再起動時にブローカーと突合して復旧）
  - Broker クライアントファクトリ（paper_trading では Mock を使用）
- monitoring
  - SystemMonitor（CPU/メモリ/ディスク、Execution プロセス存在、データ鮮度）
  - TradeMonitor（滞留注文・約定異常価格検出）
  - RiskMonitor（ドローダウン / ポジション上限監視）
  - KillSwitch（致命条件で Execution を停止する flag 書き込み）
  - AlertManager（LINE push）
  - Streamlit ベース監視ダッシュボード
- ai
  - news_nlp: OpenAI を用いた銘柄別ニュースセンチメント算出（ai_scores へ書き込み）
  - regime_detector: ma200 とマクロニュースで市場レジーム判定（market_regime テーブルへ書き込み）
- tools
  - paper_verification_report: Paper Trading DB から検証レポートを生成

---

## 前提（依存ライブラリ）

最低限必要な Python パッケージ（バージョンは実装に合わせて調整してください）:

- python >= 3.9
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボードを使う場合)
- その他（標準ライブラリ: sqlite3, threading, logging 等）

（requirements.txt があればそれを使ってください。無ければ pip で上のパッケージを個別にインストールしてください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   (requirements.txt が無い場合は手動で)
   ```
   pip install duckdb psutil requests openai streamlit
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を作成すると自動読み込みされます（既存 OS 環境変数は保護されます）。
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 重要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能利用時必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB（デフォルト: data/paper_trading.db）
     - SQLITE_PATH — monitoring 用 DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用
     - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）

5. データディレクトリとファイル
   - デフォルトデータベース・フラグは `data/` 下を参照します。必要なら事前に `mkdir -p data` しておくと便利です。

---

## 使い方（実行例）

注意: モジュールはパッケージとして実行できます（プロジェクトルートが PYTHONPATH に入っていることを前提）。

1. ExecutionEngine の起動
   - 実行スクリプト: `src/kabusys/run_execution.py`
   - 実行例:
     ```
     python -m kabusys.run_execution
     ```
   - 特記事項:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、データは `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に書き込まれ、本番 DB と分離されます。
     - 起動時に `data/execution.pid` に PID が書かれます。`data/stop_requested.flag` が存在すると起動せず終了します。
     - `set_process_priority("high")` を試みます（権限がない場合は警告ログでスキップ）。

2. Monitoring の起動（SystemMonitor 単体）
   - 実行スクリプト: `src/kabusys/run_monitoring.py`
   - 実行例:
     ```
     python -m kabusys.run_monitoring
     ```
   - 環境変数:
     - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を変更可能（デフォルト 60）。
   - 重要:
     - run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（Settings.sqlite_path）を使用して monitoring DB を操作します（監視は production DB を見る想定）。

3. Streamlit 監視ダッシュボード
   - スクリプト: `src/kabusys/monitoring/streamlit_dashboard.py`
   - 実行例:
     ```
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
     ```
   - DB は read-only URI で開かれます。MonitoringEngine が動いていることが望ましいです。

4. Paper Trading 検証レポート
   - ツール: `kabusys.tools.paper_verification_report`
   - 実行例:
     ```
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     ```
   - オプション:
     - `--db PATH` で SQLite ファイルを指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）
   - 出力: 標準出力に Pass/Fail を含む検証レポートを出力します。

5. AI 機能（ニューススコア・レジーム判定）
   - OpenAI API キーが必須（環境変数 OPENAI_API_KEY または関数引数で指定）
   - news_nlp.score_news / regime_detector.score_regime を DuckDB 接続と target_date を与えて呼ぶ
   - 429 やタイムアウト、5xx は指数バックオフでリトライする実装

---

## 運用上のファイル・フラグ

- data/stop_requested.flag
  - run_monitoring / run_execution のループを静かに止めるためのファイル。存在すると各ループは終了します。
- data/execution.pid
  - ExecutionEngine の PID を書き込むファイル（存在しない場合はプロセスが起動していないと見なす）。
- data/kill.flag
  - KillSwitch が致命的条件で Execution を停止させたい場合に書き込むフラグ（存在時、Execution は停止処理を行います）。

---

## 設定周りの仕様（Settings）

- 設定値は環境変数から読み込まれます。プロジェクトルートに `.env` / `.env.local` を置くと自動ロードされます（OS 環境変数は上書きされません）。
- 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
- 主要設定:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
  - PAPER_FILL_MODE: paper_trading の約定モード（instant, partial, never, reject）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など監視関連

---

## 開発者向け（内部構成の要点）

- settings は `kabusys.config.Settings` を通じてアクセス。自動的に .env をロードするロジックがあるためテスト時などは制御に注意。
- MonitoringDB (`kabusys.monitoring.monitoring_db`) は SQLite に対する CRUD を提供。初回 init で必要なテーブルを作成（冪等）。
- Execution 側は paper_trading モードで本番 DB と分離される（`run_execution` の sqlite_path 選択ロジック参照）。
- AI の OpenAI 呼び出しは `kabusys.ai.news_nlp` / `kabusys.ai.regime_detector` に実装。API 呼び出し箇所はテスト時に差し替え可能な実装（private 関数を patch する想定）。
- process 優先度や CPU affinity は `kabusys.utils.process_priority` で抽象化。権限不足時は警告で続行。

---

## ディレクトリ構成（主なファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings の読み取りロジック
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - data/ (想定される出力先: data/*.db, data/*.flag)
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）と ai_scores 書き込み
    - regime_detector.py — 市場レジーム判定
  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - portfolio/
    - portfolio_builder.py — 候補選定、重み
    - position_sizing.py — 発注株数算出
    - risk_adjustment.py — セクター上限、レジーム乗数
  - execution/
    - order_manager.py
    - reconciler.py
    - （Broker / Engine 実装が別ファイルに存在）
  - monitoring/
    - monitoring_db.py — SQLite テーブル作成・読み書き
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

---

## 注意事項 / 運用上のヒント

- Paper Trading モードは mock ブローカーを用いて本番 DB と完全分離するため、検証時は必ず KABUSYS_ENV=paper_trading をセットしてください。
- monitoring は run_monitoring の docstring にある通り「環境にかかわらず本番 sqlite_path を使用」します。監視対象 DB を間違えないよう注意してください。
- OpenAI を使う機能は API キー制約・コストがあるため、テストやローカル検証ではモックを利用することを推奨します。
- process 優先度や CPU affinity を設定しますが、権限不足で失敗するケースがある点に注意（警告ログのみ）。
- フラグファイル（stop_requested.flag / kill.flag）でプロセス制御を行うため、運用スクリプトや監視での掃除（clear）処理を忘れないでください。

---

この README は現行コードベースの注釈をもとに作成しています。実際の運用やデプロイ時はセキュリティ（API キー管理、権限）やバックアップ、監視設定を十分に検討してください。必要であれば .env.example の例や systemd / supervisord 用のユニット定義、requirements.txt の追加を行いましょう。