# KabuSys

日本株自動売買システム（ライブラリ・ツール群）

このリポジトリは、銘柄選定・ポートフォリオ構築・発注実行・監視・研究機能を含む日本株向けの自動売買プラットフォームの一部です。DuckDB / SQLite を使ったデータ処理、kabuステーション（or モック）を用いた発注、OpenAI を使ったニュース NLP / レジーム判定などのコンポーネントを含みます。

主な目的は「現実的な自動売買ワークフロー」を再現することで、研究（research）、ポートフォリオ構築（portfolio）、発注実行（execution）、監視（monitoring）、AI 支援（ai）といったモジュールが分離・連携する設計になっています。

---

目次
- プロジェクト概要
- 機能一覧
- 前提 / 依存関係
- セットアップ手順
- 使い方（主要コマンド／実行例）
- 重要な環境変数一覧
- 停止 / Kill Switch の仕組み
- ディレクトリ構成

---

プロジェクト概要
- 名前: KabuSys
- 概要: 日本株自動売買システムのコンポーネント群。データ処理（DuckDB）・戦略研究・ポートフォリオ構築・発注実行・監視（SQLite）・AI を用いたニュース分析等を提供します。
- 設計方針: 各機能は可能な限り純粋関数や副作用を最小にしたクラスに分割。実行環境（development / paper_trading / live）により挙動を切り替えます。

---

