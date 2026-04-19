# KabuSys

日本株向け自動売買システムのコアライブラリ群と運用ユーティリティ群です。  
このリポジトリには発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築・ポジションサイズ決定、各種リサーチ/ファクター計算、ニュース NLP を用いた AI スコアリングなどの主要コンポーネントが含まれます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（よく使うコマンド）
- 重要な環境変数
- 動作の流れ（監視・停止・ペーパートレード）
- ディレクトリ構成（ファイル説明）

---

プロジェクト概要
- 本システムは「信号生成 → ポートフォリオ構築 → 発注 → 監視／リスク制御」を分離して提供します。
- 発注処理と監視は独立したプロセスとして起動でき、監視側からの判定で発注エンジンを停止する Kill Switch を持ちます。
- Paper Trading（ペーパートレード）モードでは本番 DB と分離して専用 SQLite に取引記録を保存します。
- DuckDB を用いたファクター計算 / リサーチ、OpenAI（gpt-4o-mini）を利用したニュース NLP / レジーム判定のモジュールを含みます。

主な機能一覧
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV に応じて実際のブローカーまたは MockBroker を使用
  - Paper Trading 時はデータを data/paper_trading.db に保持
  - プロセス優先度設定・PID ファイル管理・停止フラグ監視
- Monitoring（監視）
  - SystemMonitor：CPU/メモリ/ディスク/データ鮮度/プロセス生存監視
  - TradeMonitor：滞留注文や約定異常の検出（trade_logs 参照）
  - RiskMonitor：ドローダウン・ポジション上限監視（dashboard/upsert）
  - KillSwitch：リスク基準超過時に data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine：上記を束ねるポーリングエンジン（run_monitoring.py 起動）
- ポートフォリオ構築（portfolio）
  - 候補選定、等加重/スコア重みの計算、セクター制限の適用、ポジションサイズ算出（単元丸め含む）
- リサーチ（research）
  - DuckDB を用いた momentum/value/volatility 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ
- AI モジュール（ai）
  - news_nlp: raw_news から銘柄毎にテキストを集約して OpenAI に投げ、スコアを ai_scores に保存
  - regime_detector: ma200 とマクロニュースの LLM 結果を合成して市場レジームを判定し market_regime に書き込み
- ユーティリティ
  - 環境設定ウィザード（config_setup.py）で .env を対話的に作成可能
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート（tools/paper_verification_report.py）
  - 共通のログセットアップ / プロセス優先度設定ユーティリティ

---

セットアップ手順（ローカル開発向け・最小）
1. Python バージョン
   - Python 3.10+ を推奨（typing の | 演算子等を使用）

2. 必要パッケージ（例）
   - duckdb, psutil, openai, PyYAML（任意。validate_config で YAML 検証を行う場合）
   例:
     pip install duckdb psutil openai PyYAML

   実際の requirements ファイルがある場合はそちらを使用してください。

3. リポジトリルートで .env を作成
   - 推奨: 対話式ウィザードを使う
     python -m kabusys.config_setup
   - 既存の OS 環境変数を尊重しつつ .env（および .env.local）が自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

4. 設定検証
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いにできます。

5. 必要なデータディレクトリの作成（通常は自動で作られますが事前に作ることも可）
   mkdir -p data logs

注意: OpenAI を使う機能を使う場合は OPENAI_API_KEY を環境変数または関数引数で設定してください。

---

使い方（よく使うコマンド）
- 環境設定ウィザード（.env を生成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）を起動
  python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading のときは MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - 起動時に data/stop_requested.flag が存在する場合は起動を行いません。

- Monitoring（監視ループ）を起動
  python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）。
  - 監視は常に本番の sqlite_path（Settings.sqlite_path）を使用します。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを指定可能（例: --db data/paper_trading.db）。

- ログ
  - ログはデフォルト logs/<app_name>.log に日次ローテートで記録されます。
  - LOG_DIR 環境変数で出力先ディレクトリを変更可能。

停止・Kill Switch
- 手動でプロセスを停止したい場合は project_root/data/stop_requested.flag を作成すると、run_execution/run_monitoring のループは検知して安全に終了します（run_execution は起動直後にも存在チェックを行います）。
- 監視側がリスク基準を満たした場合（ドローダウン超過等）、KillSwitch が data/kill.flag を書き込み ExecutionEngine に停止を通知します。起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動的に消去します（本番では 0 推奨）。

