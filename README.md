# KabuSys

日本株自動売買システムの軽量実装（ライブラリ + 起動スクリプト群）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。  
主な目的は取引エンジンの実行、監視、ポートフォリオ構築、リサーチ（ファクター計算）、およびニュースベースの AI スコアリングを行うことです。  
本リポジトリは実行用スクリプト（ExecutionEngine / Monitoring）と、ポートフォリオ構築・リスク管理・研究ユーティリティ群を含みます。

主要設計方針の例:
- Paper Trading（ペーパートレード）と Live（本番）を分離
- DuckDB / SQLite を用いたローカルデータ管理
- OpenAI（LLM）を利用したニュース NLP（任意）
- kill.flag による外部からの安全停止（Kill Switch）

---

## 主な機能一覧

- 実行エンジン (ExecutionEngine)
  - ブローカークライアントを抽象化し、Paper Trading 時は MockBroker を使用
  - 注文管理、リスク管理、照合（Reconciler）などのコンポーネントを統合

- 監視 (Monitoring)
  - SystemMonitor: CPU/Memory/Disk、プロセス生存、データ鮮度を監視し SQLite に永続化
  - TradeMonitor / RiskMonitor: 注文滞留、約定異常、ドローダウン・ポジション上限をチェック
  - KillSwitch: 条件により data/kill.flag を書き込み、ExecutionEngine を停止

- ポートフォリオ構築
  - 候補選定、等金額/スコア加重配分、リスクベースなポジションサイズ算出
  - セクター制限、レジーム乗数の適用

- 研究（Research）
  - ファクター計算（Momentum, Value, Volatility 等）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ

- AI（任意）
  - ニュースのセンチメント評価（OpenAI を利用、gpt-4o-mini 想定）
  - market_regime 判定（MA200 とマクロニュースの合成）

- ユーティリティ
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト

---

## 必須依存（代表）

コード中で使用されている主なライブラリ例:

- Python 3.10+（型ヒントに | 演算子を使用）
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config/*.yaml の検証を行う場合）

インストール例（仮の requirements がない場合）:
```sh
python -m pip install duckdb psutil openai pyyaml
```

※ 実運用環境では仮想環境（venv / poetry / pipenv 等）を推奨します。

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を作成して依存をインストール
3. .env を作成
   - 対話式ウィザード:
     ```sh
     python -m kabusys.config_setup
     ```
   - 手動で `.env` ファイルを作成（.env.example を参照）
4. 設定検証:
   ```sh
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```
5. DB/データディレクトリの作成（必要に応じて）
   - デフォルト:
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - DuckDB: data/kabusys.duckdb
   - .env の `DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH` で変更可能

注意:
- Settings モジュールは自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（環境変数より優先度低）。
- 自動ロードを無効にする場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

---

## 実行・使い方

以下は主要なスクリプトの起動方法の例です。

- 実行エンジン（ExecutionEngine）起動:
  ```sh
  # 本番 or 開発は環境変数 KABUSYS_ENV で制御
  # 例: paper_trading モードで起動（MockBroker を使用）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
  備考:
  - paper_trading モード時は `PAPER_TRADING_SQLITE_PATH` に記録され、本番 DB と分離されます。
  - 実行中は data/execution.pid を使用します。
  - data/stop_requested.flag が存在すると起動を抑止・停止します。

- 監視（Monitoring）起動:
  ```sh
  # ポーリング間隔を変更する場合:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  備考:
  - デフォルトのポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（正の整数のみ有効）。
  - Monitoring は常に本番 sqlite_path を参照（環境に関係なく監視 DB は本番 DB を使用）。

- .env 設定ウィザード:
  ```sh
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```sh
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成:
  ```sh
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能を使う場合:
  - 環境変数 `OPENAI_API_KEY` を設定するか、関数呼び出しに api_key を渡す
  - 例: ニューススコア付け（プログラム経由で呼び出す）
    ```py
    from kabusys.ai import score_news
    # duckdb_conn は duckdb.connect(...) で得た接続
    score_news(duckdb_conn, target_date, api_key="sk-...")
    ```

停止 / Kill Switch:
- 外部から ExecutionEngine を停止させたい場合は、`data/kill.flag` を作成（KillSwitch が評価して停止）。
- また、`data/stop_requested.flag` を置くことで run_execution/run_monitoring の外部ループを検知して停止できます。

ログ:
- デフォルトのログディレクトリは `logs/`。`LOG_DIR` 環境変数で変更可能。
- ログレベルは `LOG_LEVEL`（例: DEBUG/INFO）で指定。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能使用時）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- LOG_DIR — ログ保存先ディレクトリ（デフォルト: logs）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — Paper Trading の注文約定動作（instant | partial | never | reject）

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys を基準に抜粋）

- src/kabusys/
  - __init__.py (バージョン情報)
  - config.py (環境変数 / 設定管理)
  - config_setup.py (.env 対話式ウィザード)
  - validate_config.py (設定検証 CLI)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor 起動スクリプト)
  - utils/
    - logging_setup.py (統一ロギング設定)
    - process_priority.py (プロセス優先度 / CPU affinity)
  - execution/ (発注エンジン周り)
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py (等)
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (アラート送信)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py (ニュース NLP / OpenAI 呼び出し)
    - regime_detector.py (市場レジーム判定)
  - tools/
    - paper_verification_report.py (ペーパートレード検証レポート)

data/ と logs/ は起動時に作成される（または .env でパスを変更）。

---

## 開発上の注意点 / 安全性

- Paper Trading と Live はデータベース等で分離されるよう配慮されています（paper_trading 用 DB を用意）。
- Kill Switch（data/kill.flag）により本番エンジンを停止できる仕組みを実装しています。`KILL_FLAG_CLEAR_ON_START` は本番では 0 推奨。
- AI（OpenAI）呼び出しは外部 API 依存。API キー/呼び出し回数の管理に注意。
- config.py は自動で .env/.env.local を読み込みます。CI / テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を指定して挙動を制御可能。
- logging_setup は標準出力と日次ローテーションファイルを併用。ログディレクトリ作成失敗時はファイル出力をスキップし stdout のみで継続します。

---

## よく使うコマンドまとめ

- .env 作成:
  ```sh
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```sh
  python -m kabusys.validate_config
  ```
- ExecutionEngine 起動:
  ```sh
  python -m kabusys.run_execution
  ```
- Monitoring 起動:
  ```sh
  python -m kabusys.run_monitoring
  ```
- Paper Trading 検証レポート:
  ```sh
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要に応じて README に詳細な API 使用例（関数別ドキュメントや設定例）を追加できます。特に AI 関連やブローカー接続部分はキーや接続先の具体例（安全なサンプル）を記載すると導入が容易になります。必要であれば、追記して作成します。