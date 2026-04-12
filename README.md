# KabuSys

日本株自動売買システムのシンプル実装（モジュール群のみを抜粋したコードベース）。  
この README はコードベースの概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買システムのコンポーネント群です。主な関心事は以下のとおりです：

- 実行（Execution）エンジン：ブローカーとのやり取り、注文管理、リスク管理、再コンシリエーション等
- 監視（Monitoring）：システム稼働状態、注文の滞留・約定異常、ドローダウン・ポジション上限などの監視とアラート
- ポートフォリオ構築（Portfolio）：候補選定、重み計算、ポジションサイズ決定、セクターキャップやレジーム調整
- リサーチ（Research）：ファクター計算（Momentum/Value/Volatility 等）、特徴量探索・IC計算
- AI モジュール：ニュースを LLM（OpenAI）でスコアリングして銘柄・マクロセンチメントを算出
- ツール：Paper Trading 検証レポート生成や Streamlit ダッシュボード

設計上の特徴：
- DuckDB（市場データ / ファクター計算）と SQLite（監視ログ・注文ログ/ペーパートレードDB）を併用
- Paper Trading と本番 DB は分離（環境変数で切替）
- .env 自動ロード（ただし無効化可能）
- OpenAI API 呼び出しはバックオフ・バリデーションを含む堅牢な実装

---

## 機能一覧

主要な機能・モジュール（抜粋）：

- 実行関連
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - OrderManager：注文生成・送信・同期ロジック
  - Reconciler：OrderSent 状態の自動復旧／ポジション差分照合
  - RiskManager：発注前リスク制約（設定例あり）

- 監視関連
  - SystemMonitor：CPU/メモリ/ディスク、プロセス生存確認、データ鮮度チェック
  - TradeMonitor：滞留注文・約定価格異常の検出
  - RiskMonitor：ドローダウン・ポジション上限監視
  - KillSwitch：条件に応じて実行エンジン停止フラグ（data/kill.flag）を書き込む
  - AlertManager：LINE に通知（クールダウン管理あり）
  - MonitoringEngine：複数 Monitor の束ね・ポーリング
  - Streamlit ダッシュボード（監視 DB の閲覧）

- ポートフォリオ構築
  - 候補選定（スコア/ランク順）
  - 等金額 / スコア加重の重み計算
  - ポジションサイズ計算（リスクベース、単元株丸め、aggregate cap）
  - セクター集中制限・レジーム乗数

- リサーチ / AI
  - ファクター計算（mom/value/volatility） — DuckDB を使った純粋関数
  - Feature exploration（forward returns, IC, summary）
  - ニュース NLP（OpenAI）を使った銘柄センチメント集計（ai/news_nlp.py）
  - 市場レジーム判定（ma200 とマクロセンチメントの合成）

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
  - Streamlit ダッシュボード（監視用）

---

## セットアップ手順（開発環境向け）

以下はローカルで動かすときの一般的な手順例です。

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # POSIX
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール  
   （コード中で使用されているライブラリに基づく推奨セット）
   ```
   pip install duckdb psutil openai requests streamlit
   ```
   ※テストや開発で pytest 等を使う場合は追加でインストールしてください。

   実運用では requirements.txt を用意しておくと便利です（本リポジトリに無ければ作成してください）。

4. 環境変数 (.env) の準備  
   プロジェクトルートに `.env` または `.env.local` を置くことで自動ロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   最低限設定が必要な変数：
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - OPENAI_API_KEY（AI 機能を使う場合）
   - KABUSYS_ENV（development / paper_trading / live）
   - 必要に応じて：DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

   例（.env）
   ```
   KABUSYS_ENV=development
   OPENAI_API_KEY=sk-...
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   ```

5. データディレクトリ作成
   ```
   mkdir -p data
   ```

6. DuckDB / SQLite の初期データはプロジェクト固有の手順に従って用意してください（prices_daily / raw_financials / raw_news 等のテーブルは DuckDB 側で用意する必要あり）。

---

## 使い方

主要な起動方法・ツールの例を示します。

- 監視ループを起動（ポーリングで監視情報を永続化する）
  ```
  python -m kabusys.run_monitoring
  ```
  環境変数:
  - MONITOR_POLL_INTERVAL：ポーリング間隔（秒、デフォルト 60）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視 DB は本番 DB を前提）

