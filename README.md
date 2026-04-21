# KabuSys — 日本株自動売買システム（概要 README）

このリポジトリは、シンプルな日本株向け自動売買システムの主要コンポーネント群を含みます。実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）、AI（ニュースNLP / レジーム判定）、およびユーティリティ類がまとまっています。

以下は主な説明・セットアップ・使い方・ディレクトリ構成です。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（実行コマンド / よく使うスクリプト）
- 環境変数（主要項目とデフォルト）
- 停止・キルシグナルについて
- ディレクトリ構成（主要ファイルの説明）

---

## プロジェクト概要

KabuSys は日本株自動売買の基盤的なモジュール群を含んだプロジェクトです。設計方針として以下を重視しています。

- 本番（live）とペーパートレード（paper_trading）を環境で明確に分離
- SQLite / DuckDB を用いた永続化（監視ログ・トレード履歴・分析データ）
- モジュール単位での純粋関数設計（ポートフォリオ構築・サイズ決定等）
- 監視（Monitoring）によるサービス健全性チェックと自動的な Kill Switch
- OpenAI API を用いたニュース NLP / レジーム判定（任意）
- ログ・プロセス優先度・PID 管理など運用に配慮したユーティリティ

---

## 主な機能一覧

- 実行エンジン（ExecutionEngine）起動スクリプト（run_execution.py）
  - 本番／ペーパーを切り替え、ブローカークライアントを注入してセッション実行
  - Paper trading 時は MockBrokerClient を用い、data/paper_trading.db に記録

- 監視モジュール（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視ログは SQLite（data/monitoring.db 等）へ永続化
  - KillSwitch による停止フラグ（data/kill.flag）書き出し

- ポートフォリオ構築（kabusys.portfolio）
  - 銘柄選定・重み計算（等配分・スコア配分）
  - リスク調整（セクター上限・レジーム乗数）
  - 株数決定（position sizing、単元株丸め、aggregate cap）

- リサーチ（kabusys.research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を参照）
  - 将来リターン計算、IC（情報係数）や統計サマリ機能

- AI モジュール（kabusys.ai）
  - news_nlp: ニュース記事を集約して OpenAI に投げ、銘柄別センチメントを ai_scores に保存
  - regime_detector: ETF 指標 + マクロニュースで市場レジーム（bull/neutral/bear）判定

