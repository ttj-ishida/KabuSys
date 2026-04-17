# KabuSys

日本株向け自動売買システム（ライブラリ＋ランタイムコンポーネント）のREADME。  
このリポジトリはアルゴリズム（ファクター計算・ポートフォリオ構成）、実行エンジン、監視機構、AI 補助（ニュース NLP / レジーム判定）などを含みます。

---

## プロジェクト概要

KabuSys は次を目的としたモジュール群です。

- ファクター計算・特徴量探索（research）
- ポートフォリオ構築・銘柄選定・株数決定（portfolio）
- 発注ロジック・ExecutionEngine（execution） — 本番 / ペーパートレード対応
- 監視（system / trade / risk）と Kill Switch（monitoring）
- ニュース NLP による銘柄センチメント評価、レジーム判定（AI）
- 運用補助ツール（設定ウィザード・設定検証、Paper Trading レポート）

主要設計方針の例：

- ルックアヘッドバイアスを避ける（datetime.today() を直接参照しない設計）
- Paper Trading は本番 DB と分離し、MockBroker を利用する
- フェイルセーフを優先（API 失敗はフォールバックして継続）
- DuckDB を分析用、SQLite を監視・発注履歴用に使用

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（project root に基づく）
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config [--strict]

- 実行エンジン / 発注
  - ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBroker を使用し別 DB に記録

- 監視
  - System / Trade / Risk 各種 Monitor 実装
  - MonitoringEngine（ポーリング・アラート集約）
  - 監視スクリプト: python -m kabusys.run_monitoring
  - Kill Switch（data/kill.flag）による ExecutionEngine 停止

- ポートフォリオ構成
  - 候補選定、等配分・スコア加重配分
  - セクターキャップ適用、レジーム乗数
  - 株数決定（単元丸め、risk_based 等）

- リサーチ / ファクター計算
  - モメンタム、バリュー、ボラティリティ、Forward Returns、IC 計算など（DuckDB ベース）

- AI（OpenAI）
  - ニュース記事の銘柄単位センチメント評価（gpt-4o-mini を想定）
  - マクロニュース + ETF MA200 乖離を組み合わせた市場レジーム判定

- 運用ツール
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

---

## セットアップ手順（開発環境）

1. リポジトリをクローンし、仮想環境を作成・有効化します（任意の方法で）:

   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

2. 依存パッケージをインストールします（最低限）:

   ```bash
   pip install duckdb psutil openai
   ```

   - 追加で YAML 検証を使う場合: `pip install pyyaml`
   - 実運用で必要な他パッケージ（kabu API クライアント等）がある場合は適宜追加してください。
   - requirements.txt がある場合は `pip install -r requirements.txt` を推奨します。

3. 環境変数設定（.env）:

   - 対話式ウィザードで初期 .env を作成するのが簡単です:

     ```bash
     python -m kabusys.config_setup
     ```

   - 重要な環境変数（例）:

     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV = development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）

4. 設定検証:

   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ作成（必要に応じて）:

   ```bash
   mkdir -p data
   ```

---

## 使い方（主要コマンド）

- ExecutionEngine（発注エンジン）起動:

  - 本番 / 開発 / ペーパートレードは KABUSYS_ENV に依存
  - 実行:

    ```bash
    python -m kabusys.run_execution
    ```

  - ペーパートレードでは `Settings.is_paper` が True になり、MockBroker を使用、`PAPER_TRADING_SQLITE_PATH` に記録します。
  - 停止方法: `data/stop_requested.flag` を作成すると安全に停止します（run_execution は起動時・ループ中にこのファイルを監視）。

- Monitoring（システム監視）起動:

  ```bash
  # ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

  - 監視は常に本番用 sqlite_path を参照します（環境にかかわらず）。
  - run_monitoring も `data/stop_requested.flag` を参照し、存在するとループを抜けて終了します。

- Paper Trading 検証レポート:

  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- 環境設定ウィザード / 検証:

  ```bash
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

