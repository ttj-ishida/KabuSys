CHANGELOG
=========

すべての注目すべき変更をこのファイルに記載します。  
このファイルは "Keep a Changelog" の形式に準拠しています。  

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正 / 安定化
- Removed / Security: 必要に応じて記載

[Unreleased]
-------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-18
-------------------

Added
- 起動スクリプト・デーモン類を追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御用の stop_requested.flag を監視して安全に停止。
    - duckdb / sqlite（監視 DB）接続および監視用 DB 初期化処理を実行。
    - 起動時にプロセス優先度を "high" に設定し、共通ログ設定を行う。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用し、MockBrokerClient を利用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - ExecutionEngine をデーモンスレッドで実行し、停止フラグ・PID ファイルによる制御を実装。

- 環境設定関連
  - config.py: Settings クラスを導入し、環境変数アクセスを集中管理。
    - J-Quants / kabu API / LINE / DB パス / 監視閾値などのプロパティを提供。
    - PAPER_FILL_MODE の検証・有効値制約、KABUSYS_ENV/LOG_LEVEL の検証を実装。
    - PAPER_TRADING_SQLITE_PATH / PID ファイル / Kill flag 等のパス取得を標準化。
    - プロジェクトルート自動検出と .env の自動読み込み（.env / .env.local）を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - OS 環境変数を保護する仕組み（.env の読み込み時に既存 OS 環境変数を上書きしない / .env.local は override 可）。

- 設定支援 CLI
  - config_setup.py: 対話式ウィザードで .env ファイルを初期作成・更新するツールを追加。
    - シークレット値のマスク表示、選択肢サポート、既存 .env の読み込み・再利用、最終確認とファイル出力を実装。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV・LOG_LEVEL の妥当性チェック、DB パス（親ディレクトリ存在有無）のチェック、config/*.yaml の存在とパース検証（PyYAML がある場合）。
    - --strict モードにより警告を FAIL 扱いにできる。live 環境向けの追加ガード（LINE 設定未設定や Kill Switch 警告）も実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選定（タイブレークに signal_rank を使用）。
    - calc_equal_weights: 等金額配分の実装。
    - calc_score_weights: スコア比例配分の実装。全スコアが 0 の場合は等配分にフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限を適用し、上限超過セクターの新規候補を除外するロジック（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知のレジームは 1.0 でフォールバックして警告ログを出す。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method="risk_based"／"equal"／"score" をサポートした発注株数決定ロジック。
    - 単元(lot_size)丸め、per-position 上限・aggregate cap（利用可能現金に基づくスケーリング）、cost_buffer（手数料/スリッページ見積り）を考慮。
    - aggregate スケーリング時に残余キャッシュを考慮して lot 単位で再配分する残差処理を実装（再現性のあるソート順で配分）。

- ユーティリティ
  - utils/logging_setup.py: ルートロガーの一元設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテートされる TimedRotatingFileHandler（デフォルト logs/、30 日分保持）を設定。
    - 既存ハンドラのクリア処理、ログディレクトリ作成失敗時のフォールバック（コンソール出力のみ）を実装。
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX を吸収した set_process_priority、set_cpu_affinity を提供。
    - 権限不足や未実装 OS では警告を出して安全にスキップ。

- ツール
  - tools/paper_verification_report.py: Paper Trading 向けの検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均／最大／P95）等を集計して表示。
    - 基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定。

- 研究用モジュール（部分実装）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨格（モメンタム等）を追加。設計方針と計算定数を定義。

Changed
- .env 自動読み込みの取り扱いを明確化
  - 自動ロードはデフォルトで有効、プロジェクトルート検出により .env/.env.local を上から順に読み込む。
  - OS 環境変数は保護され、.env.local の override は許可されるが既存の OS 環境変数は上書きされない。
  - 無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
- ロギング
  - ロギングは stdout を使用（stderr ではない）。既存ハンドラを一度クリアしてから再設定することで二重出力を防止。
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
- DB の扱い
  - 監視（run_monitoring）は環境にかかわらず本番 sqlite_path を使用する旨を明確化（監視 DB は本番データを参照する想定）。
  - Execution は KABUSYS_ENV=paper_trading のとき paper_trading 用 SQLite を使用して本番 DB と分離。
- 設定検証
  - validate_config による事前チェックを強化（YAML のパース検証は PyYAML が存在する場合のみ実行、ファイル未存在は警告）。
- ポートフォリオ計算の安定化
  - calc_score_weights は全スコア 0 の場合に等分フォールバックして警告を出す。
  - apply_sector_cap は "unknown" セクターを上限チェック対象外とする仕様（既知セクターのみブロック）。
  - calc_position_sizes の集約スケールロジックは残差処理を改善して lot 単位でできるだけ有効利用するよう変更。

Fixed
- .env パーサーの堅牢性向上
  - export KEY=val 形式のサポート、シングル/ダブルクォート内部のバックスラッシュエスケープ処理、インラインコメント取り扱いの改善を実装。
  - 無効行（コメント・空行・キー無し等）を適切にスキップするよう修正。
- プロセス優先度 / CPU affinity の障害耐性を向上
  - 権限不足やプラットフォーム未サポート時に例外で落とさず警告してスキップする動作を追加。
- Monitoring / Execution のリソース解放
  - 起動スクリプトの finally ブロックで sqlite/duckdb コネクションを確実に閉じるように修正。
- Paper verification report
  - P95 計算のロジック追加（空データ時の None ハンドリング）、各クエリがテーブル欠損時に安全に N/A を返すフォールトトレラント化。

Removed
- （なし）

Security
- 環境変数取り扱いの注意書きを追加
  - .env ファイルは絶対に Git にコミットしない旨のコメントを config_setup の生成ファイルに明示。

Notes / その他
- Settings のプロパティは未設定や不正値の場合に ValueError を送出する設計になっているため、起動前に validate_config.py での事前チェックを推奨します。
- 一部モジュール（research/factor_research.py 等）は計算ロジックの完成がまだ見込まれており、内部的に TODO コメントや未実装の箇所があります。
- このリリースは初期バージョン（__version__ = "0.1.0"）に相当します。導入・運用に際しては README / ドキュメントの確認、.env の適切な設定、監視・停止フラグ運用の確立を推奨します。