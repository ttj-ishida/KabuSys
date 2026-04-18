# KabuSys

日本株自動売買システムの軽量実装。  
本リポジトリは取引実行エンジン、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AIベースのニュース評価などのコンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的で設計されたモジュール群です。

- データベース（DuckDB / SQLite）を用いたリサーチ・分析
- シグナルに基づくポートフォリオ構築と発注ロジック
- 実際の売買実行（kabuステーション API を想定）とペーパートレード分離
- 実行状況・システム状態・リスク監視（Kill Switch 等）
- ニュースを LLM（OpenAI）でスコアリングし意思決定に活用
- 運用を支援する CLI（.env ウィザード・設定検証・レポート生成）

設計方針の一部:
- 環境依存設定は .env（または環境変数）で管理
- 設定検証やウィザードを提供し起動前に問題を検出
- Paper Trading は本番 DB と完全分離（別 SQLite）
- LLM 呼び出しは失敗してもフェイルセーフで継続する設計

---

## 主な機能一覧

- 設定管理
  - .envの自動読み込み（プロジェクトルートを検出）
  - config_setup: 対話式 .env ウィザード（`python -m kabusys.config_setup`）
  - validate_config: 設定検証 CLI（`python -m kabusys.validate_config`）

- 実行エンジン
  - ExecutionEngine を起動するスクリプト（`python -m kabusys.run_execution`）
  - Paper trading（`KABUSYS_ENV=paper_trading`）は MockBroker を使用し `data/paper_trading.db` に記録

- 監視（Monitoring）
  - System / Trade / Risk 各モニター
  - Kill Switch（`data/kill.flag`）による ExecutionEngine の停止指示
  - 監視ループ起動スクリプト（`python -m kabusys.run_monitoring`）
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）
  - 監視ログは SQLite（デフォルト `data/monitoring.db`）に永続化

- リサーチ & ポートフォリオ
  - Factor 計算（Momentum / Value / Volatility）
  - ファクターの統計・IC 計算
  - 候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数等

- AI（OpenAI）連携
  - ニュース記事の銘柄別センチメント評価（`kabusys.ai.news_nlp`）
  - マクロニュース + ETF MA200 を使った市場レジーム判定（`kabusys.ai.regime_detector`）
  - OpenAI API キーは `OPENAI_API_KEY`（環境変数）で指定

- 運用支援ツール
  - Paper Trading 検証レポート生成（`python -m kabusys.tools.paper_verification_report`）

---

## 必要要件（概略）

- Python 3.10+
- 必須パッケージ（代表例）
  - duckdb
  - psutil
  - openai（AI 機能利用時）
