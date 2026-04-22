# KabuSys

日本株向け自動売買システムのコアライブラリ群（ライブラリ + 起動スクリプト群）

このリポジトリは、取引実行エンジン、監視（Monitoring）、ポートフォリオ構築、調査（Research）、AI ベースのニュース NLP、各種ユーティリティを含むモジュール群を提供します。設計方針として「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアスの回避」「ログ・監視・Kill Switch による安全ガード」を重視しています。

---

## 主要機能（抜粋）

- ExecutionEngine 起動スクリプト（run_execution）  
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、ペーパートレード用 DB（data/paper_trading.db）へ記録
  - リスク管理、OrderManager、Reconciler などの組み立てロジックを内蔵

- Monitoring（監視）  
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセスの監視
  - TradeMonitor: 注文の滞留・約定異常等の検知（モジュールは同梱）
  - RiskMonitor: ドローダウン・ポジション上限の監視とアラート記録
  - KillSwitch: 条件に応じて data/kill.flag を作成して ExecutionEngine を停止させる仕組み
  - 独自の SQLite ベース MonitoringDB（スキーマ初期化・読み書きユーティリティ）

- ポートフォリオ構築（Portfolio）  
  - 候補選定、等比重/スコア重み付け、ポジションサイジング（リスクベース）、セクター上限、レジーム乗数等

- Research（調査・因子計算）  
  - モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB 接続を受け取り SQL + Python で実装）
  - 特徴量探索、将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI モジュール（OpenAI）  
  - news_nlp: ニュース記事を LLM でセンチメント化して ai_scores テーブルへ書き込み
  - regime_detector: ETF（1321）MA200 とマクロニュースセンチメントを合成して市場レジーム（bull/neutral/bear）を判定・永続化

- ユーティリティ  
  - ロギング設定（stdout + 日次ローテーションファイル）: kabusys.utils.logging_setup
  - プロセス優先度・CPU affinity 設定: kabusys.utils.process_priority
  - .env ウィザード: kabusys.config_setup（対話式）
  - 設定検証 CLI: kabusys.validate_config
  - Paper Trading 検証レポート: kabusys.tools.paper_verification_report

---

## 動作要件（推奨）

- Python 3.9+（ソースは型アノテーションを使用）
- 主要依存ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイル検証時）
- その他: SQLite（組み込み）、ネットワークアクセス（kabuステーション API / OpenAI API 利用時）

requirements.txt が無い場合は手動でインストールしてください（例）:
```
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト

2. 仮想環境を作成して有効化（推奨）
```
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
.venv\Scripts\activate     # Windows
```

3. 依存パッケージをインストール
```
pip install -r requirements.txt
# あるいは必要なパッケージを個別にインストール
pip install duckdb psutil openai pyyaml
```

4. .env を作成（対話式ウィザード推奨）
```
python -m kabusys.config_setup
```
ウィザードで入力するとプロジェクトルートに `.env` を生成します。生成後、設定を検証してください：
```
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```

---

## 主要な環境変数（代表例）

- JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレード時の約定動作（instant/partial/never/reject）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

（.env の雛形は config_setup.py の出力を参照してください）

---

## 実行方法

- 設定ウィザード（対話式）:
```
python -m kabusys.config_setup
```

- 設定検証:
```
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```

- 監視ループ起動（Monitoring）:
```
python -m kabusys.run_monitoring
```
- 補足:
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックします。
  - Monitoring は KABUSYS_ENV に関わらず設定された本番用 `SQLITE_PATH` を使用して監視 DB（monitoring.db）を更新します。
  - 停止はプロジェクトルートの `data/stop_requested.flag` を作成することで行えます（スクリプトは存在を監視して安全終了します）。

- 実行エンジン起動（ExecutionEngine）:
```
python -m kabusys.run_execution
```
- 補足:
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に記録され、本番 DB と完全に分離されます。
  - 起動時に `data/stop_requested.flag` が既にある場合は起動しません。
  - 実行プロセスの PID は `data/execution.pid` に書き込まれます。
  - 停止シグナルは Monitoring の KillSwitch が `data/kill.flag` を書き込むことで送られます（Execution 側はこのフラグを検出して停止を行う仕様です）。

- Paper Trading 検証レポート生成:
```
python -m kabusys.tools.paper_verification_report
# 期間指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB 指定
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

