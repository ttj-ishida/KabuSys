# KabuSys

日本株自動売買システムの基礎ライブラリ群と起動スクリプト群。  
このリポジトリは、戦略・ポートフォリオ構築、実行エンジン、監視、AI（ニュース NLP）などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム向けユーティリティ群です。主な役割:

- 市場データ / ファクター計算（DuckDB ベース）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 実行エンジン（発注管理、リスク管理、リコンサイル）
- 監視（システム状態、注文ログ、リスク監視）と Kill Switch
- ニュースの NLP によるセンチメント評価（OpenAI を利用）
- 開発用ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計方針として、可能な限り純粋関数・DB 分離・フェイルセーフな挙動を重視しています。

---

## 主な機能一覧

- 環境設定ウィザード（.env の対話的生成）: kabusys.config_setup
- 起動前設定検証 CLI: kabusys.validate_config
- 実行エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し paper_trading.db に記録
  - 停止フラグ（data/stop_requested.flag）で安全停止
- 監視ループ起動スクリプト: run_monitoring.py
  - システム状態、データ鮮度、注文ログなどを定期ポーリングし監視
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整（デフォルト 60 秒）
  - 実行プロセス優先度を高く設定（可能な場合）
- 監視 DB 永続化層（SQLite）と MonitoringEngine
- RiskMonitor / KillSwitch によるドローダウンやポジション上限の検出と停止
- ポートフォリオ構築ユーティリティ
  - 候補選定、等重・スコア重み、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元株丸め・集約キャップ考慮）
- 研究用モジュール（DuckDB 経由のファクター計算、Forward Returns、IC 計算 等）
- AI モジュール
  - news_nlp: OpenAI を使ったニュースセンチメント → ai_scores への書き込み
  - regime_detector: ETF とマクロニュースを組み合わせた市場レジーム判定
- 開発用ツール: Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 前提 / 必要環境

