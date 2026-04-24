CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

[Unreleased]
------------

（現時点では未リリースの変更はありません。）

[0.1.0] - 2026-04-24
-------------------

最初の公開リリース。システム全体の基本機能を実装しました（構成読み込み、実行エンジン、監視ループ、ポートフォリオ構築ユーティリティ、ユーティリティ群、検証／ウィザード CLI、ペーパートレード検証ツールなど）。

Added
- 全体
  - 初期バージョン 0.1.0 を公開。
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を追加。

- 設定管理
  - Settings クラスを実装し、環境変数（および .env / .env.local）から設定を取得できるようにしました。
  - 自動 .env ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化サポート。
  - 環境変数読み込みの堅牢化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの扱い（クォート外でのみコメントとして扱う）
    - OS 環境変数を保護する protected オプション（.env.local が OS 環境を上書きしないよう制御）
  - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / PID・kill フラグパス / 監視閾値 / 環境判定等）。
  - PAPER_FILL_MODE のバリデーション実装（instant/partial/never/reject）。
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用DB）サポート。

- CLI / ユーティリティ
  - config_setup: 対話式 .env ウィザードを実装（.env 作成・更新支援）。
    - シークレット入力（マスク）対応、既存値の再利用、確認プロンプト、保存処理を提供。
    - デフォルト値や選択肢の指定に基づく入力ガイドを実装。
  - validate_config: 起動前設定検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ確認、config/*.yaml 存在チェック（PyYAML があればパース検証）を行う。
    - --strict モード（警告を FAIL 扱い）をサポート。
  - tools.paper_verification_report: ペーパートレード用検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を表示。
    - コマンドライン引数で日付範囲指定および DB パス指定をサポート。

- 実行・監視
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（完全分離）を使用し、MockBroker を利用する設計（BrokerClientFactory 経由）。
    - プロセス優先度設定（High）および PID ファイル管理、停止フラグ（data/stop_requested.flag）による安全停止をサポート。
    - 各コンポーネント（OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine）の組み立てと起動ルーチンを実装。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告のうえデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - stop フラグによるループ終了、KeyboardInterrupt ハンドリング、check_once の例外捕捉とログ出力を実装。

- ポートフォリオ構築ライブラリ（純粋関数群、DB 非依存）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順で上位 N を選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights を実装（スコア全て 0 の場合は等金額配分にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限の適用（既存ポジションのセクター比率を計算し、上限を超えるセクターの新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームはフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を加味した保守的見積り、残余配分ロジックを実装。

- ユーティリティ
  - utils.logging_setup:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定するセットアップ関数を実装。
    - 多重ハンドラ登録防止（既存ハンドラを一度クリア）やログディレクトリ作成失敗時のフォールバックを考慮。
    - LOG_LEVEL / LOG_DIR の解決順を実装。
  - utils.process_priority:
    - プロセス優先度設定ユーティリティを実装（Windows と POSIX を吸収）。
    - set_cpu_affinity による CPU アフィニティ固定機能を追加（アクセス権や未対応環境は警告でスキップ）。
    - 権限不足時の安全なフォールバックを実装（psutil 例外を捕捉して警告）。

- リサーチ
  - research.factor_research（開始実装）
    - モメンタム等のファクター計算用の基盤関数を追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計）。
    - 定数（短期〜長期の窓など）と calc_momentum のインターフェースを定義（実装途中の箇所あり）。

Changed
- なし（初回リリースのため既存機能の「変更」はありません）。

Fixed
- なし（初回リリースのためバグ修正履歴はありません）。

Notes / Migration
- .env ファイルは絶対にリポジトリにコミットしないでください（config_setup にも注意書きを含めています）。
- 自動 .env ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト環境等で利用）。
- run_monitoring は監視データベースとして常に Settings.sqlite_path（デフォルト data/monitoring.db）を参照します。ペーパートレードで監視データを分離したい場合は別途運用上の注意が必要です。
- run_execution は KABUSYS_ENV=paper_trading の場合に settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。ペーパーと本番の DB は分離されています。
- 外部依存:
  - duckdb, psutil は実行時に必要です。PyYAML は validate_config での YAML 検証にのみ使用され、未インストール時は該当検証をスキップして警告を出します。

Known issues / TODO
- research.factor_research 内の関数は一部実装が途中の箇所があります（実際のファクター計算ロジックは追加実装が必要）。
- position_sizing / risk_adjustment の一部ロジックは外部データ（前日終値や銘柄別 lot_size 等）を参照するため、将来的に銘柄マスタ等との連携拡張が想定されています（コード中に TODO コメントあり）。
- 一部のシステム機能（Process 優先度 / CPU affinity / ファイルハンドラ作成等）は権限や OS に依存し、失敗した場合は警告ログを出して安全にスキップします。

--- 

（以降のリリースでは変更点をバージョンごとに追記してください）