# KabuSys

日本株自動売買システムの一部を抜粋したコードベースです。  
このリポジトリはトレード実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI 補助（ニュース NLU / レジーム判定）などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムで、主に以下を提供します。

- 発注エンジン（実環境 / ペーパートレード切替）
- 実行状況・システム監視（プロセス死活、データ鮮度、リスク監視）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- リサーチ（ファクター計算、特徴量探索、IC 計算）
- AI 補助（ニュースのセンチメント評価、マクロセンチメントを用いた市場レジーム判定）
- 運用補助スクリプト（.env ウィザード、設定検証、ペーパートレード検証レポート等）

設計方針として、DBアクセスとビジネスロジックの分離、フェイルセーフ（API失敗時は安全側で継続）、ルックアヘッドバイアス回避などが採用されています。

---

## 主な機能一覧

- Execution
  - 実際の broker クライアントと接続して注文を出す（KABUSYS_ENV=live）
  - ペーパートレード用モード（KABUSYS_ENV=paper_trading、MockBrokerClient を使用し専用 DB に記録）
- Monitoring
  - システムリソース監視（CPU/メモリ/ディスク）
  - Execution プロセスの生存チェック
  - 注文・約定の監視（滞留注文・異常約定など）
  - リスク監視（ドローダウン、ポジション上限）
  - Kill Switch（重大なリスクで ExecutionEngine を停止させるためのフラグ）
- Portfolio
  - 候補選定（スコア順）
  - 重み計算（等配分・スコア加重）
  - ポジションサイズ計算（risk-based 等）
  - セクター制限・レジーム乗数の適用
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリー
- AI
  - ニュース記事を LLM（OpenAI）でスコアリングして ai_scores に保存
  - マクロニュース + ETF MA200 を使った市場レジーム判定
- ツール類
  - .env 初期ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools.paper_verification_report）

---

## 前提（Prerequisites）

- Python 3.9+（コードは型ヒント等から若干のバージョン要件があるため 3.9 以上を推奨）
- SQLite（標準ライブラリに含まれる）
- DuckDB（pip でインストール）
- psutil（プロセス優先度 / CPU affinity / リソース取得）
- openai パッケージ（AI 機能を使う場合）
- PyYAML（設定ファイル検証を行う場合、任意）

代表的な依存パッケージ（例）:
- duckdb
- psutil
- openai
- pyyaml (任意)

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（実運用では requirements.txt を用意して pip install -r することを推奨します）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動
2. 仮想環境作成・依存パッケージをインストール（上記参照）
3. .env の作成（ウィザード推奨）
   - 対話式で .env を作成:
     ```bash
     python -m kabusys.config_setup
     ```
   - 作成後、設定検証:
     ```bash
     python -m kabusys.validate_config
     # 警告も FAIL 扱いにする場合:
     python -m kabusys.validate_config --strict
     ```
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY を環境変数に設定
4. データディレクトリの準備
   - デフォルトの DB / ログ / PID / フラグファイルは `data/` と `logs/` に作られます。必要に応じて .env でパスを変更してください。
   - デフォルト:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - ログ: logs/<app>.log
     - Kill flag: data/kill.flag
     - Stop requested: data/stop_requested.flag
5. （任意）Paper Trading 用にデータ分離
   - KABUSYS_ENV=paper_trading の場合、発注は MockBrokerClient を使い data/paper_trading.db に記録されます（本番 DB と完全に分離）。

---

## 使い方（起動・コマンド）

- ExecutionEngine（発注エンジン）を起動:
  - 通常起動:
    ```bash
    python -m kabusys.run_execution
    ```
  - KABUSYS_ENV により挙動が変わります:
    - development: 発注なし（開発用）
    - paper_trading: MockBrokerClient を使用（PAPER_TRADING_SQLITE_PATH に記録）
    - live: 実ブローカに接続して発注
  - 停止:
    - プロセスは `data/stop_requested.flag` の存在を監視しています。ファイルを作成すると起動中のループを終了して安全に停止します。
    - Kill Switch により `data/kill.flag` が書かれると ExecutionEngine 側で検知して停止するフローがあります（監視プロセス経由）。

- Monitoring を起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更するには環境変数:
    - MONITOR_POLL_INTERVAL（秒、デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は本番の sqlite_path（Settings.sqlite_path）を使います（環境に依らず本番 path を使用する設計）。
  - 監視プロセスも `data/stop_requested.flag` を見て終了します。

- 設定ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 部分（ニューススコア、レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数で指定）
  - メソッドはモジュール関数として提供（プログラムから呼ぶ形）
    - kabusys.ai.news_nlp.score_news(...)
    - kabusys.ai.regime_detector.score_regime(...)

---

## 環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- システム / パス
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - LOG_LEVEL（デフォルト: INFO）
  - LOG_DIR（デフォルト: logs/）
- AI
  - OPENAI_API_KEY（AI 機能使用時に必要）
- その他
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔 秒、デフォルト 60）
  - PAPER_FILL_MODE（paper_trading の約定振る舞い: instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START（1 にすると起動時に kill.flag を自動クリア。production では 0 推奨）

---

## 運用メモ / 注意点

- ログ
  - setup_logging が root ロガーに StreamHandler（stdout）と TimedRotatingFileHandler（logs/<app>.log）を設定します。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- プロセス優先度
  - 起動スクリプトは set_process_priority("high") を呼びます。psutil の権限によっては設定できないことがあります（警告ログが出ます）。
- データベース
  - monitoring は起動時に init_monitoring_db を呼び、テーブル・マイグレーション（列追加等）を行います。冪等に実行できます。
- Kill Switch / stop flag
  - 監視モジュールがリスク検出時に data/kill.flag を書き込み、Engine 側がこれを検出して停止する仕組みです。手動で停止したい場合は data/stop_requested.flag を作成してください。
- Paper Trading
  - paper_trading モードでは本番 DB と完全に分離された SQLite を使用します。ペーパートレードは MockBrokerClient によりシミュレーションされます。

---

## ディレクトリ構成（主要ファイル）

（実際は src/kabusys 以下がパッケージです）

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照実装あり)
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
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
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py
  - data/  (ランタイム生成)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kill.flag, stop_requested.flag, execution.pid など

---

## 開発者向けヒント

- .env の自動ロードは Settings モジュール内で行われますが、テスト等で無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB を利用したリサーチ系関数は副作用が少ない（読み取り専用）ように設計されています。テスト時は小さな DuckDB を用意してユニットテストが可能です。
- OpenAI API 呼び出し周りはリトライ・エラー処理や JSON バリデーションを重視して実装されています。テストでは _call_openai_api をモックすることを推奨します。

---

この README はコードの主要部分に基づき作成しています。ローカルでの実行や運用に際しては .env/設定ファイル・DB のバックアップやアクセス権限管理にご注意ください。必要であれば、さらに詳細な運用手順（systemd/サービス化、監視ダッシュボード構築、DB マイグレーション手順など）を追加します。