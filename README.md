# KabuSys

日本株自動売買システム（ライブラリ + 実行スクリプト群）

このリポジトリは、投資システムのコアライブラリ（ポートフォリオ構築・リサーチ・AIスコアリング等）、監視・リスク管理、実行エンジン起動スクリプト、および運用ユーティリティを含みます。

---

## プロジェクト概要

- 戦略：ファクター計算（Momentum / Value / Volatility / Liquidity）や特徴量解析を行う research モジュールを提供
- ポートフォリオ構築：候補選定、重み計算、ポジションサイジング、セクター集中制御などの純粋関数群を提供
- 実行：ExecutionEngine を起動してブローカークライアント経由で発注（paper_trading モードをサポート）
- 監視：SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine（ログ/アラート/kill switch）
- AI：ニュースのセンチメント算出（OpenAI）や市場レジーム判定を行うモジュールを提供
- 永続化：SQLite（監視・発注ログ等）と DuckDB（分析用）を利用

---

## 主な機能一覧

- 実行系
  - run_execution.py: ExecutionEngine を起動（paper_trading モードで MockBroker を使用）
  - 発注履歴 / trade_logs を SQLite に記録
- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL 指定可）
  - System / Trade / Risk の監視、kill.flag による ExecutionEngine 停止トリガー
  - monitoring_db: 監視ログ用の SQLite スキーマと操作ラッパー
