# KabuSys

日本株向けの自動売買システム（試作版）。  
戦略の研究・ファクター計算、ポートフォリオ構築、発注実行（本番 / ペーパートレード分離）、監視・アラート、LLM を使ったニュース NLP・レジーム判定等を含むモジュール構成になっています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のコンポーネントで構成されています。

- ExecutionEngine: ブローカークライアント経由で発注を行う実行エンジン。KABUSYS_ENV に応じて本番 / ペーパートレードを切替。
- Monitoring: システム稼働状況・発注ログ・リスクを監視し、必要に応じて Kill Switch（停止フラグ）を書き込む。
- Portfolio: 候補選定・重み計算・ポジションサイズ決定などポートフォリオ構築ロジック（純粋関数）。
- Research: DuckDB を用いたファクター計算・特徴量解析ユーティリティ。
- AI: OpenAI（gpt-4o-mini など）を利用したニュースセンチメント（ai_scores）や市場レジーム判定。
- Tools: ペーパートレードの検証レポート生成などのユーティリティスクリプト。
- 設定ユーティリティ: .env ウィザード（対話式）、設定検証 CLI など。

設計上のポイント:
- ペーパートレード時は本番 DB と分離して `data/paper_trading.db`（デフォルト）を使用。
- 監視ログは SQLite（デフォルト: `data/monitoring.db`）へ永続化。
- 分析用に DuckDB（デフォルト: `data/kabusys.duckdb`）を使用。
- LLM（OpenAI）呼び出しは API キー必須、エラーはフェイルセーフで処理を続行する設計。

---

## 主な機能一覧

- 設定管理
  - .env ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- 実行エンジン
  - 本番 / ペーパーの切り替え（KABUSYS_ENV）
  - Risk Manager / Order Manager / Reconciler を備えた ExecutionEngine（run_execution）
  - 実行中の停止はフラグファイルで制御（data/stop_requested.flag, data/kill.flag）
- 監視
  - SystemMonitor: CPU/Mem/Disk / データ鮮度 / プロセス生存確認
  - TradeMonitor: 発注ログの滞留・約定異常検出（実装参照）
  - RiskMonitor: ドローダウン、ポジション数上限の検出とログ化
  - KillSwitch: 条件に応じて kill.flag を書き込み Execution を停止
  - 監視ループ起動スクリプト（run_monitoring）
- ポートフォリオ構築
  - 候補選定、等重・スコア重み、リスクベースのポジション計算、セクターキャップ、レジーム乗数
- リサーチ（DuckDB）
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- AI/LLM
  - ニュース記事の銘柄別センチメント集約と ai_scores 書き込み
  - マクロニュース + ETF MA200 を用いた市場レジーム判定
  - エラー/429/タイムアウトに対してリトライ制御あり
- ツール
  - Paper Trading の検証レポート生成（期間指定可）

---

## 前提・依存関係

推奨 Python バージョン: 3.10+（型記法に | を使用）  
主なパッケージ（代表例）:
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config 検証で YAML 内容チェックを行う場合）
- その他、標準ライブラリのみで動作する部分も多いです。

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動。
2. 仮想環境を用意して依存パッケージをインストール（上記参照）。
3. 初期設定 (.env) を作成:
   - 対話式ウィザード:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは手動で `.env` を作成。最低限必要な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH（例: data/kabusys.duckdb）
     - SQLITE_PATH（例: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB; 任意）
     - OPENAI_API_KEY（AI 機能を使用する場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用、任意）
     - LOG_LEVEL（例: INFO）
