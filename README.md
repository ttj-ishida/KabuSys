# KabuSys

日本株向け自動売買システムのライブラリ/実行スクリプト群です。  
本リポジトリは次を含みます：戦略・ポートフォリオ構築、実行エンジン（ExecutionEngine）起動スクリプト、監視（Monitoring）・Kill Switch、研究用ユーティリティ、AI ニューススコアリングなど。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買に必要なコンポーネント群を提供します。主な役割は以下の通りです。

- 戦略/リサーチ: ファクター計算、特徴量解析、将来リターン計算など（DuckDB を用いる）
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ算出、セクター制約など
- Execution: ブローカークライアントを用いた発注ロジック（paper_trading 環境時はモックを使用）
- Monitoring: システム稼働状況・注文ログ・リスク（ドローダウン・ポジション上限）監視、Kill Switch
- AI 支援: ニュース NLP によるセンチメントスコアリング、レジーム判定（OpenAI API を使用）
- ツール: Paper Trading の検証レポート生成など

設計注記:
- 設定は .env（環境変数）で管理。`config_setup.py` による対話式ウィザードあり。
- DuckDB / SQLite を用いたデータ永続化。paper_trading は本番 DB と分離された専用 SQLite を使用可能。
- ログは stdout と日次ローテーションファイル（logs/*.log）に出力。

---

## 機能一覧

主な機能（抜粋）:

- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- ExecutionEngine 起動（本番/ペーパートレード対応）: python -m kabusys.run_execution
- Monitoring 起動（定期ポーリング）: python -m kabusys.run_monitoring
- Kill Switch：リスク条件で `data/kill.flag` を書き込み ExecutionEngine を停止
- Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
- ポートフォリオ構築ユーティリティ（等分配・スコア加重・リスクベース等）
- リサーチモジュール（モメンタム、ボラティリティ、バリュー等）
- AI モジュール（ニュースセンチメント、レジーム判定：OpenAI API を利用）

---

## 前提条件

- Python 3.9+
- SQLite（標準ライブラリ）
- 外部パッケージ（最低限）:
  - duckdb
  - psutil
  - openai（AI 機能使用時）
  - PyYAML（設定検証で YAML ファイルのパースを行う場合）

例（venv 作成後）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（プロジェクトに requirements.txt がないため、必要に応じて追加してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成・依存パッケージのインストール（上を参照）

3. ディレクトリ作成（data, logs 等）
   ```bash
   mkdir -p data logs
   ```

4. 対話式で .env を作成
   ```bash
   python -m kabusys.config_setup
   ```
   - 必須: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`
   - KABUSYS_ENV の選択: `development` / `paper_trading` / `live`

5. 設定検証（任意）
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL として扱う場合:
   python -m kabusys.validate_config --strict
   ```

6. AI 機能を使う場合は環境変数 `OPENAI_API_KEY` を設定（または関数引数で渡す）

---

## 主要な環境変数（よく使うもの）

- KABUSYS_ENV: 実行環境 (development | paper_trading | live)。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーションのベース URL（デフォルト localhost）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- LOG_DIR: ログディレクトリ（デフォルト: logs）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE: PaperTrading 時の fill モード（instant | partial | never | reject）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動でクリアするか（0/1）

---

## 使い方

### 監視ループの起動（Monitoring）

デフォルトで本番 sqlite_path を使用して監視を行います（MONITOR_POLL_INTERVAL で間隔を変更可能）。

```bash
# 環境変数例（必要に応じて .env に設定）
export MONITOR_POLL_INTERVAL=60

# 起動
python -m kabusys.run_monitoring
```

- 監視中に停止を要求するにはプロジェクトルートの `data/stop_requested.flag` を作成します（存在を検知してループを抜けます）。
- Monitoring は MonitoringDB（SQLite）に system_status / trade_logs / risk_logs / positions / dashboard を記録します。

### Execution エンジンの起動

本番/ペーパートレードに応じて DB が変わります（paper_trading は設定された paper_sqlite_path を使用）。

```bash
# paper_trading で起動する例
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution

# 本番（live）
export KABUSYS_ENV=live
python -m kabusys.run_execution
```

- 実行中の強制停止は `data/stop_requested.flag` を作成することで要求できます。ExecutionEngine は起動時に `data/execution.pid` を作成します。
- Kill Switch（`data/kill.flag`）が存在すると起動を抑止したり実行を停止します（設定により起動時に自動クリア可）。

### Paper Trading 検証レポート

ペーパートレード用 SQLite を元に検証レポートを生成します。

```bash
# デフォルト DB: data/paper_trading.db
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# 別ファイルを指定
python -m kabusys.tools.paper_verification_report --db /path/to/db.sqlite
```

主要な判定基準（レポート内で使用）:
- 稼働率（uptime） >= 99.0%
- 注文成功率 (fill rate) >= 90.0%
- 送信率 (send rate) >= 95.0%
- P95 レイテンシ <= 200 ms

### AI 機能（ニュース NLP / レジーム判定）

OpenAI API を使用します。事前に `OPENAI_API_KEY` をセットしてください。

- ニューススコア（ai_scores への書き込み）:
  - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
- レジーム判定:
  - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注: API 呼び出しはリトライ・失敗フォールバックが組み込まれていますが、API キーは必須です。

---

## 停止・Kill Switch

- data/stop_requested.flag: run_monitoring / run_execution が定期ループ中に存在を検出すると安全に終了します。手動で作成してプロセスを停止できます。
- data/kill.flag: Monitoring の KillSwitch ロジックがリスク条件を満たした場合に書き込まれ、ExecutionEngine に停止指示を出します。
- 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると `kill.flag` を自動クリアします（本番では 0 推奨）。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要なファイル・モジュールと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数/.env の読み込みと Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py — 統一的なログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — 監視用 SQLite テーブルの初期化と簡易 DB ラッパ
    - system_monitor.py — システム / データ鮮度監視
    - trade_monitor.py — (注文監視: 省略したファイルもあり)
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch 実装
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — （通知管理、LINE 等の統合用）
  - execution/  — ExecutionEngine 関連（order_manager, broker_factory, risk_manager 等）
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 発注株数計算、投下資金スケール
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum, value, volatility）
    - feature_exploration.py — IC / 将来リターン / 統計サマリ
  - ai/
    - news_nlp.py — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py — マクロ + MA200 でレジーム判定（OpenAI）
  - tools/
    - paper_verification_report.py — ペーパートレード評価レポート生成

---

## 開発者向けメモ / 注意点

- .env は決して Git にコミットしないでください（config_setup の注記参照）。
- validate_config は .env のプレースホルダ（`*_here` など）を検出して警告します。live 環境では特に注意して設定してください。
- DuckDB/SQLite のファイルパスは Settings で管理され、環境に依らず監視は本番 sqlite_path を参照します（run_monitoring の挙動）。
- paper_trading 環境では発注は MockBrokerClient によって分離され、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録されます。
- OpenAI 呼び出しのテスト時はモック化（patch）してネットワーク依存を排除してください（内部関数はモジュール間で明示的に差替え可能）。

---

必要に応じて README を拡張します。特定の機能（ExecutionEngine の設定、broker の実装詳細、alert_manager と LINE 連携方法など）を追記したい場合は指示してください。