- ツール
  - config_setup.py: 対話式で .env を生成・更新
  - validate_config.py: 環境変数および config/*.yaml の事前検証（--strict オプションあり）
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポート生成
- ポートフォリオ（純粋関数）
  - 銘柄候補選定（select_candidates）
  - 等金額・スコア加重の重み計算
  - position sizing（risk_based / equal / score）、単元株丸め、aggregate cap
  - セクターキャップ適用、レジーム乗数
- リサーチ
  - factor_research: momentum/volatility/value の計算（DuckDB 経由で prices_daily / raw_financials を利用）
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄ごとの ai_score を ai_scores テーブルへ書込
  - regime_detector: ETF（1321）の MA200 等とマクロニュースの LLM センチメントを合成し market_regime を決定
- ユーティリティ
  - logging_setup: 一貫したログ設定（stdout + 日次ローテーションファイル）
  - process_priority: Windows / POSIX を吸収したプロセス優先度設定ユーティリティ

---

## 前提 / 推奨環境

- Python 3.10+
- 主な依存パッケージ（最低限）
  - duckdb
  - psutil
  - openai
- 開発用・追加
  - PyYAML（config/*.yaml の検証に使用。なくても動作するが警告が出る）
- 仮想環境を推奨:
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

依存パッケージのインストール例:
```
pip install duckdb psutil openai PyYAML
```
（実際にはプロジェクトに requirements.txt があればそれを使ってください）

---

## 設定（.env）と環境変数

このプロジェクトは環境変数（または .env ファイル）で設定します。自動的にプロジェクトルートの `.env` と `.env.local` を読み込みます（OS 環境変数が優先）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な必須 / 重要な環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: `development` | `paper_trading` | `live`（デフォルト: development）
  - `paper_trading` のとき、発注は MockBroker を使用し DB は data/paper_trading.db に書き込む
  - `live` は本番運用向けの挙動（注意が必要）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI 呼び出しを行う機能で必要
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログファイルの出力先（デフォルト: logs/）
- その他:
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE — paper_trading の fill 挙動（instant/partial/never/reject）
  - KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時の kill.flag 自動クリア（0/1）
  - KILL_FLAG_PATH / PID_FILE_PATH など（Settings 参照）

.env を対話式に作成する:
```
python -m kabusys.config_setup
```

設定検証:
```
python -m kabusys.validate_config
# 警告も FAIL 扱いにする場合:
python -m kabusys.validate_config --strict
```

---

## セットアップ手順（簡易）

1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境作成・有効化（推奨）
3. 依存パッケージをインストール（上記参照）
4. .env を作成
   - 対話式: `python -m kabusys.config_setup`
   - または `.env.example` を参考に作成
5. 設定検証: `python -m kabusys.validate_config`
6. データ / ログ用ディレクトリの作成（通常は自動作成されますが、権限等に注意してください）
   - data/
   - logs/

---

## 使い方（実行例）

- 実行エンジン（ExecutionEngine）起動:
```
python -m kabusys.run_execution
```
- 監視ループ起動:
```
# MONITOR_POLL_INTERVAL（秒）を上書きする例
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- 設定ウィザード:
```
python -m kabusys.config_setup
```
- 設定検証:
```
python -m kabusys.validate_config
```
- Paper Trading 検証レポート生成:
```
# デフォルト DB を参照
python -m kabusys.tools.paper_verification_report

# 期間指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# DB を明示
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

停止 / フラグについて:
- run_execution / run_monitoring はプロジェクトルート下 `data/stop_requested.flag` の存在を監視し、検知すると優雅に終了します（run_execution は起動中に同フラグがあれば起動を中止）。
- kill flag:
  - `data/kill.flag` は KillSwitch による ExecutionEngine 停止トリガーとして使用されます。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動クリアされます（本番では `0` が推奨）。

OpenAI を使う機能:
- `kabusys.ai.news_nlp` / `kabusys.ai.regime_detector` は `OPENAI_API_KEY` が必要です。API 呼び出しの失敗はフェイルセーフな挙動（代替値で継続）になっていますが、キーの設定を推奨します。

ログ:
- デフォルトは stdout と `logs/<app_name>.log`（日次ローテーション、30日保持）。

---

## 主要スクリプトと振る舞いの注意点

- run_execution.py
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用しデータは paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録して本番 DB と分離します。
  - 実行は別スレッドで Engine.run_session を起動し、stop フラグにより安全に停止します。
  - 起動時にプロセス優先度を "high" に設定しようとします（権限がないと警告になります）。

- run_monitoring.py
  - SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を使います（環境にかかわらず production path を参照する点に注意）。

- validate_config.py / config_setup.py
  - 運用前に .env と config/*.yaml を検証するための CLI ツール。PyYAML が無い場合は YAML 検証をスキップして警告。

---

## ディレクトリ構成（主要ファイル）

（リポジトリルートに `src/kabusys` がある想定）

- src/kabusys/
  - __init__.py
  - config.py — 設定読み込み・Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパー検証レポート
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (参照されるが抜粋に含まれていない)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
  - execution/  (発注周りの実装)
    - execution_engine.py (参照)
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/ （実行時に作られる想定）
    - monitoring.db (default SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (default DUCKDB_PATH)
    - kill.flag / stop_requested.flag / execution.pid
  - logs/ （ログファイル出力先、デフォルト）

---

## 開発・運用のヒント / 注意点

- 環境変数の自動ロードはプロジェクトルートの `.env` / `.env.local` を参照します。CI / テスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを抑止できます。
- 本番環境では `KABUSYS_ENV=live` を設定するため、設定値は慎重に管理してください（validate_config は本番向けガードを含みます）。
- OpenAI API を使う処理はレート制限や一時的な障害を想定して実装されており、リトライやフェイルセーフ（代替値）を行いますが、API 使用コスト・レイテンシには注意してください。
- monitoring 系は監視ログを SQLite に永続化します。スキーマのマイグレーション（カラム追加）は init_monitoring_db 内である程度カバーされています。
- run_execution/run_monitoring の停止は `data/stop_requested.flag` と `data/kill.flag` を組み合わせて行います。これらはファイルシステムでのフラグ管理を意図しています。

---

必要があれば README をさらに拡張して、各モジュール（execution engine の詳細、OrderRepository の API、TradeMonitor の挙動、DuckDB のスキーマなど）のドキュメントを追加できます。どの部分を詳しく記載すべきか指定してください。