- 実行エンジン（ExecutionEngine）を起動
  ```
  python -m kabusys.run_execution
  ```
  注意点:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）。
  - プロセス優先度を "high" に変更する試みを行います（権限不足で失敗する場合は警告ログ）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  オプション:
  - --db PATH：SQLite DB ファイルパス（環境変数 PAPER_TRADING_SQLITE_PATH と併用可能）
  - レポートは uptime / fill rate / send rate / latency 等を算出して PASS/FAIL 判定を行います。

- Streamlit ダッシュボード（監視 DB の閲覧）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  監視 DB を読み取り専用で開きます。MonitoringEngine が先に起動して DB を作成している必要があります。

- AI モジュール（プログラム内利用例）
  - ニューススコアリング（ai/news_nlp.py）
    - 関数 score_news(conn, target_date, api_key=None) を呼び、DuckDB 接続と target_date を渡す。api_key 未指定なら環境変数 OPENAI_API_KEY を参照します。
  - レジーム判定（ai/regime_detector.py）
    - 関数 score_regime(conn, target_date, api_key=None) を呼ぶ。

- 設定の切替
  - KABUSYS_ENV の値：development / paper_trading / live
    - is_paper フラグを見て paper_trading 用 DB を使う箇所が分離されています。
  - PAPER_FILL_MODE（paper trading の擬似約定モード）：instant / partial / never / reject

- .env 自動ロード
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）にある `.env` / `.env.local` を自動的に読み込みます。自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: development / paper_trading / live（必須、Settings クラスで検証）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper trading の約定モード（instant|partial|never|reject）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: KillSwitch のフラグファイルパス（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）用

※ Settings クラス内で値の検証（許容値チェック）を行っています。誤った値を入れると起動時に例外が投げられます。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイルとサブパッケージの概観（今回のコードベースから抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py                  — 環境変数 / 設定管理（.env 自動ロード含む）
    - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py           — ExecutionEngine 起動スクリプト
    - ai/
      - __init__.py
      - news_nlp.py              — ニュース NLP（OpenAI 呼び出し、スコア保存）
      - regime_detector.py       — 市場レジーム判定（ma200 + マクロセンチメント）
    - monitoring/
      - __init__.py
      - monitoring_db.py         — SQLite ベースの永続化層（監視用テーブル）
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
      - order_repository.py       (一部のみコード提供)
      - execution_engine.py      (参照されるがここでは抜粋)
      - broker_factory.py
      - broker_api.py
      - ...
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - utils/
      - __init__.py
      - process_priority.py

データファイル（デフォルト）
- data/kabusys.duckdb
- data/monitoring.db
- data/paper_trading.db

監視用 SQLite のスキーマは monitoring_db.init_monitoring_db() で自動作成・マイグレーションされます（system_status / trade_logs / positions / risk_logs / dashboard 等）。

---

## 運用上の注意・設計ノート（抜粋）

- Paper Trading と本番 DB は分離されています（settings.is_paper で切替）。ペーパートレードの検証は本番資産に影響を与えません。
- OpenAI 呼び出しはリトライ（429, ネットワーク障害, タイムアウト, 5xx）を実装。応答の JSON バリデーションを行い、安全に失敗フォールバックします（fail-safe）。
- プロセス優先度（psutil）や CPU affinity の設定は OS に依存するため、権限不足や未対応 OS の場合は警告を出してスキップします。
- MonitoringEngine は各 Monitor の例外を個別にハンドリングし、ループを継続します。KillSwitch の評価により ExecutionEngine 停止フラグを生成できます。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）から行われるため、パッケージ配布後でも動作することを意図した実装です。自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 参考コマンド一覧

- 監視を起動:
  ```
  python -m kabusys.run_monitoring
  ```

- 実行エンジンを起動:
  ```
  python -m kabusys.run_execution
  ```

- Paper 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- Streamlit ダッシュボード:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

---

この README はコードベースの提供ファイルから作成しています。実運用・本番導入前には以下を推奨します：

- requirements.txt の作成（依存関係固定）
- DuckDB のテーブル（prices_daily, raw_financials, raw_news など）の初期投入手順を整備
- 実運用向けの監視・ログ収集・バックアップ設計
- OpenAI キー等の機密情報の安全な管理（Vault / Secrets Manager 等）

必要であれば、上記の各セクションを詳述した運用手順書や設計ドキュメント（例：ポートフォリオ構築の数式・パラメータ解説、ExecutionEngine のフロー図、DB スキーマ図）を作成します。どの部分を詳細化したいか教えてください。