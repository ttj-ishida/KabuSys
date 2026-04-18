CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。
リリースはセマンティックバージョニングに従います。

Unreleased
----------

- ドキュメント化・リファクタが残っている箇所があります（例: research/factor_research.py の一部実装が途切れ）。
- いくつかの TODO / 改善余地をソース内コメントで保持（価格フォールバック、銘柄別単元対応など）。

0.1.0 - 2026-04-18
------------------

Added
- 基本アプリケーション構成を追加
  - パッケージ初期リリースとして、実行・監視・構成管理・ポートフォリオ構築・各種ユーティリティを実装。
  - バージョン: __version__ = "0.1.0"

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db をデフォルト）へ記録し、本番 DB と完全分離する設計。
    - BrokerClientFactory により環境に応じたブローカークライアント（本番 / モック）を生成。
    - 実行中の停止制御: data/stop_requested.flag の検知で Engine.stop() を呼び停止。data/execution.pid に PID を記録する想定の pid_file をサポート。
    - ExecutionEngine の依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler）を組み立てて起動。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60秒）。不正な値はログ警告のうえデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを操作（init_monitoring_db を実行）。
    - data/stop_requested.flag の検知でループを終了。

- 環境設定・検証ツール
  - config_setup.py
    - 対話式ウィザードで .env を初期作成/更新する CLI を提供。
    - シークレット項目はマスクして対話。結果は .env に書き込み（書式と説明付きテンプレート）。
    - .env の既存値を読み込み、Enter で再利用可能。
  - validate_config.py
    - .env と config/*.yaml の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML がインストールされている場合）等を実行。
    - --strict オプションで警告も失敗扱いにできる。

- 設定管理
  - config.py
    - Settings クラスで環境変数を一元管理。
    - .env 自動ロード機能（プロジェクトルートを .git または pyproject.toml から検出）を実装。既存 OS 環境変数は保護され、.env.local は上書き可能。
    - 値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を行い、無効値で例外を送出するユーティリティを提供。
    - デフォルト値（DuckDB/SQLite パス等）を定義。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - シグナル選別 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコアが全て 0 の場合は等金額にフォールバックして警告を出す挙動を持つ。
  - portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap) を実装。既存保有のセクター時価を計算し、上限超過セクターの新規候補を除外する。
    - レジーム乗数 (calc_regime_multiplier) を実装（bull:1.0, neutral:0.7, bear:0.3、未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元（lot_size）に丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）を実装。残差を考慮した再配分ロジックを持つ。
    - price が取得できない銘柄はスキップ。cost_buffer により保守的なコスト見積りを適用。

- 解析・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを提供。期間フィルタ（--from/--to）や DB パス指定（--db / 環境変数）に対応。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。
    - 判定基準（しきい値）を定義（稼働率 >=99% など）し、PASS/FAIL を出力。
    - DB が存在しない場合やテーブルが欠けている場合は N/A を扱う保護ロジックを持つ。

- 研究（リサーチ）基盤
  - research/factor_research.py（骨組み）
    - DuckDB 接続を受けてファクター計算（Momentum / Value / Volatility / Liquidity）を行う設計のモジュールを追加。モメンタム計算関数等を部分実装（未完の箇所あり）。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに対して StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定するユーティリティを追加。
    - ログディレクトリ作成に失敗した場合はファイルロギングをスキップし、コンソールのみで継続。
    - LOG_LEVEL / LOG_DIR の解決順を文書化。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（high/normal/low）および CPU affinity を設定する関数を追加。
    - Windows と POSIX 系（Linux/Mac/FreeBSD）をサポートし、未対応 OS や権限不足の場合は警告を出して安全にフォールバックする。

- パッケージ初期化
  - kabusys/__init__.py にパッケージ情報と __version__ を設定。
  - portfolio, tools などのサブパッケージをエクスポートする __all__ を整備。

Changed
- ロギングの標準出力先を stderr ではなく stdout に変更（StreamHandler）。理由: Task Scheduler / cron 等で stdout/stderr を一本化してリダイレクトしやすくするため。
- .env の自動ロード動作
  - OS 環境変数を保護する仕組みを採用。_.env_ と _.env.local_ のロード順と override 挙動を明確化。

Fixed
- run_execution と run_monitoring における DB 初期化の冪等性を確保
  - init_monitoring_db を起動時に呼び出し、必要テーブルが存在することを保証する（複数起動・再起動時の安全性向上）。

Security
- .env の生成テンプレートに注意書きを追加（絶対に Git にコミットしないよう明記）。
- シークレット項目は対話ウィザードでマスク表示にすることで、誤表示リスクを低減。

Notes / Known issues
- research/factor_research.py が実装途中の箇所（ファイル末尾が途切れている）あり。ファクター計算ロジックの完成は今後のタスク。
- position_sizing の price フォールバックが未実装（price が欠損した場合に前日終値や取得原価を使う仕組みは TODO）。
- 単元株（lot_size）を銘柄毎に管理する拡張は未対応（将来的にマスタを導入予定）。
- set_process_priority / set_cpu_affinity は権限不足や未対応環境で失敗する場合があり、その際はログに警告を出してスキップする挙動。

導入・利用上のポイント
- .env の自動ロードはデフォルトで有効。テスト等で無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番運用時は KABUSYS_ENV を "live" に設定し、LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を確認してください。validate_config.py が live 環境での注意点を警告します。
- Paper Trading（模擬発注）は settings.is_paper 判定により paper_sqlite_path に記録され、本番 DB と分離されます。
- 監視プロセスは data/stop_requested.flag を用いて外部から安全に停止できます。

----------------------------------------
今後の予定（候補）
- research/factor_research の完成（全ファクター実装・テスト）
- 単元・手数料・スリッページ等のマスタ管理導入
- DuckDB を用いた分析パイプラインの拡張と CI テスト追加
- 監視・実行の e2e テストおよびドキュメント強化

もし特定の変更点（セクションの追加/除去や詳しい日付付与など）を反映したい場合は、反映したい情報を教えてください。