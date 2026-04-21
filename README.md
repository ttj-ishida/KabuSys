# KabuSys

日本株向け自動売買システムの参考実装です。  
本リポジトリは取引実行、監視、リサーチ、ポートフォリオ構築、AI ベースのニュース評価などのコンポーネントを含んでいます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローを構成するモジュール群を集めたコードベースです。主な責務は以下のとおりです。

- Execution: ブローカークライアントを通じた注文発行、注文管理、リスク管理、照合処理
- Monitoring: システム稼働・データ鮮度・注文状況・リスク指標のポーリング監視とアラート / Kill Switch
- Research: DuckDB ベースのファクタ計算・将来リターン計算・特徴量評価
- Portfolio: 候補選定、重み計算、ポジションサイズ算出、セクター制約など
- AI: ニュース記事のセンチメント評価（OpenAI）や市場レジーム判定
- Tools: ペーパートレード検証レポート生成などのユーティリティ

設計方針として、フェイルセーフ（API失敗時は安全側にフォールバック）、ルックアヘッドバイアスの排除、DB／ファイルの明確な分離（本番 vs paper_trading）が採用されています。

---

## 主な機能一覧

- 環境設定ウィザード（.env 作成/更新）
  - `python -m kabusys.config_setup`
- 設定検証 CLI
  - `python -m kabusys.validate_config [--strict]`
- 実行エンジン起動スクリプト（ExecutionEngine）
  - `python -m kabusys.run_execution`
  - `KABUSYS_ENV=paper_trading` で MockBroker を使用し paper_trading DB に記録
- 監視ループ起動スクリプト（SystemMonitor）
  - `python -m kabusys.run_monitoring`
  - ポーリング間隔は `MONITOR_POLL_INTERVAL`（秒、デフォルト 60）
- Paper Trading 検証レポート生成
  - `python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]`
- DuckDB ベースのファクタ計算（モメンタム/バリュー/ボラティリティ）
- ニュース NLP による銘柄ごとのセンチメント評価（OpenAI）
- 市場レジーム判定（ETF + マクロNews の融合）
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・単元丸め・リスク調整）

---

## セットアップ手順

注: 実行環境に依存するライブラリ（例: psutil, duckdb, openai）を使用します。以下は推奨される手順の例です。

1. Python 仮想環境を作成・有効化
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 代表的な必須パッケージ:
     - pip install duckdb psutil openai
   - 任意（YAML 検証を行う場合）:
     - pip install PyYAML

3. プロジェクトルートに移動（.git または pyproject.toml を基準に自動検出されます）。

4. 初期環境変数の設定
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - もしくは手動で `.env` を作成。最低限必要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（例: INFO）
     - LOG_DIR（ログ出力先、デフォルト: logs/）

5. (任意) 設定検証
   - python -m kabusys.validate_config
   - 詳細なチェックを厳格扱いにする場合: python -m kabusys.validate_config --strict

6. データディレクトリ作成（必要に応じて）
   - mkdir -p data logs

---

## 使い方（コマンド一覧）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗として exit(1)

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 起動中は `data/execution.pid` が使用され、停止は `data/stop_requested.flag` を作成すると検出して停止します
  - KABUSYS_ENV=paper_trading のときは MockBroker で paper_trading DB（data/paper_trading.db）に記録されます

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔(秒)を上書き可能（デフォルト 60）
  - 監視は本番 sqlite_path（KABUSYS_ENV に関係なく設定された SQLITE_PATH）を使用します
  - 停止は `data/stop_requested.flag` を作成すると検出して終了します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能
  - OpenAI を使う関数（news scoring / regime scoring）は `OPENAI_API_KEY` を環境変数に設定する必要があります
  - 例: export OPENAI_API_KEY="sk-..."

---

## 主要な環境変数（例 / 意味）

- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能時）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading: 実発注は行わず MockBroker を使用し、paper DB（PAPER_TRADING_SQLITE_PATH）へ記録
  - live: 本番挙動（実発注）
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant|partial|never|reject）
- DUCKDB_PATH: 分析用 DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用監視/ログ DB（デフォルト data/paper_trading.db）
- LOG_LEVEL, LOG_DIR: ログ設定
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

注意: validate_config で必須・推奨項目のチェックができます。

---

## 動作上の重要な挙動・注意点

- DB の分離:
  - paper_trading モードでは本番の SQLite を使用せず `PAPER_TRADING_SQLITE_PATH` を使って完全分離されます。
  - Monitoring は KABUSYS_ENV に関わらず設定された `SQLITE_PATH`（本番パス）を使用します（監視データは共有される設計）。

- Kill / Stop シグナル:
  - `data/kill.flag` (KillSwitch) と `data/stop_requested.flag`（起動中プロセスが監視して停止するフラグ）を用います。
  - `KILL_FLAG_CLEAR_ON_START=1` は本番で危険なのでデフォルト 0 を推奨します。

- ログ:
  - 共通の logging 設定ユーティリティを使用しています。デフォルトは `logs/<app_name>.log` に日次ローテーションで保存されます。
  - ログディレクトリが作成できない場合はコンソール出力のみになります。

- OpenAI 呼び出し:
  - レート制限・一時エラーに対してリトライ・バックオフ処理を行います。
  - API キー未設定時は例外を投げるか、安全側フォールバック（0.0）になるケースがあります（モジュールにより挙動が異なります）。

- テスト容易性:
  - API 呼び出し関数は内部で抽象化されており、ユニットテスト時にパッチしやすい設計です（例: _call_openai_api のモック化）。

---

## ディレクトリ構成（主要ファイル）

プロジェクト内の主要モジュールを抜粋したツリー例:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定読み込みロジック（自動 .env 読み込みを含む）
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル作成／CRUD）
    - system_monitor.py      — システム稼働・データ鮮度監視
    - trade_monitor.py       — 発注/約定ログ監視（存在）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — Kill Switch ロジック（flag ファイル生成）
    - monitoring_engine.py   — 各監視のオーケストレーション
    - alert_manager.py       — アラート送信管理（存在）
  - execution/
    - execution_engine.py    — 実行エンジン本体（EngineConfig, run_session 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 発注株数算出
    - risk_adjustment.py     — セクター制約・レジーム乗数
  - research/
    - factor_research.py     — ファクター計算 (momentum/value/volatility)
    - feature_exploration.py — forward return / IC / summary
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（ETF + マクロ）
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成

- data/                      — 実行時生成の DB / flag / pid 等（既定）
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - stop_requested.flag
  - kill.flag
  - execution.pid

- logs/                      — ログ出力先（LOG_DIR）

---

## 追加ドキュメント / 参照先

コード内に多くの docstring が埋め込まれています。特に以下のモジュールを参照してください:

- PortfolioConstruction.md / StrategyModel.md（コード参照でコメントに言及あり）：ポートフォリオ構築・戦略設計の仕様
- 各モジュールの docstring（research, ai, monitoring など）：挙動や設計上の注意点が詳細に記載されています

---

## トラブルシューティング / よくある質問

- Q: .env が自動ロードされない / テスト時に邪魔になる  
  A: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化できます。

- Q: OpenAI API 呼び出しで失敗するとき  
  A: `OPENAI_API_KEY` が正しく設定されているか、ネットワークやレート制限を確認してください。モジュールはリトライを実装していますが、キーが未設定だと例外になります。

- Q: 監視プロセスのポーリング間隔を変えたい  
  A: 環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能です。1 未満や不正値は無視されデフォルト 60 秒が使用されます。

---

この README はコードベースの概要説明と基本的な操作法をまとめたものです。具体的な実装や拡張を行う場合は各モジュールの docstring を参照してください。必要であればデプロイ手順・運用手順や追加の設定例を別途作成します。