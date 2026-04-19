CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠します。  
日付は本コード解析時点（2026-04-19）を使用しています。コード内容から推測して記載しています。

Unreleased
----------
注: コード中の TODO や将来的な改善余地に基づく今後の作業候補を列挙しています。

Added
- position_sizing:
  - 銘柄ごとの単元株数（lot_size）を将来的に銘柄マスタから参照できるよう拡張する予定の TODO を追加。
- risk_adjustment:
  - price が欠損した場合のフォールバック価格（前日終値や取得原価など）を導入する検討メモを追加。
- utils:
  - logging_setup のファイルハンドラ作成失敗時のフォールバックと警告ログ出力の扱いが明記されているため、ファイル出力失敗時に安全に継続できる改善予定。

Changed
- process_priority:
  - 未対応 OS（Windows/Linux/Posix 以外）での優先度設定のスキップと警告出力を明確化。
  - set_cpu_affinity のエラー時に警告を出してスキップする動作はそのまま維持。

Notes
- 上記はコードコメントや TODO から推測される「今後の改善候補」です。

v0.1.0 - 2026-04-19
-------------------

Added
- 基本パッケージ情報
  - パッケージ初期バージョンを __version__ = "0.1.0" として追加。

- 起動スクリプト / 実行系
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用して本番 DB と完全分離。
    - 起動時にプロセス優先度を "high" に設定。
    - stop flag（data/stop_requested.flag）検知により安全にエンジンを停止する仕組みを実装。
    - PID ファイル（data/execution.pid）取り扱いをサポート。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔の上書きが可能（デフォルト 60 秒）。
    - 停止フラグを検知してループを終了する安全処理を実装。
    - Monitoring は環境にかかわらず production の sqlite_path を使用する挙動を明記。

- 設定周り
  - config.py:
    - .env 自動ロード機構を実装（.env / .env.local、OS環境変数を保護して上書き制御）。
    - プロジェクトルート自動検索（.git または pyproject.toml を基準）。
    - 複数の設定プロパティ（J-Quants、kabu API、LINE、DB パス、監視閾値、KABUSYS_ENV 等）を持つ Settings クラスを実装。
    - PAPER_FILL_MODE のバリデーション、paper_sqlite_path 等 Paper Trading 用設定を追加。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化フラグをサポート。

  - config_setup.py:
    - 対話式ウィザードで .env の作成・更新を支援する CLI を追加。
    - シークレット項目のマスク表示や選択肢、デフォルト処理を実装。

  - validate_config.py:
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パスや config/*.yaml の存在チェック等を実装。
    - --strict モードで警告を失敗扱いにできるオプションを追加。
    - PyYAML 未インストール時には YAML 検証をスキップして警告を出す。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - すべての起動スクリプトから共通で利用できるログ設定ユーティリティを追加。
    - stdout への StreamHandler（標準出力、cron 等で扱いやすい）と日次ローテーションの TimedRotatingFileHandler（ログディレクトリ：logs、30 日分保持）をルートロガーに設定。
    - 既存ハンドラの二重設定防止（既存ハンドラを閉じて置換）を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップして安全に継続。

  - utils/process_priority.py:
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応環境で失敗した場合は警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を選出する関数を追加。
    - calc_equal_weights: 等金額配分の重み計算を追加。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額にフォールバック）。

  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 1 セクター当たりの上限比率を超えている場合に新規候補を除外するロジックを追加。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた投下資金乗数（1.0 / 0.7 / 0.3）を実装。

  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算を実装。
    - リスクベース、等配分・スコア配分に対応。max_position_pct、max_utilization、lot_size、cost_buffer 等の制約を考慮。
    - aggregate cap（available_cash を超えた場合のスケーリング）と lot_size 単位での再配分ロジックを実装。

  - portfolio/__init__.py: 上記関数をパッケージエクスポート。

- Paper Trading ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を集計し PASS/FAIL を判定する閾値と出力フォーマットを実装。
    - SQLite（デフォルト: data/paper_trading.db）からデータを読み取り、期間指定（--from / --to）に対応。
    - P95 計算、NULL / データ不足ケースの扱い、OperationalError による安全なフォールバックを実装。

- データ解析（研究用）
  - research/factor_research.py（部分実装）:
    - DuckDB 接続を受けてモメンタム・ボラティリティ等のファクターを計算するための基盤を追加（関数シグネチャと定数を導入、実装続行中）。

- DB 関連
  - monitoring/monitoring_db.init_monitoring_db を実行して監視用テーブルの存在を保証（冪等）する処理を各起動スクリプトから実行。

Changed
- run_execution.py / run_monitoring.py:
  - 起動時に最初に set_process_priority("high") を呼び出すようにして、重要プロセスの優先度を上げる運用方針を適用。
  - run_execution.py は paper_trading 環境向けに DB を分離（settings.paper_sqlite_path）することで本番 DB との衝突を回避。
  - run_monitoring.py は環境にかかわらず監視用 sqlite_path（production 想定）を使用する設計にしている点を明示。

Fixed
- config._load_env_file:
  - 読み込み失敗時に warnings.warn を投げる実装でエラーハンドリングを改善（ファイルアクセス問題を明示）。

- logging_setup:
  - 既存ハンドラを適切に flush/close してから削除することで二重ハンドラ登録の問題を回避。

Security
- 環境変数の取扱い:
  - config_setup による .env 出力テンプレートでは「.env を絶対に Git にコミットしないこと」を明記し、J-Quants / KABU API のシークレットはマスクして扱うなど安全運用を促す記載を追加。

Removed
- なし

Notes / 今後の改善点（コード中の TODO など）
- position_sizing: 銘柄ごとの lot_size を銘柄マスタで管理する設計への拡張検討。
- risk_adjustment.apply_sector_cap: price が欠損した場合のフォールバック価格導入検討（現在は 0.0 を使っており過少見積りの可能性あり）。
- research/factor_research: 実装途中（calc_momentum 関数以降が未完）。DuckDB ベースのファクター計算ロジックを完成させる必要あり。
- logging_setup: ログディレクトリ作成やファイルハンドラ生成で失敗した場合の挙動は現在安全にフォールバックするが、外部監視・アラート化を検討すると良い。

ライセンスや既知の制約
- 本 CHANGELOG はコードベースの静的解析・コメントと TODO から推測して作成しています。実際の変更履歴（コミット履歴等）とは差異がある可能性があります。