KabuSys — 日本株自動売買システム (README)
=======================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python ベースの小規模なシステム群です。本リポジトリには環境設定ウィザード、設定検証、ExecutionEngine（発注実行）起動スクリプト、Monitoring（監視）ループ、ファクター計算やポートフォリオ構築、AI ベースのニュースセンチメント評価、ペーパートレード向け検証レポート生成などのモジュールが含まれます。

主な設計方針（抜粋）
- 運用環境（live / paper_trading / development）を環境変数で切替
- Paper Trading は本番 DB から完全分離（専用 SQLite を使用）
- DuckDB を分析用に使用、SQLite を監視・発注ログ用に使用
- OpenAI（gpt-4o-mini 想定）を利用する NLP 部分は API キーを外部から注入可能
- フェイルセーフ重視（API 失敗時はフォールバックするなど）

機能一覧
--------
- 環境設定ウィザード（.env 生成 / 更新）
- 設定検証 CLI（.env と config/*.yaml の基本チェック）
- ExecutionEngine 起動スクリプト（実発注 / ペーパートレード切替）
- Monitoring 起動スクリプト（システム状態 / 注文 / リスク監視の定期実行）
- MonitoringDB：SQLite を使った監視ログの永続化層
- Kill Switch：リスク条件（ドローダウン等）で停止フラグを書き込み Execution を停止
- リサーチモジュール：ファクター計算（Momentum / Volatility / Value 等）
- ポートフォリオ構築：候補選定、等金額/スコア加重、リスク調整、株数決定（単元丸め）
- AI モジュール：ニュースの NLP スコアリング、レジーム判定（OpenAI 利用）
- ユーティリティ：ログ設定、プロセス優先度 / CPU affinity 設定
- ツール：ペーパートレード検証レポート生成スクリプト

セットアップ手順
----------------
1. Python
   - Python 3.10 以降を推奨（パイプラインの型アノテーションに | が使われています）。

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージのインストール
   - 必要な主なパッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（config.yaml の検証を行う場合）
   - 例（requirements.txt が無い場合の一例）:
     - pip install duckdb psutil openai PyYAML

4. .env の作成
   - 対話式ウィザードで .env を生成できます（推奨）:
     - python -m kabusys.config_setup
   - 必須環境変数（最低限設定すること）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他の重要な環境変数やデフォルトは下記「環境変数」参照。

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）になります。

使い方（主要コマンド）
---------------------
- 環境設定ウィザード（.env 生成 / 更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient 相当を使用して data/paper_trading.db に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在すると起動を行わず終了
    - data/execution.pid に PID を書く（設定に応じて）

- Monitoring（監視）起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト 60 秒）
  - python -m kabusys.run_monitoring
  - 挙動:
    - 監視ループは project_root/data/stop_requested.flag を検出すると終了
    - Monitoring は環境にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視ログを記録

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH を設定可能）

- AI 関連（ニューススコア / レジーム判定）
  - news_nlp.score_news や regime_detector.score_regime を呼び出して利用します（コマンドライン用の thin wrapper は無いのでスクリプト/ジョブから利用する想定）
  - OpenAI API キーを環境変数 OPENAI_API_KEY または関数引数で渡す必要あり

重要な環境変数（主なもの）
--------------------------
以下は Settings クラスで参照される主要な環境変数とデフォルト値の一覧（.env に設定可能）。

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN (任意)
- LINE_USER_ID (任意)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (paper_trading の fill モード, default "instant", 有効値: instant|partial|never|reject)
- KABUSYS_ENV (実行環境, default "development", 有効値: development|paper_trading|live)
- LOG_LEVEL (default "INFO")
- KILL_FLAG_PATH (default: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (default "0")
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔を秒で指定; デフォルト 60)
- OPENAI_API_KEY (AI モジュール利用時に必要)

停止 / Kill Switch
------------------
- Monitoring や ExecutionEngine の制御はフラグファイルで行われます。
  - data/stop_requested.flag: run_monitoring / run_execution のループ停止を検出するために使用
  - data/kill.flag: KillSwitch が評価条件に合致したときに作成され、ExecutionEngine に外部停止シグナルとして作用
- KillSwitch はドローダウンやポジション上限などの条件を満たした場合に kill.flag を書き込みます。kill.flag の自動クリアは KILL_FLAG_CLEAR_ON_START 環境変数で制御されます（デフォルトはクリアしない 0）。

ログ
---
- ログは kabusys.utils.logging_setup.setup_logging で設定されます。
  - コンソール (stdout) 出力と日次ローテーションのファイル出力（logs/<app_name>.log）を提供
  - LOG_DIR 環境変数または引数でログディレクトリの変更可能
  - デフォルトログディレクトリ: logs/

トラブルシューティング（よくある問題）
------------------------------------
- パッケージ不足: duckdb, psutil, openai, PyYAML 等をインストールしてください。
- DB ファイルの親ディレクトリが存在しない場合は起動時に自動作成されることがありますが、権限エラー等に注意してください。
- OpenAI を使う処理では API キー未設定だと ValueError が発生します（スクリプト側でキャッチされフェイルセーフをとる箇所あり）。

ディレクトリ構成
----------------
（src/kabusys 以下の主要ファイル群。実際のリポジトリはこのツリーに合わせてください）

- src/kabusys/
  - __init__.py
  - config.py                -- Settings / .env 自動読み込みロジック
  - config_setup.py          -- .env 対話式ウィザード
  - validate_config.py       -- 設定検証 CLI
  - run_execution.py         -- ExecutionEngine 起動スクリプト
  - run_monitoring.py        -- Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  -- ペーパートレード検証レポート生成
  - utils/
    - __init__.py
    - logging_setup.py       -- ログ設定ユーティリティ
    - process_priority.py    -- プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       -- MonitoringDB 永続化層（SQLite）
    - monitoring_engine.py   -- 各モニタを束ねるエンジン
    - system_monitor.py      -- システム状態・データ鮮度監視
    - risk_monitor.py        -- ドローダウン・ポジション上限監視
    - kill_switch.py         -- Kill Switch フラグ管理
    - (trade_monitor.py 等も参照されます)
  - portfolio/
    - __init__.py
    - portfolio_builder.py   -- 候補選定・重み計算
    - position_sizing.py     -- 株数決定・投下キャップ
    - risk_adjustment.py     -- セクター制限・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py     -- Momentum / Volatility / Value 計算
    - feature_exploration.py -- 将来リターン計算、IC、統計サマリ等
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュースセンチメント・AI スコアリング
    - regime_detector.py     -- 市場レジーム判定（MA + マクロセンチメント合成）
  - （その他 execution, data, strategy 等のパッケージが想定されます）

開発メモ / 注意点
-----------------
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は既存 DB に対して冪等にテーブル作成・列追加を行います。
- 時刻・日付:
  - 多くのモジュールはルックアヘッドバイアスを避けるため date.today()/datetime.today() を直接参照しないように設計されています（呼び出し元から target_date を渡す等）。
- フェイルセーフ:
  - AI 呼び出しや外部 API はリトライやフォールバックを含む設計になっています。運用時はログをチェックしてください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"（ソース内に記載）

問い合わせ / 拡張
------------------
- 新しい変数やログ出力、モニタ条件を追加する場合は config.py の Settings にプロパティを追加し、config_setup.py / .env テンプレートを更新してください。
- AI モジュールのモデルやプロンプトは定数として定義されており、ここを調整して挙動を変えられます（ただし API 呼び出しのコストやレスポンス形式に注意）。

以上がプロジェクトの概観と主要な使い方です。必要であれば README を英語に翻訳したり、起動例・.env.example を作成するテンプレートも用意します。どちらが良いか指示ください。