- AI スコアリング（ニュース NLP）／レジーム判定 の利用例（プログラムから呼び出す）
  - news_nlp: `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`
  - regime_detector: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
  - いずれも OpenAI API キーが必要（引数で渡すか `OPENAI_API_KEY` 環境変数を設定）

---

## 停止・Kill Switch の仕組み（概略）

- Monitoring は RiskMonitor 等を評価し、KillSwitch が条件（例: ドローダウン閾値超過、ポジション上限超過）を満たすと `data/kill.flag` に理由を記録します。
- ExecutionEngine は `kill.flag` の存在を確認して安全にセッションを停止します。
- 物理的な強制停止（即時停止）ではなく、安全に終了させるためにこれらのフラグと永続化（DB）を使った協調設計になっています。
- `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動的にクリアしますが、本番環境では 0 を推奨します。

---

## 使い方（開発者向け／よく使うコマンド）

- パッケージ内の関数を直接使う（例: ポートフォリオ計算）
```py
from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
candidates = select_candidates(buy_signals, max_positions=10)
weights = calc_equal_weights(candidates)
sizes = calc_position_sizes(weights, candidates, portfolio_value=100_000_000, available_cash=50_000_000, current_positions={}, open_prices={...})
```

- DuckDB を使った研究（例: ファクター計算）
```py
import duckdb
from kabusys.research import calc_momentum
conn = duckdb.connect("data/kabusys.duckdb")
results = calc_momentum(conn, target_date=date(2026, 4, 15))
```

- Monitoring の単発実行（テスト用）
  - MonitoringEngine を生成して `run_once()` を呼べば 1 サイクルだけ実行します（ユニットテスト向け）。

---

## ディレクトリ構成（主なファイル）

プロジェクトのソースは `src/kabusys` に配置されています。主要なファイルとディレクトリの概観:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ロギング設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite ベースの監視 DB ユーティリティ
    - monitoring_engine.py   — 各 Monitor を束ねるループ
    - system_monitor.py      — システム状態／データ鮮度監視
    - trade_monitor.py       — 注文監視（滞留／異常）
    - risk_monitor.py        — ドローダウン／ポジション上限監視
    - kill_switch.py         — kill.flag 制御
    - alert_manager.py       — （アラート送信のラッパー。実装を参照）
  - execution/                — Execution 関連（Engine, OrderManager, BrokerFactory 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュースを LLM でスコア化
    - regime_detector.py     — 市場レジーム判定
  - tools/
    - paper_verification_report.py

（実際のファイル数や詳細はリポジトリのツリーを参照してください）

---

## 開発・運用上の注意点

- .env は機密情報を含みます。絶対に Git 等にコミットしないでください（config_setup.py にも注意喚起コメントあり）。
- 本番環境（KABUSYS_ENV=live）では設定を十分に確認してください。validate_config の --strict モードが有用です。
- OpenAI API を利用するモジュールは通信障害やレート制限を考慮してリトライやフェイルセーフ（スコア 0.0 フォールバック等）を実装していますが、API キーとコスト管理には注意してください。
- Monitoring と Execution の DB 分離（ペーパートレード用 DB）は意図的に設計されています。運用時に DB パスやアクセス権限を誤らないよう注意してください。
- ログはデフォルトで `logs/` に日次ローテーションで保存されます。ログディレクトリの作成に失敗した場合は標準出力のみで稼働します。

---

この README はコードベースの主要構成と運用時に必要となる操作の概要を示します。詳細な API 仕様や内部モジュールの使い方は該当ソース（各モジュールの docstring）を参照してください。必要であれば README に追記します — どの部分を詳しく書くか教えてください。