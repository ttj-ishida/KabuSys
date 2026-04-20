KabuSys — 日本株自動売買システム
==============================

このリポジトリは日本株向けの自動売買／研究フレームワークです。  
実運用向けの ExecutionEngine／監視（Monitoring）機能、ポートフォリオ構築・リスク制御関数群、研究用ファクター計算、ニュース NLP / レジーム判定などを含みます。

この README はコードベース（src/kabusys）に基づいて作成しています。

概要
----
- 設計方針は「本番と研究／ペーパートレードを分離」「ルックアヘッドバイアスを防ぐ」「フェイルセーフ（障害時は安全に続行）」です。
- 主要コンポーネント:
  - ExecutionEngine: 発注・オーダー管理・リスク管理・照合（reconciler）
  - Monitoring: システム状態 / 注文状態 / リスク監視・Kill Switch
  - Portfolio: 候補選定、重み付け、株数計算、セクターキャップ、レジーム補正
  - Research: DuckDB を用いたファクター計算・特徴量解析
  - AI: ニュース NLP（OpenAI）を用いた銘柄センチメント評価、レジーム判定
  - CLI ツール: .env ウィザード、設定検証、Paper Trading 検証レポートなど

主な機能一覧
--------------
- 環境設定
  - 対話式ウィザードで .env を生成/更新（kabusys.config_setup）
  - 起動前チェック（必須環境変数、DBパス、YAML構成ファイルの簡易検証）(kabusys.validate_config)
- 実行 / 発注
  - 本番 / ペーパートレードを切り替え（KABUSYS_ENV）
  - Paper Trading 時は本番DBと分離して data/paper_trading.db に記録
  - 発注・リスク制御・order manager / reconciler を備える
- 監視
  - システムリソース、プロセス稼働、データ鮮度を監視（監視DB に記録）
  - リスク監視（ドローダウン、ポジション上限）→ Kill Switch へ連携
  - アラート発行（AlertManager 経由；実装に応じて LINE 等へ通知可能）
- ポートフォリオ構築
  - シグナル選定、等配分 / スコア加重配分、リスクベース配分、単元株丸め、セクター制限
- 研究
  - DuckDB を用いたモメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算・IC（情報係数）・統計サマリー
- AI
  - ニュースをまとめて OpenAI へ投げ、銘柄ごとの sentiment（ai_scores）を算出
  - ETF・マクロニュースを組み合わせた市場レジーム判定（bull/neutral/bear）
- ユーティリティ
  - ロギング設定ユーティリティ（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定（psutil 利用）

セットアップ手順
----------------

前提
- Python 3.9+（ソースで typing や newer features を利用）
- pip 等で次のライブラリをインストールしてください（必要に応じて）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（validate_config の YAML 検証を行う場合）
  - 例: pip install duckdb psutil openai pyyaml

リポジトリの準備
1. ソースを取得・配置（プロジェクトルートに src/ を置く想定）。
2. 仮想環境を作成・有効化（任意）。
3. 依存をインストール（上記）。

.env の準備
- 対話式ウィザードで .env を作成:
  - python -m kabusys.config_setup
- 主要な必須環境変数:
  - JQUANTS_REFRESH_TOKEN （必須）
  - KABU_API_PASSWORD （必須）
- その他（デフォルト値あり・任意）:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 DB（PAPER_TRADING 時に使用）デフォルト: data/paper_trading.db
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — アラート通知用（任意）
  - OPENAI_API_KEY — AI 機能利用時に必要

設定検証
- 作成後に次で検証:
  - python -m kabusys.validate_config
  - --strict オプションを使うと警告も失敗（exit 1）扱い

使い方（運用例）
----------------

ロギング
- 共通のログ初期化関数が用意されています。ログファイルはデフォルトで logs/<app_name>.log に日次ローテートで出力されます。

監視（Monitoring）を起動
- デフォルトポーリングは 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可（秒、1 以上）。
- 例:
  - python -m kabusys.run_monitoring
  - 環境変数を指定して起動:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 停止:
  - プログラムは data/stop_requested.flag の存在を検知するとループを終了します（安全停止）。
  - Kill Switch により ExecutionEngine 停止が必要な場合は data/kill.flag を書き込む（KillSwitch が生成）。

ExecutionEngine を起動
- KABUSYS_ENV によって挙動が変わります:
  - paper_trading: MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH に記録（本番と完全分離）
  - live/development: 本番 sqlite_path を使用
