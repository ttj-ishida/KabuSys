# KabuSys

日本株向け自動売買システム（ライブラリ & 実行スクリプト群）

---

## プロジェクト概要

KabuSys は日本株アルゴリズム売買のためのモジュール群と簡易実行スクリプトを含むリポジトリです。  
主な目的は以下の通りです。

- ファクター計算・研究（DuckDB を利用）
- ポートフォリオ構築（候補選定、ウェイト計算、ポジションサイズ算出）
- Execution エンジン（本番 / ペーパートレード切替）
- 監視（システム状態・注文・リスク監視）および Kill Switch
- AI（ニュース NLP によるセンチメント評価、レジーム判定）
- ユーティリティ（設定ウィザード、設定検証、レポート生成 等）

この README はローカル開発・運用を始めるための手順と各機能の概要をまとめたものです。

---

## 主な機能一覧

- portfolio: 候補選定・重み付け・ポジションサイズ決定（等金額 / スコア / リスクベース）
- research: DuckDB 上でのファクター計算（モメンタム・バリュー・ボラティリティ等）と統計解析ツール
- execution: ブローカー抽象化（本番・ペーパートレード）、ExecutionEngine の起動スクリプト
- monitoring: system / trade / risk の監視、kill.switch の評価、ログ永続化（SQLite）
- ai: ニュースの LLM (OpenAI) を使ったセンチメントスコア付与、レジーム検出
- tools: ペーパートレード検証レポート生成スクリプト 等
- utils: ロギング設定、プロセス優先度 / CPU affinity 設定 等

---

## 必要な依存パッケージ（例）

少なくとも下記のパッケージが必要です（バージョンは適宜調整してください）:

- Python 3.10+
- duckdb
- psutil
- openai (AI 機能を利用する場合)
- PyYAML （config 検証で YAML 内容をチェックする場合に必要）

インストール例:

```bash
pip install duckdb psutil openai PyYAML
```

（プロジェクトに requirements.txt がある場合はそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. Python 仮想環境を作成して依存をインストール
3. 環境変数設定 (.env) を用意する

.env の生成を対話式で行う場合:

```bash
python -m kabusys.config_setup
```

このウィザードは `.env` を作成／更新します。作成後、次の検証を行ってください:

```bash
python -m kabusys.validate_config
# 警告も FAIL 扱いにしたい場合
python -m kabusys.validate_config --strict
```

自動ロードについて:
- `kabusys.config` はプロジェクトルート（.git または pyproject.toml を含む場所）を探索し、`.env` と `.env.local` を自動で読み込みます。
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 主要な環境変数（.env で設定）

必須・重要なもの:

- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- OPENAI_API_KEY — OpenAI を利用する場合に必要（ai モジュール）

任意（デフォルトを使用可能）:

- DUCKDB_PATH (`data/kabusys.duckdb`)
- SQLITE_PATH (`data/monitoring.db`)
- PAPER_TRADING_SQLITE_PATH (`data/paper_trading.db`)
- LOG_LEVEL (`INFO`)
- LOG_DIR (`logs/`)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（本番での通知）

Kill / Stop 関連:

- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（0=無効 / 1=有効）

ログディレクトリや DB パスは環境変数で上書きできます。詳細は `kabusys.config.Settings` を参照してください。

---

## 使い方 (実行例)

基本的にパッケージモジュールとして実行します。

- 環境設定ウィザード（.env 作成）

```bash
python -m kabusys.config_setup
```

- 設定検証

```bash
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```

- ExecutionEngine 起動（本番 / ペーパートレードは KABUSYS_ENV に依存）

例：ペーパートレードで起動（MockBroker 使用、DB は data/paper_trading.db）

```bash
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```

例：本番想定（注意して使用）

```bash
export KABUSYS_ENV=live
python -m kabusys.run_execution
```

- Monitoring 起動（ポーリング監視ループ）

デフォルトは 60秒間隔。環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可（1 以上）:

```bash
# 30秒間隔で監視
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```

- 停止フラグ / 強制停止
  - 実行エンジン停止シグナルは `data/kill.flag` を書き込むことで送出します（KillSwitch が監視・評価）。
  - 監視スクリプト等を即時停止したい場合は `data/stop_requested.flag` を作ると監視・実行ループが検出して終了します。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると Execution 起動時に `kill.flag` を自動で削除します（本番では 0 推奨）。

- ペーパートレード検証レポート

```bash
# 指定期間を与えて実行
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# DB を手動指定する場合
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

- AI / レジーム判定・ニューススコアリング（ライブラリ利用）

これらは CLI ではなく関数呼び出しを想定しています。例:

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
conn = duckdb.connect("data/kabusys.duckdb")
n = score_news(conn, target_date=date(2026,4,10), api_key="YOUR_OPENAI_KEY")
print(f"scored {n} codes")
```

注意: OpenAI API 呼び出し関係は API キーとネットワークが必要です。失敗時はフェイルセーフが働き、一部機能はスキップされます。

---

## 実行時のログ

- ログはデフォルトで stdout と `logs/<app_name>.log` に出力されます（`kabusys.utils.logging_setup.setup_logging`）。
- ローテーションは日次、30 日分のバックアップ保持。
- ログレベルは `LOG_LEVEL` 環境変数または `setup_logging(level=...)` で変更可能。

---

## 注意点・挙動メモ

- ExecutionEngine は KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用して `data/paper_trading.db` へ記録します（本番 DB と分離）。
- Monitoring は環境にかかわらず本番用 sqlite_path（`SQLITE_PATH`）を利用する設計になっています。
- 一部のモジュール（AI 系、YAML 検証）は外部ライブラリに依存します（openai, PyYAML）。
- プロセス優先度設定（high / normal / low）は `psutil` を利用して行われます。設定に失敗しても警告が出るだけで継続します。

---

## ディレクトリ構成（抜粋）

以下は主要なファイル / モジュール構成の抜粋です。

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / 設定管理
    - config_setup.py              — .env 対話式ウィザード
    - validate_config.py           — 設定検証 CLI
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — SystemMonitor 起動スクリプト
    - tools/
      - paper_verification_report.py
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
      - trade_monitor.py (存在を仮定)
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py (存在を仮定)
    - execution/
      - execution_engine.py (存在を仮定)
      - broker_factory.py (存在を仮定)
      - order_manager.py (存在を仮定)
      - order_repository.py (存在を仮定)
      - reconciler.py (存在を仮定)
      - risk_manager.py (存在を仮定)
    - utils/
      - logging_setup.py
      - process_priority.py

（実際のリポジトリには上記以外にも補助モジュールや追加ファイルがあります。変更があれば随時参照してください。）

---

## 開発・運用のヒント

- .env は決してソース管理にコミットしないでください（config_setup.py のヘッダにも注意書きがあります）。
- `python -m kabusys.validate_config` を CI あるいはデプロイ前チェックに組み込むと設定漏れを早期に検出できます。
- 本番では `KABUSYS_ENV=live` を設定する前に LINE 通知や kill flag の設定を入念に確認してください（validate_config が警告出力します）。
- DuckDB は高速な分析用 DB として設計されています。ファクター計算や research ワークフローでは DuckDB に十分なデータをロードしてから実行してください。

---

この README はコードベース（主要スクリプト・モジュール）からの抜粋ドキュメントです。より詳細な実装仕様や設計背景はソース内 docstring や別途用意された `*.md` ファイル（存在する場合）を参照してください。質問や特定の機能の使い方を知りたい場合は、用途に応じて具体的に聞いてください。