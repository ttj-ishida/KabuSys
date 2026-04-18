# KabuSys

日本株向け自動売買システムのコアライブラリ群・起動スクリプト群のリポジトリです。  
この README はコードベース（src/kabusys 以下）を元に、日本語での導入・実行手順、機能説明、ディレクトリ構成をまとめています。

注意: 本リポジトリには実際のブローカ接続・資金を操作するコード（kabuステーション連携部分など）を含みます。`KABUSYS_ENV=live` での実行は十分に注意して行ってください。まずは `development` や `paper_trading` で動作確認することを推奨します。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動・コマンド例）
- 環境変数（主要なもの）
- 運用のポイント（停止 / Kill Switch 等）
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株自動売買のためのライブラリ群と実行スクリプトを提供します。
- 主な役割:
  - データ基盤（DuckDB / SQLite）を使ったリサーチ・集計
  - シグナル生成・ポートフォリオ構成・ポジションサイズ計算
  - ExecutionEngine による発注処理（paper_trading と live の分離）
  - 監視（Monitoring）とアラート / Kill Switch による安全停止
  - News NLP（OpenAI）を使ったセンチメント評価・レジーム判定
  - ペーパートレードの検証レポート生成ツール

主な機能一覧
- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（KABUSYS_ENV により paper_trading 用 DB / MockBroker を使用）
  - run_monitoring.py — SystemMonitor のポーリング（システム/データ鮮度監視）
- 設定・検証
  - config_setup.py — 対話式ウィザードで .env を生成
  - validate_config.py — .env と config/*.yaml の事前チェック（--strict オプションあり）
- モニタリング
  - system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch, monitoring_db（SQLite 永続化）
- ポートフォリオ構成
  - portfolio_builder, position_sizing, risk_adjustment（等金額/スコア重み/リスクベース等）
- リサーチ
  - research.factor_research（モメンタム／ボラティリティ／バリュー等）
  - research.feature_exploration（将来リターン / IC / 統計サマリ等）
- AI 関連
  - ai.news_nlp — OpenAI を使ってニュース記事の銘柄別センチメントを算出
  - ai.regime_detector — ETF の MA とマクロニュースの LLM スコアを合成して市場レジーム判定
- ユーティリティ
  - utils.logging_setup（統一ログ設定）、utils.process_priority（プロセス優先度設定）など
- ツール
  - tools.paper_verification_report — ペーパートレード DB から検証レポート生成

セットアップ手順（ローカル開発向け）
1. Python 環境
   - 推奨: Python 3.10+
   - 仮想環境を作成して有効化する:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主に必要なパッケージ（少なくとも以下をインストールしてください）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証や YAML を扱う場合に推奨）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. プロジェクトルートに移動（.env 自動ロードはプロジェクトルート検出に依存）
   - パッケージルートに .git または pyproject.toml があることを確認

4. 初期設定（対話式ウィザード）
   - python -m kabusys.config_setup
   - 対話に従って .env を生成します（重要な秘密情報はここで設定）
   - 生成後は python -m kabusys.validate_config で検証
     - 警告も FAIL にしたい場合: python -m kabusys.validate_config --strict

5. データディレクトリ作成（.env のデフォルトに基づく）
   - デフォルトのデータパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
   - ログディレクトリ: logs/ （setup_logging が作成）

使い方（起動・コマンド例）
- ExecutionEngine を起動
  - 通常（module 実行）:
    - python -m kabusys.run_execution
  - 実行前に .env の KABUSYS_ENV を設定:
    - development（デバッグ / 発注なし）
    - paper_trading（MockBrokerClient 使用、記録先は data/paper_trading.db）
    - live（実発注）
  - 実行中の停止:
    - data/stop_requested.flag を作成すると実行ループが検出して停止します
    - kill_switch（条件成立）により data/kill.flag が書かれると ExecutionEngine 側で停止する設計

- Monitoring を起動（定期監視）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    - export MONITOR_POLL_INTERVAL=30  # 30秒ごとに監視
  - メモ:
    - run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（Settings.sqlite_path）を使って監視テーブルを書きます

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - デフォルト DB: data/paper_trading.db、または環境変数 PAPER_TRADING_SQLITE_PATH

主要な環境変数（抜粋）
- 必須/重要
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- 実行環境 / ログ
  - KABUSYS_ENV — execution の動作モード: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
  - LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs/）
- DB パス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- Paper trading 固有
  - PAPER_FILL_MODE — MockBrokerClient のフィルモード（instant / partial / never / reject）
- OpenAI（AI 機能を使う場合）
  - OPENAI_API_KEY — OpenAI API キー（ai.news_nlp, ai.regime_detector などで使用）
- Monitoring / Kill Switch
  - PID_FILE_PATH — 実行エンジンの PID ファイルパス（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch が書き込むフラグファイル（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動削除するか（1 = 自動クリア。default=0 推奨）

サンプル .env（例）
- .env の作成は python -m kabusys.config_setup で対話的に生成するのが簡単です。手動例:
  JQUANTS_REFRESH_TOKEN=your_jquants_token_here
  KABU_API_PASSWORD=your_kabu_password_here
  KABUSYS_ENV=development
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  LOG_LEVEL=INFO
  KILL_FLAG_CLEAR_ON_START=0
  OPENAI_API_KEY=sk-...

運用のポイント / 安全機構
- Kill Switch
  - RiskMonitor の結果に応じて KillSwitch が data/kill.flag を書き込み、ExecutionEngine に停止を促します。
  - KillSwitch は drawdown（ドローダウン）やポジション上限超過などをトリガーにします。
  - 本番環境では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨（誤って自動クリアされると危険）。
- 手動停止
  - run_execution/run_monitoring は data/stop_requested.flag の存在を監視し、検出時に安全に終了します（手動で停止したい場合はこのファイルを作成）。
- ログ
  - 共通のロギング設定により stdout と logs/<app>.log（日次ローテーション）に出力されます。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は既存 DB に対するマイグレーション（カラム追加など）処理を含みます（冪等）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込み（.env 自動ロード）
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - utils/
    - __init__.py
    - logging_setup.py        — 共通ログ設定
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py        — （ファイル冒頭に未掲示だが存在想定）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        — （アラート送信ロジック）
  - execution/
    - execution_engine.py     — ExecutionEngine コア（起動/セッション管理）
    - order_manager.py
    - order_repository.py
    - broker_factory.py       — BrokerClientFactory（paper/live 切替）
    - reconciler.py
    - risk_manager.py
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
  - monitoring/                — 上記 Monitoring 関連
  - tools/
    - paper_verification_report.py
  - data/                      — 実行時に生成する想定ディレクトリ（DB, PID, flags など）
  - logs/                      — ログ出力先（setup_logging により作成）

（注）上記はリポジトリ内の主要スクリプト / モジュールを抜粋した構成です。詳細な補助モジュール・クラスはソース内にあります。

トラブルシューティング / よくある注意点
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テストや CI で自動ロードを無効化したい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB / OpenAI に関連する処理は外部ライブラリ / API を利用します。該当部分の利用時は適切なキー・パッケージが必要です。
- psutil によるプロセス優先度設定は権限が必要な場合があります（AccessDenied を警告として扱います）。

最後に
- まずは .env を生成し、validate_config.py でチェックした後に、development / paper_trading モードで実際に起動して動作を確認してください。  
- 本番運用（live）ではアラート設定、LINE トークン、Kill Switch 動作を十分にテストしてから運用に移行してください。

必要であれば、README に含めるコマンド例や .env のテンプレートをさらに具体化して出力します。ご希望があれば教えてください。