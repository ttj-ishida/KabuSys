# KabuSys — 日本株自動売買システム（README）

このリポジトリは日本株向けの自動売買・研究・監視ツール群を含むパッケージ「KabuSys」です。  
以下はコードベースの概要、機能、セットアップ手順、使い方、および主要なディレクトリ構成の説明です。

---

## プロジェクト概要
KabuSys は以下の主要機能を備えた、モジュール化された自動売買フレームワークです。

- 注文実行エンジン（ExecutionEngine）／ブローカー抽象化（実口座／ペーパートレード切替）
- 監視サブシステム（System / Trade / Risk モニタ）と Kill Switch（異常時に実行を停止）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出、セクター制約）
- 研究（ファクター計算、特徴量探索、IC計算など）用の DuckDB ベースの処理
- ニュース NLP を利用した AI スコアリング（OpenAI API）
- ペーパートレードの検証レポート生成ツール
- 設定ウィザードと設定検証 CLI

特徴として、設定は .env（環境変数）ベース、DB は SQLite（監視・ペーパー）と DuckDB（分析）を利用する設計です。ログは stdout と日次ローテーションファイルに出力します。

---

## 主な機能一覧（抜粋）
- Execution
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV による本番／ペーパー切替）
  - BrokerClientFactory による実ブローカー／Mock ブローカー切替
- Monitoring
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
  - MonitoringDB: system_status / trade_logs / positions / risk_logs / dashboard 等の永続化
  - KillSwitch: 条件（ドローダウン、ポジション数超過等）で data/kill.flag を書き込み実行停止を指示
- Portfolio
  - 銘柄選定、等重／スコア重み、ポジションサイズ計算、セクターキャップ、レジーム乗数
- Research
  - ファクター計算（モメンタム・ボラティリティ・バリュー）、将来リターン、IC、統計サマリ
  - DuckDB を用いたデータ集計処理
- AI
  - ニュースセンチメント（score_news）／市場レジーム判定（score_regime）: OpenAI を用いた LLM 評価
- Tools
  - paper_verification_report: ペーパートレード DB のパフォーマンス・安定性レポートを生成
- 設定補助
  - config_setup.py: 対話式で .env を生成
  - validate_config.py: .env と config/*.yaml の事前チェック

---

## 必要条件（推奨）
- Python 3.9+
- 必要パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - pyyaml（config 検証を行う場合）
- （任意）仮想環境（venv, virtualenv, poetry 等）

requirements.txt は本リポジトリに含まれていない可能性があるため、上記パッケージを個別にインストールしてください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## 環境設定（.env）
設定は環境変数で行います。.env をプロジェクトルートに置くことで自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

重要な環境変数（抜粋）:
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API トークン）
- KABU_API_PASSWORD — 必須（kabuステーション API パスワード）
- KABUSYS_ENV — 実行環境: development / paper_trading / live （デフォルト: development）
- OPENAI_API_KEY — AI 機能を使う場合に必須
- DUCKDB_PATH — DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード時の専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用）

簡易ウィザードで .env を作る:
```
python -m kabusys.config_setup
```

作成後、設定検証:
```
python -m kabusys.validate_config
# 警告も失敗扱いにする場合:
python -m kabusys.validate_config --strict
```

---

## セットアップ手順（推奨）
1. リポジトリをクローン
2. Python 仮想環境を作成して有効化
3. 必要パッケージをインストール（duckdb, psutil, openai, pyyaml など）
4. .env を作成（config_setup.py を推奨）
   - `python -m kabusys.config_setup`
5. 設定を検証
   - `python -m kabusys.validate_config`
6. 必要なディレクトリを作成（自動で作られるが手動で準備することも可）
   - data/, logs/ 等

注意:
- monitoring は常に settings.sqlite_path（監視 DB）を使用します。run_execution は KABUSYS_ENV=paper_trading の場合 paper_sqlite_path を使用して本番 DB と分離します。
- Kill/Stop 制御ファイルはプロジェクト内 data ディレクトリを用います（例: data/kill.flag, data/stop_requested.flag）。

---

## 使い方（主要コマンド）
各モジュールはモジュール実行（-m）で起動できます。いずれもプロジェクトルートで実行してください。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（ExecutionEngine）
  - 本番または開発:
    ```
    export KABUSYS_ENV=development  # または live
    python -m kabusys.run_execution
    ```
  - ペーパートレード:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  実行中にプロセス停止は data/stop_requested.flag を作成して行います。Kill Switch が条件を満たした場合、data/kill.flag が書き込まれ ExecutionEngine に停止指示を出します。

- 監視ループ起動（SystemMonitor）
  ```
  python -m kabusys.run_monitoring
  ```
  ポーリング間隔を変更するには環境変数:
  ```
  export MONITOR_POLL_INTERVAL=30   # 秒
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI スコアリング / レジーム判定（プログラム的に呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=...)
  - regime_detector.score_regime(conn, target_date, api_key=...)

  これらは DuckDB 接続を受け取り内部で ai_scores / market_regime 等のテーブルに書き込みます。OPENAI_API_KEY の設定を忘れないでください。

---

## ログ
- ログは stdout とファイル（logs/<app_name>.log）に出力されます。
- 日次でローテーション（30 日保持）。
- ログレベルは LOG_LEVEL 環境変数で変更できます。例: LOG_LEVEL=DEBUG

ロギング初期化は各スクリプトで `setup_logging(app_name="execution" | "monitoring")` を呼び出しています。

---

## 停止／Kill スイッチ周り
- 停止フラグ（手動）: data/stop_requested.flag を作成すると run_execution/run_monitoring のループは検知して停止します。
- Kill Switch（自動）: リスク条件（ドローダウン超過やポジション上限超過等）により data/kill.flag を書き込み、ExecutionEngine に停止指示を出します。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動クリアしますが、本番では 0 を推奨します。

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要なファイルとサブパッケージの一覧（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py               — 環境変数 / Settings 管理
    - config_setup.py         — .env 対話式ウィザード
    - validate_config.py      — 設定検証 CLI
    - run_execution.py        — ExecutionEngine 起動スクリプト
    - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py           — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py    — 市場レジーム判定（OpenAI + MA200）
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py (参照あり)
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py (参照あり)
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - execution/ (参照あり)
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - data/ (参照: kabusys.data を利用するモジュールが存在)
      - pipeline.py 等（別ファイルで管理）

（実際の全ファイルはリポジトリ内の src/kabusys を参照してください）

---

## 開発上の注意 / 補足
- DB マイグレーション: monitoring_db.init_monitoring_db は必要テーブルを冪等に作成し、既存カラムがなければ ALTER TABLE によるマイグレーション処理を含みます。
- ペーパートレードと本番 DB は分離する設計（settings.is_paper 判定により paper_sqlite_path を使用）。
- AI 機能は OpenAI API を利用するため、API キーの管理に注意してください。レスポンス検証やリトライロジックが実装されていますが、コストに注意して運用してください。
- process priority / CPU affinity は utils.process_priority で OS に依存しないラッパー実装を提供します（権限不足時は警告ログのみ）。

---

## よく使うコマンドまとめ
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

問題や追加で README に入れたい項目（例: 詳細な環境変数の全リスト、実行例ログ、CI 設定、テスト手順など）があれば教えてください。必要に応じて追記・整形します。