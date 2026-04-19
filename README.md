# KabuSys

日本株向け自動売買システムの一部を切り出したリポジトリ。戦略・ポートフォリオ構築、注文実行、監視、研究、AI（ニュースセンチメント / レジーム判定）などのモジュール群を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するコンポーネント群です。本リポジトリは以下の役割を持つ主要機能を提供します。

- ExecutionEngine：ブローカー操作（本番 or ペーパートレード）を担う実行エンジン
- Monitoring：システム状態、注文状態、リスク監視、Kill Switch を含む監視基盤
- Portfolio：銘柄選定・重み付け・株数決定などのポートフォリオ構築ロジック
- Research：ファクター計算・特徴量探索など分析用モジュール（DuckDB を利用）
- AI：ニュースセンチメント（OpenAI）によるスコアリングや市場レジーム判定
- ユーティリティ：ログ設定、プロセス優先度設定、設定ファイル読み書き等

設計方針の一例：
- DuckDB / SQLite を用いたローカルデータ管理
- 本番とペーパートレードの明確な分離（DB・ブローカーの切替）
- ルックアヘッドバイアスを避ける設計（日時参照やクエリの排他条件）
- フェイルセーフ（API失敗などは安全側へフォールバック）

---

## 主な機能一覧

- 実行（execution）
  - ブローカー切替（live / paper_trading）
  - OrderManager / RiskManager / Reconciler 等による注文管理
- 監視（monitoring）
  - SystemMonitor：CPU/メモリ/ディスク、データ鮮度、Execution プロセス監視
  - TradeMonitor：注文滞留や約定異常検出（コード上に存在）
  - RiskMonitor：ドローダウン・ポジション上限の監視とアラート記録
  - KillSwitch：閾値到達時に data/kill.flag を作成して Execution を停止
  - MonitoringEngine：上記モニタを定期実行し、AlertManager 経由で通知
  - SQLite に監視ログを永続化（monitoring_db）
- ポートフォリオ（portfolio）
  - 候補選定、等ウェイト・スコア重み付け、リスク調整、ポジションサイズ計算
- リサーチ（research）
  - モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB 経由）
  - 将来リターン、IC（Information Coefficient）、統計サマリ
- AI（ai）
  - news_nlp: raw_news を集約して OpenAI を使い銘柄ごとにセンチメントスコアを生成し ai_scores に書き込み
  - regime_detector: ETF とマクロニュースを組み合わせて market_regime を算出・保存
