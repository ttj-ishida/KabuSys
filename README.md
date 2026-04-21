# KabuSys

日本株向け自動売買システムのコアライブラリおよび起動スクリプト集です。  
本リポジトリには、取引実行エンジン、監視モジュール、ポートフォリオ構築・ポジションサイズ計算、研究用ファクター計算、ニュース NLP（OpenAI）連携などが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要コンポーネントで構成されています。

- ExecutionEngine（発注・約定・リスク管理） — run_execution.py で起動
- Monitoring（システム健全性 / 注文・リスク監視 / Kill switch） — run_monitoring.py で起動
- Portfolio（候補選定、重み算出、ポジションサイズ計算、セクター制約等）
- Research（ファクター計算、将来リターン、IC 計算など、DuckDB ベース）
- AI（ニュースの NLP 評価、レジーム判定：OpenAI API を使用）
- Tools（ペーパートレード検証レポート生成スクリプト等）
- utils（ログ設定、プロセス優先度制御等）
- config（環境変数読み込み・設定）

設計方針の一部：
- DuckDB / SQLite を用いたローカル DB 保持（分析用と監視ログを分離）
- 本番環境（live）とペーパートレード（paper_trading）を明確に分離
- OpenAI を利用する部分は API キーを明示的に指定（環境変数参照）
- 起動スクリプトは python -m kabusys.<module> で実行可能

---

## 機能一覧

主な機能（抜粋）：

- 実行エンジン
  - Broker クライアントの抽象化（paper_trading 時は MockBrokerClient を使用）
  - OrderManager / RiskManager / Reconciler による発注制御
  - 実行時 PID 管理・停止フラグ対応
- 監視
  - CPU / メモリ / ディスク / プロセス稼働の定期監視
  - 注文ログ、ポジション、リスクログ、ダッシュボードの永続化（SQLite）
  - Kill Switch（閾値超過で data/kill.flag を書込む）
  - アラート送信基盤（LINE などの外部通知を想定）
- ポートフォリオ構築
  - シグナルに基づく候補選定、等配分・スコア加重配分
  - セクターキャップ、レジーム乗数の反映
  - ポジションサイズ算出（単元株丸め、aggregate cap、コストバッファ）
- 研究・分析
  - Momentum / Volatility / Value 等の因子計算（DuckDB）
  - 将来リターン、IC、統計サマリー、rank ユーティリティ
- AI（OpenAI）
  - ニュース記事を集約して銘柄ごとのセンチメントを算出（gpt-4o-mini 想定）
  - 市場レジーム判定（ETF MA とマクロニュースの合成）
  - リトライ・レスポンスバリデーション・スコアクリップ等の堅牢化
- ツール
  - ペーパートレード検証レポート生成（成功率・稼働率・レイテンシ指標など）
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）

---

## 必要環境 / 依存パッケージ（例）

Python 3.9+ を想定しています。主な外部依存：

- duckdb
- psutil
- openai
- PyYAML（設定検証で YAML チェックを行う場合）
- （その他、実行環境に応じた Broker クライアント依存など）

インストール例（仮の requirements.txt がない場合）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

※ 実際の requirements はプロジェクトで管理している場合があるので、該当ファイルがあればそちらを利用してください。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します。

2. 依存パッケージをインストールします（上記参照）。

3. 初期設定 (.env) の作成（対話式ウィザード）:

```bash
python -m kabusys.config_setup
```

このウィザードは .env ファイルを作成・更新します。必須項目（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は入力必須です。

4. 設定検証:

```bash
python -m kabusys.validate_config
# 警告もエラー扱いにしたい場合:
python -m kabusys.validate_config --strict
```

5. デフォルトの DB パスやログディレクトリは .env に設定した値、または以下のデフォルトになります:
- DuckDB: data/kabusys.duckdb
- SQLite (監視): data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db
- ログ: logs/<app_name>.log

初回起動時に必要なディレクトリ（data/, logs/ 等）は起動スクリプトが自動作成しますが、パーミッションに注意してください。

---

## 使い方

主要な起動方法を示します。

- 監視ループ（SystemMonitor のポーリング）

  MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60 秒）。

