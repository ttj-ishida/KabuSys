KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買／リサーチ基盤の一部実装です。  
README は日本語で、プロジェクト概要・機能一覧・セットアップ手順・使い方・ディレクトリ構成をまとめています。

前提
----
- Python 3.10 以上（typing の | 記法を使用）
- SQLite（標準ライブラリ）
- 推奨外部ライブラリ: duckdb, psutil, openai
- オプション: PyYAML（config YAML の構文チェック用）

推奨 pip インストール例:
    pip install duckdb psutil openai pyyaml

プロジェクト概要
-------------
KabuSys は以下の主要機能を持つコンポーネント群を含みます（このリポジトリはフル実装の一部）:

- ExecutionEngine: 発注・リスク管理・オーダー管理（run_execution.py で起動）
- Monitoring: システム稼働・注文状況・リスク指標の監視（run_monitoring.py）
- Portfolio Construction: 候補選定・配分・ポジションサイジング（kabusys.portfolio）
- Research: ファクター計算・特徴量探索（kabusys.research）
- AI ユーティリティ: ニュース NLP（OpenAI 利用）と市場レジーム判定（kabusys.ai）
- ツール: Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
- 環境設定ユーティリティ: 対話式 .env ウィザード・設定検証ツール

主な設計方針
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV により切替）
- ルックアヘッドバイアスを防ぐ（日時参照の扱いに注意）
- フェイルセーフ重視（API 失敗時はフォールバックして継続）
- モジュールは可能な限り純粋関数または DB 層を分離している

