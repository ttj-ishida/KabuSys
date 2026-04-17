KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買システム（KabuSys）の一部モジュール群です。
README はコードベース（src/kabusys 以下）に基づく概要・セットアップ・使い方・ディレクトリ構成をまとめたものです。

要点
----
- Python 3.10+ を想定（型記法に | を使用）
- DuckDB / SQLite をデータ保管に利用
- OpenAI（gpt-4o-mini）を使ったニュース NLP / レジーム判定機能を含む（API キー必須）
- 本番 / ペーパートレードの分離設計（環境変数 KABUSYS_ENV）
- モニタリング（System / Trade / Risk）と Kill Switch による強制停止機能あり

機能一覧
--------
- 実行エンジン起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading では MockBroker を使用し DB を分離）
- 監視ループ起動スクリプト
  - run_monitoring.py: SystemMonitor をポーリング（MONITOR_POLL_INTERVAL で間隔調整）
- 環境設定支援
  - config_setup.py: .env の対話式ウィザードで初期作成・更新
  - validate_config.py: .env / config/*.yaml の起動前検証（--strict オプションあり）
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード DB を集計して検証レポート出力（期間指定可）
- ポートフォリオ構築ユーティリティ（純粋関数群）
  - portfolio: 候補選定、重み計算、セクター制約、ポジションサイズ計算
- リサーチ / ファクター計算
  - research: モメンタム / ボラティリティ / バリュー等のファクター計算、IC 等の解析ユーティリティ
- AI 関連
  - ai/news_nlp.py: ニュース記事を LLM でセンチメント化し ai_scores に書き込み
  - ai/regime_detector.py: ETF MA とマクロニュースの LLM 結果を合成して市場レジームを判定
- 監視（monitoring）モジュール群
  - monitoring_db.py: SQLite による監視ログの永続化
  - system_monitor.py / trade_monitor.py / risk_monitor.py / monitoring_engine.py / kill_switch.py / alert_manager (一部) 等

重要な環境変数（抜粋）
---------------------
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API のトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV — development | paper_trading | live （デフォルト: development）
    - paper_trading: ブローカーは Mock、SQLite は data/paper_trading.db（分離）
    - live: 本番運用（注意深く設定）
- DB / ファイルパス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
- AI
  - OPENAI_API_KEY — OpenAI API を使う機能（news_nlp / regime_detector）で必要
- 監視間隔
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト 60）
- Paper Trading 振る舞い
  - PAPER_FILL_MODE — instant | partial | never | reject（デフォルト instant）
- その他
  - LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など（config_setup で設定可）

セットアップ手順
----------------
例: 仮想環境 + 必要パッケージの導入（実際の requirements.txt に合わせて調整してください）

1. リポジトリをクローン
   - git clone <repo_url>
   - cd <repo_root>

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  # Unix/macOS
   - .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai pyyaml
   - 追加でプロジェクトで必要なパッケージがあればインストールしてください。

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または .env.example を参考に手動で .env を作成
   - 必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定してください。

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告を厳密に扱いたい場合は --strict を付ける

使い方（主要コマンド）
--------------------

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し MockBrokerClient で分離されたペーパートレードを行います。
    - 起動時に data/stop_requested.flag が存在すると起動を中止します。
    - プロセス優先度を "high" に設定し、data/execution.pid に PID を書きます。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定できます（デフォルト 60）。
  - 動作:
    - SystemMonitor を起動して定期的に check_once() を呼びます。
    - 監視 DB（sqlite）は settings.sqlite_path（環境にかかわらず本番 sqlite_path）に接続して初期化されます。
    - デフォルトの停止フラグ: data/stop_requested.flag（存在時にループ終了）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能（デフォルト: data/paper_trading.db）

停止 / Kill Switch / フラグ
-------------------------
- Kill Switch:
  - monitoring.kill_switch は条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止信号を送ります。
  - 実行時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動で kill.flag をクリアする（本番では 0 推奨）。
- stop_requested.flag:
  - run_execution.py / run_monitoring.py では data/stop_requested.flag の存在で安全にループを終了します。
- PID 管理:
  - ExecutionEngine は data/execution.pid に PID を書きます。SystemMonitor はこの PID ファイルをチェックしてプロセス存在を検証します。stale PID を検出すると削除してリスクイベントをログします。

データベース / マイグレーション
-----------------------------
- monitoring_db.init_monitoring_db() は必要なテーブルとインデックスを冪等に作成します。また既存 DB に足りないカラム（例: peak_value や latency_ms）がない場合は ALTER TABLE によるマイグレーションを行います。
- デフォルトパス:
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュールと簡単な説明です（抜粋）。

- src/kabusys/
  - __init__.py                      — パッケージ定義（version 等）
  - config.py                        — 環境変数 / .env 自動読み込み、Settings クラス
  - config_setup.py                  — .env 対話式ウィザード
  - validate_config.py               — 設定検証 CLI
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - run_monitoring.py                — SystemMonitor ポーリング起動スクリプト

- src/kabusys/ai/
  - news_nlp.py                      — ニュース NLP（OpenAI）による銘柄センチメント化
  - regime_detector.py               — 市場レジーム判定（MA + LLM）

- src/kabusys/monitoring/
  - monitoring_db.py                 — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py                — システム状態 & データ鮮度監視
  - trade_monitor.py                 — 注文滞留・約定価格異常監視
  - risk_monitor.py                  — ドローダウン・ポジション上限監視
  - kill_switch.py                   — kill.flag の書き込みロジック
  - monitoring_engine.py             — 各モニタを束ねるエンジン
  - alert_manager.py                 — アラート送信管理（未列挙箇所あり）

- src/kabusys/portfolio/
  - portfolio_builder.py             — 候補選定・重み付け
  - position_sizing.py               — 株数決定・単元丸め・投下資金スケーリング
  - risk_adjustment.py               — セクターキャップ・レジーム乗数

- src/kabusys/research/
  - factor_research.py               — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py           — 将来リターン / IC / 統計サマリー
  - __init__.py                      — エクスポート（zscore_normalize 等）

- src/kabusys/tools/
  - paper_verification_report.py     — Paper Trading 検証レポート生成スクリプト

- src/kabusys/utils/
  - process_priority.py              — プロセス優先度 / CPU affinity 設定ユーティリティ

注意事項 / 運用上のポイント
----------------------------
- 本番運用（KABUSYS_ENV=live）の場合は LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）や KILL_FLAG_CLEAR_ON_START 等を慎重に設定してください。validate_config.py は本番時のガードチェックを行います。
- OpenAI を使う機能は API キー（OPENAI_API_KEY）が必須です。API 呼び出しはリトライやフォールバックを実装していますが、API コストやレイテンシを考慮してください。
- Paper Trading は本番 DB と分離されていますが、運用時に誤って本番 DB を上書きしないよう .env の DB パスを必ず確認してください。
- process_priority / cpu_affinity の設定は OS 権限に依存します。権限不足時は警告ログが出て処理をスキップします。

サンプル .env（最低限）
-----------------------
以下は最低限必要なキーの例（config_setup で対話的に生成できます）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

最後に
------
この README はコードベースの主要機能と運用上のポイントをまとめたものです。実運用を行う際は .env、config/*.yaml、そして validate_config の出力を必ず確認してください。追加の開発用ユーティリティや ExecutionEngine 等の詳細は各モジュールの docstring を参照してください。