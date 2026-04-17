# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買／分析を行うためのコンポーネント群を含んでいます。  
この README はコードベース（src/kabusys 以下）をもとに、概要・機能・セットアップ・使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群です。

- 株価データや財務データを用いたファクター計算・研究（research）
- ポートフォリオ構築・ポジションサイズ計算（portfolio）
- 発注エンジン（ExecutionEngine）とブローカークライアント（実運用 / ペーパートレード切替）
- 実行状況・注文・リスクの監視（monitoring）
- ニュースの LLM ベースセンチメント評価や市場レジーム判定（AI）
- 各種ユーティリティとツール（ツールや CLI）

設計上のポイント：

- 環境依存の設定は .env（環境変数）で管理。`config_setup.py` で対話的に .env を生成できます。
- ペーパートレード（KABUSYS_ENV=paper_trading）は本番 DB と分離された専用 SQLite DB を使用します（data/paper_trading.db がデフォルト）。
- 監視は SQLite（monitoring.db）にログを残し、DuckDB は分析用途で使用します。
- OpenAI 等の外部 API を使う機能は API キーが必要（環境変数または引数で指定）。

---

## 主な機能一覧

- 設定ウィザード
  - python -m kabusys.config_setup — 対話的に .env を作成・更新
- 設定検証
  - python -m kabusys.validate_config — .env や config/*.yaml の基本チェック
- 実行エンジン起動
  - python -m kabusys.run_execution — ExecutionEngine を起動（paper_trading では MockBroker）
- 監視ループ起動
  - python -m kabusys.run_monitoring — SystemMonitor のポーリングループを起動
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report — ペーパートレード DB から検証レポートを生成
- AI 関連
  - kabusys.ai.score_news — raw_news を LLM でセンチメント評価して ai_scores に格納
  - kabusys.ai.score_regime — マクロ+ETF 指標を組み合わせて市場レジームを判定
- 研究モジュール
  - calc_momentum / calc_volatility / calc_value などのファクター計算（DuckDB を利用）
  - forward returns / IC / 統計サマリ機能
- ポートフォリオ構築
  - 候補選定、等重・スコア重み、ポジションサイズ計算、セクターキャップやレジーム乗数

---

## 必要条件（依存）

最低限必要なパッケージ（主なもの）：

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（validate_config の YAML 検証を使う場合）

インストール例（venv を推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb psutil openai PyYAML
# またはプロジェクトの requirements がある場合はそれを利用
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動。

2. 仮想環境を作成し、依存をインストール（上記参照）。

3. .env の作成（対話ウィザード推奨）:

   ```bash
   python -m kabusys.config_setup
   ```

   ウィザードで入力するとプロジェクトルートに `.env` が作成されます。必須項目は次の通りです:

   - JQUANTS_REFRESH_TOKEN（J-Quants API）
   - KABU_API_PASSWORD（kabuステーション API）

   そのほか重要な環境変数（主なもの）:

   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE（paper_trading の fill モード: instant|partial|never|reject）
   - LOG_LEVEL（ログレベル: DEBUG|INFO|WARNING|ERROR|CRITICAL）
   - KILL_FLAG_CLEAR_ON_START（Execution 起動時に kill.flag を自動クリアするか: 0/1）

4. 設定の検証（必須項目やパス確認）:

   ```bash
   python -m kabusys.validate_config
   # --strict を付けると警告も失敗扱いになります
   python -m kabusys.validate_config --strict
   ```

5. DB 初期化
   - 監視用 SQLite（monitoring.db）は run_monitoring/run_execution 実行時に init_monitoring_db により自動的にテーブル作成されます。
   - DuckDB は分析用で、必要に応じてテーブルを用意してください（prices_daily, raw_financials, raw_news 等）。

---

## 使い方（主要コマンド）

- 設定ウィザード（.env の作成・更新）

  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証

  ```bash
  python -m kabusys.validate_config
  ```

- 監視ループ起動（SystemMonitor のポーリング。デフォルト 60 秒間隔）

  ```bash
  python -m kabusys.run_monitoring
  ```

  - ポーリング間隔を変える: 環境変数 MONITOR_POLL_INTERVAL（秒）で上書きできます。
    - 例: export MONITOR_POLL_INTERVAL=30
  - 停止: プロセスに Ctrl+C するか、プロジェクトの data/stop_requested.flag ファイルを作成すると安全にループを抜けます。
  - 監視は常に本番（settings.sqlite_path）を使用します（KABUSYS_ENV にかかわらず）。

- 実行エンジン起動（ExecutionEngine）

  ```bash
  python -m kabusys.run_execution
  ```

  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します（本番 DB と分離）。
  - 実行開始前に data/stop_requested.flag が既に存在する場合は起動せず終了します。
  - 実行中に停止させるには data/stop_requested.flag を作成するか、監視側が kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）を書き込むと ExecutionEngine を停止します。
  - 起動時にプロセス優先度が "high" に設定されます（psutil が必要）。

- ペーパートレード検証レポート生成

  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

  - DB パスは引数 --db または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。デフォルトは data/paper_trading.db。

- AI 系（プログラム API）

  - ニュースセンチメント:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI キーは api_key 引数または環境変数 OPENAI_API_KEY を利用します。
  - レジーム判定:
    - kabusys.ai.score_regime(conn, target_date, api_key=None)

  注意: AI 機能は API呼び出し・料金が発生します。テスト時は _call_openai_api をパッチして外部通信を抑える実装箇所があります。

---

## フラグ／停止制御について

- data/stop_requested.flag
  - run_monitoring と run_execution はこのファイルの存在を監視しており、検知すると安全に停止します（手動停止用）。
- data/kill.flag（Settings.kill_flag_path）
  - Monitoring の KillSwitch によって書き込まれ、ExecutionEngine に停止シグナルを送るために使われます（本番保護機能）。
  - 設定 KILL_FLAG_CLEAR_ON_START=1 にすると Execution 起動時に自動でクリアされますが、本番では 0 を推奨します。
- PID ファイル
  - run_execution は data/execution.pid を利用します。SystemMonitor は PID ファイルを見てプロセスの存否を判定します。

---

## 設定（主な環境変数）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用
  - KABU_API_PASSWORD: kabuステーション API 用

- 主なオプション
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）
  - LOG_LEVEL: ログレベル（INFO 等）
  - KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

---

## ディレクトリ構成

リポジトリの主要なファイル・パッケージ構成（簡易ツリー）:

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py                — 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
  - config_setup.py          — .env 作成ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成
    - __init__.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）による銘柄スコアリング
    - regime_detector.py     — マクロ + ETF で市場レジーム判定
    - __init__.py
  - monitoring/
    - monitoring_db.py       — SQLite テーブル作成・永続化 API
    - system_monitor.py      — システムリソース・データ鮮度監視
    - trade_monitor.py       — 注文滞留・約定異常監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch 書き込みロジック
    - monitoring_engine.py   — 複数モニタを束ねるエンジン
    - alert_manager.py       — アラート送信管理（ファイル末尾に未表示の実装あり）
  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み計算
    - position_sizing.py     — 発注株数計算（ロット丸め・キャップ等）
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py     — ファクター計算（momentum / volatility / value）
    - feature_exploration.py — forward returns / IC / summary
    - __init__.py
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py
  - （その他: execution, data 等のサブパッケージが存在する想定）

data/ ディレクトリ（実行時に使用・生成されるファイルの例）:

- data/kabusys.duckdb       — DuckDB（分析用）
- data/monitoring.db        — SQLite（監視ログ）
- data/paper_trading.db     — ペーパートレード用 SQLite（KABUSYS_ENV=paper_trading）
- data/execution.pid        — Execution の PID（run_execution が利用）
- data/kill.flag            — Monitoring が書き込む停止フラグ（Kill Switch）
- data/stop_requested.flag  — 手動停止要求（run_monitoring / run_execution が監視）

---

## 運用上の注意点

- 本番（KABUSYS_ENV=live）では設定（LINE 通知や Kill Switch など）を十分確認してください。validate_config は live 特有の危険設定を警告します。
- OpenAI など外部 API 利用時はレート制限や料金に注意してください。ログやリトライロジックは一部実装済みですが、運用条件に応じて調整してください。
- プロセス優先度設定や CPU affinity 設定は psutil を使っています。OS による制約や権限の違いにより設定できない場合があります（警告でスキップされます）。
- .env は絶対にバージョン管理にコミットしないでください（config_setup でその旨の注意書きがあります）。

---

## よく使うコマンドまとめ

- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 監視起動: python -m kabusys.run_monitoring
- Execution 起動: python -m kabusys.run_execution
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report

---

この README はコードベースの公開部分（src/kabusys 以下）をもとに作成しています。実際の運用や拡張を行う際は、プロジェクトの追加ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）や実際の config/*.yaml を参照してください。必要であれば README を補足・更新しますので、よく使う機能や運用手順について追加の要望を教えてください。