機能一覧
- 環境設定ウィザード（.env 生成）: kabusys.config_setup
- 設定検証 CLI（.env、config/*.yaml のチェック）: kabusys.validate_config
- 実行エンジン起動スクリプト（ExecutionEngine）: run_execution.py
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、paper_trading DB に書き込む
  - PID ファイル管理、停止フラグ検出
- 監視ポーリング（SystemMonitor 単体 / MonitoringEngine）: run_monitoring.py / monitoring_engine.py
  - システム状態、データ鮮度、注文滞留、約定異常、リスク（ドローダウン等）の監視
  - SQLite への永続化用 monitoring_db
- Kill Switch: 条件により data/kill.flag を書き込み ExecutionEngine を停止
- ポートフォリオ構築: select_candidates, 等金額/スコア重み、ポジションサイズ計算、セクター上限適用、レジーム乗数
- リサーチ: ファクター計算（momentum / volatility / value）、将来リターン、IC 計算、統計サマリ
- AI:
  - news_nlp: OpenAI を使ったニュースセンチメント集約 / ai_scores への書き込み
  - regime_detector: ETF MA とマクロニュースの LLM スコアを合成して日次レジーム判定
- ツール:
  - paper_verification_report: ペーパートレード DB を集計して検証レポート出力
- ユーティリティ:
  - process_priority / CPU affinity 設定ユーティリティ（psutil を利用）
  - .env 読み込みパーサ（クォートやコメント対応）

---

前提 / 依存関係
最低要件（推奨）
- Python 3.10+（型注釈で | 演算子を使用）
- SQLite（標準ライブラリ）
- 以下の Python パッケージ（用途に応じて）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML (validate_config で YAML 検証を行う場合)
  
インストール例:
  pip install duckdb psutil openai PyYAML

（プロジェクトに requirements.txt がある場合はそちらを使用してください）

---

セットアップ手順（ローカル開発向けの基本フロー）
1. リポジトリをクローン / チェックアウト
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. .env の作成（対話式推奨）
   - python -m kabusys.config_setup
     - J-Quants リフレッシュトークンや KABU_API_PASSWORD 等の必須値を入力してください
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合: python -m kabusys.validate_config --strict
6. データディレクトリの確認
   - デフォルト DB 等は data/ 配下:
     - DuckDB: data/kabusys.duckdb
     - monitoring (SQLite): data/monitoring.db
     - paper trading DB: data/paper_trading.db
   - 必要に応じて .env で上書きしてください

---

使い方（主要コマンド・実行例）

1) 環境設定ウィザード
   - python -m kabusys.config_setup
   - 対話形式で .env を生成・更新します

2) 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

3) 実行エンジン起動（Execution）
   - python -m kabusys.run_execution
   - 起動時に PID ファイル (data/execution.pid) を作成し、停止フラグ（data/stop_requested.flag）や kill.flag を監視します
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading 用の DB に記録します
   - 停止方法:
     - data/stop_requested.flag を作成すると run_execution は安全に停止します
     - KillSwitch が条件を満たすと data/kill.flag を作成して Execution を停止させます

4) 監視プロセス起動（Monitoring）
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更（デフォルト 60）
     - 例: export MONITOR_POLL_INTERVAL=30
   - 監視は常に本番用 sqlite_path を参照（環境にかかわらず monitoring DB は本番パスを使用）
   - run_monitoring は data/stop_requested.flag を検出すると終了します

5) Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パスを指定する場合: --db path/to/paper_trading.db
   - 環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能

6) AI 機能（ニュース NLP / レジーム判定）
   - AI 機能を使うには OPENAI_API_KEY を設定してください（.env または環境変数）
   - kabusys.ai.news_nlp.score_news や kabusys.ai.regime_detector.score_regime を利用できます
   - 実行例（ライブラリ呼び出し）:
       from kabusys.ai.news_nlp import score_news
       score_news(conn, target_date, api_key="...")

---

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用トークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API を使う場合に必要
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（monitoring）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant | partial | never | reject）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START — 監視・停止関連

（上記の多くは .env を config_setup で生成できます）

---

停止 / Kill Switch の仕組み
- run_execution / ExecutionEngine:
  - 起動時に data/execution.pid（デフォルト）に PID を書きます
  - 停止要求は data/stop_requested.flag の存在で検出され、よって外部から停止できます
- KillSwitch（kabusys.monitoring.kill_switch）:
  - 監視がドローダウン閾値やポジション上限を検出した場合に data/kill.flag を書き込みます
  - ExecutionEngine は kill.flag を検出して自己停止することが期待されます
- run_monitoring/run_execution は stop_requested.flag の存在を見て graceful shutdown します

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動ラッパー
  - run_monitoring.py         — SystemMonitor ポーリング起動ラッパー
  - tools/
    - __init__.py
    - paper_verification_report.py  — ペーパートレード検証レポート
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py       — 市場レジーム判定（MA + マクロニュース）
  - research/
    - __init__.py
    - factor_research.py       — momentum / value / volatility
    - feature_exploration.py   — 将来リターン / IC / 統計
  - portfolio/
    - __init__.py
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 発注株数計算・スケール調整
    - risk_adjustment.py       — セクター上限・レジーム乗数
  - execution/                 — 発注実行関連（OrderManager 等、実装コードは別ファイル）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（system_status/trade_logs/...）
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 注文滞留・約定異常監視
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 制御
    - monitoring_engine.py    — 各モニタ束ね・アラート発行
    - alert_manager.py        — （アラート送信機能; ファイル終端で未表示の可能性あり）
  - utils/
    - __init__.py
    - process_priority.py     — psutil を使ったプロセス優先度・CPU affinity 設定
  - data/                     — 実行時に使うデータディレクトリ（DB / PID / flag 等）

注: execution ディレクトリの具体的な発注ロジックや broker_factory, order_repository 等はコードベースに含まれており、発注の流れを管理します（本 README の概要で全てを網羅してはいません）。

---

補足・運用上の注意
- .env は絶対にリポジトリへコミットしないでください（API キー等の機密情報を含む）。
- 本番（KABUSYS_ENV=live）では LINE 通知などのアラート設定を必ず確認してください（validate_config にガードチェックあり）。
- OpenAI を使う処理は外部 API 呼び出しを伴い、レート制限やコストが発生します。API キーや呼び出し頻度は適切に管理してください。
- モジュールは「データ参照のみ」の関数と「副作用を伴う DB 書き込み/外部呼び出し」クラスが混在します。ユニットテストを書く場合は副作用部分をモックすることを推奨します。

---

問題・改善提案・貢献
- バグ報告や改善提案は Issue を立ててください。
- 大きな変更は PR を作成し、テストとドキュメントの更新をお願いします。

---

以上がこのコードベースの概要と基本的な使い方です。必要であれば、各モジュールの詳しい API 使用例やよくある運用手順（デプロイ、監視設定、ログ周りの取り扱い等）を追加で作成します。どの部分のドキュメントを優先的に拡充しますか？