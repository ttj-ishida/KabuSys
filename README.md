# KabuSys — 日本株自動売買システム

バージョン: 0.1.0

このリポジトリは日本株の自動売買・研究・監視を目的とした小規模なフレームワークです。発注エンジン（ExecutionEngine）と監視コンポーネント、ポートフォリオ構築・リスク調整ロジック、ファクター計算・研究ツール、OpenAI を使ったニュース NLP / レジーム判定などを含みます。

---

## 主要な特徴（概要）

- 実行コンポーネント
  - ExecutionEngine（本番 / ペーパートレード対応。環境変数 KABUSYS_ENV により動作モードを切替）
  - ブローカークライアントのファクトリ（本番は kabuステーション、paper_trading 時は MockBrokerClient）
- 監視コンポーネント
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite（monitoring.db）に監視ログを永続化する MonitoringDB
  - Kill Switch（条件に応じて data/kill.flag を書き込み、Execution を安全停止）
  - stop フラグファイル（data/stop_requested.flag）によるローカル停止
- ポートフォリオ構築
  - 候補選定、等金額・スコア加重配分、リスクベースのポジションサイズ決定、セクター上限適用、レジーム乗数
- 研究（Research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上の prices_daily / raw_financials を参照）
  - 将来リターン・IC（Information Coefficient）・統計サマリ
- AI（OpenAI）
  - ニュース記事のセンチメントスコア化（news_nlp）
  - マクロ + ETF MA200 を組み合わせた市場レジーム判定（regime_detector）
  - OpenAI の利用は環境変数 OPENAI_API_KEY が必要
- ツール
  - Paper Trading の検証レポート生成スクリプト（tools/paper_verification_report.py）
- ユーティリティ
  - 統一ログ設定（logs/ に日次ローテート）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - .env ウィザード（config_setup）と設定検証 CLI（validate_config）

---

## セットアップ（開発環境）

想定: Python 3.10+（型注釈に union 型などを使用）

1. リポジトリをクローンする
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - Unix/macOS:
     - source .venv/bin/activate
   - Windows:
     - .venv\Scripts\activate

3. 必要な依存パッケージをインストール
   - 必須（主要なランタイム）:
     - duckdb
     - psutil
     - openai
   - 任意 / 開発:
     - PyYAML（config の YAML 検証に使用）
   - 例:
     - pip install duckdb psutil openai PyYAML

   > 補足: requirements.txt はこのリポジトリに含まれていない場合があります。上記パッケージをプロジェクトの用途に合わせてインストールしてください。

4. データ / ログディレクトリの作成（通常は自動作成されますが手動で準備しておくと権限エラーが出にくいです）
   - mkdir -p data logs

5. .env の初期作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは .env（デフォルトプロジェクトルート）を生成・更新します。
   - ウィザード実行後、設定を検証:
     - python -m kabusys.validate_config
     - 本番に慎重を期す場合は --strict を付与（警告も失敗として扱う）

6. 重要な環境変数（一部）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須、本番用）
   - KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
   - OPENAI_API_KEY（AI 機能を使用する場合）
   - LOG_LEVEL（デフォルト: INFO）
   - PAPER_FILL_MODE（ペーパートレードの約定挙動: instant|partial|never|reject、デフォルト: instant）
   - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動でクリアするか: 0/1、デフォルト 0）

---

## 実行方法（使い方）

以下は代表的な実行コマンド例です。各スクリプトはパッケージモジュールとして実行できます。

- Execution Engine を起動（本番またはペーパートレードは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - ペーパートレード時（KABUSYS_ENV=paper_trading）は MockBrokerClient を使い、data/paper_trading.db に記録されます。
  - 実行中の強制停止:
    - ローカル停止フラグを作成: touch data/stop_requested.flag（run_execution はこのファイルを検出して安全に停止します）
    - Kill Switch（リスク条件）により停止する場合は data/kill.flag が作成されます。

- Monitoring を起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で変更:
    - export MONITOR_POLL_INTERVAL=30  # 単位: 秒（1秒以上の整数）
  - run_monitoring は監視ログを sqlite_path に記録し、duckdb も接続します。

- .env の対話式作成 / 更新
  - python -m kabusys.config_setup

- 設定検証（起動前のチェック）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポートの生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI / Research / Portfolio モジュールをプログラムから呼び出す（例）
  - Python REPL またはスクリプト内で:
    - from kabusys.research import calc_momentum
    - from kabusys.ai import score_news
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - AI 関数（score_news, score_regime）を使うには OPENAI_API_KEY を設定してください。

---

## 運用上の重要ポイント

- Kill Switch と停止フラグ
  - Kill Switch はリスク条件（ドローダウン、ポジション上限等）を満たすと data/kill.flag に理由を書き込みます。ExecutionEngine はこのフラグを参照して停止できます。
  - run_execution/run_monitoring は data/stop_requested.flag を検知して自己終了します（手動停止用）。
  - 本番環境では KILL_FLAG_CLEAR_ON_START はデフォルト 0 にして自動クリアを無効化することを推奨します。

- DB 関連
  - 監視 DB（SQLite）: default data/monitoring.db（monitoring 用テーブルを自動作成・マイグレーションする init_monitoring_db を提供）
  - 分析 DB（DuckDB）: default data/kabusys.duckdb
  - ペーパートレード用 SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に分離して使用）

- ログ
  - ログ設定は kabusys.utils.logging_setup.setup_logging で統一
  - デフォルトのログディレクトリ: logs/
  - 日次ローテーション（30日保持）

- プロセス優先度
  - 起動スクリプトは set_process_priority("high") を呼び出します（プラットフォーム依存、psutil による実装）

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 以下の主な構成を抜粋）

- src/kabusys/
  - __init__.py (version)
  - config.py — 環境変数読み込み / Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）による銘柄スコア付与
    - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（schema/init）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py — （注文ログ監視）※本ベースコードに含まれる想定モジュール
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - monitoring_engine.py — 各 Monitor の統合とアラート送出
    - alert_manager.py — （アラート送信ロジック 想定）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・スケーリング
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum, volatility, value 等）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - utils/
    - logging_setup.py — ログ初期化ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/monitoring_db.py — DB スキーマ定義・MonitoringDB クラス

（注）一部モジュールはここに示した以外の補助ファイルや想定される実装を含むことがあります。

---

## 開発・拡張メモ

- DuckDB 接続を受け取る設計により、研究/ファクター計算は本番 DB に直接アクセスせずオフライン分析に利用できます。
- AI 呼び出し部分はリトライ・バリデーションの保険付きで実装されていますが、API コストや失敗ケースのハンドリングは運用時に注意してください（API キー、レート制限）。
- ポートフォリオ構築・ポジションサイズ計算は純粋関数として実装されており、ユニットテストが行いやすい設計です。

---

## よくあるコマンド一覧まとめ

- .env ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動
  - python -m kabusys.run_execution
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 短周期: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

もし README に追加したい「導入手順のスクリーンショット」「サンプル .env」「API のレスポンス例」「ユニットテストの実行方法」などがあれば、必要な情報を教えてください。README をその内容に合わせて更新します。