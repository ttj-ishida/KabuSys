README — KabuSys（日本語）

概要
- KabuSys は日本株向けの自動売買・研究・監視システムのコードベースです。
- 主な責務:
  - 発注実行エンジン（ExecutionEngine / 発注・リスク管理）
  - 監視サブシステム（System / Trade / Risk の監視、Kill Switch）
  - ポートフォリオ構築（銘柄選定、重み付け、ポジションサイズ）
  - リサーチ（ファクター計算、特徴量解析）
  - AI 補助（ニュース NLP によるセンチメント、レジーム判定）
  - ペーパートレード検証ツール・レポート出力

主な機能一覧
- 実行（run_execution.py）
  - 本番 / ペーパートレード（KABUSYS_ENV）に対応
  - Paper trading は MockBrokerClient を使用し DB を分離（data/paper_trading.db）
  - リスク管理、注文レポジトリ、再整合処理を統合して ExecutionEngine を起動
- 監視（run_monitoring.py + monitoring package）
  - システム状態（CPU/メモリ/ディスク）やデータ鮮度を定期チェック
  - 注文の滞留・約定異常・ドローダウン監視
  - Kill Switch による ExecutionEngine 停止（data/kill.flag）
  - 監視ログは SQLite（デフォルト data/monitoring.db）へ永続化
- ポートフォリオ構築（portfolio package）
  - 候補選定（スコア順）、等金額/スコア重み、リスク調整、ポジションサイズ計算
- リサーチ（research package）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 上で動作）
  - 将来リターン計算・IC（Information Coefficient）等の解析ツール
- AI（ai package）
  - news_nlp: OpenAI を使ったニュースセンチメント計測（ai_scores への書き出し）
  - regime_detector: MA とマクロニュースの LLM 結果を合成した市場レジーム判定
- ツール
  - 環境設定ウィザード: python -m kabusys.config_setup（.env を対話式作成）
  - 設定検証 CLI: python -m kabusys.validate_config
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report

セットアップ手順（ローカル開発向け）
1. 必要な Python バージョン
   - Python 3.10+（typing の | None などを使用しているため）

2. リポジトリをクローンしてソースツリーへ
   - （省略）

3. 依存ライブラリをインストール
   - 推奨（例）:
     pip install duckdb psutil openai
   - 任意（YAML 検証）:
     pip install PyYAML
   - もし requirements.txt があれば:
     pip install -r requirements.txt

4. .env を作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - または .env を手動作成（プロジェクトルートに配置）。主な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development|paper_trading|live) — デフォルト: development
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - LOG_LEVEL (DEBUG|INFO|...)
     - KILL_FLAG_CLEAR_ON_START (0/1)
     - PAPER_FILL_MODE (instant|partial|never|reject) — paper_trading の挙動指定

   - config.py は自動で .env/.env.local を読み込みます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）になります。

使い方（主要コマンド）
- 実行エンジン（Execution）
  - 本番相当（KABUSYS_ENV=live）または開発:
    python -m kabusys.run_execution
  - ペーパートレードで起動するには KABUSYS_ENV=paper_trading を .env に設定。ペーパートレードは専用 SQLite（デフォルト data/paper_trading.db）を使います。
  - 実行中停止:
    - 管理用: data/stop_requested.flag を作成すると run_execution のループが検知して停止
    - KillSwitch は監視側から data/kill.flag を書き込んで ExecutionEngine に停止シグナルを送ります（実行側は KILL_FLAG の存在を検知して挙動を定義）。

- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
  - 監視は監視専用 SQLite（Settings.sqlite_path）へログを書きます。run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能
  - ニューススコア付与:
    - 利用関数: kabusys.ai.score_news(conn, target_date, api_key=None)
    - OPENAI_API_KEY が必要（引数で渡すことも可能）
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

監視 / 停止フラグ（運用上の注意）
- stop_requested.flag
  - run_monitoring/run_execution はプロジェクト data ディレクトリにある stop_requested.flag を検知するとループを終了します。
  - フラグ作成で安全にシャットダウンできます。
- kill.flag
  - KillSwitch（monitoring）により書き込まれると ExecutionEngine に対する停止シグナルとして運用できます（Settings.kill_flag_path、デフォルト data/kill.flag）。
  - 手動で削除するには rm data/kill.flag（もしくは KillSwitch.clear を呼ぶ）。

データベース（簡単な説明）
- DuckDB: 分析用・履歴データ（デフォルト data/kabusys.duckdb）
- SQLite（monitoring.db）: 監視ログ（system_status, trade_logs, positions, risk_logs, dashboard）
- Paper trading は本番 DB と完全分離（PAPER_TRADING_SQLITE_PATH）

ディレクトリ構成（src/kabusys の主要ファイル）
- __init__.py
- config.py — 環境変数読み込みと Settings クラス
- config_setup.py — .env 対話生成ウィザード
- validate_config.py — 起動前設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - risk_adjustment.py — セクターキャップ・レジーム乗数
  - position_sizing.py — 株数算出ロジック
- research/
  - factor_research.py — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- ai/
  - news_nlp.py — ニュース NLP スコアリング（OpenAI 連携）
  - regime_detector.py — マーケットレジーム判定（LLM + MA200）
- monitoring/
  - monitoring_db.py — 監視 DB 層（テーブル作成・CRUD）
  - monitoring_engine.py — 各 Monitor を束ねるループ
  - system_monitor.py — システム/データ鮮度チェック
  - trade_monitor.py — 注文滞留・約定異常チェック
  - risk_monitor.py — ドローダウン・ポジション数チェック
  - kill_switch.py — フラグファイル作成による停止トリガ
  - alert_manager.py — （アラート送信管理、実装ファイルあり）
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

運用上の注意・ベストプラクティス
- 本番（live）モードでは LINE 通知や Kill Switch の設定を正しく行ってください（validate_config で警告を確認）。
- .env は絶対に Git 等へコミットしないでください。
- AI 機能を使うには OpenAI API の利用制限とコストに注意してください。
- 監視 DB のマイグレーションは monitoring_db.init_monitoring_db が起動時に冪等的に行います。
- 実行プロセスの優先度は set_process_priority("high") で変更されますが、権限不足で失敗する場合があります（ログで警告）。

トラブルシューティング
- .env 読み込みを止めたい・テストで上書きしたい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化
- モジュールが DuckDB / PyYAML に依存している箇所はインポート時に例外になる可能性があります。validate_config は PyYAML がない場合に YAML チェックをスキップします。

参考コマンド一覧
- .env 作成（対話）:
  python -m kabusys.config_setup
- 設定検証:
  python -m kabusys.validate_config
- Execution 起動:
  python -m kabusys.run_execution
- Monitoring 起動:
  python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上です。README に追加して欲しい具体的なコマンド例や、各モジュールの API ドキュメント（関数引数・返り値の詳細）を展開したい場合は知らせてください。