# KabuSys

日本株向け自動売買システムのリファレンス実装（ライブラリ＋実行スクリプト群）

短い概要:
- ファクター計算・シグナル生成・ポートフォリオ構築・ポジションサイジングを含む研究／実行モジュール群
- ExecutionEngine（発注実行）と Monitoring（稼働監視・アラート・Kill Switch）
- Paper Trading モードを用いた本番分離（専用 SQLite DB）と、OpenAI を使ったニュース NLP / レジーム判定機能

---

目次
- プロジェクト概要
- 主な機能
- 前提・依存関係
- セットアップ手順
- 使い方（実行コマンド／環境変数）
- 停止方法（フラグファイル）
- ディレクトリ構成（主要ファイルの説明）
- 補足（注意点）

---

## プロジェクト概要

KabuSys は日本株自動売買の研究→実行パイプラインを目的としたコード群です。  
本リポジトリは、以下の領域をカバーします。

- データ解析・ファクター計算（DuckDB を前提）
- ポートフォリオ構築（候補選定、重み算出）
- ポジションサイズ計算（単元株丸め、資金配分のスケールダウン処理）
- Execution エンジン（ブローカークライアント経由で注文を送信。paper_trading モードではモック）
- 監視（System / Trade / Risk のチェック、Kill Switch、アラート）
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定。OpenAI を利用）
- 運用支援ツール（設定ウィザード、設定検証、Paper Trading 用レポート生成）

---

## 主な機能（抜粋）

- Settings 管理 (.env 自動ロード / .env.local の優先)
- 実行環境分離: KABUSYS_ENV = development | paper_trading | live
  - paper_trading 時は MockBrokerClient を使い、専用 DB（data/paper_trading.db）に記録
- Monitoring:
  - CPU / メモリ / ディスク / Execution プロセスの稼働チェック
  - 注文滞留・約定異常チェック
  - ドローダウン・ポジション上限のリスク監視（Kill Switch 起動）
- AI:
  - news_nlp.score_news: raw_news を LLM（gpt-4o-mini）で評価し ai_scores に保存
  - regime_detector.score_regime: MA200 とマクロセンチメントを合成して daily regime を判定
- Research:
  - ファクター計算（momentum/value/volatility）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー
- Tools:
  - 対話式 .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools.paper_verification_report）

---

## 前提・依存関係

