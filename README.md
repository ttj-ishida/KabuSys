# KabuSys

日本株自動売買システム（ライブラリ / 起動スクリプト群）

このリポジトリは、シンプルな自動売買基盤（監視 / 実行エンジン / ポートフォリオ構築 / 研究・ファクター計算 / AIニュースセンチメント等）の実装群を含みます。設計方針としては「本番環境での安全性」「ルックアヘッドバイアスの排除」「DBはファイルベース（SQLite / DuckDB）」が重視されています。

## 主な特徴
- ExecutionEngine（発注エンジン）起動スクリプト（run_execution）
  - KABUSYS_ENV に応じて paper_trading モード（MockBroker）を使用し、本番 DB と分離して data/paper_trading.db に記録可能
- System / Trade / Risk の監視フレームワーク（run_monitoring, MonitoringEngine）
  - system_status / trade_logs / risk_logs / dashboard などの永続化（SQLite）
  - Kill Switch（閾値超過で data/kill.flag を書き込んで ExecutionEngine に停止指示）
- Portfolio 構築ユーティリティ（候補選定・重み付け・ポジション決定・セクター制限など）
- Research ツール（DuckDB を使ったファクター計算・IC計算・将来リターン計算）
- AI モジュール（OpenAI を用いたニュースセンチメント評価、レジーム判定）
- ユーティリティ
  - 環境設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ロギング設定 / プロセス優先度設定ユーティリティ
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report）

## 必要条件（概略）
- Python 3.9+
- pip パッケージ
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config/*.yaml の検証に使用）
- OS: Linux / macOS / Windows（プロセス優先度設定は OS による差異あり）

※ 実行に必要な追加ライブラリはプロジェクトの requirements.txt に合わせてインストールしてください（このリポジトリ断片には requirements.txt が含まれていませんので、上記パッケージを目安にしてください）。

## セットアップ手順（ローカル開発向けの基本フロー）
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （YAML 検証を行う場合）pip install PyYAML

4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
     - J-Quants、kabuステーション、OpenAI（必要なら）などの環境変数を設定します。
   - 手動で作成する場合は .env.example を参照して .env を作成してください（.env.example はこの抜粋には含まれませんが、config_setup が基本構成を生成します）。
   - 自動ロード: ロード順は OS 環境 > .env.local > .env。自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 重要なエラーや警告がないか確認。--strict を付けると警告も失敗扱いになります。

6. データディレクトリとログディレクトリの準備
   - デフォルトの DB / フラグ / PID ファイル等は project_root/data 以下に作成されます（例: data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag）。
   - ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（LOG_DIR 環境変数で変更可）。

## 環境変数（主要項目）
- 必須（少なくとも実運用で）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意 / デフォルトあり
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト: data/paper_trading.db）
  - LOG_LEVEL: DEBUG/INFO/…
  - OPENAI_API_KEY: AI モジュールを使う場合に必要
  - PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant|partial|never|reject、デフォルト: instant）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか (0/1、既定 0)

詳細は kabusys.config.Settings のプロパティ説明を参照してください（設定値の妥当性検査が組み込まれています）。

## 主要コマンド / 使い方

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - 対話式に .env を作成・更新します。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）になります。

- 監視プロセスの起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60秒）。
    - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用。環境に依存せず本番 sqlite_path を使用します。
    - 停止方法:
      - プロジェクトルート/data/stop_requested.flag を作成するとループを終了します（run_monitoring と run_execution の両方が stop flag を参照します）。

- 実行エンジンの起動（Execution）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading 用 DB（デフォルト data/paper_trading.db）に記録し、本番 DB と分離します。
    - 実行中は data/execution.pid に PID が書き出されます。
    - 停止方法:
      - data/stop_requested.flag を作成するとエンジンを停止します。
      - kill.flag（data/kill.flag）は監視側が書き込むことで ExecutionEngine に停止を促す「Kill Switch」として機能します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --db PATH を指定すると PAPER_TRADING_SQLITE_PATH の代わりに使用します。
  - 出力: 指定期間に対する稼働率、注文成功率、送信率、レイテンシ等のサマリと PASS/FAIL 判定。

- AI モジュール（ニュース NLP / レジーム判定）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime をプログラムから呼び出して利用します。
  - 必要: OPENAI_API_KEY と openai パッケージ
  - 実行時は外部 API の通信制限・失敗を想定したリトライやフェイルセーフ処理が組み込まれています。

## Kill Switch / フラグの挙動
- data/kill.flag
  - 監視ロジック（RiskMonitor 等）で閾値を超えた際に KillSwitch が作成します。
  - ExecutionEngine はこのフラグの存在を検出して停止します（本番停止）。
  - 起動時に自動クリアするかは KILL_FLAG_CLEAR_ON_START を使用して制御できます（本番は 0 推奨）。
- data/stop_requested.flag
  - 開発者が単にすべての起動スクリプトを安全に停止させたい場合に使用します（両 run_monitoring/run_execution が参照）。

## ロギング
- ログは stdout に StreamHandler と、日次ローテートされるファイル logs/<app_name>.log に出力されます。
- LOG_DIR 環境変数でログディレクトリを変更できます。
- setup_logging(app_name="execution") のように各起動スクリプトが呼び出して統一的に設定します。

## ディレクトリ構成（抜粋）
以下は src/kabusys 以下の主要ファイル・ディレクトリと簡単な説明です。

- kabusys/
  - __init__.py — ライブラリのメタ情報（__version__ 等）
  - config.py — 環境変数・設定管理（Settings クラス）
  - config_setup.py — .env 対話式設定ウィザード
  - validate_config.py — 設定検証 CLI
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - ai/
    - news_nlp.py — ニュースを OpenAI でセンチメント判定して ai_scores に書き込む処理
    - regime_detector.py — ETF MA とマクロニュースを使って市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite に対する永続化レイヤ（テーブル作成・CRUD）
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - system_monitor.py — システムリソース・データ鮮度監視
    - trade_monitor.py —（抜粋では省略）取引ログ監視ロジック（参照）
    - risk_monitor.py — ドローダウン / ポジション上限の監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数計算・集約キャップ処理
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算・IC・統計サマリ
  - utils/
    - logging_setup.py — ロギング一元設定
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記は抜粋です。完全な構成はリポジトリのファイルツリーをご確認ください。）

## 運用上の注意
- KABUSYS_ENV=live の場合は本番環境になります。LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や KILL_FLAG_CLEAR_ON_START の設定に十分注意してください（validate_config は live 用の追加チェックを行います）。
- Paper Trading を使う場合、DB を本番と分離してください（PAPER_TRADING_SQLITE_PATH を設定）。
- AI（OpenAI）モジュールに関しては API 利用料とレイテンシが発生します。API キーの管理は厳重に行ってください。
- run_execution / run_monitoring は stop flag / kill flag を参照します。強制的にプロセスを kill する方法（SIGKILL など）はログや DB の整合性を崩す恐れがあるため推奨しません。

## 開発・テスト
- 各モジュールは副作用を最小限にするよう設計されています（DuckDB / SQLite 接続を引数で受け取るなど）。ユニットテストでは DB 接続や OpenAI 呼び出しをモックすることで外部依存を切り離せます。
- research / ai / portfolio の各関数は外部状態に依存しない純粋関数的な実装箇所が多く、単体テストが容易です。

---

README はここまでです。必要であれば次の追加情報を作成します：
- 例となる .env.example（テンプレート）
- requirements.txt の候補
- systemd / supervisor 用のサービス定義テンプレート
- 実行フロー図（Monitoring ↔ Execution の関係）