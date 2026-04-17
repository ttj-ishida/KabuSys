# KabuSys — 日本株自動売買システム

概要
----
KabuSys は日本株の自動売買（Execution）とその稼働監視（Monitoring）、リサーチ・ポートフォリオ構築、AI を用いたニュース評価などを含む統合的なシステムです。  
このリポジトリは、発注処理・リコンシリエーション、リスク監視、監視ダッシュボード、Paper Trading 検証ツール、ファクター計算や特徴量探索、LLM を用いたニュースセンチメント／レジーム判定などのモジュール群を提供します。

主な機能
--------
- Execution エンジン
  - ブローカー抽象化（実ブローカー／モック切替）
  - 注文作成・管理・再同期（Reconciler）
  - リスク管理（ポジション上限、利用率、ドローダウン等）
- Monitoring
  - システム状態（CPU/メモリ/ディスク）、データ鮮度の定期チェック
  - 注文滞留・約定異常の検出
  - リスクイベントのログ保存とアラート（LINE push）
  - Kill switch による安全停止（フラグファイル）
  - Streamlit ダッシュボード（監視表示）
- Portfolio / Strategy ユーティリティ
  - 候補選定・重み付け（等配分、スコア加重）
  - セクター制約、レジーム乗数、株数決定（ロット丸め・資金配分制限）
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI（OpenAI）連携
  - ニュースセンチメント（ai_scores 生成）
  - 市場レジーム判定（market_regime）
  - 再試行とフェイルセーフ処理を備えた API 呼び出し設計
- ツール
  - Paper Trading 検証レポート生成スクリプト（過去期間の稼働率・注文成功率・レイテンシ統計など）

必要条件（例）
--------------
- Python 3.10+
- duckdb
- sqlite3（標準ライブラリ）
- psutil
- requests
- openai（OpenAI Python SDK）
- streamlit（ダッシュボード利用時）
- （推奨）仮想環境（venv、poetry、pipenv 等）

セットアップ手順
----------------
1. リポジトリをクローンしてワークディレクトリへ移動します。
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell)
   ```

3. 必要なパッケージをインストールします（requirements.txt の用意に応じて）。
   例:
   ```
   pip install duckdb psutil requests openai streamlit
   ```
   開発用: package を editable install
   ```
   pip install -e .
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（デフォルト）。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（代表）
- KABUSYS_ENV: 実行モード。`development`（デフォルト） / `paper_trading` / `live`  
  - `paper_trading` 時は MockBroker を使い、本番 DB と分離して `data/paper_trading.db` を使います。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須な箇所あり）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- OPENAI_API_KEY: OpenAI 呼び出しに必要
- PAPER_FILL_MODE: Paper Trading の約定挙動（`instant` / `partial` / `never` / `reject`）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite パス（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH / KILL_FLAG_PATH 等のパスも環境変数で上書き可能
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

使い方
------
ここでは代表的なコマンドを示します。パッケージとしてインストールしている場合は `python -m kabusys.<module>` で呼べます。

1. Monitoring（監視ループ）起動
   - デフォルトポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で秒数を上書きできます（1秒以上）。
   - 実行:
     ```
     python -m kabusys.run_monitoring
     ```
   - 停止:
     - プロセスを Ctrl+C で停止するか、プロジェクトルートの `data/stop_requested.flag` を作成するとループが検知して終了します。

2. Execution エンジン起動
   - 起動:
     ```
     python -m kabusys.run_execution
     ```
   - `KABUSYS_ENV=paper_trading` のときは Paper Trading 専用 DB を使い、Mock ブローカーで動作します。
   - 停止:
     - `data/stop_requested.flag` を作成するか、KillSwitch により `data/kill.flag` が書かれると停止します。
     - 実行中は PID が `data/execution.pid` に書き込まれます（プロセス管理や stale PID 検出に使用）。

3. Streamlit ダッシュボード（監視 UI）
   - 起動:
     ```
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
     ```
   - 読み取り専用で SQLite DB を開きます（監視が開始されていない場合はデータが存在しない旨表示されます）。