- Python 3.9+（コードは typing などモダンな構文を使用）
- 主な Python パッケージ（最低限）:
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML — config/*.yaml の内容検証時に使用

※ requirements.txt が無い場合は下記のように個別インストールしてください:
  pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローン / 配布を取得
2. 仮想環境を作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
3. 必要パッケージをインストール
   pip install duckdb psutil openai PyYAML
4. .env の作成（対話式ウィザード）
   python -m kabusys.config_setup
   - ウィザードで J-Quants トークン、kabu API パスワード等を入力してください。
   - .env は絶対に Git にコミットしないでください。
5. 設定検証
   python -m kabusys.validate_config
   - 問題がある場合はメッセージに従って修正してください。

---

## 重要な環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DB パス
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: 監視 DB のデフォルト data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（paper_trading 時）
- ログ
  - LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）
  - LOG_DIR: ログディレクトリ（デフォルト logs/）
- AI
  - OPENAI_API_KEY: OpenAI を使う機能で必要
- 監視関連
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
- Paper Trading 挙動
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト instant）

詳細は kabusys.config.Settings のプロパティを参照してください。

---

## 使い方（主なコマンド）

- 環境ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱い（exit code 1）

- 実行エンジン起動（デイリートレード等を担うプロセス）
  python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading の場合、MockBroker を使用し随時 data/paper_trading.db に記録
  - 実行中は data/execution.pid を書込む
  - data/stop_requested.flag が存在すると終了します（外部から停止要求を出せます）

- 監視ループ起動
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定（デフォルト 60 秒）
  - 監視は常に本番用 sqlite_path（SQLITE_PATH）を使用します（paper_trading でも同じ）

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを上書き可能（環境変数 PAPER_TRADING_SQLITE_PATH と優先順位）

- 研究 / AI モジュールはライブラリ呼び出しとして利用可能
  例: from kabusys.research import calc_momentum
       from kabusys.ai.news_nlp import score_news

---

## 停止 / Kill Switch の仕組み

- 外部から実行エンジンを停止したい場合:
  - data/stop_requested.flag を作成すると run_execution のループが検知して停止します（run_monitoring もこれを検知して自身を終了する場合があります）。
- 自動停止（Kill Switch）
  - RiskMonitor の判定により KillSwitch が data/kill.flag を書き込むと、次回の Execution 起動時に検出して起動を抑止できます。
  - 本番では KILL_FLAG_CLEAR_ON_START を 0（クリアしない）にすることを推奨します。

---

## ログ / データ

- ログディレクトリ（デフォルト）: logs/
  - ログファイル名はアプリ名（例: execution.log, monitoring.log）
  - 日次ローテーション（30 日保持）
- データディレクトリ（デフォルト）: data/
  - DuckDB: data/kabusys.duckdb
  - 監視 SQLite: data/monitoring.db
  - ペーパートレード SQLite: data/paper_trading.db (paper_trading 環境)

---

## ディレクトリ構成（主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - config_setup.py              — .env ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py           — ログ初期化ユーティリティ
    - process_priority.py        — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py           — 監視 DB 層（SQLite）
    - system_monitor.py          — システム状態・データ鮮度監視
    - trade_monitor.py           — 注文ログ監視（存在）
    - risk_monitor.py            — ドローダウン / ポジション上限監視
    - kill_switch.py             — Kill Switch（kill.flag）
    - monitoring_engine.py       — 各 Monitor を束ねるエンジン
    - alert_manager.py           — アラート送信（LINE 等、存在を仮定）
  - execution/                    — 実行エンジン関連（Engine, BrokerFactory, OrderManager 等）
  - portfolio/
    - portfolio_builder.py       — 候補選定・重み付け
    - position_sizing.py         — 株数決定（lot 単位丸め・aggregate cap）
    - risk_adjustment.py         — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py         — Momentum / Value / Volatility 等
    - feature_exploration.py     — Forward Returns / IC / summary
  - ai/
    - news_nlp.py                — ニュース NLP（OpenAI 呼び出し、ai_scores 書込）
    - regime_detector.py         — レジーム判定（ETF + マクロニュース）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート

※ 上記は主要モジュールの抜粋です。細かな補助モジュールはコード内にあります。

---

## 開発 / テストに関する注意

- .env の自動読み込み:
  - デフォルトでプロジェクトルートの .env / .env.local を自動でロードします。
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 実行時にプロセス優先度変更や CPU affinity を試みますが、権限不足や未対応 OS の場合はログ警告を出してスキップします。
- OpenAI API を使う機能は API キー（OPENAI_API_KEY）が必要です。API 呼び出しは堅牢化（リトライ・バックオフ・バリデーション）されていますが、コストとレート制限に注意してください。
- config/*.yaml の検証には PyYAML が必要です（無ければ検証をスキップします）。
- DuckDB のバージョンや SQLite の細かな挙動差異に注意（executemany に対する空リストの制約など、コード内に互換性対策が入っています）。

---

## トラブルシューティング

- 「環境変数が未設定」と出る場合:
  - python -m kabusys.config_setup を実行して .env を作成し、必要な環境変数を設定してください。
  - もしくは OS 環境に直接設定してください。
- OpenAI 連携で JSON 解析エラーが多発する場合:
  - モデル出力のバリエーションに備えたパーサがありますが、それでも失敗するケースは存在します。ログを確認してプロンプトやトークン長等を調整してください。
- ログファイルが作成されない場合:
  - LOG_DIR を指定、または実行ユーザーにディレクトリ作成権限があるか確認してください。ディレクトリ作成失敗時はコンソール出力のみになります。

---

この README はコード内のドキュメント（関数・クラスの docstring）と起動スクリプトを元に作成しています。詳細な設計仕様（PortfolioConstruction.md など）が別途ある場合はそれに従ってください。必要であれば README の追加項目（デプロイ手順、CI 設定、ユニットテストの実行方法など）を追記します。