# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このファイルにはリポジトリ内の現在のコードベースから推測した機能追加・振る舞いの要約を日本語でまとめています。

現行バージョン: 0.1.0（リリース日: 2026-04-18）

## [0.1.0] - 2026-04-18
初回リリース。以下の主要機能・ユーティリティ・ツールを追加。

### Added
- 基本 CLI / 起動スクリプト
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は本番 DB と分離して PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を使用する設計。
    - ブローカークライアントを BrokerClientFactory 経由で作成し、OrderRepository / OrderManager / RiskManager / Reconciler 等を組み立ててエンジンを起動する。
    - エンジンは別スレッドで実行され、data/stop_requested.flag の検知でグレースフルに停止する。PID ファイルを扱う（data/execution.pid）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視プロセスは KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを記録する（monitoring 用テーブルを初期化）。
    - 停止フラグ（data/stop_requested.flag）でループ停止。
- 設定管理 / 補助ツール
  - config.py: Settings クラスによる環境変数ラッパーを追加。
    - .env 自動読み込み（プロジェクトルートが検出可能な場合）をサポート。読み込み優先度: OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
    - 各種プロパティ（duckdb/sqlite パス、PID/kill flag、しきい値、env/log_level 判定、paper_fill_mode の検証など）を提供。
    - 必須キー未設定時は ValueError を送出する _require ユーティリティを提供。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - J-Quants・kabuステーション・DB パス・ログレベル等の入力を支援し .env を生成。
    - シークレット項目やデフォルト値の扱いを実装。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境に対する追加ガード等を実施。
    - --strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア降順で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等分配およびスコア加重配分（スコア全て 0 の場合は等分配にフォールバックし WARNING を出す）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限の適用。既存ポジションに基づき上限を超えるセクターの新規候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知のレジームは 1.0 にフォールバックして警告）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 重み・候補・ポートフォリオ情報に基づく発注株数計算。
    - risk_based / equal / score の配分方式をサポート。単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金を超えた場合のスケールダウン）処理、残差を考慮した再配分ロジックを実装。
- リサーチ（骨組み）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュール（モメンタム / MA200 / ATR 等の計算方針と実装途中の関数群の骨組み）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）からデータを読み、稼働率・注文成功率・送信率・P95 レイテンシ等を計算し PASS/FAIL を判定する。
    - P95 計算や日付フィルタ（from/to）に対応し、DB・テーブル欠如時は適切にハンドリングして N/A を出力。
- ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定する共通ユーティリティを追加。
    - 既存ハンドラをクリアして二重設定を防止。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - stdout を使用することでタスクスケジューラ等とのリダイレクト運用を想定。
  - utils/process_priority.py:
    - Windows / POSIX の差分を吸収してプロセス優先度設定（high/normal/low）と CPU affinity の固定機能を提供。
    - アクセス権限や未対応 OS の場合は警告を出してスキップ。

### Changed
- パッケージ基盤
  - パッケージ __init__ に __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ で公開。

### Fixed / Robustness
- .env パーサの強化（config._parse_env_line）
  - export KEY=val 形式に対応。
  - シングル/ダブルクォート内部のバックスラッシュエスケープを正しく扱う。
  - クォートなしの値に対するインラインコメント処理（'#' の直前がスペース/タブの場合のみコメントと判定）を実装。
- 自動 .env 読み込みの保護
  - OS 環境変数を保護するため .env 読み込み時に既存の OS 環境変数を上書きしない仕組み（.env.local の override をサポート）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプションを追加。
- ログ設定の堅牢化
  - ログディレクトリ作成に失敗しても落ちずにコンソールログのみで継続するようにフォールバックを実装。
  - 既存のハンドラは安全に flush/close してから削除する。
- 実行時の安全措置
  - run_execution/run_monitoring は起動時にプロセス優先度を上げることを試み、失敗時は警告で継続。
  - init_monitoring_db を起動前に呼ぶことで必要な監視テーブルの存在を冪等に保証する（存在しない DB でも安全に初期化）。
  - 多くの場所で想定外のデータ欠損や SQLite/duckdb のテーブル未存在時に例外を捕捉して合理的なデフォルト（N/A 等）を出力する実装が追加。
- Paper trading / モック動作の区別
  - run_execution のドキュメントと実装で paper_trading 環境時に MockBrokerClient を使って本番 DB と完全に分離する設計が明示されている（data/paper_trading.db を利用）。

### Notes / Known limitations
- factor_research.calc_momentum の実装ファイルは途中で終わっており、未完のコード片が存在する（今後完成予定）。
- position_sizing の価格欠損時の挙動について TODO コメントがあり、将来的にフォールバック価格（前日終値や取得原価）を導入する余地がある。
- 一部の機能（例えば単元株サイズを銘柄ごとに変える等）は現状ハードコード（lot_size）で、将来拡張が予定されている旨の注記あり。

---

今後のリリースでは、factor_research の完成、各種テスト追加、監視・実行フローの更なる堅牢化（例: トランザクション境界の明確化、DB マイグレーション対応）やドキュメント拡充を想定しています。必要であれば、この CHANGELOG を英語版や細分化したエントリ（Bugfix/Performance/Docs）に分割して作成します。