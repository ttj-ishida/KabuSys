# KabuSys

日本株向けの自動売買システム骨格ライブラリ。戦略リサーチ、ポートフォリオ構築、注文実行（本番 / ペーパートレード切替）、監視・アラート、LLM を使ったニュース NLP などの機能を含みます。

> 現行バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の主要機能を持つモジュール群から構成されています。

- 価格・財務データを使ったファクター計算（research）
- 銘柄選定や配分・ポジションサイズ決定の純粋関数群（portfolio）
- 注文実行エンジン（実口座 / ペーパートレード切替）
- リスク管理・オーダー管理（execution 以下）
- 監視（システム状態 / 注文滞留 / ドローダウン監視）と Kill Switch（monitoring）
- OpenAI を使ったニュースセンチメント評価および市場レジーム判定（ai）
- 各種ユーティリティ（環境設定、プロセス優先度設定、レポート生成ツールなど）

設計方針として、
- 本番 DB とペーパートレード DB を分離
- ルックアヘッドを防ぐ（date/day の取り扱いに注意）
- フェイルセーフ（API エラー時のフォールバック）
- 多くの関数は副作用のない純粋関数で設計
が採られています。

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
- 起動前の設定検証 CLI（python -m kabusys.validate_config）
- 実行エンジン起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、ペーパートレード専用 DB に記録
- 監視ループ起動スクリプト（python -m kabusys.run_monitoring）
  - 環境に依らず本番 sqlite_path を監視 DB として使用
  - MONITOR_POLL_INTERVAL でポーリング間隔を設定可能（デフォルト 60 秒）
- Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
- DuckDB を用いたファクター計算（research.calc_*）
- OpenAI を利用したニュースセンチメント（ai.news_nlp.score_news）
- 市場レジーム判定（ai.regime_detector.score_regime）
- ポートフォリオ構築・リスク調整関数群（portfolio）

---

## 必要要件 / 推奨環境

- Python 3.10 以上（型ヒントの | 記法等を使用）
- 主な Python パッケージ:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で YAML 検証を行う場合）
- OS: Linux / macOS / Windows（ただし process priority / cpu affinity の挙動は OS に依存）

インストール例（venv を使用）:
```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# または必要なものだけ:
pip install duckdb psutil openai pyyaml
```

（requirements.txt は本コードベースに含まれていない場合があるので、必要に応じて上記パッケージを直接インストールしてください。）

---

## 環境変数と設定 (.env)

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / よく使うもの:
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)。デフォルト: development
  - paper_trading: MockBroker を使用し data/paper_trading.db に記録（本番 DB と分離）
  - live: 本番運用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: アラート用（任意）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールを使う場合）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60）

.env を対話的に作る:
```sh
python -m kabusys.config_setup
```

設定検証:
```sh
python -m kabusys.validate_config
# 警告も FAIL 扱いにする:
python -m kabusys.validate_config --strict
```

注意:
- .env は自動的にロードされます（プロジェクトルート .git または pyproject.toml を探してロード）。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（簡易）

1. リポジトリをクローン / ソースを配置
2. Python 仮想環境を作成し依存をインストール
3. .env を作成（config_setup を推奨）
4. data ディレクトリや DB の親ディレクトリが存在するか確認（validate_config が警告を出します）
5. 必要に応じて DuckDB に価格・財務・news テーブルなどを投入（リサーチ機能を使う場合）
   - 本コードベースはテーブルを使う関数群を提供しますが、データロード処理は別途用意する必要があります
6. 実行:
   - 監視: python -m kabusys.run_monitoring
   - 実行エンジン: python -m kabusys.run_execution
   - Paper レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

## 使い方（主要コマンド）

- 環境ウィザード（.env 作成）
  ```sh
  python -m kabusys.config_setup
  ```

- 設定検証
  ```sh
  python -m kabusys.validate_config
  ```

- 実行エンジン起動
  ```sh
  python -m kabusys.run_execution
  ```
  KABUSYS_ENV=paper_trading のときは MockBroker を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  起動時に data/stop_requested.flag が存在すると起動を中止します。実行中は data/execution.pid（デフォルト）に PID が書かれます。

- 監視ループ起動
  ```sh
  python -m kabusys.run_monitoring
  ```
  MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更できます（例: MONITOR_POLL_INTERVAL=30）。
  監視は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用して監視ログを記録します。
  停止は data/stop_requested.flag の作成で行えます（監視側で検知してループを抜けます）。

- Paper Trading 検証レポート
  ```sh
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  or
  ```sh
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- プログラムとしての利用例（AI スコアリング）
  ```py
  from kabusys.ai.news_nlp import score_news
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
  ```

---

## Kill Switch / フラグファイル

- data/kill.flag: ExecutionEngine に停止（Kill）シグナルを送るためのファイル。KillSwitch が書き込みます。
  - ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START=1 の場合は自動クリアする挙動をサポート（環境変数で制御）。
- data/stop_requested.flag: run_monitoring / run_execution の外部停止制御に使用（起動スクリプトで検知して終了する）。

---

## 主要ファイルとディレクトリ構成

（src 配下を基準）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py — 対話式 .env 生成ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py — ニュースを LLM でセンチメント化して ai_scores に書込む
    - regime_detector.py — 市場レジーム判定（LLM + MA200 合成）
  - monitoring/
    - monitoring_db.py — SQLite 操作用の永続化層（テーブル作成・migration 含む）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度 / プロセス監視
    - trade_monitor.py — 注文滞留 / 約定異常モニタ
    - risk_monitor.py — ドローダウン / ポジション数監視
    - kill_switch.py — kill.flag の書込みロジック
    - monitoring_engine.py — 各モニタを束ねるループ
    - alert_manager.py — （アラート送信ロジック: 未掲示部分）
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 株数決定・スケールダウンロジック
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — momentum/value/volatility ファクター計算（DuckDB）
    - feature_exploration.py — forward return / IC / 統計サマリー
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - execution/、data/ 等 — 実行・データ関連のサブモジュール（OrderRepository 等。今回抜粋に含まれます）

※ この README はコード抜粋に基づく構成図です。実際のリポジトリには追加ファイルやスクリプトが存在する可能性があります。

---

## 注意事項 / トラブルシューティング

- プロセス優先度設定（set_process_priority）は OS 権限に依存します。権限不足や未サポート OS の場合は警告が出てスキップされます。
- DuckDB や SQLite に必要なテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等）はデータ投入スクリプトが別途必要です。research / ai 機能を利用する前にデータを準備してください。
- OpenAI 呼び出しは API 料金が発生します。API キー・利用制限に注意してください。LLM 呼び出しはリトライ・フォールバックロジックを含みますが、頻繁な失敗があるとスコアが生成されない場合があります。
- validate_config の YAML 検証は PyYAML がインストールされている場合のみ行われます。

---

## 開発者向けメモ

- 設定自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。配布パッケージ化した場合は自動ロードの挙動に注意してください。
- 多くの関数は副作用を持たない純粋関数として実装されており、ユニットテストを書きやすい設計です。
- DuckDB の SQL は大型クエリで一括して集計する設計になっています。大規模データセットでのパフォーマンスは DuckDB の最適化に依存します。

---

必要であれば、README に含めるサンプル .env（例）や具体的な起動シェルスクリプト、Dockerfile / systemd ユニットの例なども作成します。どの情報を優先して補足したいか教えてください。