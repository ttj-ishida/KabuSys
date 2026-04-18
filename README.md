# KabuSys

日本株向け自動売買・研究プラットフォームのコードベースドキュメント（README）。  
この README はリポジトリ内の主要スクリプト・ユーティリティの使い方、設定、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買エンジン、モニタリング、リサーチ（ファクター計算・特徴量解析）、および AI を使ったニュースセンチメント／レジーム判定を含むツール群です。  
主な設計方針は以下です:

- 発注ロジックと永続化・監視ロジックを明確に分離
- DuckDB を使った分析用 DB、SQLite を監視／注文履歴用 DB として利用
- Paper Trading（ペーパートレード）と Live（本番）を環境変数で分離
- OpenAI を利用したニュース NLP / マクロセンチメント機能をサポート（設定により有効化）
- ログは統一的に設定（コンソール + 日次ローテーションファイル）

バージョン: __0.1.0__

---

## 機能一覧

- ExecutionEngine（発注エンジン）
  - Live / Paper Trading の切替
  - リスク管理（ポジション上限／ドローダウン等）
  - Order 管理・再整合（Reconciler）
- Monitoring（監視）
  - システムリソース監視（CPU / メモリ / ディスク）
  - データ鮮度チェック（DuckDB の prices_daily 等）
  - 取引イベント監視（滞留注文・約定異常など）
  - Kill Switch（一定条件で Execution を停止するフラグ）
- Portfolio Construction（ポートフォリオ構築）
  - 候補選定、重み付け（等配分 / スコア加重）
  - セクター集中制限、レジーム乗数
  - ポジションサイズ計算（単元株の丸め・集約制限対応）
- Research（研究用）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）等の統計解析
- AI（OpenAI を利用）
  - ニュースセンチメント（ai_scores への書き込み）
  - 市場レジーム判定（market_regime テーブルへ書き込み）