---

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須） — J-Quants API 用トークン
- KABU_API_PASSWORD（必須） — kabuステーション API パスワード
- KABUSYS_ENV（必須, default=development） — 実行環境: development | paper_trading | live
- LOG_LEVEL（任意, default=INFO）
- DUCKDB_PATH（任意, default=data/kabusys.duckdb）
- SQLITE_PATH（任意, default=data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, default=data/paper_trading.db）
- OPENAI_API_KEY（AI 機能で必要）
- PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject、default=instant）
- MONITOR_POLL_INTERVAL（監視ポーリング秒数, default=60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag をクリアするか: "1" でクリア）

Settings クラスは起動時にプロジェクトルートの .env および .env.local を自動で読み込みます（OS 環境変数が優先）。

---

動作の流れ（概念図）
- 起動前
  - .env を用意（config_setup を推奨）
  - validate_config で必須設定を確認
- 発注エンジン（run_execution）
  - プロセス優先度を high に設定（psutil を使用）
  - DB 接続（paper_trading 時は専用 SQLite を使用）
  - ブローカークライアント生成（実ブローカ or Mock）
  - ExecutionEngine.run_session をスレッドで実行。stop_requested.flag / kill.flag を監視
- 監視（run_monitoring）
  - プロセス優先度 high
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングし、条件に応じて kill.flag を生成・アラート送信
- AI モジュール
  - news_nlp.score_news: raw_news から銘柄別に記事を集約し OpenAI に投げて ai_scores を更新
  - regime_detector.score_regime: ETF ma200 と LLM マクロセンチメントを用いて market_regime を更新

---

開発者向けノート
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行われます。テストなどで自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- monitoring_db.init_monitoring_db() はテーブル作成と簡単なマイグレーション（列追加）を行います。既存 DB と後方互換性を保つために冪等に実装されています。
- OpenAI の呼び出しは堅牢化（429/タイムアウト/5xx のリトライ、JSON 検証、部分失敗時の DB 保護）を行っています。
- DuckDB 接続は research / ai モジュールで利用します。prices_daily / raw_financials / raw_news 等のテーブルが期待されます。

---

ディレクトリ構成（主要ファイルと説明）
- src/kabusys/
  - __init__.py — パッケージ定義（__version__）
  - config.py — 環境変数・設定読み込みロジック（Settings クラス）
  - config_setup.py — .env 対話ウィザード（CLI）
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（メイン実行入口）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成 CLI
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI 使用）
    - regime_detector.py — 市場レジーム判定（OpenAI 使用）
  - monitoring/
    - monitoring_db.py — 監視用 SQLite 永続層（テーブル定義・ログ操作）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （trade 関連監視、ファイルから参照）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — （アラート送信の抽象化。LINE 等の実装を想定）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・単元丸め・集約スケーリング
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum/Value/Volatility の計算
    - feature_exploration.py — 将来リターン, IC, 統計サマリ
  - utils/
    - logging_setup.py — 統一ログ設定ユーティリティ
    - process_priority.py — psutil を使った優先度・CPU affinity 設定
  - monitoring/*, execution/*, portfolio/* などその他の補助モジュール（詳細はソース参照）

---

トラブルシューティング（よくある注意点）
- .env の読み込み順:
  OS 環境変数 > .env.local > .env（自動ロードを無効化する環境変数あり）
- OpenAI を使う機能で API キー未設定だと例外を投げます。テストやオフライン実行時は該当機能をスキップしてください。
- ログディレクトリの作成に失敗するとファイルログは無効化されコンソール出力のみになります（警告が出ます）。
- Paper Trading と本番 DB は分離されています。paper_trading モードで本番 DB を上書きしないよう注意してください（PAPER_TRADING_SQLITE_PATH を確認）。

---

ライセンス・貢献
- 本リポジトリのライセンス情報・コントリビュート手順はプロジェクトルートにある LICENSE / CONTRIBUTING ファイルを参照してください（存在しない場合は管理者に確認してください）。

---

そのほか質問や README に追記してほしい点があれば教えてください。README を環境向けにカスタマイズ（Docker、systemd ユニット例、CI 設定等）することもできます。