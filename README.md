README — KabuSys（日本語）
===========================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤のコードベースです。  
主な目的は、信号生成 → ポートフォリオ構築 → 発注管理（ExecutionEngine）と、
システム監視（Monitoring）、研究／ファクター計算、AI を利用したニュースセンチメント分析などを統合することです。

特徴（抜粋）
-----------
- ExecutionEngine：発注管理／レコンシリエーション／リスク管理を含む実行層
- Paper trading 分離：KABUSYS_ENV=paper_trading 時は MockBroker を使用し、専用 DB に記録
- Monitoring：システム状態（CPU/メモリ/ディスク）・データ鮮度・注文ログを定期的に監視
- Kill Switch：閾値超過（ドローダウン・ポジション上限等）時に Execution を停止するフラグ機能
- Portfolio コンポーネント：候補選定・重み付け・ポジションサイズ計算・セクターキャップ等
- Research モジュール：モメンタム／バリュー／ボラティリティ等のファクター計算、IC/統計解析
- AI モジュール：OpenAI を用いたニュースのセンチメントスコアリング（news_nlp）と市場レジーム判定
- ユーティリティ：ログ設定、プロセス優先度 / CPU affinity 設定、.env ウィザードと設定検証
- ツール：Paper Trading の検証レポート生成スクリプト等

前提（推奨）
-------------
- Python 3.10+
- SQLite（標準ライブラリ利用）
- 推奨パッケージ（ランタイム依存）:
  - duckdb
  - psutil
  - openai（AI モジュールを使う場合）
  - PyYAML（config/*.yaml の検証を行う場合）
- Git ワークツリーに基づいて .env 自動読み込みを行う設計

セットアップ手順
----------------

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

3. 必要パッケージのインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - なければ最低限:
     - pip install duckdb psutil
     - AI 機能を使う場合: pip install openai
     - YAML 検証を使う場合: pip install pyyaml

4. .env の作成（ウィザード推奨）
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成

5. 設定の検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合は --strict を付与

主要な環境変数（抜粋）
--------------------
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db） — Monitoring は常に本番 sqlite_path を参照
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL / LOG_DIR: ログレベル / ログ出力先
- OPENAI_API_KEY: OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

使い方（実行例）
----------------

- .env を作ったら設定を検証:
  - python -m kabusys.validate_config

- ExecutionEngine を起動:
  - python -m kabusys.run_execution
  - Paper Trading モード（実際のブローカ連携を行わない専用 DB を使用）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  実行時の振る舞い:
  - 起動時に PID ファイル（デフォルト data/execution.pid）を書き出し
  - data/stop_requested.flag が存在するとエンジン起動・ループを停止
  - paper_trading の場合は settings.paper_sqlite_path を使用して本番 DB と完全分離

- Monitoring を起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、例: MONITOR_POLL_INTERVAL=30）

  監視の特徴:
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視ログを保持
  - 警報（AlertManager）経由で外部通知（LINE 等）も可能（設定があれば）

- Kill Switch（手動で Execution を止める）
  - data/kill.flag を作成すると ExecutionEngine の停止シグナルになります
  - KillSwitch は自動で kill.flag を書き込み（閾値超過時）し、Execution 側で検出して停止します

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能

AI（OpenAI）関連
-----------------
- news_nlp.score_news / ai.regime_detector.score_regime を使用してニュースセンチメントや市場レジーム判定を行えます。
- これらは OPENAI_API_KEY が必要です（引数で直接キーを渡すことも可能）。
- API の呼び出しはリトライ戦略・バッチ処理・レスポンス検証を組み込んでいます。

ログ
----
- 共通ユーティリティ kabusys.utils.logging_setup.setup_logging を使い、
  - コンソール (stdout) と 日次ローテートされたファイルログ（logs/<app_name>.log）に出力します。
- LOG_LEVEL / LOG_DIR 環境変数で挙動を制御できます。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数 / Settings 管理（自動 .env ロード機能）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト（PID / stop flag の制御）
- run_monitoring.py — Monitoring 起動スクリプト（MONITOR_POLL_INTERVAL）
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - risk_adjustment.py — セクター上限・レジーム乗数
  - position_sizing.py — 株数決定ロジック
- research/
  - factor_research.py — Momentum / Value / Volatility 等の計算（DuckDB 利用）
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- ai/
  - news_nlp.py — ニュースのセンチメントスコアリング（OpenAI 経由）
  - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント合成）
- monitoring/
  - monitoring_db.py — SQLite による監視用永続化層（テーブル初期化/CRUD）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文滞留や約定異常の検出（該当ファイル実装あり）
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag の生成 / 判定
  - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
  - alert_manager.py — （存在すれば）アラート送信ロジック
- execution/
  - broker_factory.py — ブローカークライアント作成（Mock / 実ブローカー切り替え）
  - execution_engine.py — 実行エンジン本体
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 実行周りの分割コンポーネント
- utils/
  - logging_setup.py — ログ初期化ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- data/ (ランタイムファイル置き場: DB / PID / flag などを配置)
  - monitoring.db（デフォルト） / paper_trading.db（ペーパー用）
  - execution.pid, stop_requested.flag, kill.flag など

注意事項 / 運用上のヒント
------------------------
- 本コードベースは運用中の実際の発注を含むため、KABUSYS_ENV=live 時は設定値に十分注意してください。
- .env は機密情報を含むため絶対に Git 等へコミットしないでください（config_setup.py のヘッダにも明記）。
- Monitoring は監視用 DB（SQLITE_PATH）へログを永続化します。バックアップやローテーション戦略を検討してください。
- OpenAI を使う機能は API キーと利用コストが発生します。運用前に使用方針を決めてください。
- DuckDB 上のテーブル（prices_daily / raw_financials / raw_news 等）は研究モジュール・AI モジュールで参照されます。データ投入用の ETL パイプラインを別途用意することを想定しています。

貢献 / 開発
------------
- 開発時は KILL_FLAG_CLEAR_ON_START などの設定を誤らないように注意してください（本番で危険）。
- 単体テストやモックによる API コール差し替えを行い、外部依存（OpenAI・ブローカー等）を切り離してテスト可能な設計になっています。
- README の補足やドキュメント化、requirements.txt の整備があれば運用が容易になります。

ライセンスや著作権情報はリポジトリに従ってください。

以上が本リポジトリの概要・セットアップ・使い方の概要です。必要であれば、起動スクリプト別の詳しいオプションや実行時ログの読み方、モジュール別 API リファレンス（関数署名一覧）なども作成できます。どの情報を優先して追加しますか？