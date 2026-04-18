# KabuSys

日本株自動売買システム（ライブラリ/実行スクリプト群）のリポジトリ README。

以下はこのコードベースの概要、機能、セットアップ、使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・調査・監視ツール群です。  
主な目的は以下：

- ExecutionEngine：発注・注文管理・リスク管理（本番 / ペーパートレード切替対応）
- Monitoring：システム状態・注文・リスクの監視、Kill Switch による自動停止
- Portfolio / Position Sizing：銘柄選定、配分、リスク調整、株数決定
- Research：ファクター計算、将来リターン計算、特徴量解析
- AI モジュール：ニュースを LLM（OpenAI）でスコアリング、レジーム判定
- ツール：設定ウィザード、設定検証、Paper Trading レポート生成 等

設計上のポイント：
- 設定は .env ファイルまたは環境変数で管理
- DuckDB（分析用）と SQLite（監視 / ペーパートレード用）を使用
- プロダクション / ペーパートレード（分離 DB）をサポート
- ロギングは統一されたセットアップ（console + 日次ローテートファイル）
- LLM 呼び出しはフェイルセーフ（リトライ・フォールバック）

---

## 主な機能一覧

- 環境設定
  - 対話式 .env ウィザード（kabusys.config_setup）
  - 起動前設定検証 CLI（kabusys.validate_config）
- 実行 / 発注
  - ExecutionEngine（kabusys.run_execution）: ブローカー抽象化、OrderManager、RiskManager、Reconciler 等
  - Paper trading モード（KABUSYS_ENV=paper_trading）では MockBrokerClient を使用し DB を分離
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor（kabusys.monitoring.*）
  - MonitoringEngine（ポーリング、アラート送信、Kill Switch 評価）
  - run_monitoring スクリプト（定期ポーリング、停止フラグ検出）
- ポートフォリオ構築
  - 候補選定、スコア重み、等金額配分、リスクベース配分、ポジションサイズ計算
  - セクター制限、レジーム乗数
- リサーチ
  - Momentum / Volatility / Value のファクター計算（DuckDB 経由）
  - 将来リターン、IC（Spearman）計算、統計サマリ
- AI（OpenAI）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
  - 市場レジーム判定（kabusys.ai.regime_detector）
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順（開発環境向け）

前提
- Python 3.9+（ソース中の型指定等を踏まえた目安）
- SQLite は Python 標準ライブラリで利用可能
- DuckDB は外部パッケージ

推奨依存パッケージ（一例）:
- duckdb
- psutil
- openai
- PyYAML（config 検証のため任意）
- その他（必要に応じて）

例: pip で最低限のパッケージを入れる
```
pip install duckdb psutil openai PyYAML
```

クローン / インストール
```
git clone <this-repo>
cd <this-repo>
# （任意）仮想環境を作る
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
# または必要パッケージだけ pip install ...
```

環境変数 / .env
- 既定でプロジェクトルートにある `.env` / `.env.local` を自動ロードします（CWD に依存しない検出ロジック）。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- 初期セットアップは対話式ウィザードが便利:
```
python -m kabusys.config_setup
```
このウィザードは `.env` ファイルを生成します（.env を絶対に Git へコミットしないでください）。

必須となる主な環境変数（最低限）
- JQUANTS_REFRESH_TOKEN（J-Quants API）
- KABU_API_PASSWORD（kabuステーション API）
- KABUSYS_ENV（development / paper_trading / live） ※デフォルト: development
- OPENAI_API_KEY（AI 機能を使う場合）

DB パス
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading モード時の専用 DB、デフォルト: data/paper_trading.db）

ログ
- デフォルトのログ出力先: logs/<app_name>.log（日次ローテーション、30日保持）
- 環境変数 LOG_DIR で変更可能。ログレベルは LOG_LEVEL。

---

## 使い方（主要コマンド）

設定検証
```
python -m kabusys.validate_config
# 警告を失敗にしたい場合:
python -m kabusys.validate_config --strict
```

設定ウィザード（.env 作成 / 更新）
```
python -m kabusys.config_setup
```

Execution Engine（実行）
- 実行例（コマンドライン）:
```
python -m kabusys.run_execution
```
- 挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、`PAPER_TRADING_SQLITE_PATH` に記録（本番 DB と完全分離）。
  - 起動時に `data/stop_requested.flag` が存在すると起動せず終了。
  - 実行中の停止は `data/stop_requested.flag` を作成するか、Monitoring が `data/kill.flag` を書き込むことでトリガーできます。
  - PID ファイル: `data/execution.pid`（Settings.pid_file_path で変更可能）