- 実行例:
  - python -m kabusys.run_execution
- 停止:
  - data/stop_requested.flag を配置すると監視ループ／エンジンが停止します。
  - ExecutionEngine は pid ファイル（デフォルト data/execution.pid）を生成／参照します。

Paper Trading 検証レポート
- ペーパートレード DB（デフォルト data/paper_trading.db）から各種指標を集計してレポートを標準出力へ出力します。
- 例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パス指定可能（優先度: --db > PAPER_TRADING_SQLITE_PATH > デフォルト）

AI 機能（ニュースNLP / レジーム判定）
- OpenAI API キーが必要（OPENAI_API_KEY または引数経由）。
- news_nlp.score_news(conn, target_date, api_key=None) — DuckDB 接続を渡して ai_scores を書き込み。
- regime_detector.score_regime(conn, target_date, api_key=None) — market_regime を書き込み。
- 注意:
  - API 呼び出しはリトライやフォールバックを備えていますが、APIキー未設定時は例外になります。
  - JSON mode を利用する想定で厳格なバリデーションを行います。

プロセス優先度・ログ
- run_* スクリプトは起動時にプロセス優先度を "high" に設定しようとします（psutil を利用）。権限がない場合は警告を出してスキップします。
- ログ出力は stdout と logs/<app>.log に記録されます。ログレベルは LOG_LEVEL で制御。

停止 / Kill
- 監視ループ停止用フラグ: data/stop_requested.flag（両 run スクリプトで監視）
- Execution 停止（Kill Switch）: data/kill.flag（KillSwitch により生成）
- KillFlag の自動クリアは KILL_FLAG_CLEAR_ON_START=1 で有効になりますが、production では推奨されません。

ディレクトリ構成（主要ファイル）
--------------------------------

プロジェクトルート（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数読み込み・Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前検証 CLI
  - run_monitoring.py         — Monitoring ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - logging_setup.py        — 共通ロギング設定
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py       — システム状態監視
    - trade_monitor.py        — （実装中／ログ検出） ※コード参照
    - risk_monitor.py         — ドローダウン・ポジション監視
    - monitoring_engine.py    — 各 Monitor を束ねる
    - kill_switch.py          — フラグ生成ロジック
    - alert_manager.py        — （実装により通知を実行）
  - execution/
    - broker_factory.py       — ブローカークライアント生成（Mock / 実ブローカー）
    - execution_engine.py     — ExecutionEngine 本体（run_session 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング
    - regime_detector.py      — レジーム判定
    - __init__.py

重要なデフォルトパス・環境変数（抜粋）
-------------------------------------
- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — data/kabusys.duckdb
- SQLITE_PATH — data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — data/paper_trading.db
- LOG_LEVEL — INFO（DEBUG 等可能）
- OPENAI_API_KEY — AI 機能で必要
- MONITOR_POLL_INTERVAL — 監視のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH — 実行時に Settings から参照

運用上の注意
--------------
- .env は絶対にリポジトリにコミットしないでください（config_setup は警告を出して生成します）。
- 本番環境（KABUSYS_ENV=live）では Kill Switch 設定や LINE 通知等を十分確認してください。
- DuckDB/SQLite のバックアップやローテーション（ログ・データ管理）は運用方針に合わせて導入してください。
- OpenAI 利用時は API 利用料に注意してください。リトライやバッチサイズは定数で調整可能です。

開発・拡張のヒント
-------------------
- 各モジュールはできるだけ純粋関数・副作用最小化で実装されています（特に portfolio / research）。
- DuckDB 接続を渡して関数を呼ぶ実装が多く、テスト用に in-memory DB やモックが利用できます。
- AI 呼び出し部分は _call_openai_api をモック化して単体テストしやすい設計です。

問い合わせ / 貢献
-----------------
- バグ報告・機能提案は issue でお願いします。  
- コードスタイルやドキュメントの改善、ユニットテスト追加は歓迎します。

付録 — よく使うコマンド（まとめ）
---------------------------------
- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 監視起動:
  - python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- Paper トレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上。README の追加修正や、より詳細な運用手順（systemd / cron 登録例、ログローテーション設定、DB マイグレーション手順など）を希望される場合は、その用途（本番運用 / ローカル開発 / CI テスト）を教えてください。