- 任意
  - PyYAML（`validate_config` が config/*.yaml の中身検証を行う場合）

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（プロジェクトに requirements.txt があればそれを使ってください）

---

## セットアップ手順

1. リポジトリをクローンし仮想環境を作成・有効化します。

2. 依存パッケージをインストールします（上記参照）。

3. 初期設定（.env）を作成します（推奨: ウィザードを利用）:
```bash
python -m kabusys.config_setup
```
ウィザードは対話式で .env を生成します。生成後は `python -m kabusys.validate_config` で検証できます。

4. 必須環境変数（例）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）

その他の設定（省略時はデフォルト）:
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用、デフォルト: data/paper_trading.db）
- LOG_LEVEL, LOG_DIR 等

5. データディレクトリの準備:
通常はスクリプトが必要なディレクトリを自動作成しますが、事前に `data/` や `logs/` を作っておくと権限問題を回避できます。

---

## 使い方（代表的なコマンド）

- 設定ウィザード（.env 作成・更新）
```bash
python -m kabusys.config_setup
```

- 設定検証
```bash
python -m kabusys.validate_config
# --strict を付けると警告も FAIL 扱い
python -m kabusys.validate_config --strict
```

- Execution エンジン起動（メイン発注プロセス）
```bash
python -m kabusys.run_execution
```
動作概要:
- 起動時にプロセス優先度を "high" に設定し、SQLite / DuckDB に接続します。
- KABUSYS_ENV=paper_trading の場合、専用の paper_trading DB を使用します（`PAPER_TRADING_SQLITE_PATH`）。
- 起動直後に `data/stop_requested.flag` が存在すると起動せず終了します。
- 実行中に `data/stop_requested.flag` を作成するとエンジンに停止を要求します。
- 実行時に PID ファイル（デフォルト `data/execution.pid`）を書きます。

- Monitoring 起動（監視ループ）
```bash
# ポーリング間隔を 30 秒に上書きする例
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
動作概要:
- SystemMonitor, TradeMonitor, RiskMonitor 等を初期化してポーリングを行います。
- `MONITOR_POLL_INTERVAL` で間隔を指定（デフォルト 60 秒）。
- 監視はモードに関係なく production の sqlite_path を使用して監視データを蓄積します。
- `data/stop_requested.flag` を検知するとループを終了します。

- Paper Trading 検証レポート生成
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを指定する場合
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```
出力: 稼働率、注文成功率、レイテンシ等のサマリと PASS/FAIL 判定。

- AI 関連（ライブラリ利用）
  - ニューススコアリング: `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`
  - レジーム判定: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

注意: 上記関数は DuckDB 接続オブジェクトと target_date（datetime.date）を受け取ります。OpenAI を使う場合は `OPENAI_API_KEY` 環境変数を設定するか、api_key 引数で渡してください。

---

## 運用に関する重要点

- 環境（KABUSYS_ENV）
  - development / paper_trading / live のいずれかを設定。`live` は本番のため慎重に。
  - `paper_trading` は MockBroker を使用し、本番 DB と分離されます。

- Kill Switch / stop flag
  - Kill Switch（自動判定で発動）: `data/kill.flag` を書き込みます。ExecutionEngine は起動時や監視でこのファイルを検出して停止します（`Settings.kill_flag_path` 参照）。
  - 手動停止要求: `data/stop_requested.flag` を書くことで run_* スクリプトに停止を促します（両方ともプロジェクトルートの `data/` 下がデフォルト）。

- ログ
  - ログは stdout と 日次ローテートされたファイル（logs/<app_name>.log）に出力されます。`LOG_DIR` / `LOG_LEVEL` で制御可能。
  - ログ設定は `kabusys.utils.logging_setup.setup_logging()` から統一的に行われます。

- DB マイグレーション
  - monitoring DB 初期化関数（`init_monitoring_db`）は冪等で、必要なカラムがない場合は ALTER TABLE で追加します。

---

## ディレクトリ構成（主要ファイル）

（`src/kabusys/` 以下を想定）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度・CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — 監視用 SQLite 永続化層
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （trade 監視ロジック）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - kill_switch.py         — kill.flag 書き込みロジック
    - alert_manager.py       — （アラート送信管理）
  - execution/
    - execution_engine.py    — 実行エンジンコア（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュースセンチメント (OpenAI)
    - regime_detector.py     — マクロ + MA200 による市場レジーム判定

（上記は主要ファイル・責務の一覧です。実際のファイルはさらに細分化されています）

---

## 開発 / テストのヒント

- 自動環境読み込み:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に .env を自動読み込みします。テスト時に自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

- ローカルで Paper Trading を試す:
  - `KABUSYS_ENV=paper_trading` をセットして `python -m kabusys.run_execution` を起動。DB は `data/paper_trading.db`（`PAPER_TRADING_SQLITE_PATH` で上書き可）。

- OpenAI を使った機能をテストする際は、API 呼び出し部分（`_call_openai_api` など）をモックすることで外部依存を排除できます（ユニットテスト向け）。

---

## ライセンス・注意事項

- .env ファイルは機密情報（APIキー等）を含むため、絶対にバージョン管理に含めないでください（config_setup のヘッダにもその旨が記載されています）。
- 本コードはサンプル実装のため、実運用の前にリスク管理、例外処理、外部 API エラーハンドリング、セキュリティ検証などを十分に行ってください。

---

必要であれば README に含める実行例（systemd / Docker compose 用の簡易手順）、より詳細な設定項目説明、各モジュールの API ドキュメント（関数引数・戻り値）を追加できます。どの情報を優先して拡充しますか？