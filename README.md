# KabuSys

日本株自動売買システムのリファレンス実装（ライブラリ＋起動スクリプト群）。

このリポジトリは戦略のリサーチ、ポートフォリオ構築、注文実行、監視、AI を用いたニュース解析までを含むモジュール群で構成されています。設計方針として本番・ペーパートレード・開発を切り替え可能にし、DB やログはファイルベースで運用できるようになっています。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動・ユーティリティ）
- 主要環境変数
- ディレクトリ構成

---

プロジェクト概要
- 自動売買システムの各コンポーネント（Research / Portfolio / Execution / Monitoring / AI）をモジュール化した Python パッケージ。
- DuckDB を分析用 DB、SQLite を監視・発注ログ用 DB に利用。
- 本番（live）・ペーパー（paper_trading）・開発（development）を環境切替でサポート。
- OpenAI を用いたニュースセンチメント解析やレジーム判定の実装例を含む。

主な機能一覧
- 起動スクリプト
  - run_execution.py — ExecutionEngine の起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 DB に分離保存。
  - run_monitoring.py — SystemMonitor をポーリング起動。MONITOR_POLL_INTERVAL で間隔変更可。
- 設定操作
  - config_setup.py — 対話式 .env 作成ウィザード。
  - validate_config.py — .env と config/*.yaml の事前チェック CLI（--strict あり）。
- モニタリング
  - monitoring_engine.py / system_monitor.py / trade_monitor.py / risk_monitor.py / kill_switch.py — システム状態監視、滞留注文検知、ドローダウン検知、Kill Switch（停止フラグ）発動など。
  - monitoring_db.py — 監視用 SQLite スキーマと永続化ラッパー（冪等）。
- Execution 関連（発注）
  - execution/*.py — ブローカークライアント生成、ExecutionEngine、OrderManager、RiskManager 等（コードベースに依存）。
  - ペーパートレードでは data/paper_trading.db を利用（本番 DB と完全分離）。
- Portfolio（銘柄選定・個別サイズ算出）
  - portfolio/* — 候補選定、重み付け、セクター上限、ポジションサイジング等。
- Research（ファクター計算 / 特徴量）
  - research/* — モメンタム・ボラティリティ・バリューなどのファクター計算、将来リターン／IC 計算。
- AI（ニュース NLP / レジーム判定）
  - ai/news_nlp.py — raw_news を OpenAI に送り銘柄別センチメントを取得して ai_scores に保存（バッチ・リトライ・バリデーション実装）。
  - ai/regime_detector.py — ETF MA とマクロニュースを合成して market_regime を判定し DB に保存。
- ツール
  - tools/paper_verification_report.py — Paper Trading の検証レポート（稼働率・成立率・レイテンシ等）を生成。

セットアップ手順（開発 / 実行向け）
1. Python バージョン
   - Python 3.10 以上を推奨（ソース内で X | Y 型ヒントを使用）。

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai
   - （任意）PyYAML があると validate_config の YAML 検証が有効になります: pip install PyYAML

   ※ requirements.txt がない場合は上記主要パッケージをインストールしてください。

4. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくはリポジトリルートに .env を手動作成（.env.example を参考に）。

5. 設定検証
   - python -m kabusys.validate_config
   - 本番運用前は --strict を付けて警告も FAIL 扱いにできます:
     - python -m kabusys.validate_config --strict

6. データディレクトリ作成
   - デフォルトでは data/ 以下に DB や PID/flag ファイルを作成します。必要であれば .env でパスを変更してください。

使い方（起動例・ユーティリティ）
- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 動作:
    - Settings.env によって本番/ペーパーを切替。
    - paper_trading は専用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用。
    - 起動時に data/stop_requested.flag が既にあれば起動せず終了。
    - 実行中は data/execution.pid に PID を書き込む（設定により変動）。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は常に本番 sqlite_path を使って監視テーブルへ記録します（環境に依存せず monitoring DB は production path を参照する設計）。
  - 停止: data/stop_requested.flag を作成すると監視ループが検知して終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH を上書き）

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant|partial|never|reject、デフォルト instant）
- OPENAI_API_KEY: OpenAI を利用する機能（news_nlp / regime_detector）が参照
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 本番での auto-clear が危険なためデフォルトは 0（0=クリアしない / 1=起動時に kill.flag をクリア）

運用上の注意
- 本番環境（KABUSYS_ENV=live）では .env を慎重に管理し、LINE の通知設定や KILL_FLAG_CLEAR_ON_START の値を確認してください。
- kill.flag（Settings.kill_flag_path）を書き込むと ExecutionEngine に停止シグナルが送られます。KillSwitch はドローダウンやポジション上限で自動発行されます。
- ペーパートレードモードは本番 DB と分離するよう設計されているため、本番 DB に誤って書き込むリスクは低減されていますが、.env を必ず確認してください。
- ログはデフォルト logs/ に出力され、日次ローテーションで最大 30 日分保持されます。LOG_DIR 環境変数で変更可。

ディレクトリ構成（主要ファイルと概要）
- src/kabusys/
  - __init__.py                       — パッケージ定義、バージョン
  - config.py                         — Settings クラス（環境変数/.env の読み込み・検証）
  - config_setup.py                   — .env 対話ウィザード
  - validate_config.py                — 起動前設定検証 CLI
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - run_monitoring.py                 — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py    — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py                — 共通ログ設定ユーティリティ
    - process_priority.py             — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py                — 監視用 SQLite スキーマと DB ラッパー
    - monitoring_engine.py            — 各 Monitor をまとめるポーリングエンジン
    - system_monitor.py               — システム状態・データ鮮度監視
    - trade_monitor.py                — （滞留注文など）取引監視（実装あり）
    - risk_monitor.py                 — ドローダウン・ポジション上限監視
    - kill_switch.py                  — kill.flag 書き込み / 管理
    - alert_manager.py                — アラート送信管理（LINE 等、実装に依存）
  - execution/
    - execution_engine.py             — ExecutionEngine（セッション管理）
    - broker_factory.py               — ブローカークライアント生成（Mock / real）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注周り
  - portfolio/
    - portfolio_builder.py            — 候補選定・重み計算
    - position_sizing.py              — 株数決定・投下上限・丸め処理
    - risk_adjustment.py              — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py              — ファクター計算（mom/vol/value 等）
    - feature_exploration.py          — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py                     — ニュース NLP（OpenAI へ送信、ai_scores 書込）
    - regime_detector.py              — マーケットレジーム判定（ETF MA + マクロ NLP）
  - data/ （実行時に作成されることが多い）
    - monitoring.db / paper_trading.db / kabusys.duckdb
    - execution.pid / kill.flag / stop_requested.flag

開発者向けヒント
- テストや一時的な実行では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動的な .env の読み込みを抑制できます。
- validate_config は PyYAML がインストールされていれば config/*.yaml のパース検証も行います。YAML 検証が不要な場合は PyYAML を省略できますが、エラー・警告の見落としに注意してください。
- AI 関連をテストする場合、OpenAI の呼び出し部分は内部で分離されており、ユニットテスト時には _call_openai_api をモックできます（ソース内コメント参照）。
- run_monitoring は停止フラグ（data/stop_requested.flag）を確認して終了するようになっています。自動停止処理・手動停止に利用してください。

ライセンス・貢献
- 本 README はコードベースのリファレンス用途です。実際に運用する際はセキュリティや実環境の検証を十分行ってください。
- 貢献は Pull Request でお願いします。重要な設計変更は事前に Issue で議論してください。

---

README に不足している情報や、より詳細な起動例（systemd / Supervisor / Docker 化など）が必要であれば、どの環境向けかを教えてください。実運用向けの systemd ユニット例や Dockerfile のテンプレートも提供できます。