# KabuSys

日本株向け自動売買システムのリファレンス実装（モジュール群・ユーティリティ群）。  
このリポジトリは、戦略開発・ペーパートレード検証・実運用に必要なコンポーネントを分離して提供します。

主な設計方針：
- コンポーネントは責務分離（監視 / 実行 / ポートフォリオ構築 / リサーチ / AI）で実装
- 本番とペーパートレードの DB を分離
- 外部 API 呼び出し部分は抽象化・フェイルセーフ設計（LLM 呼び出しリトライ等）
- .env による環境設定と対話式ウィザード / 設定検証 CLI を提供

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルート検出）・対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
- 実行エンジン起動スクリプト
  - run_execution: ExecutionEngine を起動。`KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し、ペーパートレード用 DB に記録
- 監視プロセス
  - run_monitoring: SystemMonitor をポーリングして状態を記録。MONITOR_POLL_INTERVAL で間隔変更可
  - MonitoringEngine: System / Trade / Risk の各 Monitor を束ね、Kill Switch とアラート発行
  - MonitoringDB: SQLite に監視ログ・トレードログ・ポジション等を永続化（冪等な初期化・マイグレーション含む）
  - KillSwitch: ドローダウン等で `data/kill.flag` を書き込み ExecutionEngine に停止命令を送る
- ポートフォリオ構築（純粋関数）
  - 銘柄選定（スコア順）、等配分・スコア重み配分、リスク調整（セクター制限・レジーム乗数）、ポジションサイズ計算（単元丸め・集約キャップ）
- リサーチ / ファクター計算（DuckDB を利用）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）等の統計ユーティリティ
- AI モジュール
  - news_nlp: OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別スコア）
  - regime_detector: ETF（1321）の MA200 とマクロニュースを合成して市場レジーム判定
  - API 呼び出しはリトライ・バリデーション等を実装（フェイルセーフで失敗時はスキップまたは中立値）
- ツール
  - paper_verification_report: ペーパートレード DB から検証レポートを生成（稼働率、注文成功率、レイテンシ等）

---

## セットアップ手順

前提
- Python 3.10 以上（typing 構文等を利用）
- OS: Linux / macOS / Windows（ただし一部プロセス優先度/CPU affinity は OS 依存の動作）

推奨: 仮想環境を作成してパッケージを分離してください。

例（Unix 系）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
# 必要なパッケージをインストール
pip install duckdb psutil openai PyYAML
# （requirements.txt がある場合は `pip install -r requirements.txt`）
```

主な外部依存:
- duckdb — 分析用 DB
- psutil — プロセス / リソース監視
- openai — LLM 呼び出し（news_nlp / regime_detector）
- PyYAML — 設定ファイル検証（validate_config で使用）

環境変数（主要なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: `development` | `paper_trading` | `live`（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（上書き）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時）

.env 作成（対話式ウィザード）
```bash
python -m kabusys.config_setup
# 完成後に python -m kabusys.validate_config で検証
python -m kabusys.validate_config
python -m kabusys.validate_config --strict  # 警告も失敗扱いにする
```

注意:
- `.env` はリポジトリにコミットしないでください（シークレット情報を含む）
- プロジェクトはルートに `.git` または `pyproject.toml` があることで自動的にプロジェクトルートを検出し .env を読み込みます

---

## 使い方

1. 設定の準備
   - `python -m kabusys.config_setup` で .env を作成
   - `python -m kabusys.validate_config` で設定検証

2. 監視プロセス起動（常駐でポーリング）
```bash
# ポーリング間隔を変更したい場合
export MONITOR_POLL_INTERVAL=30  # 秒
python -m kabusys.run_monitoring
```
- 注意: 監視は常に「本番用の sqlite_path」を使用します（設定の KABUSYS_ENV に関わらず）。停止させるには `data/stop_requested.flag` を作成してください（起動スクリプトはこのファイルを監視して終了します）。

3. 実行エンジン起動（ExecutionEngine）
```bash
python -m kabusys.run_execution
```
- `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使い、ペーパートレード用 DB（`PAPER_TRADING_SQLITE_PATH` またはデフォルト `data/paper_trading.db`）に記録します。
- 実行開始時に `data/stop_requested.flag` が既にある場合は起動せず終了します。
- 停止は `data/stop_requested.flag` を作成することで通知され、エンジンは安全に停止します。
- `Settings.kill_flag_path`（デフォルト `data/kill.flag`）は Kill Switch 用フラグです。Kill Switch が発動すると ExecutionEngine の停止を促します。

4. Paper Trading 検証レポート
```bash
# デフォルト DB を使用
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# DB を明示する場合
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