- ツール
  - config_setup: .env を対話式に生成/更新するウィザード
  - validate_config: 起動前に環境変数・config/*.yaml 等の妥当性を検証
  - paper_verification_report: ペーパートレード DB から検証レポートを生成

---

## 要件（推奨）

- Python 3.9+
- 必要なパッケージ（主要）
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイルの検証を行う場合）
- SQLite（標準ライブラリ）
- ネットワークアクセス（OpenAI を使用する場合）

インストール例（venv 使用例）:
- python -m venv .venv
- source .venv/bin/activate
- pip install -r requirements.txt
（requirements.txt を用意している場合。一時的に個別インストールするなら `pip install duckdb psutil openai PyYAML`）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動
2. 仮想環境を作成して有効化（推奨）
3. 依存パッケージをインストール
4. .env を作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参考）
5. 設定を検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱い
6. デフォルトのデータディレクトリを作成（必要に応じて）
   - mkdir -p data logs

重要な環境変数（主なものとデフォルト）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード専用 DB）
- LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI を利用する場合に必須
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定モード）
- KILL_FLAG_CLEAR_ON_START: 0 | 1（本番は 0 推奨）

ログ:
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存
- コンソール出力は stdout に出ます

---

## 使い方（実行例）

- ExecutionEngine を起動（本番/ペーパートレードは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 動作: Settings を読み、適切な SQLite（paper_trading なら専用 DB）と DuckDB に接続し ExecutionEngine を別スレッドで実行
  - 停止は data/stop_requested.flag を作成することで開始待機ループがエンジン停止を検知して安全終了します
  - pid ファイルは data/execution.pid（デフォルト）に書き込まれます

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を参照します（環境にかかわらず）
  - 停止フラグ: data/stop_requested.flag を作成するとループを抜けます

- 設定ウィザード（.env の作成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH を使うか --db で DB を指定

- AI 関連
  - OpenAI API キー (OPENAI_API_KEY) を設定した上で、以下の関数をコードから呼び出す
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - DuckDB 接続を渡して実行する設計

停止・Kill Switch の考え方:
- KillSwitch は RiskMonitor 等と連携し、条件を満たした場合に data/kill.flag を作成します。ExecutionEngine はこのフラグを検出して安全に停止する仕組みを持ちます。
- 管理上、KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動でクリアしますが、本番では 0 のままにすることが推奨されます。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / .env 自動読み込み・Settings クラス
- config_setup.py — .env 作成ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト

src/kabusys/execution/
- broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
  （注文実行に関する主要コンポーネント）

src/kabusys/monitoring/
- monitoring_db.py — SQLite ベースの永続化層
- system_monitor.py — システム / データ鮮度監視
- trade_monitor.py — 注文関連の監視（ファイルに同様の実装がある）
- risk_monitor.py — ドローダウン・ポジション上限監視
- kill_switch.py — Kill Switch 実装（flag ファイル書き込み）
- monitoring_engine.py — 各モニタを束ねるエンジン
- alert_manager.py — 通知管理（LINE 等、実装に依存）

src/kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py
- __init__.py

src/kabusys/research/
- factor_research.py
- feature_exploration.py
- __init__.py

src/kabusys/ai/
- news_nlp.py — ニュースを OpenAI でスコアリング
- regime_detector.py — レジーム判定

src/kabusys/tools/
- paper_verification_report.py — ペーパートレード検証レポート生成

src/kabusys/utils/
- logging_setup.py — 統一的なログ設定
- process_priority.py — プロセス優先度 / CPU affinity のユーティリティ

データ・ログ（デフォルトパス）
- data/monitoring.db （SQLITE_PATH デフォルト）
- data/paper_trading.db （PAPER_TRADING_SQLITE_PATH デフォルト）
- data/kabusys.duckdb （DUCKDB_PATH デフォルト）
- data/execution.pid, data/kill.flag, data/stop_requested.flag
- logs/<app_name>.log

---

## 注意点 / 運用上のヒント

- 本番環境 (KABUSYS_ENV=live) では LINE の通知設定・Kill Switch 設定等を十分に確認してください。validate_config の live 用チェックが有用です。
- OpenAI を使う機能は API キーが必須であり、コストとレイテンシを考慮してください。失敗時はフォールバック動作が組み込まれていますが、頻繁な失敗は運用リスクになります。
- ペーパートレードは paper_sqlite_path に完全に分離して保存されるようになっています（本番 DB と混ざらない）。
- ログディレクトリの作成に失敗するとファイル出力はスキップされますが、コンソール出力は残ります。適切に logs ディレクトリを用意してください。
- モジュール間で DuckDB / SQLite の接続を渡す設計になっています。複数プロセスでの同時アクセスやバックアップ運用は注意が必要です。

---

## 開発・拡張ポイント

- StrategyModel や PortfolioConstruction の仕様文書に基づいて戦略を実装できます（コード内に参照あり）。
- AI モジュールはプロンプトやモデルを変更して精度改善が可能です（レスポンスバリデーションは堅牢に実装済み）。
- Monitoring のアラートチャネル（LINE 等）は AlertManager を拡張して対応してください。

---

必要であれば、README をさらに詳しく（各 CLI のオプション一覧、サンプル .env、よくあるトラブルシュート）に拡張できます。どの部分を詳しく書いて欲しいか教えてください。