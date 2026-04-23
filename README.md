# KabuSys — 日本株自動売買システム

KabuSys は日本株の自動売買システム向けに設計されたモジュール群です。  
主なコンポーネントとして、注文実行エンジン（ExecutionEngine）、システム/注文/リスク監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）、AI ベースのニューススコアリング／レジーム判定などを含みます。

バージョン: 0.1.0

---

## 概要

- 実行エンジンは本番・ペーパートレードモードをサポートし、ブローカークライアントの差替えで振る舞いを切り替えます（`KABUSYS_ENV=paper_trading` では Mock を使用して DB を分離）。
- 監視モジュールはシステムの稼働状況・データ鮮度・注文状況・リスク（ドローダウン・ポジション上限）を定期的にチェックし、必要に応じてアラートや Kill Switch を発動します。
- ポートフォリオ構築・ポジションサイジング・セクター制約などは純粋関数群で実装され、単体テストや研究用途に適しています。
- AI モジュールは OpenAI（gpt-4o-mini 等）を用いてニュースセンチメントやマクロセンチメントを算出し、レポジトリに書き込みます（APIキーが必要）。
- 開発支援ツールとして `.env` を対話的に作るウィザード (`config_setup`) と設定検証 CLI (`validate_config`)、ペーパートレードの検証レポート生成ツールがあります。

---

## 機能一覧

- Execution
  - ExecutionEngine の起動スクリプト（run_execution.py）
  - 本番 / ペーパートレードの DB 分離（paper_trading 用 SQLite）
  - リスクマネージャ、注文管理、調整・突合せ処理（内部コンポーネント）
- Monitoring
  - SystemMonitor（CPU/メモリ/Disk、データ鮮度、プロセス監視）
  - TradeMonitor / RiskMonitor（注文滞留やドローダウン等の監視）
  - KillSwitch（条件を満たすと kill.flag を書込）
  - MonitoringEngine（ポーリングループ）
  - 永続化用 SQLite スキーマ（monitoring_db）
- Portfolio
  - 候補選定、等金額/スコア加重の重み算出
  - セクター制約、レジーム乗数
  - ポジションサイズ算出（lot 単位、リスクベース等）
- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 将来リターン計算、IC（Information Coefficient）算出、統計サマリ
- AI
  - ニュースを LLM でスコアリングして ai_scores に保存（news_nlp）
  - マクロ＋価格指標から日次レジーム判定（regime_detector）
- Utilities / Tools
  - ロギング設定ユーティリティ（コンソール + 日次ファイルローテーション）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ペーパートレード検証レポート生成ツール（tools/paper_verification_report.py）

---

## 動作環境 / 依存

- Python 3.10+
- 必要パッケージ（代表例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml の内容検証を行う場合。必須ではない）
- 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib 等

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```
※requirements.txt は本リポジトリに付属していないため、プロジェクトで使うパッケージに応じてインストールしてください。

---

## セットアップ手順

1. リポジトリのルートで仮想環境を作成・有効化し、必要パッケージをインストールする（上記参照）。

2. data / logs ディレクトリを作成（多くの処理がここにファイルを書きます）:
```bash
mkdir -p data logs
```

3. 環境変数設定 (.env) を作成:
```bash
python -m kabusys.config_setup
```
ウィザードに従って `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD` などの必須パラメータを入力してください。`.env` は絶対に Git にコミットしないでください。

4. 設定の検証:
```bash
python -m kabusys.validate_config
# 警告を致命的に扱いたい場合:
python -m kabusys.validate_config --strict
```

5. （オプション）config/*.yaml を生成するスクリプトがある場合はそれで生成してください（validate_config は存在確認を行います）。該当スクリプトはプロジェクトの scripts ディレクトリ等にある想定です。

---

## 環境変数（主要）

- KABUSYS_ENV: 実行環境。`development` | `paper_trading` | `live`（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring.py で使用）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

---

## 使い方

### ExecutionEngine を起動する
本番・ペーパートレードは `KABUSYS_ENV` に依存します。ペーパートレード時は DB が分離され、実際の発注は行われません。

例（ペーパートレード）:
```bash
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```

例（開発）:
```bash
export KABUSYS_ENV=development
python -m kabusys.run_execution
```

停止方法:
- 実行プロセスを正常に停止したい場合、プロジェクトルートの `data/stop_requested.flag` を作成すると、起動中の監視ループや ExecutionEngine が検知して安全に停止します。
- 監視モジュール（Monitoring）により重大リスクが検出されると KillSwitch が `data/kill.flag` を書き込みます（ExecutionEngine 側は kill.flag の存在を参照して停止する実装がある想定です）。

### Monitoring を起動する
監視ループを開始します。デフォルトのポーリング間隔は 60 秒ですが、環境変数で上書きできます。

```bash
# 例: ポーリング間隔を 30 秒に設定
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```

注意:
- Monitoring の DB 接続は本番 sqlite_path（`SQLITE_PATH`）を使用します（環境にかかわらず監視 DB は本番 DB を参照します）。
- Monitoring は `data/stop_requested.flag` を検知するとループを終了します。

### 設定検証
```bash
python -m kabusys.validate_config
```
`--strict` を付けると警告も失敗扱いになります。

### .env ウィザード
```bash
python -m kabusys.config_setup
```

### ペーパートレード検証レポート
ペーパートレード DB を参照して検証レポートを出力します。
```bash
# デフォルト DB: data/paper_trading.db
python -m kabusys.tools.paper_verification_report