5. AI モジュール（プログラムから呼ぶ）
- kabusys.ai.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- いずれも `OPENAI_API_KEY` 環境変数、もしくは引数で API キーを渡します。
- AI 呼び出しはリトライ・バリデーション処理があり、失敗時は安全側の値で継続する設計です。

ログ
- ログは `kabusys.utils.logging_setup.setup_logging` を通じて設定されます。
- デフォルトは stdout と `logs/<app_name>.log`（日次ローテーション、30 日保持）に出力されます。
- `LOG_DIR` 環境変数でログディレクトリを変更できます。

運用に関するフラグ / ファイル
- data/stop_requested.flag — run_monitoring / run_execution の停止フラグ
- data/kill.flag — KillSwitch が書き込むファイル（ExecutionEngine 停止用）
- data/execution.pid — ExecutionEngine の PID ファイル（run_execution が管理）

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / Settings
- config_setup.py — .env 対話ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

src/kabusys/utils/
- logging_setup.py — ログ設定ユーティリティ
- process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
- __init__.py

src/kabusys/monitoring/
- monitoring_db.py — SQLite 永続化層（初期化・CRUD）
- system_monitor.py — CPU/メモリ/ディスク・データ鮮度監視
- trade_monitor.py — （発注トレード監視、ファイルには存在）
- risk_monitor.py — ドローダウン・ポジション上限監視
- kill_switch.py — Kill Switch ロジック
- monitoring_engine.py — 各 Monitor を束ねる実行ループ
- alert_manager.py — アラート送信（LINE など）※ファイルに依存する実装

src/kabusys/execution/
- broker_factory.py — BrokerClient の生成（本番 / モックの分岐）
- execution_engine.py — 発注セッション管理
- order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 実行ロジック周り

src/kabusys/portfolio/
- portfolio_builder.py — 候補選定・重み計算
- position_sizing.py — 株数決定、集約キャップ
- risk_adjustment.py — セクター上限・レジーム乗数
- __init__.py

src/kabusys/research/
- factor_research.py — Momentum / Volatility / Value 計算（DuckDB 使用）
- feature_exploration.py — 将来リターン / IC / 統計サマリー
- __init__.py

src/kabusys/ai/
- news_nlp.py — ニュースセンチメント（OpenAI）
- regime_detector.py — レジーム判定（MA200 + マクロニュース）
- __init__.py

src/kabusys/tools/
- paper_verification_report.py — ペーパートレード検証レポート生成

データ / ログ / 一時ファイル（プロジェクトルート）
- data/monitoring.db (SQLite, デフォルト)
- data/paper_trading.db (ペーパートレード用 SQLite)
- data/kabusys.duckdb (DuckDB)
- data/kill.flag, data/stop_requested.flag, data/execution.pid
- logs/<app_name>.log

---

## 主要設定例 (.env の抜粋例)

例:
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

注意: 上のシークレットは必ず外部に公開しないでください。

---

## 運用・開発上の注意点

- 本番稼働時は KABUSYS_ENV=live を設定し、LINE 周りや Kill Switch の挙動を十分確認してください（validate_config の live ガードを参照）。
- run_monitoring は監視専用 DB（monitoring.db）を用いて稼働を記録します。監視は常に本番 sqlite_path を参照する設計です。
- run_execution は環境に応じて DB を切り替え（paper_trading は専用 DB）し、本番データと切り離すことで安全性を高めています。
- AI（OpenAI）を使う機能は API 呼び出し回数・料金が発生します。ローカル開発や CI ではモック化してテストすることを推奨します。
- process_priority, cpu_affinity の設定は OS 権限に依存します。権限不足時は警告が出て処理は継続されます。

---

## テスト / 開発

- 各 pure function（portfolio, research, utils）は外部副作用が少ないためユニットテストが書きやすい設計です。
- AI 呼び出しはユニットテストではモック（`unittest.mock.patch`）することを推奨します。ソース内にもモックを想定した差し替え可能関数が用意されています。

---

この README はコードベースから抽出した主要情報をまとめたものです。追加の API や内部設計の詳細は該当モジュール（src/kabusys/ 以下）の docstring を参照してください。必要であれば別途「運用手順」や「開発ガイド」を作成します。