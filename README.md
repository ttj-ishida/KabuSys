# KabuSys

日本株向けの自動売買システム（ライブラリ＋実行スクリプト群）

本リポジトリは、データ基盤（DuckDB / SQLite）を用いたリサーチ・ファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、およびシステム監視（Monitoring）を含む自動売買基盤のコード群です。CLI ワークフローとして .env の対話的生成、設定検証、Execution/Monitoring の起動、Paper Trading の解析ツールなどを提供します。

---

## 主な特徴（機能一覧）

- 環境設定ウィザード（.env の対話式生成）：`kabusys.config_setup`
- 設定検証 CLI（.env と config/*.yaml のチェック）：`kabusys.validate_config`
- 発注エンジン起動スクリプト（ExecutionEngine）：`kabusys.run_execution`
  - `KABUSYS_ENV=paper_trading` 時は MockBroker を使用し、本番 DB と分離（data/paper_trading.db）
  - 停止フラグ（data/stop_requested.flag）で安全停止
- 監視ループ起動スクリプト（SystemMonitor）：`kabusys.run_monitoring`
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）
  - プロセス優先度を設定（High を試行）
- 監視コンポーネント
  - SystemMonitor（プロセス生存・CPU/メモリ/ディスク・データ鮮度）
  - TradeMonitor（滞留注文、約定異常価格）
  - RiskMonitor（ドローダウン・ポジション上限）
  - KillSwitch（条件に応じた `data/kill.flag` 出力）
  - MonitoringDB（SQLite にログ永続化）
- ポートフォリオ構築ユーティリティ（純粋関数）
  - 候補選定、等重／スコア重み、ポジションサイズ計算、セクターキャップ、レジーム乗数
- リサーチ（DuckDB 接続を受けてファクター計算）
  - momentum / volatility / value 等のファクター計算
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- AI モジュール（OpenAI を用いたニュース NLP / レジーム判定）
  - news_nlp.score_news：ニュースセンチメントを LLM によって算出して ai_scores に保存
  - regime_detector.score_regime：ETF の MA とマクロニュースを合成して市場レジームを判定
- ユーティリティ
  - process priority / cpu affinity 設定ユーティリティ（psutil ベース）
- ツール
  - Paper Trading 検証レポート生成：`kabusys.tools.paper_verification_report`

---

## 前提条件

- Python 3.10 以上（PEP 604 の型記法や union タイプ `|` を使用）
- 下記主要依存パッケージ（プロジェクトごとに必要なものは異なる）
  - duckdb
  - psutil
  - openai
  - PyYAML（config.yaml の検証に任意で使用）
- SQLite（Python 標準ライブラリに含まれます）

推奨：仮想環境（venv / pyenv など）を使用してください。

---

## インストール

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成・有効化
3. 必要パッケージをインストール

例（pip）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（requirements.txt があれば `pip install -r requirements.txt` を使用）

---

## 環境設定 (.env)

対話式ウィザードで `.env` を生成・更新できます。

```
python -m kabusys.config_setup
```

ウィザードでは J-Quants / kabuステーション の認証情報、DB パス、実行環境（development / paper_trading / live）などを設定します。

主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading の場合の専用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading の fill 振る舞い: instant|partial|never|reject、デフォルト: instant）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- OPENAI_API_KEY（AI モジュールを使う場合に必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用、任意）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag をクリアするか：0/1、本番では 0 推奨）

設定を保存したら、検証を実行してください。

```
python -m kabusys.validate_config
```

必要に応じて `--strict` を指定すると警告もエラー扱いになります。

---

## 実行方法（使い方）

1. データディレクトリ作成
```
mkdir -p data
```

2. 発注エンジン（ExecutionEngine）起動
- 通常実行（設定済みの .env に従う）:
```
python -m kabusys.run_execution
```
- Paper Trading（.env 内で KABUSYS_ENV=paper_trading を設定）では MockBroker を使用し、`data/paper_trading.db` に記録されます。

挙動:
- プロセス優先度を「high」へ設定しようとします（psutil 権限が必要）。
- 起動時に `data/stop_requested.flag` が存在すれば起動をキャンセルします。
- 実行中は `data/execution.pid` に PID を書きます（停止時は削除）。
- 停止は `data/stop_requested.flag` の作成、または KillSwitch（監視コンポーネント）が `data/kill.flag` を書き込むことで行えます。

3. 監視ループ起動
```
python -m kabusys.run_monitoring
```
- `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60 秒）。
- 監視は常に本番 sqlite_path を参照します（モニタリング DB は環境にかかわらず本番の監視 DB を使う設計）。
- 停止は `data/stop_requested.flag` を作ることで行います。

4. Paper Trading 検証レポート生成
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
```
- `--db` で DB パスを直接指定可能。指定がない場合は `PAPER_TRADING_SQLITE_PATH` 環境変数、さらに未指定なら `data/paper_trading.db` を使います。

5. AI（ニュース NLP / レジーム判定）
- OpenAI API キー（`OPENAI_API_KEY`）が必要です。
- プログラム的に使う例:
```py
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
conn = duckdb.connect("data/kabusys.duckdb")
score_news(conn, date(2026, 4, 1), api_key="sk-...")
```

6. ライブラリ的利用（リサーチ・ポートフォリオ）
- 例（ファクター計算）:
```py
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, date(2026,4,1))
vols = calc_volatility(conn, date(2026,4,1))
vals = calc_value(conn, date(2026,4,1))
```

- 例（ポートフォリオ構築）:
```py
from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes

candidates = select_candidates(buy_signals, max_positions=10)
weights = calc_score_weights(candidates)
orders = calc_position_sizes(weights, candidates, portfolio_value=100_000_000, available_cash=50_000_000,
                             current_positions={}, open_prices=price_map)
```

---

## 停止・制御用フラグ

- data/stop_requested.flag
  - 実行スクリプト（run_execution, run_monitoring）が監視している停止フラグ（任意のファイル）。作成するとループを抜けて終了します。
- data/kill.flag
  - Monitoring の KillSwitch が書き込む停止フラグ。ExecutionEngine 起動時に Kill Switch の存在で自動停止されることを想定しています（本番保護用）。
- data/execution.pid
  - ExecutionEngine が自身の PID を書き込むファイル。SystemMonitor はこの PID の存在とプロセス生存確認を行います。

---

## 環境変数一覧（主要）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- KABU_API_BASE_URL: kabu API のベース URL
- DUCKDB_PATH: DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite
- PAPER_FILL_MODE: instant | partial | never | reject
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- LOG_LEVEL: ログレベル
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- PID_FILE_PATH / KILL_FLAG_PATH: ファイルパスの上書き
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1）

（詳細は `kabusys.config.Settings` を参照）

---

## ディレクトリ構成（概要）

- src/kabusys/
  - __init__.py — パッケージのメタ情報
  - config.py — 環境変数 / .env の自動読み込み、Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - ai/
    - news_nlp.py — ニュースセンチメント取得（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py — SQLite ベースの永続化層（テーブル作成 / CRUD）
    - system_monitor.py — システム状態監視（CPU/メモリ/ディスク/データ鮮度）
    - trade_monitor.py — 注文滞留・約定異常の検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — KillSwitch ロジック（kill.flag 書き込み）
    - monitoring_engine.py — 各 monitor の纏め
    - alert_manager.py — （アラート管理、実装ファイルがプロジェクトに存在）
  - execution/ (発注ロジック関連 — OrderRepository, Engine, BrokerFactory など)
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・制限・丸め
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value の計算
    - feature_exploration.py — 将来リターン・IC・統計
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - data/ （アプリが使用するデータディレクトリ、実行環境で作成）
    - *.db, .flag, .pid など

---

## 運用上の注意

- 本番運用（KABUSYS_ENV=live）の設定は慎重に扱ってください。`validate_config` は本番ガード（LINE 通知の確認、KILL_FLAG_CLEAR_ON_START の警告など）を実行します。
- .env は機密情報を含むため、絶対に Git 等にコミットしないでください。
- OpenAI を使用する機能は API 呼び出し料金とレート制限に注意してください。ネットワークエラーや 5xx はリトライを行う設計ですが、完全な可用性は保証しません。
- process priority / cpu affinity の操作は OS と権限に依存します。権限エラーは警告でスキップされます。
- DuckDB / SQLite のファイルパスは .env で調整可能です。Paper Trading は本番 DB と完全に分離するよう設計されています。

---

この README はコードベースの概要と主要な使い方をまとめたものです。詳細な設計やアルゴリズム（PortfolioConstruction.md / StrategyModel.md 等の参照が想定されているドキュメント）は別途参照してください。必要であれば README を補足して運用手順やデプロイ手順（systemd / Docker / CI）も追記できます。