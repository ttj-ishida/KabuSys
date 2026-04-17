# KabuSys

日本株向け自動売買フレームワーク（ライブラリ / 実行スクリプト群）

このリポジトリは、データ収集・ファクター計算・ポートフォリオ構築・注文実行・監視・AI を組み合わせた自動売買システムの一部実装を含みます。設計は本番（live）・ペーパートレード（paper_trading）・開発（development）を区別しており、安全機構（Kill Switch / リスク監視）や監視ログ永続化を備えています。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（コマンド例）
- 主要環境変数
- ファイル・ディレクトリ構成

---

プロジェクト概要
- モジュール群は、データ処理（DuckDB）、ファクター計算、ポートフォリオ構築、ポジションサイズ計算、注文管理、監視（System / Trade / Risk）、AI を使ったニュースセンチメント評価などを提供します。
- 実行スクリプトは主に:
  - ExecutionEngine を起動する run_execution.py（実注文またはペーパートレード）
  - 監視ループを起動する run_monitoring.py
  - 設定ウィザード（.env 作成）config_setup.py
  - 設定検証 CLI validate_config.py
  - ペーパートレード検証レポート生成ツール tools/paper_verification_report.py
- 設計上、ペーパートレード環境は本番 DB と明確に分離（デフォルトで data/paper_trading.db を使用）されます。
- AI（OpenAI）を使う機能（news_nlp / regime_detector）は OpenAI API キーを必要とします。API 呼び出しはフェイルセーフ設計で、失敗時は安全側にフォールバックします。

---

主な機能一覧
- 設定管理
  - .env/.env.local 自動ロード（必要に応じて無効化可）
  - 対話式設定ウィザード（kabusys.config_setup）
  - 設定検証ツール（kabusys.validate_config）
- Execution
  - ExecutionEngine 起動（run_execution.py）
  - Broker クライアントの抽象化（本番 / モック分離）
  - 注文管理・リコンシリエーション・リスク制御
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス監視、データ鮮度チェック
  - TradeMonitor: 滞留注文、約定価格異常検出
  - RiskMonitor: ドローダウン / ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件達成で data/kill.flag を書き込んで ExecutionEngine を停止
  - AlertManager: LINE Push 通知（トークン未設定時はログ出力のみ）
- Research / Portfolio
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC 計算、ファクター統計
  - ポートフォリオ候補選定・重み計算・ポジションサイズ計算・セクターキャップ等の純粋関数群
- AI
  - ニュース NLP による銘柄別センチメント算出（OpenAI 使用、結果を ai_scores に書込）
  - 市場レジーム判定（ETF MA200 とマクロニュースを組み合わせる）
- ユーティリティ
  - process priority / CPU affinity 設定ユーティリティ
  - Paper Trading 検証レポート生成ツール

---

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - 必須ライブラリ（例）:
     - duckdb
     - psutil
     - openai
     - requests
     - PyYAML（config 検証で任意。無ければ YAML 内容検証はスキップ）
   - 例:
     - pip install duckdb psutil openai requests pyyaml

   ※ requirements.txt がない場合は上記を手動でインストールしてください。

4. .env の作成
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成（.env は絶対に Git にコミットしないこと）

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗として扱う場合: python -m kabusys.validate_config --strict

6. データディレクトリの準備
   - デフォルトの DB パスは data/ 以下に置かれます（例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）。
   - 必要に応じて環境変数で上書きしてください（下記参照）。

注意:
- .env の自動ロードはプロジェクトルート（.git or pyproject.toml の位置）を基準に行われます。
- 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

主要な環境変数（一部）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBroker を使用し DB を data/paper_trading.db に切り替え
- DUCKDB_PATH: 分析用 DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定挙動 ("instant" | "partial" | "never" | "reject")
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知設定（任意）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に Kill Flag を自動クリアするか ("0" or "1")
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

---

使い方（よく使うコマンド例）
- 環境作成・保存（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番 or paper_trading に依存）
  - python -m kabusys.run_execution
  - 実行前に .env で KABUSYS_ENV を設定してください（paper_trading の場合は paper_trading DB に分離されます）。
  - 実行はデーモン化やプロセスマネージャ（systemd / supervisor / pm2 等）で運用することを推奨します。

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で指定可能（デフォルト 60）
  - run_monitoring は常に本番用 sqlite_path を使って監視ログを書きます（KABUSYS_ENV に関わらず）。