- ツール
  - 環境設定ウィザード（.env の対話式作成）: config_setup
  - 設定検証 CLI（必須環境変数や config/*.yaml の検査）: validate_config
  - Paper Trading 検証レポート生成: paper_verification_report

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローンして作業ディレクトリへ移動

   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成（推奨）

   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール

   このリポジトリでは次を使用します（例）:

   - duckdb
   - psutil
   - openai
   - PyYAML（オプション: config の YAML 検証に使用）
   - （標準ライブラリ: sqlite3 等）

   例:

   ```
   pip install duckdb psutil openai pyyaml
   ```

   実際のプロジェクトでは requirements.txt を用意している場合があります。その場合は `pip install -r requirements.txt` を使用してください。

4. 環境変数の設定（.env）

   対話式ウィザードで .env を作成できます:

   ```
   python -m kabusys.config_setup
   ```

   あるいはプロジェクトルートに `.env` を作成し、必要変数を設定してください。自動ロードは既定で有効です（.env / .env.local を読み込みます）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. 設定検証（起動前チェック）

   ```
   python -m kabusys.validate_config
   ```

   --strict フラグを付けると警告も失敗扱いになります:

   ```
   python -m kabusys.validate_config --strict
   ```

6. データ / ログ ディレクトリの確認

   - デフォルトの DuckDB: data/kabusys.duckdb
   - デフォルトの SQLite(監視): data/monitoring.db
   - Paper Trading DB: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）
   - ログディレクトリ: logs/（デフォルト、日次ローテーション）

   実行時に自動作成しますが、ファイルシステムの権限に注意してください。

---

## 必須・主な環境変数

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境切替
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development

- DB パス
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB（デフォルト: data/paper_trading.db）

- OpenAI（AI 機能を使う場合）
  - OPENAI_API_KEY

- ログ / 動作
  - LOG_LEVEL — デフォルト: INFO
  - LOG_DIR — ログ出力先（デフォルト: logs/）
  - MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START — 本番環境で Kill Flag の自動クリアを抑止するためのフラグ（0/1）

---

## 使い方（主要スクリプト）

各スクリプトは Python のモジュールとして起動できます（プロジェクトルートがパスに存在すること前提）。

- 環境設定ウィザード（.env の作成・更新）

  ```
  python -m kabusys.config_setup
  ```

- 設定検証

  ```
  python -m kabusys.validate_config
  ```

- 監視ループ（Monitoring）

  Monitoring は SQLite の監視 DB（settings.sqlite_path）に書き込みを行います。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL でオーバーライド可能（秒）。
  停止指示はプロジェクト内の data/stop_requested.flag を作成するとループが終了します。

  ```
  python -m kabusys.run_monitoring
  ```

  例: ポーリングを30秒に変更して起動

  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- 実行エンジン（ExecutionEngine）

  KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（data/paper_trading.db）へ記録します。本番 DB と分離されます。停止は data/stop_requested.flag を置くことで検知します。

  ```
  python -m kabusys.run_execution
  ```

- Paper Trading 検証レポート生成

  Paper Trading DB から統計を抽出してレポートを標準出力に出します（期間指定可）。

  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

  DB を明示する場合:

  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連（プログラムから呼び出す API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

  これらを直接呼び出す場合は `OPENAI_API_KEY` を設定するか、api_key を引数で渡してください。

---

## Kill / Stop の仕組み

- 外部から ExecutionEngine を停止したい場合は `data/kill.flag`（path は Settings.kill_flag_path）を作成する方法があります。KillSwitch は監視条件（ドローダウン超過、ポジション数超過など）によりこのフラグを作成します。ExecutionEngine 側はこのファイルを参照して安全停止します。
- run_monitoring / run_execution はプロジェクトルートの `data/stop_requested.flag` を検知してループを終了します（管理用のグローバル停止フラグ）。
- Settings に `KILL_FLAG_CLEAR_ON_START` が `1` のときは起動時に kill.flag を自動クリアする挙動があります（本番では `0` 推奨）。

---

## ログ

- ログは `kabusys.utils.logging_setup.setup_logging` を通じて統一的に設定されます。
- 出力先:
  - stdout（StreamHandler）
  - ファイル: default `logs/<app_name>.log` 日次ローテーション（30日分保持）
- ログレベルは `LOG_LEVEL` 環境変数または setup_logging の引数で設定します。

---

## よくあるトラブルシューティング

- ファイル作成エラー（data/ または logs/ の作成失敗）
  - 実行ユーザーに書き込み権限があるか確認してください。
- `.env` がロードされない
  - 自動ロードを無効化しているか（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - プロジェクトルートが検出されないと自動ロードをスキップします（.git または pyproject.toml が目印）。
- 必須環境変数エラー
  - `python -m kabusys.validate_config` を実行して不足している環境変数を確認してください。
- OpenAI API 呼び出し失敗
  - `OPENAI_API_KEY` が正しいか、ネットワーク接続、レート制限に注意してください。リトライロジックは一部に実装されていますが、API制限は運用で管理してください。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 以下の主要モジュールと簡単な説明です。

- kabusys/
  - __init__.py                     — パッケージ定義（__version__ 等）
  - config.py                       — Settings クラス（環境変数読み込み・検証、自動 .env ロード）
  - config_setup.py                 — .env 対話式ウィザード
  - validate_config.py              — 起動前設定検証 CLI
  - run_monitoring.py               — Monitoring ポーリングループ起動スクリプト
  - run_execution.py                — ExecutionEngine 起動スクリプト

  - utils/
    - logging_setup.py              — ログ設定ユーティリティ
    - process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py              — SQLite 監視 DB 永続化層
    - system_monitor.py             — システム・データ鮮度監視
    - trade_monitor.py              — 取引ログ監視（滞留注文等）※（実装あり）
    - risk_monitor.py               — ドローダウン・ポジション上限監視
    - monitoring_engine.py          — 各 Monitor を束ねるエンジン
    - kill_switch.py                — kill.flag の書き込みユーティリティ
    - alert_manager.py              — アラート送信（LINE 等）※（実装あり）
  - execution/
    - execution_engine.py           — ExecutionEngine 本体（run_session 等）
    - order_manager.py              — 発注管理
    - order_repository.py           — 発注履歴 / CRUD
    - broker_factory.py             — BrokerClient の生成（Mock/Live 切替）
    - reconciler.py                 — 注文整合処理
    - risk_manager.py               — 発注前リスクチェック
  - portfolio/
    - portfolio_builder.py          — 候補選定・重み付け
    - position_sizing.py            — 発注株数計算
    - risk_adjustment.py            — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py            — ファクター計算（momentum/value/volatility）
    - feature_exploration.py        — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py                   — ニュースセンチメント（OpenAI 呼び出し）
    - regime_detector.py            — マクロ+MA200 によるレジーム判定（OpenAI 補助）
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成

注: 上記は主要ファイルの要約です。詳細は各モジュールの docstring を参照してください。

---

## 開発者向けメモ

- DB マイグレーション: monitoring_db.init_monitoring_db は既存 DB に列を追加する軽量マイグレーションを含んでいます（冪等）。
- テスト性重視: 多くの関数は副作用を避け純粋関数として実装されており、ユニットテストが書きやすい構造になっています（例: portfolio.*, research.*）。
- 外部 API（OpenAI 等）コールは個別のラッパー関数を通しており、テスト時は patch / モックで差し替え可能です。

---

必要に応じて、README に具体的な例（.env.example のサンプル、requirements.txt の内容、各コンポーネントの起動手順の詳細）を追加できます。追記したい項目があれば教えてください。