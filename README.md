README — KabuSys（日本語）
概要
- KabuSys は日本株自動売買システムのコードベースです。
- 戦略の研究・ファクター計算、ポートフォリオ構築、ポジションサイズ計算、発注エンジン、監視・アラート、ペーパートレード用検証ツール、LLM を使ったニュース NLP / レジーム判定などを含みます。
- ローカルでの開発・ペーパートレード・本番（live）の3つの実行モードを想定しています。

主な機能
- portfolio
  - 候補選定・重み付け（等金額・スコア加重）
  - セクター上限適用、レジーム乗数
  - 株数算出（risk-based / equal / score）、単元株丸め・aggregate キャップ処理
- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリー
- execution（発注）
  - ExecutionEngine を起動して注文処理を行う（本番/ペーパー別DB）
  - BrokerClientFactory により実際のブローカー／モックを切替え
- monitoring（監視）
  - SystemMonitor: CPU/メモリ/Disk、プロセス生存、データ鮮度チェック
  - TradeMonitor: 滞留注文／約定異常監視
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新、risk_logs
  - KillSwitch: 条件により data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine: 各モニタを定期実行しアラート発行
- tools
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
- ai
  - news_nlp: OpenAI を用いたニュースセンチメント集約→ai_scores テーブル書き込み
  - regime_detector: マクロニュース + ETF MA 乖離で市場レジーム判定し DB に保存
- utils
  - process_priority: OS に依らないプロセス優先度 / CPU affinity 設定

セットアップ手順（ローカル）
1. リポジトリをクローン
   - git clone <repo>
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - 必須ライブラリ（抜粋）: duckdb, psutil, openai
   - 開発・検証で PyYAML を使う場合はインストールしておく（config 検証）
4. 初期設定（.env）
   - 対話式ウィザードで .env を作成・更新:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に .env を作成して環境変数を設定
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）になる
6. DB 関連
   - 監視用 SQLite（デフォルト: data/monitoring.db）は run 実行時に init されます
   - Paper Trading は KABUSYS_ENV=paper_trading を使うと専用 DB（data/paper_trading.db, 環境変数で上書き可）に切替
7. 環境変数の要点（主要）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（ペーパートレード時の DB、デフォルト: data/paper_trading.db）
   - OPENAI_API_KEY（news_nlp / regime_detector を使う場合必須）
   - LOG_LEVEL（デフォルト: INFO）
   - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動でクリアするか、0/1。production は 0 推奨）
   - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔を秒で上書き、デフォルト 60）

使い方（実行コマンド・例）
- 環境設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- ExecutionEngine 起動（本番 or ペーパートレード切替は KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 特記事項: KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録する。本番と DB は分離される。
  - 実行開始前に data/stop_requested.flag や data/kill.flag による動作を確認。stop_requested.flag があると起動しない/停止する。
- Monitoring の起動（単体モニタ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト 60 秒）
  - 監視は monitoring DB（Settings.sqlite_path）に記録。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する点に注意
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH
- AI 関連（プログラム的に呼ぶ例）
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, date(2026,4,1), api_key="sk-...")
  - regime_detector.score_regime(duckdb_conn, target_date, api_key=...)
  - 両方とも OPENAI_API_KEY が必要（引数で渡すことも可）。API 呼び出しはリトライ・バックオフ処理を含む。
- 開発用: MonitoringEngine.run_once() を使って単発チェックを行える（テスト容易化）

停止／Kill Switch
- ExecutionEngine の停止は data/stop_requested.flag（run scripts 用）や data/kill.flag（KillSwitch による自動停止）で制御されます。
- KillSwitch は RiskMonitor の結果（ドローダウン、ポジション上限）等に基づき data/kill.flag を書き込みます。Execution は flag 検出で安全に停止する設計です。
- 設定 KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では OFF 推奨）。

その他の注意点
- .env は決して Git にコミットしないでください（config_setup のヘッダにも同旨コメントあり）。
- duckdb / sqlite のパス設定によりローカルファイルが作成されます。デフォルトは data/ ディレクトリ配下。
- psutil を使ってプロセス優先度や CPU affinity を設定するため、実行 OS と権限により設定が失敗する場合があります（ログに警告が出ますが処理は継続します）。
- news_nlp / regime_detector は外部 API（OpenAI）への依存があります。API の利用に伴うコストとレート制限に注意してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env ロード機能含む）
  - config_setup.py          — .env 生成ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングスクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (実装ファイルはプロジェクト内に存在)
  - execution/                — 発注エンジン関連（OrderManager, ExecutionEngine 等）
  - data/                     — デフォルトの DB ファイル出力先（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db など）
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ヘルパ

トラブルシューティング
- .env 自動ロードを無効化したい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- validate_config が警告やエラーを出す場合は指示に従い .env の必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）や config/*.yaml の存在を確認
- OpenAI 関連で JSON パースエラーや API エラーが発生しても設計上はフェイルセーフ（スコアをスキップ / デフォルト値）で継続しますが、ログを必ず確認してください

ライセンス・バージョン
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照（例: 0.1.0）

以上。README に含めてほしい追加項目やコマンド例があれば教えてください。