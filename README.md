# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ用 README。  
本ドキュメントはソースツリー（src/kabusys 以下）に含まれる主要スクリプト・モジュールに基づいて作成しています。

## プロジェクト概要
KabuSys は日本株向けの自動売買 / リサーチ基盤です。主な機能は以下のとおりです。
- 発注エンジン（ExecutionEngine）による売買実行（本番 / ペーパートレード対応）
- システム監視（SystemMonitor / MonitoringEngine）と Kill Switch（停止フラグ）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- ファクター計算・特徴量探索（DuckDB を用いたリサーチモジュール）
- ニュースの NLP によるセンチメント評価（OpenAI を利用）
- 市場レジーム判定（MA と LLM による合成判定）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード / 検証ツール）
- Paper Trading 検証レポート生成ツール

設計方針として、発注ロジックとリサーチロジックを分離し、DuckDB / SQLite により分析データと監視ログを永続化します。Paper Trading は本番 DB と完全分離されるよう配慮されています。

## 機能一覧（抜粋）
- Execution:
  - 本番 / paper_trading 切替（環境変数 KABUSYS_ENV）
  - PaperTrading 時は MockBrokerClient を使用し、data/paper_trading.db に記録
  - 実行中の PID 管理（data/execution.pid）
- Monitoring:
  - system_status / trade_logs / positions / risk_logs / dashboard の SQLite 永続化
  - SystemMonitor（CPU / メモリ / ディスク / プロセス監視、データ鮮度チェック）
  - TradeMonitor / RiskMonitor / KillSwitch / AlertManager 統合（MonitoringEngine）
  - 停止フラグ（data/stop_requested.flag）を監視して安全停止
- Portfolio:
  - 候補選定（スコアソート）
  - 等金額／スコア加重配分
  - セクター上限適用、レジーム乗数、リスクベースのポジションサイズ計算
- Research:
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI:
  - ニュースの銘柄毎センチメント評価（OpenAI Chat API、JSON Mode を期待）
  - レジーム判定（ETF MA200 とマクロニュースの LLM 評価の合成）