- 設定ツール
  - config_setup.py: .env を対話式で作成
  - validate_config.py: .env / config/*.yaml の整合性チェック

- 運用ツール
  - tools/paper_verification_report.py: ペーパートレード DB を解析してレポート出力

- ユーティリティ
  - logging_setup: 統一されたログ設定（コンソール + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定

---

## セットアップ手順

前提
- Python 3.10 以上（コード中での union 型注記など）
- SQLite は標準ライブラリで利用
- 開発環境では適宜仮想環境を推奨（venv / poetry 等）

1. リポジトリをクローンし仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - 必須（最低限）
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
   - 推奨/オプション
     - PyYAML（config/*.yaml の構文検査を行う場合）
   例:
     pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がない場合は上記を個別にインストールしてください）

3. .env の作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - もしくは手動でファイルをプロジェクトルートに作成（下欄「環境変数」を参照）

4. 設定検証
   - python -m kabusys.validate_config
   - 厳密モード（警告も FAIL）:
     python -m kabusys.validate_config --strict

5. データディレクトリ
   - デフォルトでは data/ 配下の SQLite / PID / flag 等を使います。必要に応じて .env のパスを変更してください。
   - ログディレクトリは logs/（LOG_DIR 環境変数で上書き可）

---

## 使い方

主要な CLI/起動ポイント:

- 実行エンジン（注文処理・ペーパートレード切替）
  - python -m kabusys.run_execution
  - 挙動: KABUSYS_ENV=paper_trading の場合は paper DB を使い MockBrokerClient で完全分離されます

- 監視サービス（System / Trade / Risk のポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 監視は環境にかかわらず本番 sqlite_path を使用します（監視データは共通で本番 DB を参照）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いで exit(1)

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

AI / リサーチ機能は Python API として呼び出す設計です（例: kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime）。これらを実行する場合は OPENAI_API_KEY を設定してください。

---

## 環境変数（主要項目とデフォルト）

必須（起動前に設定が必要）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主な任意 / デフォルト
- KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 SQLite DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）デフォルト INFO
- LOG_DIR — ログ保存ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"0"/"1", デフォルト 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒, デフォルト 60）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant|partial|never|reject、デフォルト "instant"）

参考: config_setup.py を使うと対話で .env を作成できます。

---

## 停止・キル信号

運用上の仕組み：
- 停止要求（run_* スクリプト両方で参照）
  - data/stop_requested.flag（run_monitoring/run_execution がこれを検知して終了）
  - path はスクリプト内で設定（project root の data/stop_requested.flag）

- Kill Switch（システム的停止）
  - KillSwitch が条件を満たすと data/kill.flag を書き込みます。ExecutionEngine は kill.flag が存在すると動作を停止するよう設計されています。
  - KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動クリア（ただし本番では危険なので推奨しません）

- PID ファイル
  - data/execution.pid 等に PID を書きます（プロセス管理・デッド判定に使用）

---

## 主要ファイル / ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要コンポーネントと簡単な説明です。

- src/kabusys/__init__.py
  - パッケージ定義、バージョン

- 起動スクリプト
  - run_execution.py — ExecutionEngine（発注エンジン）起動
  - run_monitoring.py — SystemMonitor のポーリングループ起動

- 設定関連
  - config.py — Settings クラス (環境変数読み込み / デフォルト値 / バリデーション)
  - config_setup.py — .env 作成ウィザード
  - validate_config.py — 起動前検証（required env / config yaml 等）

- monitoring/
  - monitoring_db.py — SQLite を使った監視テーブル作成 / CRUD ラッパ
  - system_monitor.py — システムリソース・データ鮮度監視
  - trade_monitor.py —（trade 関連監視 — 実装参照）
  - risk_monitor.py — ドローダウン・ポジション制限監視
  - monitoring_engine.py — 各モニタを束ねる実行ループ
  - kill_switch.py — kill.flag 管理
  - alert_manager.py —（LINE 通知等の抽象化）

- execution/
  - execution_engine.py — ExecutionEngine コア（エンジン設定・セッション制御）
  - broker_factory.py — ブローカークライアント生成（本番 / モックの切替）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py など

- portfolio/
  - portfolio_builder.py — 候補選出・重み計算
  - position_sizing.py — 株数決定・スケーリング
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — Momentum / Volatility / Value 等の計算（DuckDB 接続を受ける）
  - feature_exploration.py — 将来リターン・IC 計算・統計サマリ

- ai/
  - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py — ETF MA とマクロニュースの LLM 評価を合わせて市場レジーム算出

- tools/
  - paper_verification_report.py — ペーパートレード DB の集計・判定レポート生成

- utils/
  - logging_setup.py — 統一ログ設定（stdout + 日次ファイルローテーション）
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

- data/
  - （運用時に生成される）monitoring.db, paper_trading.db, kill.flag, stop_requested.flag, execution.pid 等

---

## 運用上の注意点 / ベストプラクティス

- .env を絶対に Git にコミットしない（config_setup.py のヘッダにも注記あり）
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にすることを強く推奨
- AI 機能は OPENAI_API_KEY が必要。API 呼び出しに失敗した場合はフェイルセーフでスキップまたはデフォルト値を使う設計ですが、実運用時はレート制限やコストに注意
- 監視（monitoring）はシステムの健全性を保証する補助であり、十分なログ・アラート設定を行ってください（LINE 通知等）
- Paper trading は本番 DB と完全分離しているため、動作検証はペーパートレード環境で行ってください

---

もし README に追記して欲しい点（例: 各設定値の具体的な推奨値、運用手順のチェックリスト、デプロイ手順や systemd ユニット定義例など）があれば教えてください。必要に応じてサンプル .env テンプレートや systemd サービスの例も作成します。