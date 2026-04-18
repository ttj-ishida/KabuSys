# KabuSys

日本株向け自動売買システムの一部（ライブラリ・実行ユーティリティ群）。

このリポジトリには以下の主要機能が含まれます：
- 注文・実行エンジン起動スクリプト（ExecutionEngine 起動）
- 監視（System / Trade / Risk）コンポーネントとポーリングループ
- 環境設定ウィザードと設定検証ツール
- ポートフォリオ構築・ポジションサイズ計算ユーティリティ（純粋関数群）
- リサーチ用ファクター計算・解析ユーティリティ（DuckDB ベース）
- AI（LLM）を用いたニュースセンチメント / 市場レジーム判定モジュール
- Paper Trading 検証レポート生成スクリプト

以下は導入・利用に必要な情報と使い方のまとめです。

## 主な機能一覧
- 設定管理
  - .env 自動読み込み（.env / .env.local、OS 環境変数を保護）
  - 対話式ウィザードで .env を生成（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行関連
  - 実取引／ペーパートレードを切り替える ExecutionEngine 起動（kabusys.run_execution）
  - 実行エンジンに対する Kill Switch（フラグファイルによる停止）
  - PID ファイル管理（data/execution.pid）
- 監視関連
  - System / Trade / Risk Monitor（Polling）
  - 監視ログ永続化（SQLite、monitoring.db）
  - MonitoringEngine（アラート発行・Kill Switch 評価）
  - run_monitoring スクリプトで定期ポーリング（MONITOR_POLL_INTERVAL で間隔変更可能）
- ポートフォリオ構築
  - 候補選定、等ウェイト／スコア重み付け、位置サイズ計算、セクター制約、レジーム乗数
- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB と prices_daily/raw_financials）
  - 将来リターン・IC 計算・統計サマリ
- AI（OpenAI）
  - ニュースをまとめて LLM に送信し銘柄ごとのスコアを ai_scores テーブルへ保存
  - マクロニュースを用いた市場レジーム判定（market_regime テーブル）
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

## 必要要件（例）
- Python 3.10+
- 必須ライブラリ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で YAML のパースを行う場合のみ）
- 標準で使用する DB:
  - DuckDB（分析用、デフォルト: data/kabusys.duckdb）
  - SQLite（監視ログ、デフォルト: data/monitoring.db / ペーパートレード用: data/paper_trading.db）

（プロジェクトに requirements.txt がある場合はそちらを利用してください。なければ以下のようにインストールします）
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