```bash
# 例: 30秒間隔で監視を実行
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

停止方法:
- プロジェクトルートの data/stop_requested.flag を作成すると run_monitoring/run_execution は検知して停止します（既に存在する場合は起動をスキップする挙動あり）。
- kill.flag（data/kill.flag）は ExecutionEngine 停止のためのフラグです。KillSwitch がトリガーすると書き込まれます。

- 実行エンジン（ExecutionEngine）起動

  KABUSYS_ENV の値で挙動が変わります。`paper_trading` の場合は MockBroker を使い、data/paper_trading.db に記録します（本番 DB と分離）。

```bash
# 本番（live）または development/paper_trading を .env で設定してから実行
python -m kabusys.run_execution
```

- ペーパートレード検証レポート生成（ツール）

```bash
# デフォルト DB を使用
python -m kabusys.tools.paper_verification_report

# 期間指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# DBパス指定
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

- .env の対話式作成（再掲）

```bash
python -m kabusys.config_setup
```

- 設定検証（再掲）

```bash
python -m kabusys.validate_config
```

- AI（ニューススコア／レジーム判定）の利用（ライブラリ関数）

Python スクリプトから DuckDB 接続を渡して呼び出します（OpenAI API キーは引数または環境変数 OPENAI_API_KEY）。

例（簡略）:

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
score_regime(conn, target_date=date(2026, 4, 10), api_key="sk-...")
```

注意:
- OpenAI 呼び出しにはネットワークと API キーが必要です。
- LLM 呼び出しはレート制限・タイムアウトに対してリトライ/フェイルセーフが組み込まれていますが、コストと失敗時の影響を理解した上で実行してください。

---

## 重要な環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

推奨 / オプション:
- KABUSYS_ENV — 実行環境（development, paper_trading, live）デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視ログ SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- PAPER_FILL_MODE — ペーパートレード約定モード（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒。run_monitoring 用。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリア（"1" で有効。注意: 本番では推奨しない）

.env の初期作成には `python -m kabusys.config_setup` を利用してください。

---

## 停止・Kill の挙動

- 停止フラグ: data/stop_requested.flag
  - run_monitoring / run_execution は起動ループ内でこのファイルの存在をチェックし、検出したら安全に停止します。
  - 起動前に既に存在する場合、run_execution は起動をスキップします。

- Kill Switch: data/kill.flag
  - Monitoring の KillSwitch が閾値を満たすとこのファイルを書き込み、ExecutionEngine 停止のトリガーとなります。
  - `Settings.kill_flag_clear_on_start` が "1" に設定されていると、ExecutionEngine 起動時に自動的にクリアする挙動があります（本番では通常 "0" を推奨）。

---

## ディレクトリ構成（主要ファイル）

以下は主要モジュールに限定した構成の概略です。実際は src/kabusys 以下にモジュール群があります。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py         # （実装あり）
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py         # （実装あり）
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - risk_adjustment.py
      - position_sizing.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - monitoring/
      - ... (上記)
  - config/
    - *.yaml (system_config.yaml 等のテンプレート / 実体ファイル)
  - data/
    - monitoring.db (SQLite)  ← デフォルトパス
    - kabusys.duckdb         ← デフォルト DuckDB
    - paper_trading.db       ← paper_trading 用（存在する場合）
    - kill.flag
    - stop_requested.flag
    - execution.pid
  - logs/
    - execution.log
    - monitoring.log
    - ... 日毎ローテーション

---

## 開発者向けメモ / トラブルシュート

- ログ:
  - ロギングは kabusys.utils.logging_setup.setup_logging を通して統一されます。ログファイルはデフォルトで `logs/<app_name>.log` に日次ローテーションで保存されます。
  - ログディレクトリ作成に失敗するとファイル出力は無効化され、コンソール出力のみになります。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は idempotent にテーブルを作成します。既存 DB に新カラムがない場合は自動で ALTER TABLE による追加を試みます。

- プロセス優先度 / CPU affinity:
  - psutil を用いて優先度設定を試みますが、権限不足や未対応 OS の場合は警告をログに残してスキップします。

- OpenAI 呼び出し:
  - ネットワークエラーや 429/5xx に対して指数バックオフのリトライが組み込まれています。それでも失敗した場合はフェイルセーフでスコア 0.0 を採用する等の処理がなされています。
  - 大量の API 呼び出しはコストがかかるため、バッチサイズや呼出頻度は注意して設定してください。

---

README は以上です。必要があれば、セットアップの詳細（systemd ユニットファイル例、Dockerfile、CI 用テスト手順、requirements.txt の推奨内容など）を追加で作成します。どの情報が必要か教えてください。