4. 設定の検証:
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL にしたい場合:
   python -m kabusys.validate_config --strict
   ```
5. 必要に応じてデータディレクトリを作成（logs/, data/ 等は自動作成されますが権限に注意）。

注意:
- Paper Trading モード（KABUSYS_ENV=paper_trading）は MockBrokerClient を使い、paper 用 SQLite（デフォルト: data/paper_trading.db）に記録されます。本番データベースと分離されます。
- 監視コンポーネントは常に本番の sqlite_path を使用する実装になっています（run_monitoring の仕様）。

---

## 使い方（起動方法）

- 実行エンジン（Execution）起動:
  ```bash
  python -m kabusys.run_execution
  ```
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中は data/execution.pid に PID が記録されます（config の pid_file_path で変更可能）。
  - 停止は data/stop_requested.flag を作成するか、Execution 側に kill.flag が書かれると停止します。

- 監視ループ起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は Settings に設定された sqlite_path（本番 DB）と duckdb_path を使用します。
  - 停止はプロジェクトルート/data/stop_requested.flag を作成することで行います。

- .env ウィザード（設定作成）:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連（プログラムから呼ぶ例）:
  - ニュースセンチメント: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OpenAI API キーが必要（env 変数 OPENAI_API_KEY または引数で指定）。

ログ:
- デフォルトで logs/<app_name>.log に日次ローテートで出力されます（logs/ ディレクトリは自動作成を試みます）。
- ログレベルは LOG_LEVEL 環境変数で制御。

停止 / Kill Switch:
- KillSwitch は条件を満たすと `data/kill.flag` に理由を記述して書き込みます。ExecutionEngine はこれを検出して発注を停止します（設定により起動時に auto-clear の挙動あり）。

---

## よく使う環境変数（要点）

- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI API キー（AI 機能使用時）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用）

---

## トラブルシューティング

- ディレクトリ作成失敗（logs/ や data/）:
  - 書き込み権限を確認してください。ログファイルが作成できない場合はコンソール出力のみになります。
- psutil 関連の権限エラー:
  - process priority 設定は特定環境で権限不足になることがあります。警告ログが出ますが、処理は継続します。
- OpenAI 呼び出しの失敗:
  - API キーの有無を確認し、レート制限やネットワーク障害はリトライで回復を試みます。頻繁に失敗する場合は API キーやネットワーク、制限の見直しをしてください。
- validate_config で警告やエラーが出た場合はメッセージに従って .env や config/*.yaml を整備してください。警告をエラー扱いにしたい場合は --strict を使用します。

---

## ディレクトリ構成（主要ファイル）

以下はプロジェクト内の主要なモジュールと役割の概観です（src/kabusys 配下）。

- kabusys/
  - __init__.py — パッケージ初期化、バージョン
  - config.py — 環境変数 / 設定読み込み・Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - execution/ (実行関連: BrokerFactory, ExecutionEngine, OrderManager, RiskManager, Reconciler 等)
    - (実装ファイル群: ExecutionEngine, OrderRepository, OrderManager, RiskManager, Reconciler, broker_factory, ...)
  - monitoring/
    - monitoring_db.py — 監視ログ用 SQLite ラッパ（初期化 / CRUD）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - system_monitor.py — CPU/Memory/Disk/データ鮮度/プロセス監視
    - trade_monitor.py — 発注ログ・約定の監視（存在）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - alert_manager.py — アラート通知（LINE 等の抽象）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算・資金配分
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - data/
    - pipeline.py — DuckDB / prices_daily などデータパイプライン（参照）
    - stats.py — 正規化ユーティリティ（zscore 等）
  - ai/
    - news_nlp.py — ニュースセンチメント取得（OpenAI）
    - regime_detector.py — マクロ + MA200 でレジーム判定
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（stdout + 日次ファイルローテート）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（実際のファイル配置はプロジェクトの src ディレクトリを参照してください）

---

## 開発上の注意点 / 今後の拡張案

- DuckDB と SQLite のスキーマ変更時のマイグレーションは最小限の互換性対応ロジックを含めていますが、バックアップを取ってから更新してください。
- AI（OpenAI）呼び出しはコストがかかるため、運用時はバッチ頻度やモデル選択を検討してください。
- 現在ポートフォリオの単元株数（lot_size）はグローバル固定（デフォルト 100）です。銘柄ごとの単元対応を行う場合は拡張が必要です。
- 本番（live）環境では Kill Switch や通知設定を慎重に扱ってください（validate_config にいくつかのガードあり）。

---

必要であれば、この README をベースに「導入手順のスクリーンショット付きガイド」や「各モジュールの詳細設計ドキュメント（API/関数一覧、使用例）」を作成します。どの内容を優先して追加しますか？