# 期間指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# DB パス明示
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

---

## ファイル / ディレクトリ構成（概観）

- src/
  - kabusys/
    - __init__.py
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - run_monitoring.py              — Monitoring ポーリングループ起動スクリプト
    - config.py                      — 環境変数 / 設定読み込み・Settings
    - config_setup.py                — .env 対話式ウィザード
    - validate_config.py             — 設定検証 CLI
    - tools/
      - paper_verification_report.py — ペーパートレード検証レポート
    - ai/
      - news_nlp.py                  — ニュース NLP スコアリング
      - regime_detector.py           — マクロ + MA によるレジーム判定
    - monitoring/
      - monitoring_db.py             — SQLite スキーマ + 永続化 API
      - system_monitor.py            — CPU/メモリ/ディスク/データ鮮度監視
      - risk_monitor.py              — ドローダウン・ポジション上限監視
      - kill_switch.py               — フラグファイルの作成・確認
      - monitoring_engine.py         — 複数モニタの協調実行
      - (その他: trade_monitor.py, alert_manager.py 等の監視周辺モジュール)
    - portfolio/
      - portfolio_builder.py         — 候補選定、重み計算
      - position_sizing.py           — 株数計算・集約キャップ処理
      - risk_adjustment.py           — セクター制約・レジーム乗数
    - research/
      - factor_research.py           — モメンタム/ボラ/バリュー計算
      - feature_exploration.py       — 将来リターン、IC、統計サマリ
    - utils/
      - logging_setup.py             — 一貫したログ設定ユーティリティ
      - process_priority.py          — プロセス優先度 / CPU affinity
    - (その他: execution パッケージ、data/ 参照、config/ デフォルト yaml 等)

ルートに `data/`（DB・フラグファイル等）および `logs/`（ログファイル）が作られます。`.env` はプロジェクトルートに置きます。

---

## 運用上の注意 / トラブルシューティング

- ファイル/ディレクトリのパーミッションに注意してください。ログディレクトリや data ディレクトリに書き込み権がないとファイルハンドラの作成やフラグファイルの書き込みに失敗する場合があります。
- psutil による優先度設定や CPU affinity はプラットフォームによって動作が異なり、権限不足で設定できない場合は警告を出してスキップします。
- OpenAI を用いる機能は API キー（OPENAI_API_KEY）が必須です。API 呼び出しはレート制限・一時的なネットワーク障害を想定してリトライやフォールバックを行う設計ですが、キーがないと実行できません。
- ペーパートレード時は DB を分離しているため、本番データへの影響はありません（`PAPER_TRADING_SQLITE_PATH` を確認してください）。
- 監視・キルスイッチ周りはフラグファイル（`data/kill.flag`, `data/stop_requested.flag`）を利用するため、運用時にはこれらファイルの扱い・クリア手順を運用ルールとして明確にしてください。`KILL_FLAG_CLEAR_ON_START` により起動時に自動クリアする設定もありますが、本番では `0` を推奨します。

---

## 参考コマンドまとめ

- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

README はプロジェクトの起動と運用のための最小限の案内をまとめたものです。各モジュール（ExecutionEngine、OrderManager、Reconciler、RiskManager、TradeMonitor 等）の詳細はソースコードの docstring / コメントを参照してください。必要であれば各コンポーネントの設計ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）に基づく詳細ドキュメントも作成できます。