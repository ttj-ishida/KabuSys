# KabuSys

KabuSys は日本株向けの自動売買・研究基盤です。市場データの集計・ファクター計算、ポートフォリオ構築、発注エンジン、監視・アラート、LLM を用いたニュース NLP などの機能群を持ち、ローカル開発からペーパートレード・本番稼働まで想定した設計になっています。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- 環境設定管理
  - .env の自動読み込み / 対話式ウィザード（config_setup）
  - 起動前チェック（validate_config）

- 発注系
  - ExecutionEngine 起動スクリプト（run_execution）
  - paper_trading 環境は本番 DB と分離（PAPER_TRADING_SQLITE_PATH）

- 監視系
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視ループ起動スクリプト（run_monitoring）
  - kill.flag による外部停止（Kill Switch）
  - 監視ログ永続化（SQLite）と DuckDB を用いた分析データ格納

- ポートフォリオ構築
  - 候補選定、等重・スコア重み、リスク調整（セクター上限、レジーム乗数）
  - 株数計算（単元株丸め、資金制限、スケーリング）

- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン・IC 計算・統計サマリ（外部ライブラリに依存しない実装）

- AI / NLP
  - ニュース記事の LLM（OpenAI）によるセンチメントスコア化（news_nlp）
  - マクロニュース + ETF MA を組み合わせた市場レジーム判定（regime_detector）
  - API 呼び出しはリトライ・バックオフ・フェイルセーフ実装

- ツール
  - Paper Trading の検証レポート出力（tools/paper_verification_report）

- ユーティリティ
  - 統一ロギング設定（stdout + 日次ローテート）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順（ローカル開発向け）

以下は一般的なローカルセットアップ手順の例です。

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要パッケージ（例）: duckdb, psutil, openai, pyyaml
   - 例:
     ```
     pip install duckdb psutil openai pyyaml
     ```
   - プロジェクトに requirements.txt があればそれを使ってください。

3. .env ファイルの作成（対話式ウィザード推奨）
   - ウィザード実行:
     ```
     python -m kabusys.config_setup
     ```
   - 対話で必要な環境変数を設定します（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD は必須）。

4. 設定検証
   - .env を保存したら起動前チェックを実行:
     ```
     python -m kabusys.validate_config
     ```
   - 警告も FAIL 扱いにしたい場合は `--strict` を付ける。

5. 必要に応じてデータディレクトリなどを作成
   - デフォルトの DB / ログパスは `data/` と `logs/` です。スクリプト実行時に自動作成されますが、権限等に注意してください。

注意:
- 自動で .env を読み込む仕組みは、プロジェクトルート（.git または pyproject.toml）を基準に行われます。CWD に依存しない設計です。
- 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 必須 / 主要な環境変数

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (default: development) — 有効値: development / paper_trading / live
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, default: data/paper_trading.db)
- LOG_LEVEL (default: INFO)
- LOG_DIR (default: logs/)
- OPENAI_API_KEY (AI 機能を利用する場合)
- PAPER_FILL_MODE (paper trading の fill 動作: instant|partial|never|reject)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒、デフォルト 60)
- KILL_FLAG_CLEAR_ON_START (0/1、本番では 0 推奨)

例（.env の一部）:
```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

---

## 使い方（主要スクリプト・コマンド）

- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動（実取引・ペーパートレードの発注エンジン）
  - 実行:
    ```
    python -m kabusys.run_execution
    ```
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）。
    - 起動時に data/execution.pid を使用してプロセス管理します。
    - 停止は data/stop_requested.flag や監視側の kill.flag（data/kill.flag）で行われます。

- Monitoring 起動（監視ループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可能（デフォルト 60）。
  - 監視は KABUSYS_ENV に関係なく本番用の sqlite_path を参照して監視テーブルを作成/更新します。
  - 停止フラグ: data/stop_requested.flag を作成すると監視ループは終了します。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI / リサーチ関数（ライブラリ API）
  - ニューススコアリング:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ファクター計算（research）:
    - kabusys.research.calc_momentum(conn, date)
    - kabusys.research.calc_volatility(conn, date)
    - kabusys.research.calc_value(conn, date)
    - その他: calc_forward_returns, calc_ic, factor_summary

- ログ設定
  - すべての起動スクリプトは共通の logging_setup.setup_logging() を使って stdout と日次ローテーションのファイル出力を設定します。
  - デフォルトログディレクトリは logs/。LOG_DIR 環境変数で変更可能。

---

## 停止・安全管理

- Kill Switch:
  - RiskMonitor 等が条件を満たすと data/kill.flag を書き込みます（ExecutionEngine はこのファイルの存在を検知して停止できます）。
  - KillSwitch は既存の kill.flag を上書きしないため冪等です。

- 外部停止フラグ:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring は検知して終了します。

- 起動時の Kill Flag 自動クリア:
  - Settings.kill_flag_clear_on_start（KILL_FLAG_CLEAR_ON_START=1）で自動クリアする挙動を制御できます。本番では危険なので 0 を推奨します。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要構成（src/kabusys を起点）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）集約・スコア化
    - regime_detector.py     — レジーム判定ロジック
    - __init__.py

  - monitoring/
    - monitoring_db.py       — SQLite テーブル作成・読み書き層
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — (参照: 注文監視ロジック)
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - monitoring_engine.py   — 各 Monitor を束ねる
    - kill_switch.py         — kill.flag 管理
    - alert_manager.py       — (参照: アラート送信)
    - __init__.py

  - portfolio/
    - portfolio_builder.py   — 候補選定・スコアソート
    - position_sizing.py     — 発注株数計算（単元丸め、スケール）
    - risk_adjustment.py     — セクター上限・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py     — Momentum/Volatility/Value 計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・summary
    - __init__.py

  - utils/
    - logging_setup.py       — 共通ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity
    - __init__.py

  - tools/
    - paper_verification_report.py — Paper Trading レポート生成
    - __init__.py

- config/
  - system_config.yaml, data_config.yaml, strategy_config.yaml, ... （テンプレート/生成スクリプトで作成）

- data/
  - monitoring.db (デフォルト SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (デフォルト DUCKDB_PATH)
  - execution.pid, kill.flag, stop_requested.flag などが配置される想定

- logs/
  - execution.log, monitoring.log, ...（日次ローテート）

---

## 開発・運用上の注意

- 本番環境（KABUSYS_ENV=live）では設定ミスが重大な影響を及ぼします。validate_config の警告や .env の内容を必ず確認してください。
- OpenAI など外部 API を利用する機能は API キーの管理と呼び出し回数に注意してください。API の障害時はフェイルセーフ（スコア 0.0・処理スキップ）で継続する設計です。
- DB（SQLite / DuckDB）への書き込みはスクリプトが自動で初期化しますが、運用時のバックアップやディスク容量には注意してください。
- process priority / CPU affinity の設定は管理者権限が必要な場合があります。失敗しても警告ログを出してスキップする実装です。

---

もし README に追加したい項目（例: CI 設定、Docker 化手順、より詳細な実行フロー図や API 仕様など）があれば教えてください。それに合わせて追記します。