## セットアップ手順（簡易）
1. リポジトリをクローンして作業ディレクトリへ移動。
2. 仮想環境を作成して依存パッケージをインストール（上記参照）。
3. 対話式ウィザードで .env を作成：
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは .env を生成・更新します（.env は絶対に Git にコミットしないでください）。
4. 設定検証：
   ```
   python -m kabusys.validate_config
   ```
   必須環境変数や config/*.yaml の基本チェックを行います。警告もエラー扱いにしたい場合は `--strict` を指定します。
5. データディレクトリ（data）や DuckDB/SQLite ファイルの配置を確認。初回実行時に監視用テーブルは自動作成されます（init_monitoring_db）。

## 重要な環境変数（主なもの）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境関連
  - KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development
  - LOG_LEVEL — ログレベル（DEBUG / INFO / ...）デフォルト: INFO
- DB パス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 SQLite パス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- Paper Trading
  - PAPER_FILL_MODE — MockBrokerClient の約定モード（instant / partial / never / reject）デフォルト: instant
- OpenAI
  - OPENAI_API_KEY — OpenAI API キー（AI モジュールで使用）
- 監視制御
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
  - KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動でクリアするか（1 = クリア、デフォルト: 0）
- 監視で使われるファイル
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）

.env のテンプレートは config_setup で生成されるフォーマットを参照してください。

## 使い方（主なコマンド）
- 環境設定ウィザード（.env を作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine を起動（本番/ペーパーは KABUSYS_ENV に依存）
  ```
  python -m kabusys.run_execution
  ```
  特記事項:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading DB（PAPER_TRADING_SQLITE_PATH）へ記録します。本番 DB と完全分離されます。
  - 起動時に data/stop_requested.flag（プロジェクトルート/data/stop_requested.flag）が存在すると起動を行わず終了します。
  - 実行中は data/execution.pid に PID を書きます。停止は Kill Switch（data/kill.flag）か外部プロセスから engine.stop() を呼ぶ等で行います。

- 監視ループを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は Settings.sqlite_path（監視用の production sqlite_path）を使用します（環境にかかわらず本番 sqlite_path を参照する設計）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```
  - デフォルトは PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI モジュール（プログラムから呼び出し）
  - ニューススコア付与:
    ```
    from kabusys.ai import score_news
    import duckdb, datetime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=datetime.date(2026,4,11), api_key="sk-...")
    ```
  - レジーム判定:
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=datetime.date(2026,4,11), api_key="sk-...")
    ```
  - いずれも OPENAI_API_KEY が設定されていれば api_key を省略できます。API 呼び出しは失敗時にフェイルセーフ（ゼロ等）で続行する設計になっていますが、API キーが未設定の場合は ValueError が投げられます。

## Kill Switch / フラグファイル
- Kill Switch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります（KillSwitch クラス）。
- kill.flag が存在すると ExecutionEngine は起動時に自動的に停止（または監視ループが停止フラグを検知して終了）します。
- 起動時に kill.flag を自動で消す設定（KILL_FLAG_CLEAR_ON_START=1）がありますが、本番では 0 を推奨します。
- stop リクエスト用のファイル: data/stop_requested.flag（run_monitoring/run_execution がチェックします）

## DB / マイグレーションについて
- 監視テーブルは init_monitoring_db() により「冪等的」に作成／必要なカラム追加を行います（起動時に自動実行されます）。
- DuckDB は価格データ / 財務データの分析用途で使用します。prices_daily / raw_financials / raw_news 等のテーブルを前提とする関数群があります。
- Paper Trading 用の SQLite は本番の monitoring DB と分離して使うのが想定されています（settings.is_paper 判定により paper_sqlite_path を利用）。

## ログ・監視閾値
- Settings で CPU / メモリ / ディスクの閾値、ログレベル等を環境変数で設定可能です（例: CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT 等）。
- RiskMonitor はドローダウンやポジション上限を検出して risk_logs に記録します。発生時に Kill Switch を発動させるロジックもあります。

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数/設定読み込みロジック（.env 自動ロード含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - monitoring/
    - monitoring_db.py — SQLite による監視ログ永続化層
    - system_monitor.py — CPU/メモリ/データ鮮度/プロセス監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 操作ユーティリティ
    - monitoring_engine.py — 各 Monitor を束ねたポーリング/アラート連携
    - alert_manager.py — （アラート送信のラッパー — 実装箇所参照）
  - portfolio/ — 候補選定・配分・リスク調整・ポジションサイジング
  - research/ — ファクター計算・特徴量探索
  - ai/
    - news_nlp.py — ニュース -> LLM -> ai_scores 書込み
    - regime_detector.py — マクロ + ma200 によるレジーム判定
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - execution/ — ExecutionEngine, OrderManager, BrokerFactory 等（主要なエンジン実装。起動スクリプトから利用）

※ 上記は本リポジトリの主要モジュール一覧（提供されたコードの範囲に基づく）。実際の実装ファイルはさらに存在する場合があります。

## 運用上の注意とベストプラクティス
- .env は機密情報を含むため、決してバージョン管理に含めないでください。
- 本番環境（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）を必ず確認してください。validate_config は live 時に追加の警告を出します。
- Kill Switch（data/kill.flag）や stop_requested.flag を利用した安全な停止運用を設計してください。KILL_FLAG_CLEAR_ON_START=1 の使用は本番では危険です。
- OpenAI を利用する機能は API レート制限やエラーに対してリトライ・フォールバック処理が実装されていますが、コスト管理・トークン制限には留意してください。
- DuckDB / SQLite ファイルは適切なバックアップとディスク容量の確保を行ってください。

---

この README は提供されたコードベース（主要モジュール）を基にした概要ドキュメントです。具体的な実装や追加のユーティリティ、設定サンプルはリポジトリ内の各モジュール（config_setup.py や config/*.yaml の生成スクリプト等）を参照してください。必要であれば、各モジュールの詳細な使い方や API ドキュメントも作成できます。