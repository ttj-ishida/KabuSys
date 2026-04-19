# KabuSys

日本株向けの自動売買関連ライブラリおよび運用スクリプト群です。  
監視（Monitoring）・実行（Execution）・ポートフォリオ構築・リサーチ・AI（ニュースNLP / レジーム判定）等のコンポーネントを含み、ローカル開発・ペーパートレード・本番運用の切替を想定しています。

Version: 0.1.0

---

## 概要

このリポジトリは次の役割を持つモジュール群で構成されています。

- ExecutionEngine：発注ロジック・注文管理・リスク制御を行うエンジン（run_execution.py で起動）
- Monitoring：システム監視、取引ログ監視、リスク監視、Kill Switch（run_monitoring.py で起動）
- Portfolio：銘柄選定、重み付け、ポジションサイズ計算などの純粋関数群
- Research：DuckDB を使ったファクター計算・特徴量解析
- AI：OpenAI を用いたニュースセンチメント評価・市場レジーム判定
- Utilities：ログ設定、プロセス優先度などの補助ユーティリティ
- ツール群：Paper Trading の検証レポート生成など

設計上の注意点：
- .env / 環境変数により挙動を切り替えます（自動ロード機構あり）。
- Paper Trading は本番 DB と分離（デフォルトで `data/paper_trading.db`）。
- AI モジュールは OpenAI API（モデル例: gpt-4o-mini）を利用します。APIキーが必要です。
- 監視・実行はフラグファイル（`data/stop_requested.flag`, `data/kill.flag`）で停止・保護します。

---

## 機能一覧

主要な機能（抜粋）：

- 環境設定ウィザード（kabusys.config_setup）
  - `.env` ファイルの対話的作成 / 更新
- 設定検証 CLI（kabusys.validate_config）
  - 環境変数・config/*.yaml の存在・整合性チェック
- 実行エンジン起動スクリプト（run_execution.py）
  - 本番 / ペーパー切替、MockBroker の利用、PID 管理
- 監視ループ起動スクリプト（run_monitoring.py）
  - システム状態・監視ログ記録、Kill Switch 評価（MONITOR_POLL_INTERVAL でポーリング間隔指定可）
- 監視永続層（monitoring_db）
  - SQLite に監視ログ／トレードログ等を永続化。起動時のマイグレーション処理あり
- RiskMonitor / SystemMonitor / TradeMonitor / MonitoringEngine
  - ドローダウン、ポジション上限、データ鮮度、滞留注文などの検出とログ化・アラート呼び出し
- Portfolio モジュール
  - 候補選定（select_candidates）、等金額/スコア加重、リスクベースのポジションサイズ計算、セクター制限、レジーム乗数
- Research モジュール
  - Momentum/Value/Volatility ファクター計算、将来リターン、IC 計算、統計サマリ
- AI モジュール
  - ニュースセンチメントのスコアリング（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## 必要条件（主な依存パッケージ）

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能利用時)
- PyYAML (config YAML の検証を行う場合)
- （その他、運用環境に応じた broker/client 実装や DB ドライバ等）

インストール例（仮）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

※ 実際の依存はプロジェクトの requirements ファイルに合わせてください。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境作成・依存インストール
   - see "必要条件" を参照

3. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 主要な必須項目:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - オプション: KABUSYS_ENV（development|paper_trading|live）、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL、OPENAI_API_KEY 等

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いで exit(1)

5. データディレクトリ
   - デフォルトの SQLite / DuckDB パスは `data/` 下にあります。プロジェクト起動時に自動作成される箇所がありますが、権限を確認してください。

6. OpenAI を利用する場合
   - 環境変数 OPENAI_API_KEY を設定（または score_news / score_regime の引数で渡す）

---

## 使い方（起動 / 実行）

各スクリプトはモジュールとして実行できます。

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ（SystemMonitor を定期実行）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き可:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視ループはプロジェクトルートの `data/stop_requested.flag` を検知すると終了します。
  - 監視 DB は Settings.sqlite_path（デフォルト: data/monitoring.db）を使用（環境にかかわらず本番 sqlite_path を参照）。

- 実行エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使われ、paper 用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に記録されます。
  - 起動中は `data/execution.pid` に PID を書きます。`data/stop_requested.flag` を置くと停止シグナルとなります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 範囲指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB のパスはオプション --db でも指定可能（優先順位: --db > env PAPER_TRADING_SQLITE_PATH > デフォルト）

- AI / リサーチ機能（ライブラリとして利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - kabusys.research.calc_momentum/ calc_volatility / calc_value など
  - DuckDB 接続（duckdb.connect(...)）を渡して使用します。

---

## 重要な環境変数（主なもの）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作モード:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - KILL_FLAG_CLEAR_ON_START: 1/0（本番で 1 は危険）

- DB パス:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB; デフォルト: data/paper_trading.db）

- ログ:
  - LOG_LEVEL（例: INFO）
  - LOG_DIR（デフォルト: logs/）

- 監視:
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、秒。デフォルト: 60）
  - KILL_FLAG_PATH（KillSwitch の flag パス、デフォルト: data/kill.flag）

- OpenAI:
  - OPENAI_API_KEY（AI 機能を使用する場合に必要）

- 自動 .env ロードの無効化:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込まなくなります（テスト向け）。

---

## 運用上の注意

- run_monitoring は本番 sqlite_path を使用します（監視は常に本番 DB に接続）。
- run_execution は KABUSYS_ENV に応じて本番/ペーパー DB を切り替えます（ペーパートレードはデータ分離）。
- Kill Switch（kabusys.monitoring.kill_switch）はドローダウンやポジション上限検出時に `data/kill.flag` を書き込み、ExecutionEngine に停止を促します。運用時は `KILL_FLAG_CLEAR_ON_START` の設定に注意してください。
- ログは `logs/<app_name>.log` に日次ローテーションで保存されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- OpenAI を呼ぶコードはリトライやフェイルセーフ処理を備えていますが、API キーとコスト管理には注意してください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / .env 自動読み込みロジック、Settings クラス
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py          — ログ設定ユーティリティ
    - process_priority.py       — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py          — SQLite 永続化層（テーブル作成・CRUD）
    - system_monitor.py         — システム状態・データ鮮度監視
    - trade_monitor.py          — （取引監視ロジック; 一部抜粋）
    - risk_monitor.py           — ドローダウン・ポジション上限監視
    - kill_switch.py            — kill.flag 管理
    - monitoring_engine.py      — 各 Monitor を束ねる実行エンジン
    - alert_manager.py          — （アラート送信ロジック: LINE など）
  - execution/
    - execution_engine.py       — ExecutionEngine 実装
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
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
    - news_nlp.py                — ニュース NLP（OpenAI 呼び出し含む）
    - regime_detector.py
    - __init__.py
  - tools/
    - paper_verification_report.py

- data/                         — デフォルトの DB / PID / flag 等（起動時に生成される）
- logs/                         — ログファイル出力先（デフォルト）

---

## 参考コマンド例

- .env の作成：
  - python -m kabusys.config_setup

- 設定チェック：
  - python -m kabusys.validate_config

- 監視プロセス起動（デフォルトポーリング60秒）：
  - python -m kabusys.run_monitoring

- 実行エンジン起動（ペーパートレード）：
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading レポート生成：
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

もし README に追加したい項目（CI、デプロイ手順、設定ファイルテンプレート、依存関係ファイル等）があれば教えてください。必要に応じてサンプル .env.example や運用チェックリストも作成できます。