- AI スコアリング / レジーム判定（プログラムから呼び出す例）:

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  # ニューススコア（target_date を指定）
  n_written = score_news(conn, target_date=date(2026,4,11), api_key="sk-...")
  # レジーム判定
  score_regime(conn, target_date=date(2026,4,11), api_key="sk-...")
  ```

  - API キーは引数で渡すか環境変数 `OPENAI_API_KEY` を使用します。
  - AI 呼び出しはリトライ・フォールバック処理を備えますが、API 使用にはコストとレート制限に注意してください。

---

## 運用上の重要点

- Kill Switch / Stop フラグ:
  - 実行エンジン停止シグナルは `data/kill.flag`（KillSwitch）と `data/stop_requested.flag`（safe stop）で扱われる箇所があります。
  - `kill.flag` は監視が判定して書き込むことで ExecutionEngine に停止を促します（ExecutionEngine 側は起動時に kill.flag の存在を確認）。
  - `stop_requested.flag` は手動での停止要求に使われ、run_execution / run_monitoring がこれを検知してループを抜けます。

- Paper Trading は本番 DB と分離する設計です（PAPER_TRADING_SQLITE_PATH を使用）。

- DB マイグレーション:
  - monitoring DB 初期化関数は既存スキーマを検査し、必要なカラムを追加する簡易マイグレーション処理を含みます。

- ログレベル:
  - 環境変数 `LOG_LEVEL`（DEBUG/INFO/...）で調整可能。

---

## ディレクトリ構成（抜粋）

以下は主要モジュールと役割（src/kabusys 配下）:

- __init__.py
- config.py
  - Settings クラス：.env 自動読み込み / 環境変数の取得と検証
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前チェック CLI

- run_execution.py
  - ExecutionEngine の起動スクリプト（スレッド実行・PID 管理・stop flag チェック）

- run_monitoring.py
  - SystemMonitor 単体のポーリング起動スクリプト

- execution/ (発注関連)
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py など
  - （発注ロジック・ブローカー抽象化を含む）

- monitoring/
  - monitoring_db.py — SQLite 永続化層
  - system_monitor.py — システム状態 / データ鮮度監視
  - trade_monitor.py — 注文滞留 / 約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - monitoring_engine.py — 各 Monitor を束ねる
  - kill_switch.py — kill.flag 書き込みロジック
  - alert_manager.py — （アラート送信管理。実装箇所を参照）

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・スケーリング
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — モメンタム / バリュー / ボラティリティ
  - feature_exploration.py — 将来リターン・IC・統計サマリー

- ai/
  - news_nlp.py — ニュース集約 + OpenAI 呼び出し + ai_scores 書き込み
  - regime_detector.py — マクロニュース + ETF MA200 によるレジーム判定

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- OPENAI_API_KEY (AI 機能を使う場合)
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード DB（default: data/paper_trading.db）
- LOG_LEVEL — ログレベル（default: INFO）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、default: 60）
- KILL_FLAG_CLEAR_ON_START — 本番での自動クリア設定（注意）

詳細は `kabusys.config.Settings` を参照してください。

---

## 開発・拡張のヒント

- DuckDB 接続を受け取る関数群（research, ai）はテストしやすい設計です。ユニットテストでは DuckDB のメモリ接続を使うと便利です。
- AI 呼び出し部はリトライ・バリデーションを行っています。テスト時は `_call_openai_api` をモックしてください（news_nlp / regime_detector ともに設計上モック差し替えが想定されています）。
- monitor / engine 周りはファイルフラグ（kill.flag / stop_requested.flag / pid ファイル）を使った運用制御を行います。運用スクリプトでこれらファイルの取り扱いを定義してください。

---

必要に応じて README を拡張します。追加で含めたい情報（例: 実行時ログ例、依存パッケージのバージョン、API キーの取り扱い方、Docker 化手順など）があれば教えてください。