4. Paper Trading 検証レポート生成
   - 使い方:
     ```
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     ```
   - DB パスは `--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能（デフォルト: data/paper_trading.db）。

5. AI 機能（ニューススコア / レジーム判定）
   - OpenAI API キーが必要です（環境変数または関数引数）。
   - プログラムから呼ぶ例:
     - ニューススコア: `kabusys.ai.score_news(duckdb_conn, target_date, api_key=...)`
     - レジーム判定: `kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=...)`

停止フラグと Kill Switch
---------------------
- 停止要求（管理者による停止）: `data/stop_requested.flag` を作成すると、run_monitoring / run_execution が検知して安全終了します。
- 実運用での自動停止（Kill Switch）: RiskMonitor → KillSwitch が条件を満たすと `data/kill.flag` に理由を書き込みます。Execution は起動時にこの flag をチェックし、存在する場合は起動を行いません。Kill flag をクリアするには手動でファイルを削除するか、KillSwitch.clear() を呼びます。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要コンポーネントと簡単な説明です。

- kabusys/
  - __init__.py: パッケージ情報
  - config.py: 環境変数・設定の読込・検証
  - run_monitoring.py: Monitoring ポーリングループ起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py: Paper Trading 検証レポート生成
  - monitoring/
    - monitoring_db.py: SQLite を使った監視ログ層（init + MonitoringDB）
    - system_monitor.py: システム状態・データ鮮度チェック
    - trade_monitor.py: 注文滞留・約定異常検出
    - risk_monitor.py: ドローダウン・ポジション上限の監視
    - monitoring_engine.py: 各 Monitor を束ねる実行エンジン
    - kill_switch.py: kill.flag の管理
    - alert_manager.py: LINE push 通知
    - streamlit_dashboard.py: Streamlit 監視 UI
  - execution/
    - order_manager.py: 注文の外向き API（OrderManager）
    - reconciler.py: 起動時リコンシリエーション
    - ...（BrokerFactory などブローカー関連）
  - portfolio/
    - portfolio_builder.py: 候補選定・重み計算
    - position_sizing.py: 株数決定・資金配分
    - risk_adjustment.py: セクターキャップ・レジーム乗数
  - research/
    - factor_research.py: Momentum / Volatility / Value 等の計算（DuckDB）
    - feature_exploration.py: 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py: ニュースを OpenAI でスコアリングして ai_scores に書き込む
    - regime_detector.py: ETF MA とマクロ NLP を合成して市場レジームを判定
  - data/ (実行時に使用する DB / flag / pid を置く想定の場所)
    - monitoring.db (監視ログ SQLite：デフォルト)
    - paper_trading.db (Paper Trading 用 SQLite)
    - kabusys.duckdb (DuckDB)
    - execution.pid, kill.flag, stop_requested.flag など

運用上の注意
------------
- paper_trading モードは本番 DB と完全に分離されるよう設計されていますが、環境変数の設定ミスに注意してください。
- OpenAI 呼び出しはネットワークエラーやレート制限を考慮したリトライとフェイルセーフが実装されています。API キーは安全に管理してください。
- Monitoring は監視情報を永続化します。DB のバックアップやサイズ管理をおこなってください。
- process priority / CPU affinity の設定は psutil を利用しています。権限や OS によっては設定がスキップされる場合があります。
- DuckDB のクエリは大量データを扱うためリソース監視を行ってください。

開発者向け
----------
- 設定は `kabusys.config.Settings` 経由で取得します。テストや CI の際は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動 .env 読込をオフにすることができます。
- テスト可能性のため、OpenAI の呼び出し関数は内部で切り替えしやすく、ユニットテストではモックを注入することが推奨されています（コード内に patch 用の注記あり）。
- SQLite / DuckDB の初期化は `monitoring_db.init_monitoring_db()` を使用して冪等に実施します。

トラブルシューティング
----------------------
- DB が開けない／存在しない: MonitoringEngine / Streamlit は DB ファイルの存在を前提にします。初回起動時は該当ディレクトリ（data/）を作成し、適切な DB ファイルを配置してください。
- PID ファイルに古い PID が残ると stale PID 検出が動作します。標準的には Execution 側が削除しますが、手動で削除することも可能です。
- MONITOR_POLL_INTERVAL に 0 や負の値を設定するとデフォルト（60秒）にフォールバックします。

ライセンス / 貢献
----------------
（ここにライセンス情報や貢献方法を記載してください。リポジトリ側の方針に合わせて補完してください。）

補足
----
この README はコードベースの主要点をまとめたもので、詳細は各モジュールの docstring、コメント、関数シグネチャを参照してください。質問や具体的な使い方（例: 設定ファイル例・実運用のデプロイ手順）が必要であれば追記します。