機能一覧
--------
- 環境設定ウィザード（.env 生成 / 更新）: kabusys.config_setup
- 設定検証 CLI（.env + config/*.yaml のチェック）: kabusys.validate_config
- ExecutionEngine 起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し paper_trading DB に分離
- Monitoring 起動スクリプト: run_monitoring.py
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）
  - 監視は常に production sqlite_path を使用（環境に依存せず）
- モニタリング内容:
  - システムリソース (CPU/Memory/Disk)、実行プロセス生存、データ鮮度
  - 注文の滞留・約定異常価格
  - ドローダウン監視・ポジション上限監視・Kill Switch 書き込み
- AI ツール:
  - news_nlp: 記事を OpenAI に送り銘柄ごとに -1.0〜1.0 のスコアを生成
  - regime_detector: ETF の MA とマクロニュースを合成して市場レジーム判定
- Paper Trading レポート生成: paper_verification_report（稼働率・約定率・レイテンシ等）

重要な環境変数（主なもの）
-------------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: AI モジュールを利用する場合に必須
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading の注文約定動作）: instant | partial | never | reject
- LOG_LEVEL（デフォルト: INFO）
- MONITOR_POLL_INTERVAL（run_monitoring 用、秒。デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START（Execution 起動時に kill.flag を自動クリアするか、0/1）

セットアップ手順
----------------

1. クローン & 仮想環境
    git clone <repo>
    cd <repo>
    python -m venv .venv
    source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 依存関係インストール（最小）
    pip install duckdb psutil openai pyyaml

   ※ 実行環境に応じて追加のライブラリが必要になる場合があります。

3. 環境変数 (.env) の作成（対話式推奨）
    python -m kabusys.config_setup

   ウィザードは .env を生成します。必須値（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）を入力してください。
   生成後に設定を検証:
    python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります。

4. データディレクトリ作成（必要に応じて）
    mkdir -p data

5. DuckDB / SQLite ファイルのパスを .env で確認（デフォルトは data/ 下）

使い方
------

- 設定ウィザード
    python -m kabusys.config_setup

- 設定検証
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番 or paper_trading に応じて .env の KABUSYS_ENV を設定）
    python -m kabusys.run_execution
  挙動:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading.db に記録します。
  - 起動時に data/stop_requested.flag が存在する場合は起動をスキップします。
  - 実行中に stop フラグを書き込むとエンジンを優雅に停止できます（詳細は Kill Switch）。

- Monitoring 起動
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  挙動:
  - デフォルト 60 秒ごとに監視を行います。MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可能。
  - 監視は常に Settings.sqlite_path（監視 DB）を使用してログを永続化します。

- Paper Trading 検証レポート
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11
  DB パスは引数 --db または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

- AI モジュール（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY が必要です（または各関数に api_key を渡す）
  - ニューススコア: kabusys.ai.score_news を呼ぶ（内部で DuckDB を参照して ai_scores に書き込み）
  - レジーム判定: kabusys.ai.regime_detector.score_regime を呼ぶ（market_regime テーブルへ書き込み）

Kill Switch / 停止フラグ
-------------------------
- kill.flag の既定パスは Settings.kill_flag_path（デフォルト data/kill.flag）
- KillSwitch はリスク条件を満たすと kill.flag を書き込み、ExecutionEngine 側で検出して停止します。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動で kill.flag をクリアします（本番では推奨されません）。
- 手動停止: data/stop_requested.flag を作成すると run_execution / run_monitoring のループが検知して終了します（stop フラグの使い方については各スクリプト内の説明を参照）。

DB とマイグレーション
--------------------
- run_monitoring は起動時に monitoring DB のテーブル作成（init_monitoring_db）を行います（冪等）。
- monitoring_db.init_monitoring_db は既存 DB のスキーマ不足項目（例: latency_ms, peak_value）を自動で ALTER します（簡易マイグレーション）。
- Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）と監視 DB（SQLITE_PATH）は分離して使うことを推奨します。

主要モジュール・ファイル一覧（抜粋）
-----------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings 管理（.env 自動ロード）
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring ポーリング起動スクリプト

パッケージ:
- kabusys/execution/       — ExecutionEngine, OrderManager, BrokerFactory 等（発注関連）
- kabusys/monitoring/      — system_monitor, trade_monitor, risk_monitor, monitoring_engine, monitoring_db, alert_manager, kill_switch 等
- kabusys/portfolio/       — portfolio_builder, position_sizing, risk_adjustment（配分・株数計算）
- kabusys/research/        — factor_research, feature_exploration（DuckDB ベースのファクター計算）
- kabusys/ai/              — news_nlp（OpenAI 呼び出し）、regime_detector（市場レジーム判定）
- kabusys/tools/           — paper_verification_report（ペーパートレード検証レポート）
- kabusys/utils/           — process_priority（プロセス優先度設定） 等

（上記の詳細実装は src/kabusys 以下の各ファイルを参照してください）

実行上の注意点・運用メモ
----------------------
- KABUSYS_ENV を live にすると本番扱いになります。LINE 通知や kill flag の取り扱いなど注意してください（validate_config は live 時に追加警告を出します）。
- MONITOR_POLL_INTERVAL に 0 や負の値を設定すると無効値としてデフォルトにフォールバックします。
- run_monitoring は「監視」専用なので、実際の発注 DB へのアクセスや環境に依存する機能（例: pid_file の判定）を行います。開発時は KABUSYS_ENV=development で実行し、実動作を行わないようにしてください。
- AI 機能は OpenAI API 利用料が発生します。API 呼び出しはバッチ化・リトライ・失敗時のフォールバック処理が実装されていますが、API キーの管理には注意してください。
- データ鮮度チェックや market_regime の計算ではルックアヘッドバイアスを避ける設計になっています（target_date 未満のデータのみ参照する等）。

トラブルシューティング
---------------------
- PyYAML が無い場合、validate_config は YAML の中身検証をスキップします（警告が出ます）。PyYAML を入れると config/*.yaml の構文検査を実行します。
- psutil の優先度設定は OS に依存し、権限不足で失敗する場合は警告を出してスキップします。
- DuckDB への executemany に空リストを渡すとエラーになるバージョン制限をコード側で回避しています（空時は実行しない）。

貢献・拡張ポイント（今後の方向）
--------------------------------
- 銘柄別 lot_size を stocks マスタに持たせる（position_sizing の拡張）
- AI コンポーネントのローカルテストのためのモッククライアント強化
- 発注ロジック・リスク設定のパラメータ化（config 経由）
- GUI/Web ダッシュボードへのデータ出力（dashboard テーブルの活用）

ライセンス
----------
（この README にはライセンス情報が含まれていません。必要に応じてリポジトリルートに LICENSE を追加してください）

参考コマンドまとめ
------------------
- .env 作成（ウィザード）:
    python -m kabusys.config_setup
- 設定検証:
    python -m kabusys.validate_config
- Execution 起動:
    python -m kabusys.run_execution
- Monitoring 起動（ポーリング間隔 30 秒に設定）:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11

以上が本コードベースの概要と利用方法です。実際の導入・運用にあたっては .env の機微設定（API キー・パス等）と本番運用時の安全策（KILL_FLAG の取り扱い・通知先設定）を必ず確認してください。