Monitoring（監視ループ）
```
python -m kabusys.run_monitoring
```
- オプション / 環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60 秒。無効値や 0 以下はデフォルトにフォールバック。
- 動作:
  - SystemMonitor / TradeMonitor / RiskMonitor を定期的に実行し、MonitoringDB（SQLite）へ記録。
  - `data/stop_requested.flag` を検出すると監視ループを終了。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視ログは共通 DB に保存される設計）。

Paper Trading 検証レポート
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを指定する場合:
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```
- 出力: 稼働率、注文成功率、送信率、レイテンシ（平均 / 最大 / P95）等のサマリと PASS/FAIL 判定

AI 機能（ニューススコア / レジーム判定）
- OpenAI API キーを用意し、`OPENAI_API_KEY` を設定してください。
- プログラム的に呼ぶ例:
```py
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
# ニューススコア
score_news(conn, target_date=date(2026,4,1), api_key="sk-...")
# レジーム判定
score_regime(conn, target_date=date(2026,4,1), api_key="sk-...")
```
- 注意: API 呼び出しはリトライ・フォールバックロジックを内包。API 未設定時は ValueError を投げます。

停止 / Kill Switch
- 手動停止: `data/stop_requested.flag` を作る（run_execution/run_monitoring はこれを検出して終了）。
- 自動 Kill: Monitoring の KillSwitch が `data/kill.flag` を書き、ExecutionEngine に停止を促します。
- Kill flag は `Settings.kill_flag_path`（デフォルト data/kill.flag）で参照されます。起動時に自動クリアする設定（KILL_FLAG_CLEAR_ON_START）を `1` にすると自動クリアされるため注意（本番では 0 推奨）。

---

## 主要設定項目（.env / 環境変数）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV: development | paper_trading | live (デフォルト development)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- LOG_DIR (ログ出力先ディレクトリ、デフォルト logs/)
- OPENAI_API_KEY（AI 機能使用時）
- MONITOR_POLL_INTERVAL（run_monitoring 用、秒）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリア、1=クリア 0=クリアしない）

---

## ディレクトリ構成（抜粋）

リポジトリ内で主要なファイル / モジュールを示します（`src/kabusys/...`）。

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス（環境変数取得・自動 .env ロードロジック）
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（PID / stop flag 連携）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py
      - SQLite スキーマ作成 & 永続化 API
    - system_monitor.py
      - CPU / メモリ / データ鮮度 / 実行プロセス監視
    - trade_monitor.py (実装ファイルあり)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (実装ファイルあり)
  - execution/
    - execution_engine.py (実装ファイルあり)
    - order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py
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
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

ファイルの多くはコメントで設計意図・副作用・フェイルセーフが明記されています。まずは `config_setup.py` → `validate_config.py` を実行して環境を整えることを推奨します。

---

## 開発 / 運用上の注意点

- 本番運用前に必ず `python -m kabusys.validate_config` で環境を検証してください。
- `.env` は機密情報を含むため Git にコミットしないでください。
- Paper trading（ペーパートレード）は本番 DB と完全分離（PAPER_TRADING_SQLITE_PATH を使用）。
- Monitoring は監視データのために共有の monitoring.sqlite（SQLITE_PATH）を使用します。
- OpenAI など外部 API を使う機能は API キーやコストに注意してください。API 呼び出しは多重化・課金要因になります。
- ログディレクトリが作成できない場合はファイル出力をスキップしてコンソールのみで動作します（ログセットアップにフェイルセーフあり）。
- プロセス優先度設定（psutil を使用）には権限が必要になる場合があります。失敗時は警告が出てスキップされます。

---

## サンプル起動フロー（初回）

1. 仮想環境作成 & 依存パッケージインストール
2. 環境設定ウィザード
   ```
   python -m kabusys.config_setup
   ```
3. 設定検証
   ```
   python -m kabusys.validate_config
   ```
4. ペーパートレードで実行（例）
   ```
   export KABUSYS_ENV=paper_trading
   python -m kabusys.run_execution
   ```
5. 監視プロセス起動（別プロセス・別端末で）
   ```
   python -m kabusys.run_monitoring
   ```
6. 終了（監視や実行を停止したい場合）
   - 手動停止: `touch data/stop_requested.flag`
   - Monitoring による自動 Kill: `data/kill.flag` が書かれると ExecutionEngine 側で停止処理されます

---

README は以上です。具体的な API 仕様や ExecutionEngine / OrderManager 等の詳細はソースの docstring を参照してください。必要であれば個別モジュールの詳しいドキュメント（使用例、関数シグネチャ、返り値例など）を別途作成します。