必須（代表例）
- Python 3.10+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の内容検証を行う場合、なくても動作は可能）

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```
（requirements.txt があればそれを利用してください）

---

## セットアップ手順

1. レポジトリをクローンし、仮想環境を作る
2. 依存パッケージをインストール（上の例参照）
3. 対話式に .env を作る（推奨）
   ```
   python -m kabusys.config_setup
   ```
   - .env に最低限必要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH, SQLITE_PATH（必要に応じて）
     - OPENAI_API_KEY（AI 機能利用時）
4. 設定検証を実行
   ```
   python -m kabusys.validate_config
   ```
   - 本番で厳密にチェックしたい場合は `--strict` を付けると警告も失敗扱いになります
5. DB 初期化は実行スクリプトが自動で行います（monitoring 用のテーブル等を作成）

---

## 使い方

主要な実行スクリプトはモジュールとして起動します。プロジェクトルートで次を実行してください。

- ExecutionEngine（発注エンジン）起動:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録します（本番 DB と分離）。
  - プロセス優先度を high に設定します。
  - 実行中は data/execution.pid に PID を書きます。
  - 起動時に stop フラグ（data/stop_requested.flag）が既に存在する場合は起動しません。

- Monitoring（監視ループ）起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - デフォルトのポーリング間隔は 60 秒。
  - 環境変数で上書き: `MONITOR_POLL_INTERVAL=30`（秒）
  - Monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使用して監視データを記録します。
  - stop フラグ: プロジェクトルート/data/stop_requested.flag を置くとループが終了します。

- 設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定（環境変数 PAPER_TRADING_SQLITE_PATH も可）
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI モジュール（プログラムから呼び出す）:
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - OPENAI API キーが必要: 引数で渡すか環境変数 `OPENAI_API_KEY` を設定

---

## 重要な環境変数（抜粋）

- KABUSYS_ENV: execution 動作モード（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時使用）
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant | partial | never | reject）
- OPENAI_API_KEY: OpenAI を使う場合は必須（AI モジュール）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

---

## 停止方法（フラグファイル）

- ループ系（run_monitoring / run_execution）は共通でプロジェクトルート下の `data/stop_requested.flag` を監視しています。
  - これを作成すると各ループは次回チェック時に安全停止します。
- Kill Switch（運用上の強制停止）は `data/kill.flag` を書き込むことで ExecutionEngine に停止シグナルを送ります。
  - kill.flag は Monitoring の KillSwitch ロジックが作成します（ドローダウン等で自動作成）。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定していると Execution の起動時に kill.flag を自動クリアします（本番では注意）。

---

## ディレクトリ構成（主要ファイルの説明）

以下は src/kabusys 下の主要モジュール一覧と用途の簡単な説明。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み・管理。.env 自動ロード（.env, .env.local）
  - config_setup.py
    - 対話式 .env 作成ウィザード
  - validate_config.py
    - 起動前の環境/ファイル検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（PID ファイル、paper_trading 分離）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
  - utils/
    - process_priority.py
      - プロセス優先度・CPU affinity 設定ユーティリティ（Windows / POSIX 吸収）
  - monitoring/
    - monitoring_db.py
      - SQLite ベースの監視ログ永続化（テーブル作成 / マイグレーション）
    - system_monitor.py
      - CPU/メモリ/ディスク、データ鮮度、Execution プロセス生存監視
    - trade_monitor.py
      - 注文滞留、約定価格の異常検出
    - risk_monitor.py
      - ドローダウン・ポジション上限監視、dashboard 更新
    - kill_switch.py
      - kill.flag の作成 / 解除ロジック
    - monitoring_engine.py
      - 複数モニタを束ねて定期実行するエンジン
    - alert_manager.py
      - （未完）アラート送信管理
  - execution/
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, ...
    - ExecutionEngine と発注関連ロジック（OrderRepository/OrderManager など）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
    - 候補選定、重み付け、株数計算、セクター制約、レジーム乗数
  - research/
    - factor_research.py
      - momentum/value/volatility 等のファクター計算（DuckDB）
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー
  - ai/
    - news_nlp.py
      - raw_news を LLM で評価して ai_scores へ書き込むロジック
    - regime_detector.py
      - MA200 とマクロセンチメントを合成して市場レジームを判定
  - tools/
    - paper_verification_report.py
      - ペーパートレード検証レポート生成スクリプト

（上記以外にもサブモジュールや実装ファイルが含まれます。README に記載のない内部関数や細部実装はソースを参照してください）

---

## 補足 / 注意点

- .env は機密情報を含みます。絶対に Git にコミットしないでください。
- KABUSYS_ENV=live の場合は validate_config が警告を出します。production 設定は慎重に確認してください。
- AI 機能は OpenAI API を使用します。API 利用料／レート制限に注意してください。network/429/5xx エラーは本実装でリトライ処理を行いますが、失敗時はフォールバック（スコア 0.0 等）する設計です。
- Paper Trading（paper_trading）は実運用での確認用です。paper_trading 時の挙動（PAPER_FILL_MODE 等）を理解してから利用してください。
- DuckDB / SQLite のパスは環境変数で変更できます。デフォルトは `data/kabusys.duckdb` / `data/monitoring.db` / `data/paper_trading.db`。

---

必要があれば README に「起動シーケンス（推奨）」や「CI / テストの実行方法」などの追記、あるいは各モジュールの詳細な API ドキュメント（関数引数/戻り値一覧）を追加できます。どの情報を優先して追記するか教えてください。