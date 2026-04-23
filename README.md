# KabuSys

日本株向け自動売買システムのコアライブラリ・スクリプト群です。本リポジトリは取引エンジン、監視、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント／レジーム判定）やユーティリティを含みます。

---

## 概要

KabuSys は以下の主要コンポーネントで構成されています。

- ExecutionEngine: 発注・注文管理・リスク管理・照合などを行う実行エンジン
- Monitoring: システム状態・注文状況・リスクを定期監視し、アラートや Kill Switch を発動
- Portfolio: 候補選定、重み計算、ポジションサイズ決定（純粋関数群）
- Research: ファクター計算・将来リターン・IC 計算などの分析ユーティリティ
- AI: ニュースの NLP スコアリング・市場レジーム判定（OpenAI を使用）
- Tools: ペーパートレード用の検証レポート生成 等
- Utils: ロギング設定・プロセス優先度設定などの共通ユーティリティ

設計方針の一部:
- 本番用／ペーパートレード用の DB を分離（KABUSYS_ENV により挙動切替）
- .env による設定管理・対話式ウィザードと検証 CLI を提供
- OpenAI を用いる機能は API キー必須、失敗時はフェイルセーフで継続する設計

---

## 主な機能一覧

- execution/run_execution.py
  - ExecutionEngine 起動スクリプト
  - KABUSYS_ENV=paper_trading の場合は MockBroker を利用し、専用 SQLite（data/paper_trading.db）に記録
- monitoring/run_monitoring.py
  - SystemMonitor ポーリングループ起動（MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能）
  - 監視は常に本番用 sqlite_path を参照（環境に依らず）
- config_setup.py
  - 対話式ウィザードで .env を生成／更新
- validate_config.py
  - .env と config/*.yaml の基本チェックを行う CLI
- monitoring モジュール
  - system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch, monitoring_db
- portfolio モジュール
  - 候補選定（select_candidates）、重み計算、ポジションサイズ（calc_position_sizes）
- research モジュール
  - ファクター計算（momentum, volatility, value）や IC・統計サマリ
- ai モジュール
  - news_nlp.score_news: raw_news を LLM でスコア化して ai_scores に書き込み
  - regime_detector.score_regime: MA200 とマクロニュースを合成して market_regime を決定
- tools/paper_verification_report.py
  - ペーパートレード DB から検証レポートを生成（稼働率・約定率・レイテンシ等）

---

## 要件（例）

Python 3.10+ を想定。主な依存パッケージ:

- duckdb
- psutil
- openai
- pyyaml（config YAML 検証で任意）

インストール例（pip）:
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# requirements.txt が無い場合:
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化する。
2. 必要パッケージをインストールする（上記参照）。
3. 環境変数設定（.env）を準備する。
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - あるいはルートに `.env` を作成する（自動読み込みされます）。
4. 設定検証（任意）:
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにするには --strict を付ける
   python -m kabusys.validate_config --strict
   ```

自動ロードについて:
- 起動時に .env（および .env.local）を自動読み込みします（OS 環境変数が優先）。
- 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

重要な環境変数（一部）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能で必要）
- LOG_LEVEL（例: INFO）

---

## 使い方

基本的な起動・操作例。

- ExecutionEngine を起動（デーモン化は環境に合わせて別途管理）:
```
python -m kabusys.run_execution
```
- Monitoring を起動（デフォルト 60 秒間隔。MONITOR_POLL_INTERVAL で秒数を指定可）:
```
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- Paper Trading 検証レポート生成:
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または PAPER_TRADING_SQLITE_PATH 環境変数で DB 指定
```

停止方法（Kill Switch / 手動停止）
- 監視 / 実行スクリプトはプロジェクトルートの `data/stop_requested.flag` を検知して安全に停止します。
- ExecutionEngine に対する Kill Switch は `data/kill.flag` を作成して発動します（KillSwitch モジュール）。
- `data/execution.pid` は ExecutionEngine の PID 保存に使われます。

AI 機能の利用
- OpenAI API キーを環境変数 `OPENAI_API_KEY` に設定してください。
- news_nlp.score_news および regime_detector.score_regime は内部で OpenAI を呼び出します（キーを引数として渡すことも可）。

ユーティリティ
- ロギングは `kabusys.utils.logging_setup.setup_logging` により、コンソール（stdout）と日次ローテートファイル（logs/<app_name>.log）に出力します。
- プロセス優先度は `kabusys.utils.process_priority.set_process_priority` を介して設定されます（起動スクリプト内で high に設定）。

モジュール的利用（ライブラリとして）
- ポートフォリオ構築:
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes
- リサーチ:
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary

例（Python から直接呼ぶ）:
```py
from kabusys.portfolio import select_candidates, calc_equal_weights
candidates = select_candidates(buy_signals, max_positions=10)
weights = calc_equal_weights(candidates)
```

---

## ディレクトリ構成（抜粋）

以下は主要ファイル／モジュールの一覧です（src/kabusys 配下）。

- kabusys/
  - __init__.py
  - config.py                # .env 自動読み込み・Settings
  - config_setup.py          # .env 対話式ウィザード
  - validate_config.py       # 設定検証 CLI
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - run_monitoring.py        # SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py       # ログ設定ユーティリティ
    - process_priority.py    # プロセス優先度設定
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py       # （コード一覧に基づくが主要ファイル）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       # （存在することを想定）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/monitoring_db.py
  - tools/
    - paper_verification_report.py

（実際のファイルは src/kabusys 配下に多数存在します。上は主要ファイルの抜粋です）

---

## 注意事項 / トラブルシューティング

- .env の自動読み込みは OS 環境変数を優先します。テストや CI で自動読み込みを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- monitoring は常に `Settings.sqlite_path`（監視 DB）を参照します。監視 DB は本番用と分離されていますが、ExecutionEngine の paper_trading モードでは別 DB（PAPER_TRADING_SQLITE_PATH）が利用されます。
- OpenAI を用いる機能は API 呼び出しに失敗する可能性があります。設計上、失敗時はフォールバック（スコア 0.0 など）またはスキップして継続しますが、API コストやレート制限に注意してください。
- ログ出力先ディレクトリ（デフォルト `logs/`）の作成に失敗するとファイル出力は無効になり、コンソール出力のみになります。
- psutil による優先度設定は権限や OS に依存します。AccessDenied 等が発生した場合は警告ログを出力してスキップします。
- DB マイグレーション（monitoring_db.init_monitoring_db）は起動時に自動で簡易的な追加カラムマイグレーションを行いますが、本格的なマイグレーションは手動管理を推奨します。

---

必要であれば README にサンプル .env テンプレート、より詳細な実行手順（systemd / コンテナでのデプロイ方法）や各モジュールの API ドキュメントを追加します。どの内容を拡充しますか？