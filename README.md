# KabuSys

日本株向け自動売買システムのコアライブラリ / 起動スクリプト群。  
このリポジトリは発注エンジン、監視、研究・ファクター計算、AIベースのニューススコアリング等の機能を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能を組み合わせて日本株のアルゴリズム取引運用を支援します。

- 実取引 / ペーパートレード用の ExecutionEngine（発注管理、リスク管理、照合）
- 監視コンポーネント（プロセス稼働監視、データ鮮度、リスク監視、Kill Switch）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算、セクター制約）
- 研究用モジュール（ファクター計算、将来リターン・IC 等）
- AI モジュール（ニュースの NLP スコアリング、レジーム判定。OpenAI を利用）
- 各種ユーティリティ（.env ウィザード、設定検証、ログ設定、プロセス優先度設定）
- 検証ツール（ペーパートレード用の検証レポート生成）

---

## 主な機能一覧

- Execution
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading モードを分離）
  - BrokerClientFactory により実ブローカー or MockBroker を選択
- Monitoring
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔を指定）
  - MonitoringEngine による各種モニタ（SystemMonitor / TradeMonitor / RiskMonitor）
  - Kill Switch（data/kill.flag）による安全停止
- Portfolio
  - 候補選定（score / rank ベース）
  - 等金額 / スコア重み / リスクベースの株数算出
  - セクター上限適用、レジーム乗数
- Research
  - ファクター（モメンタム / ボラティリティ / バリュー）計算（DuckDB を用いる）
  - 将来リターン、IC、統計サマリ
- AI
  - ニュースセンチメント（OpenAI）を用いたスコア付与（ai.score_news）
  - マクロニュース + ETF MA200 に基づく市場レジーム判定（ai.regime_detector）
- ツール
  - config_setup.py: 対話式で .env を作成
  - validate_config.py: 環境設定と config/*.yaml の検証
  - tools.paper_verification_report: ペーパートレードの検証レポート生成

---

## 前提条件（開発 / 実行環境）

- Python 3.9+
- 主要依存: duckdb, psutil, openai（AI 機能を使う場合）、PyYAML（validate_config で YAML 検証を行う場合）
- SQLite（標準ライブラリ）
- 実行環境によっては psutil の一部機能に管理者権限が必要になる場合あり

例（pip インストール）:
```
pip install duckdb psutil openai PyYAML
```
OpenAI 機能を使わない場合は `openai` は不要。

---

## セットアップ手順

1. レポジトリをクローン / 展開
2. 仮想環境を作成・有効化（推奨）
3. 依存パッケージをインストール（上記参照）
4. .env の作成（対話式ウィザード推奨）

対話式で .env を作る:
```
python -m kabusys.config_setup
```

設定を検証:
```
python -m kabusys.validate_config
# 警告もエラー扱いにする場合
python -m kabusys.validate_config --strict
```

自動 .env 読み込みについて:
- 起動時に .env / .env.local を自動で読み込みます（OS 環境変数より下位）。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 主要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: `development` | `paper_trading` | `live`（デフォルト: development）
  - paper_trading: MockBroker を使用し DB を分離
  - live: 実運用（要注意）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB）（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY（AI 機能利用時に必要）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（Execution 起動時に kill.flag を自動クリアするか。0=しない（推奨）/1=する）

PAPER_FILL_MODE（paper_trading モードでの約定挙動）:
- valid: "instant" | "partial" | "never" | "reject"（デフォルト: "instant"）

---

## 実行方法（簡易）

- 監視ループを起動（monitoring は本番 sqlite_path を使用する点に注意）
```
python -m kabusys.run_monitoring
# ポーリング間隔を環境変数で上書き
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

- ExecutionEngine を起動（Execution は env に応じて挙動が変わる）
```
python -m kabusys.run_execution
```
- Paper trading レポート生成:
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを指定する例:
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

停止 / フラグ操作:
- 監視 / 実行の両スクリプトはプロジェクトルート下の `data/stop_requested.flag` の存在を監視します。ファイルを作成すると次のポーリングで停止します（daemon スレッド等の挙動に依存）。
- Kill Switch は `data/kill.flag` を書き込み（監視コンポーネントが基準を満たしたとき）、ExecutionEngine はこのフラグで安全停止します。
- 実行時に PID を保存するファイル: `data/execution.pid`（run_execution 参照）

監視の注意点:
- run_monitoring は Monitoring のために常に本番用 sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に依存しない）。

---

## 開発者向け API とユーティリティ（抜粋）

- kabusys.config.Settings: 環境変数アクセスラッパー（プロジェクトルート検出、自動 .env ロード）
- kabusys.utils.logging_setup.setup_logging(app_name="execution"): ロギング統一設定（stdout + 日次ローテーション）
- kabusys.utils.process_priority.set_process_priority("high"|"normal"|"low")
- kabusys.portfolio: select_candidates / calc_equal_weights / calc_score_weights / calc_position_sizes / apply_sector_cap / calc_regime_multiplier
- kabusys.research: calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
  - DuckDB 接続（duckdb.connect(... )）を渡して利用する設計
- kabusys.ai.score_news(conn, target_date, api_key=None): ニューススコアリング（OpenAI API 必須）
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 起動前検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - monitoring_engine.py
    - risk_monitor.py
    - kill_switch.py
    - (その他: trade_monitor, alert_manager 等の実装想定)
  - utils/
    - logging_setup.py
    - process_priority.py

その他:
- data/ (既定のデータ格納ディレクトリ: DB, PID, flag など)
  - data/monitoring.db (デフォルトの監視 SQLite DB)
  - data/paper_trading.db (ペーパートレード用 DB)
  - data/kabusys.duckdb (DuckDB)
  - data/execution.pid
  - data/kill.flag
  - data/stop_requested.flag
- logs/（デフォルトのログ保存先）

---

## 運用上の注意 / 安全ガード

- 本番 (KABUSYS_ENV=live) では env の設定を慎重に確認してください。validate_config は本番用の追加チェックをします。
- KILL_FLAG_CLEAR_ON_START を `1` にすると起動時に kill.flag を自動で消しますが、本番では `0` を推奨します（誤起動による危険回避）。
- run_monitoring は環境に関わらず本番 sqlite_path を使用する仕様です。監視ログを分離したい場合は設定を見直してください。
- OpenAI API を使う処理はネットワークや API エラーを考慮して設計していますが、API key の管理（漏洩防止）や利用料に注意してください。
- ログディレクトリ作成に失敗した場合はコンソール出力にフォールバックします。

---

## よく使うコマンドまとめ

- .env 作成:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  ```
- 実行エンジン起動:
  ```
  python -m kabusys.run_execution
  ```
- 監視起動:
  ```
  python -m kabusys.run_monitoring
  ```
- ペーパートレード検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  ```

---

README はここまでです。必要であれば以下を追加できます:
- 具体的な依存パッケージの requirements.txt 例
- 実行時のログサンプル
- API 関数の利用例コードスニペット
- Docker / systemd ユニット定義例

どれを追加しますか？