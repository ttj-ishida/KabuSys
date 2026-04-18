# KabuSys

日本株向け自動売買システム（KabuSys）— 発注エンジン、監視、リサーチ、ポートフォリオ構築、AI 支援などを含むモジュール群の集合体です。

このリポジトリはライブラリと複数の起動スクリプトを備え、ローカル開発・ペーパートレード・本番運用の各モードに対応する設計になっています。

---

## 主な特徴（機能一覧）

- Execution（発注）エンジン
  - kabuステーションとの接続（本番/ペーパートレード切替）
  - 注文管理、リスク管理、照合（reconciler）機能
  - Paper Trading 時は MockBrokerClient を利用し、paper_trading 用 DB に記録

- Monitoring（監視）
  - システム資源（CPU/メモリ/ディスク）監視
  - データ鮮度チェック（DuckDB の prices_daily 等）
  - 取引ログの監視（滞留注文、約定異常など）
  - リスク監視（ドローダウン、ポジション上限監視）
  - Kill Switch（条件を満たしたら `data/kill.flag` を書き込み ExecutionEngine を停止）

- Research（調査・ファクター計算）
  - モメンタム、ボラティリティ、バリューなどのファクター計算（DuckDB ベース）
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ

- Portfolio（銘柄選定・配分・サイズ決定）
  - 候補選定、等配分／スコア配分、リスクに基づくサイズ算出
  - セクター上限適用・レジーム乗数（市場レジームに応じた調整）

- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini 等）を利用したニュースセンチメントスコアリング
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定

- ユーティリティ
  - ログ設定（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 制御
  - .env 対話式ウィザード、設定検証 CLI
  - Paper Trading 検証レポート生成スクリプト

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈の union 型などを使用）
- SQLite（組み込み）、DuckDB（パッケージ）

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（最低限）
   - pip install duckdb psutil openai PyYAML
   - 実運用では他にも依存がある場合があります。プロジェクトに requirements.txt があればそれを使用してください。

3. リポジトリのルートでデータ／ログディレクトリを作成
   - mkdir -p data logs

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - 必須環境変数（例）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - 作成後は設定を検証:
     - python -m kabusys.validate_config
     - strict モード: python -m kabusys.validate_config --strict

5. （オプション）OpenAI を利用する場合は環境変数 OPENAI_API_KEY を設定

6. Paper Trading 用 DB を分離したい場合は `.env` 内で PAPER_TRADING_SQLITE_PATH を指定（デフォルト: data/paper_trading.db）。

注意:
- .env は絶対にリポジトリにコミットしないでください（config_setup もその旨を注記しています）。
- KABUSYS_ENV を `live` に設定する場合、設定ミスが重大になるため validate_config の警告に従って慎重に設定してください。

---

## 主要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN（必須） — J-Quants API 用トークン
- KABU_API_PASSWORD（必須） — kabuステーション API パスワード
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）ファイル（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレード時の約定挙動: instant | partial | never | reject（デフォルト: instant）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を利用する場合必須）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0。本番は 0 推奨）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）

---

## 使い方（実行例）

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- Execution（発注エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用する（paper DB に記録）
    - 起動後は data/execution.pid を作成し、停止は data/stop_requested.flag を作成することで指示可能
    - Kill Switch（data/kill.flag）により外部から強制停止されることがあります

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番 sqlite_path を参照（設定にかかわらず）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB を指定可能（デフォルトは PAPER_TRADING_SQLITE_PATH 環境変数 または data/paper_trading.db）

- 停止 / Kill
  - run_monitoring / run_execution のようなループ処理を優雅に停止させるには、プロジェクトルートの data/stop_requested.flag を作成します（run_execution/run_monitoring はこのフラグを監視して終了）。
  - Kill Switch（リスクに応じて ExecutionEngine を止める）： KillSwitch が条件を満たすと data/kill.flag を書き込みます。ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると自動クリアされる場合があるため、本番は 0 推奨。

---

## 開発者向け: 主要モジュール概要（ディレクトリ構成）

（ルート: src/kabusys 以下）

- __init__.py
  - バージョン定義と公開パッケージ

- config.py
  - 環境変数読み込み・管理（.env 自動読み込み機能、Settings クラス）

- config_setup.py
  - .env 対話式ウィザード（python -m kabusys.config_setup）

- validate_config.py
  - 起動前設定検証 CLI（python -m kabusys.validate_config）

- run_execution.py
  - ExecutionEngine 起動スクリプト（thread ベースでエンジンを回す。paper_trading 用 DB 分離有）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL で間隔変更可能

- utils/
  - logging_setup.py — 統一的なログ設定（stdout + 日次ファイルローテート）
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py — SQLite テーブル作成 / CRUD ヘルパ（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — システム資源・データ鮮度監視
  - risk_monitor.py — ドローダウン、ポジション上限監視
  - kill_switch.py — 条件判定と data/kill.flag 書き込み
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - trade_monitor.py — （取引ログの監視。リポジトリ内で参照）

- execution/
  - broker_factory.py, execution_engine.py, order_manager, order_repository, reconciler, risk_manager など（発注ロジックと依存コンポーネント）

- portfolio/
  - portfolio_builder.py — 候補選定 / ウェイト計算
  - position_sizing.py — 株数算出・ロット丸め・投下資金スケーリング
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算（DuckDB使用）
  - feature_exploration.py — 将来リターン・IC計算・統計サマリ

- ai/
  - news_nlp.py — ニュース記事の LLM によるセンチメント（銘柄別スコア）取得と ai_scores 書込み
  - regime_detector.py — ETF MA200 とマクロニュースで市場レジーム判定

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

---

## ログについて

- setup_logging により、標準出力（stdout）と日次ローテートファイル（logs/<app_name>.log）にログが出力されます。
- LOG_DIR 環境変数でログディレクトリを変更可能（デフォルト: logs/）。
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で設定可能。

---

## 停止・安全対策

- stop_requested.flag（data/stop_requested.flag）
  - run_execution/run_monitoring のような常駐処理はこのファイルの存在を検知して安全に終了します（手動停止用）。

- kill.flag（data/kill.flag）
  - KillSwitch（RiskMonitor 等の判定）により書き込まれる。ExecutionEngine はこのフラグにより停止されます。
  - KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動クリアする設定がありますが、本番環境では 0 が推奨です。

---

## よくある操作（まとめ）

- 環境を初期化して検証する
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- 発注エンジンを起動（ペーパートレード）
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- 監視を起動
  - python -m kabusys.run_monitoring
  - export MONITOR_POLL_INTERVAL=30  # 30秒間隔に変更

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

もし README に追加したい項目（依存関係の正確な一覧、起動時のデーモン化方法、実運用での監視設定、ユニットテスト手順など）があれば教えてください。必要に応じてそれらを追記します。