CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記録しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-04-23
--------------------

Added
- 基本リリース: KabuSys 自動売買フレームワークの初期実装を追加。
- 環境設定 / 管理
  - Settings クラスによる環境変数ラッパーを実装（src/kabusys/config.py）。
  - .env 自動読み込み機能を実装:
    - プロジェクトルートの検出（.git または pyproject.toml を基準）。
    - .env と .env.local を読み込み（OS 環境変数を保護して上書き挙動を制御）。
  - .env パーサは export 形式・クォート・エスケープ・インラインコメント等に対応。
  - 設定ウィザード CLI を追加（src/kabusys/config_setup.py）。対話式で .env を生成/更新可能。
  - validate_config CLI を追加（src/kabusys/validate_config.py）。必須環境変数や config/*.yaml の存在・パース検証（PyYAML 未導入時はスキップ警告）。
- 起動スクリプト
  - run_execution（src/kabusys/run_execution.py）:
    - ExecutionEngine 起動用エントリ。プロセス優先度設定、DB 接続、ブローカー生成、ExecutionEngine の起動および停止フラグ監視を行う。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用（data/paper_trading.db がデフォルト）して、本番 DB と分離。
  - run_monitoring（src/kabusys/run_monitoring.py）:
    - SystemMonitor をポーリングで実行する監視ループ。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番の sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）による安全停止対応。
- ロギング / プロセス制御ユーティリティ
  - 統一ログ設定ユーティリティ setup_logging を実装（src/kabusys/utils/logging_setup.py）。
    - コンソール出力（stdout）と日次ローテートファイルハンドラを設定。
    - LOG_DIR/LOG_LEVEL の解決順をサポート。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX 差分を吸収し、"high"/"normal"/"low" の抽象レベルで設定可能。
    - アクセス権限不足や未対応 OS に対しては警告を出して安全にフォールバック。
- ポートフォリオ構築関連（純粋関数群、DB 参照なし）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順 + タイブレークで上位 N を選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等金額にフォールバックして警告を出す。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有を考慮してセクター上限を超える候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear をマップ、未知レジームは 1.0 でフォールバックして警告）。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づき発注株数を算出。
    - 単元（lot_size）丸め、per-position 上限、aggregate cap（available_cash に基づくスケールダウン）を実装。
    - cost_buffer を加味した保守的なコスト見積りと、残余キャッシュに基づく追加配分アルゴリズムを実装。
    - 一部将来対応の TODO（銘柄別 lot_size の導入等）をコメントで明記。
- リサーチ（部分実装）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）の骨子を追加。モメンタム等の指標算出設計（DuckDB 経由で prices_daily/raw_financials を参照）を示す。
- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計して PASS/FAIL 判定を行う。
    - 日付フィルタと DB パスオーバーライドをサポート。閾値はコード内定義（稼働率 99% など）。
- パッケージ情報
  - パッケージ __version__ を "0.1.0" に設定（src/kabusys/__init__.py）。

Changed
- なし（初回リリースのため）

Fixed
- config の .env パースや自動読み込みに関する複数の実装注意点を考慮（クォート処理、export 構文、インラインコメント、OS 環境変数の保護など）。

Deprecated
- なし

Removed
- なし

Security
- .env ファイルをリポジトリにコミットしないようドキュメント化（config_setup にヘッダコメントを付与）。
- 機密トークン入力はウィザードでマスク可能（表示は ****）。

Notes / TODO
- position_sizing の lot_size を銘柄別に持たせる拡張、price のフォールバック（risk_adjustment 内の TODO）は将来的に対応予定。
- factor_research モジュールは設計の骨子と定数があり、実装の続き（SQL 実装や正規化ユーティリティの結合）が必要。
- monitoring_db の初期化関数へ言及あり（init_monitoring_db を呼んでいる）が、関連テーブル定義の実装/変更は別ファイルに存在すると想定。
- run_monitoring は監視 DB に本番 sqlite_path を使用する仕様だが、運用上の意図（監視情報は本番 DB に記録）があるため注意が必要。

--------------------------------
今後のリリースでは、テストカバレッジ、CI ワークフロー、より詳細なドキュメント（API 仕様書、設計ドキュメントへのリンク）を追加する予定です。