- Paper Trading 検証レポートを生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能。デフォルトは 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。

- AI: ニューススコア / レジーム判定
  - ニュース NLP は kabusys.ai.score_news（呼び出し側で APIキーを渡すか OPENAI_API_KEY を設定）
  - レジーム判定は kabusys.ai.regime_detector.score_regime

停止・Kill Switch に関する操作
- 実行中の ExecutionEngine に停止命令を出すには data/kill.flag を作成（KillSwitch が検出すると停止処理を行います）。
- run_execution/run_monitoring はそれぞれ data/stop_requested.flag 等を使ってループを抜けます（スクリプト内で定義されたファイル名を参照）。

ログ / PID
- ExecutionEngine は pid ファイル（デフォルト: data/execution.pid）を書く設計です。SystemMonitor はこの PID を参照してプロセスの存否をチェックします。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / .env ロードと Settings 定義
  - config_setup.py                   — 対話式 .env ウィザード
  - validate_config.py                — 設定検証 CLI
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - run_monitoring.py                 — SystemMonitor ポーリング起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py             — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py                — 監視ログの SQLite 操作層
    - monitoring_engine.py            — 各 Monitor 統括ポーリングロジック
    - system_monitor.py               — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py                — 注文滞留 / 約定異常監視
    - risk_monitor.py                 — ドローダウン / ポジション上限監視
    - kill_switch.py                  — Kill Switch のファイル操作
    - alert_manager.py                — LINE 送信ユーティリティ
  - execution/                         — 注文実行関連（Engine, BrokerFactory, OrderManager 等）
    - （省略されているが存在想定のモジュール群）
  - portfolio/
    - portfolio_builder.py            — 候補選定 / 重み計算
    - position_sizing.py              — 株数算出・単元調整・スケーリング
    - risk_adjustment.py              — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py              — ファクター計算（momentum/value/volatility）
    - feature_exploration.py           — 将来リターン・IC・統計
    - __init__.py
  - ai/
    - news_nlp.py                      — ニュースセンチメント（OpenAI利用）
    - regime_detector.py               — 市場レジーム判定（MA200 + macro sentiment）
    - __init__.py
  - tools/
    - __init__.py
    - paper_verification_report.py     — Paper Trading 検証レポート生成ツール
  - monitoring/ (上記参照)
  - data/ (実行時生成: DB ファイル・フラグファイル等を配置)
    - kill.flag
    - stop_requested.flag
    - execution.pid
    - monitoring.db / kabusys.duckdb / paper_trading.db (デフォルトパス)

---

設計上の注意点・運用の勘所
- 本番（live）では設定変数の取り扱いに細心の注意を。validate_config の警告はよく確認してください。
- OpenAI を使う機能は API コストとレート制限に注意。API キーは安全に管理してください。
- .env は秘匿情報を含むためリポジトリにコミットしないでください。
- run_monitoring は KABUSYS_ENV に関係なく「本番の監視 DB (SQLITE_PATH)」にログを書きます。ペーパートレード環境の監視が別 DB で必要な場合は設計の見直しを検討してください。
- プロセス優先度や CPU affinity の設定は権限によって失敗する可能性があります（ログに警告が出ます）。運用環境の制約を確認してください。

---

追加情報 / 開発者向け
- DuckDB を使った分析・ファクター計算は conn（DuckDB 接続）を受け取り純粋関数的に動作します。テストや再利用が容易です。
- MonitoringDB は SQLite に対する読み書きユーティリティを提供します。複雑なビジネスロジックは監視モジュール側で扱います。
- テスト用に外部 API 呼び出し関数（OpenAI 呼び出しなど）を patch/モックする設計になっています。

---

問題報告 / 貢献
- バグ報告や機能追加提案は Issues を立ててください。Pull Request は歓迎します。

---

ライセンス / 著作権
- （この README ではソースのライセンス表記は省略しています。実際の運用では LICENSE を明記してください。）

以上。README に不足している点や、特定のコマンド例（systemd ユニット、Docker 化など）を追加で作成したい場合は教えてください。