- Tools:
  - 設定ウィザード（.env 作成 / 更新）
  - 設定検証 CLI（.env / config/*.yaml の簡易チェック）
  - Paper Trading 検証レポート生成

## 要件（主な Python パッケージ）
（プロジェクトに requirements.txt は含まれていません。必要に応じて固定バージョンを指定してください。）
- Python 3.9+
- duckdb
- psutil
- openai
- pyyaml （config YAML の検証を行う場合）
- SQLite は標準ライブラリで利用可能

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

## セットアップ手順
1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境を作成して依存パッケージをインストール（上記参照）
3. .env ファイルを作成
   - 対話型ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは .env を対話的に作成 / 更新します。シークレット値は入力時にマスクして扱います。
   - 手動で作る場合は .env.example を参考に必須変数を設定してください（.env.example がない場合は README の「環境変数」参照）。
4. 設定検証（任意だが推奨）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告を FAIL 扱いにする
   ```
   validate_config は必須環境変数や DB パス、config/*.yaml の存在（PyYAML がインストールされている場合）をチェックします。
5. データディレクトリの作成（.env でデフォルトを使う場合）
   ```
   mkdir -p data logs
   ```

## 主な環境変数（抜粋）
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

主要（デフォルトあり / 任意）:
- KABUSYS_ENV — 実行環境: development / paper_trading / live （デフォルト: development）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — Paper Trading の約定モード（instant / partial / never / reject）
- LOG_LEVEL, LOG_DIR — ログ設定
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

注意: .env は機密情報を含むため Git にはコミットしないでください。

## 使い方（起動方法の例）
- ExecutionEngine を起動（本番なら KABUSYS_ENV=live、Paperなら paper_trading）
  ```
  # デフォルト: .env を用いた設定
  python -m kabusys.run_execution
  ```
  実行時は data/execution.pid を作成し、data/stop_requested.flag が立っていると起動を行わず終了します。Paper Trading の場合は paper_sqlite_path に書き込みます。

- Monitoring を起動（定期ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。監視は本番 sqlite_path を参照（KABUSYS_ENV に依らず本番 DB を使用する設計）。

- Paper Trading 検証レポートを生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- 設定ウィザード / 検証
  ```
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

## 停止・Kill Switch の扱い
- 手動停止フラグ:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検出して終了します。
  - KillSwitch（kabusys.monitoring.kill_switch）は条件（ドローダウンやポジション上限）に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
- 起動時クリーンアップ:
  - Settings.kill_flag_clear_on_start=1 に設定すると起動時に kill.flag を自動でクリアします（本番では危険なのでデフォルトは 0）。

## ロギング
- 共通ユーティリティ kabusys.utils.logging_setup.setup_logging を使用:
  - コンソール（stdout）と日次ローテートされるファイル（logs/<app_name>.log）をルートロガーに設定します。
  - LOG_DIR / LOG_LEVEL 環境変数で挙動を変更可能。

## 主要モジュール・ディレクトリ構成
（src/kabusys 以下の主要ファイル / ディレクトリを抜粋して説明します）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数読み込み / Settings クラス（全アプリから参照）
  - config_setup.py — .env 対話式作成ウィザード
  - validate_config.py — 起動前チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート出力
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - execution/ (発注関連 — 要実装詳細)
    - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager など
  - monitoring/
    - monitoring_db.py — SQLite テーブル作成 & 永続化ヘルパ
    - system_monitor.py — システム監視（CPU/メモリ/ディスク/データ鮮度）
    - trade_monitor.py — 発注ログ監視（滞留注文、約定異常等）※ソース内に定義あり
    - risk_monitor.py — ドローダウン/ポジション制限の監視
    - kill_switch.py — 停止フラグの書込み/判定
    - monitoring_engine.py — 各 Monitor の統合ループ
    - alert_manager.py — 通知管理（LINE 等）※ソース内に定義あり
  - portfolio/
    - portfolio_builder.py — 候補選定・重み算出
    - position_sizing.py — 株数決定・スケーリング（lot 単位）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等
    - feature_exploration.py — 将来リターン / IC / 統計機能
  - ai/
    - news_nlp.py — raw_news を LLM に投げて銘柄別スコア作成
    - regime_detector.py — ETF MA200 とマクロニュースを合わせてレジーム判定

※上記はファイルのサマリであり、実行に必要な依存・設定は個々のモジュールで異なります。

## 追加の注意点 / トラブルシューティング
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は既存 DB に対して冪等にテーブル作成や軽微なカラム追加を行います（例: dashboard.peak_value、trade_logs.latency_ms の追加）。
- OpenAI API:
  - news_nlp / regime_detector は OpenAI の Chat API（gpt-4o-mini など）を利用します。API キーが未設定だと例外 or フェイルセーフ動作になります。単体テスト時は該当関数をモックしてください。
- PyYAML:
  - validate_config は PyYAML 未インストール時に YAML の内容検証をスキップします（警告のみ）。
- ログディレクトリ:
  - logging_setup でログディレクトリ作成に失敗した場合、ファイル出力を無効にしてコンソールのみでログ出力します（標準エラーに警告を出力）。

## 開発・拡張のヒント
- DuckDB 接続は research / ai モジュールで受け渡して使用する設計です。データを直接書き換える場合はトランザクションに注意してください（executemany の空リスト制約など実装依存の細かい挙動あり）。
- ポートフォリオ構築や position sizing は純粋関数として実装されているため、単体テストが容易です（DB に依存しない）。
- 実稼働前に validate_config を実行し、KABUSYS_ENV と LINE / Kill Switch 関連の設定を慎重に確認してください。

---  
本 README はコードベースから読み取れる設計・使用法の要点をまとめたものです。実際の運用に当たっては .env の設定、Broker クライアント実装、実行エンジン内のリスク管理パラメータ等を十分に確認してください。必要があれば README の改善点（追記希望箇所）を教えてください。