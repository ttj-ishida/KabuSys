# KabuSys

日本株自動売買システムのコードベース（抜粋）。この README はプロジェクト概要・機能・セットアップ・使い方・ディレクトリ構成を日本語でまとめたものです。

注意: ここに記載しているコマンドはリポジトリルートから実行する想定です。パッケージインストールや PYTHONPATH の扱いにより実行方法が変わるため、以下の「セットアップ」節を参照してください。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・検証・監視プラットフォームの一部です。本コードベースは以下の主要機能を含みます:

- 実行エンジン（ExecutionEngine）と発注管理（OrderManager / Reconciler）
- 監視サブシステム（System / Trade / Risk モニタ、アラート、kill switch）
- ポートフォリオ構築ロジック（候補選定、重み付け、ポジションサイズ計算）
- リサーチ用ファクター計算（momentum, volatility, value 等）
- ニュース NLP（OpenAI を用いたニュースセンチメント集計）とレジーム判定
- Paper Trading 用検証レポートジェネレータ
- Streamlit ベースの監視ダッシュボード
- 設定・環境変数管理ユーティリティ

設計方針として、リサーチ・AI 部分は外部 API（ブローカー）を直接操作しない、監視は SQLite にログを永続化する、Paper Trading は本番 DB と分離するなどの分離を重視しています。

---

## 主な機能一覧

- Execution
  - 発注作成/送信/同期（OrderManager）
  - 起動時リコンシリエーション（Reconciler）
  - Paper Trading モード（MockBroker を利用し、別 DB に記録）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態/データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常チェック
  - RiskMonitor: ドローダウン・ポジション上限監視、kill.flag 出力
  - AlertManager: LINE による通知（push）
  - Streamlit ダッシュボード（監視データ可視化）
- Portfolio construction
  - 候補選定、等重・スコア重み付け、リスク調整、ポジションサイズ計算
- Research
  - DuckDB 接続ベースのファクター計算（momentum/volatility/value）
  - 特徴量探索、IC 計算、将来リターン計算
- AI
  - ニュース記事のセンチメントスコアリング（OpenAI）
  - マクロニュース＋ETF MA を用いた市場レジーム判定
- Tools
  - Paper Trading の検証レポート生成（コマンドライン）
- ユーティリティ
  - 環境変数/.env ローダー
  - プロセス優先度・CPU affinity 設定ユーティリティ

---

## 必要条件（概略）

- Python 3.10 以上（PEP 604 の union 型等を使用）
- 必須パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード使用時)
- SQLite（組み込みライブラリ）
- ネットワークアクセス（LINE API / OpenAI を利用する場合）

requirements.txt がある想定なら:
```
python -m pip install -r requirements.txt
```
が簡便です。なければ上記パッケージを個別にインストールしてください。

---

## 環境変数（主なもの）

Settings クラスで参照される環境変数の一部（デフォルト値、説明を併記）:

- KABUSYS_ENV
  - 値: development | paper_trading | live
  - デフォルト: development
  - paper_trading の場合、MockBroker を使用し paper_sqlite_path に記録
- LOG_LEVEL
  - デフォルト: INFO
- JQUANTS_REFRESH_TOKEN
  - 必須: J-Quants API 用トークン
- KABU_API_PASSWORD
  - 必須: kabuステーション API 用
- OPENAI_API_KEY
  - OpenAI を使う場合に必須（AI モジュール）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
  - AlertManager による LINE 通知用
- DUCKDB_PATH
  - デフォルト: data/kabusys.duckdb
- SQLITE_PATH
  - 監視ログ SQLite、デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH
  - Paper Trading 用 DB、デフォルト: data/paper_trading.db
- PAPER_FILL_MODE
  - Paper Trading の約定モード: instant | partial | never | reject（デフォルト: instant）
- PID_FILE_PATH
  - ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH
  - kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔（秒、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 1 を設定すると .env の自動読み込みを無効化

.env ファイルはリポジトリルート（.git や pyproject.toml を基準に探索）にある場合自動読み込みされます（.env → .env.local の順、OS 環境変数は保護）。

---

## セットアップ手順（開発マシン）

1. Python 仮想環境を作成・有効化
   - 例:
     ```
     python -m venv .venv
     source .venv/bin/activate   # Unix/macOS
     .venv\Scripts\activate      # Windows
     ```

2. 必要パッケージをインストール
   - 例（requirements.txt がある場合）:
     ```
     python -m pip install -r requirements.txt
     ```
   - 必要なパッケージ（個別インストール例）:
     ```
     python -m pip install duckdb psutil requests openai streamlit
     ```

3. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を用意するか、OS 環境変数として設定します。
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（AI 機能を使うなら OPENAI_API_KEY）
   - 例（.env）:
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     OPENAI_API_KEY=sk-xxxx
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     ```

4. パッケージとしてインストール（任意）
   - 開発用にパッケージ化して使うと実行が楽です（pyproject.toml がある場合）:
     ```
     python -m pip install -e .
     ```
   - もしくは、リポジトリルートで実行する際は `PYTHONPATH=src` を通すかカレントディレクトリから `python -m kabusys.run_monitoring` のように実行してください。

5. data ディレクトリ作成
   - デフォルトの DB パスや PID/flag は `data/` 配下を想定しています:
     ```
     mkdir -p data
     ```

---

## 使い方（主要な実行例）

以下は代表的な実行コマンド例です。実行前に環境変数や DB ファイルの準備をしてください。

- 監視ポーリング（Monitoring）を起動
  - ポーリングループを起動します。MONITOR_POLL_INTERVAL（秒）で間隔を変更可能（デフォルト60秒）。
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数例:
    ```
    export MONITOR_POLL_INTERVAL=30
    export KABUSYS_ENV=development
    python -m kabusys.run_monitoring
    ```

- 実行エンジン（ExecutionEngine）を起動
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、paper_trading の専用 DB に記録します。
  ```
  python -m kabusys.run_execution
  ```
  - Paper trading の例:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```

- Paper Trading 検証レポートを生成
  - デフォルト DB: data/paper_trading.db
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスを指定:
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- Streamlit 監視ダッシュボード起動
  - Monitoring DB（SQLite）を read-only で開いて表示します:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - DB が存在しない場合はエラーメッセージが出ます（MonitoringEngine を先に実行してください）。

- AI / レジーム判定 / ニューススコア（ライブラリ API）
  - OpenAI API キーを設定してプログラムから以下を呼び出せます（例はライブラリ関数）:
    - kabusys.ai.score_news(conn, target_date, api_key=...)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

---

## 重要な挙動・設定上の注意点

- Paper Trading は本番 DB と分離
  - KABUSYS_ENV=paper_trading の場合、Settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。実際のブローカー呼び出しは MockBrokerClient に差し替わります。

- Monitoring は環境にかかわらず本番 sqlite_path を使用する設計（run_monitoring の docstring より）
  - run_monitoring は Settings().sqlite_path を使って監視ログを保存します。

- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を基準に .env / .env.local を自動で読み込みます。自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔（秒）を環境変数で上書き可能。1 未満の値や不正値はデフォルト 60 秒にフォールバックします。

- PAPER_FILL_MODE
  - Paper Trading 時の約定挙動（instant / partial / never / reject）。無効な値は例外になります。

- プロセス優先度
  - 起動スクリプトは最初に set_process_priority("high") を呼びます。psutil による権限エラー等は警告を出してスキップします。

- kill.flag
  - RiskMonitor が条件を満たすと kill.flag（デフォルト data/kill.flag）を書き込み、ExecutionEngine 停止のシグナルとして扱います。KillSwitch は既存ファイルの上書きを避ける設計です。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイルと簡単な説明です（抜粋）:

- src/kabusys/
  - __init__.py (パッケージメタ情報)
  - config.py (環境変数 / 設定管理)
  - run_monitoring.py (SystemMonitor ポーリングループ起動スクリプト)
  - run_execution.py (ExecutionEngine 起動スクリプト)
- src/kabusys/monitoring/
  - monitoring_db.py (SQLite 監視ログ永続化)
  - system_monitor.py (CPU/メモリ/データ鮮度/プロセス監視)
  - trade_monitor.py (滞留注文・約定異常監視)
  - risk_monitor.py (ドローダウン・ポジション制限)
  - kill_switch.py (kill.flag の管理)
  - alert_manager.py (LINE push)
  - monitoring_engine.py (複数 Monitor を束ねる)
  - streamlit_dashboard.py (Streamlit UI)
- src/kabusys/execution/
  - order_manager.py (発注ロジック)
  - reconciler.py (起動時リコンシリエーション)
  - （その他: broker_factory, execution_engine, order_repository 等）
- src/kabusys/portfolio/
  - portfolio_builder.py (候補選定、重み)
  - position_sizing.py (株数計算、キャップ/スケール)
  - risk_adjustment.py (セクターキャップ、レジーム乗数)
- src/kabusys/research/
  - factor_research.py (momentum / volatility / value 等)
  - feature_exploration.py (forward returns, IC, summary)
- src/kabusys/ai/
  - news_nlp.py (ニュースの OpenAI スコアリング)
  - regime_detector.py (ETF MA + マクロセンチメントでレジーム判定)
- src/kabusys/tools/
  - paper_verification_report.py (paper trading 検証レポート)
- src/kabusys/utils/
  - process_priority.py (プロセス優先度・CPU affinity)

その他、execution・data・strategy 等のモジュール群があります（コードベースに応じて拡張）。

---

## 開発・運用上のヒント

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等にテーブルと必要カラムの追加を行います。既存 DB に対して後方互換性を考慮した簡易マイグレーション処理を組み込んでいます。

- DuckDB を読み取り専用で開く（Streamlit 用）
  - streamlit_dashboard は URI モードで SQLite を読み取り専用に開く処理を行っています。DB ファイルが存在しないと起動エラーになります。

- テスト時の環境制御
  - config.py は KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化できます。テスト時に .env を読み込ませたくない場合に便利です。

- OpenAI 呼び出しの堅牢化
  - AI 関連は 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライし、失敗時はフォールバック値（例: macro_sentiment=0.0）で継続します。

---

これで README の基本説明は完了です。必要であれば以下を追加で作成できます:

- requirements.txt の推奨一覧（正確なバージョン固定）
- .env.example（必須・推奨環境変数のサンプル）
- 実行フロー図 / アーキテクチャ図
- 詳細な API ドキュメント（各モジュールの public API）

どれを追加したいか教えてください。