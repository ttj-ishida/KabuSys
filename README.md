# KabuSys

日本株向けの自動売買システム用ライブラリ／起動スクリプト群です。本リポジトリは取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築・リサーチ、AIベースのニュース解析等を含むモジュール群で構成されています。

## 概要
- 株式のシグナル生成・ポートフォリオ構築・発注管理を行う Execution コンポーネント
- システム稼働状況、注文・ポジション・リスク監視を行う Monitoring コンポーネント（kill-switch を含む）
- DuckDB を用いたファクター計算・リサーチユーティリティ
- OpenAI を使ったニュースセンチメント（AI）と市場レジーム判定の補助モジュール
- ペーパートレード用の分離された DB / モックブローカーサポート
- 各種ユーティリティ（ログ設定、プロセス優先度設定、構成ウィザード、構成検証、検証レポート出力 等）

## 主な機能
- Execution
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアント抽象化（MockBroker を含む）
  - リスク管理（最大ポジション比率、投下上限、サーキットブレーカー等）
  - 注文管理・再整合（reconciler）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、実行プロセス監視
  - TradeMonitor: 注文滞留・約定異常等の検出（trade_logs）
  - RiskMonitor: ドローダウン、ポジション上限監視と kill.flag 発行
  - MonitoringEngine: 各モニタの統合ポーリング、AlertManager 連携（必要に応じて追加実装）
- Portfolio（純粋関数）
  - 候補選定、等金額／スコア加重、ポジションサイズ計算、セクターキャップ、レジーム乗数
- Research（DuckDBベース）
  - モメンタム / ボラティリティ / バリューファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI
  - ニュースを OpenAI に渡して銘柄ごとのセンチメントを算出し ai_scores に格納
  - マクロニュース + ETF MA 指標を合わせた市場レジーム判定（bull/neutral/bear）
- ツール
  - .env 作成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

## 必要条件（推奨）
- Python 3.10+
- 以下の主要依存パッケージ（プロジェクトの requirements.txt があればそれを使用してください）
  - duckdb
  - psutil
  - openai
  - (任意) PyYAML — config/*.yaml の検証に使用
- SQLite（標準ライブラリで利用可能）
- ネットワーク接続（kabuステーション API / OpenAI を利用する場合）

例（仮に requirements.txt がある場合）:
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

依存関係を手動で入れる場合の例:
```
pip install duckdb psutil openai
# PyYAML が必要なら:
pip install pyyaml
```

## セットアップ手順（手短に）
1. リポジトリをクローン
2. 仮想環境を作成して依存をインストール
3. .env を作成（推奨: ウィザードを使用）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは J-Quants トークン、kabu API パスワードなどの入力を促します。
4. 設定検証（起動前に推奨）
   ```
   python -m kabusys.validate_config
   ```
   --strict オプションで警告も FAIL 扱いにできます。
5. DB/ログ用ディレクトリ（デフォルトは project_root/data と project_root/logs）が自動作成されますが、必要に応じて事前に作成しても構いません。

## 主な環境変数（代表）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) — デフォルト: INFO
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db（KABUSYS_ENV=paper_trading の場合使用）
- PAPER_FILL_MODE — instant | partial | never | reject（paper_trading 時の挙動）
- OPENAI_API_KEY — OpenAI を利用する機能で必要
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒）。run_monitoring で参照。デフォルト 60 秒。
- KILL_FLAG_CLEAR_ON_START — 本番での自動クリアは危険（0 推奨）

サンプル .env の一部（config_setup によって生成されます）:
```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

## 実行方法（主要スクリプト）
- ExecutionEngine を起動（発注実行）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
  - 起動時に data/stop_requested.flag が存在する場合は起動を中止します。
  - プロセス優先度が `high` に設定されます。
  - 実行中の PID は data/execution.pid に書き込まれます。

- Monitoring を起動（ポーリング監視）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）。
  - 監視は Settings に依らず本番 sqlite_path を使用して永続化します（monitoring db）。
  - stop は data/stop_requested.flag の作成で行えます（監視ループが検知して終了します）。

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  ```

- .env ウィザード（対話式）
  ```
  python -m kabusys.config_setup
  ```

- Paper Trading 検証レポート出力（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  または DB 指定:
  ```
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

## 停止・Kill Switch
- 強制停止（Execution 停止）には kill_switch（data/kill.flag）を用います。KillSwitch は RiskMonitor 等の判定により flag を書き込みます。
- ローカル的に監視・実行スクリプトを停止したい場合は data/stop_requested.flag を作成すると、run_execution / run_monitoring が検知して安全停止します。
- Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると起動時に自動クリアしますが、本番では 0 を推奨します。

## ログ
- ログはデフォルトで logs/ ディレクトリに日次ローテーションで保存されます（ログファイル名は app_name: execution.log / monitoring.log 等）。
- ログ出力設定は kabusys.utils.logging_setup.setup_logging を通じて統一されています。
- 標準出力にも同じログが出力されます（StreamHandler を stdout に設定）。

## API キー / 外部サービス
- OpenAI を利用するモジュール（kabusys.ai.news_nlp / kabusys.ai.regime_detector）は OPENAI_API_KEY を参照します。未設定の場合は ValueError を送出する場合があります。
- kabuステーション API を利用する場合は KABU_API_PASSWORD 等の設定が必要です。
- J-Quants 用のトークン（JQUANTS_REFRESH_TOKEN）も環境変数で設定してください。

## 使い方（ライブラリとして）
- ポートフォリオ構築関数群:
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes
  - apply_sector_cap, calc_regime_multiplier
  - これらは副作用を持たない純粋関数として設計されています（ユニットテストが容易）。
- リサーチ関数群（DuckDB 接続を渡して呼び出す）:
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank
- AI スコアリング:
  - kabusys.ai.score_news(conn, target_date, api_key=None)

例（研究用途）:
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, date(2026, 4, 11))
```

## ディレクトリ構成（抜粋）
（project_root/src に package がある想定）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings
  - config_setup.py            — .env ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト
  - execution/                 — 発注・注文管理関連（broker_factory 等）
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         — アラート送信処理（実装はプロジェクト依存）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py              — OpenAI を使用したニューススコアリング
    - regime_detector.py       — マクロ + ETF MA によるレジーム判定
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                      — 実行時に生成される DB / flag / pid 等（例: data/monitoring.db）

プロジェクトルートには config/*.yaml（テンプレート）や .env.example などが置かれている想定です。

## 注意点・運用上のポイント
- KABUSYS_ENV=live の際は特に注意して設定を検証してください（validate_config の警告を確認）。
- 本番 DB とペーパートレード DB は明確に分離されています（paper_trading モード）。
- OpenAI を利用する場合は API レートやエラーに対するリトライ処理が組み込まれていますが、API キー管理は慎重に行ってください。
- ログディレクトリ・データディレクトリの権限や容量管理（DuckDB/SQLite のサイズ拡大）に注意してください。
- kill.flag / stop_requested.flag の扱いは運用ルールを明確にしておくことを推奨します（特に本番環境）。

---

この README は本リポジトリに含まれるスクリプト・モジュールの主要な使い方および構成をまとめたものです。詳細な API や追加設定は各モジュールのドキュメント（ソースコードの docstring）を参照してください。必要であれば各コンポーネントごとの詳細な運用手順やデプロイ手順を別途作成できます。