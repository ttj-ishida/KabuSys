CHANGELOG
=========

すべての注目すべき変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。
バージョン番号と日付はソースコードから推測して作成しています。

フォーマット:
  - Added: 新機能
  - Changed: 既存機能の変更
  - Fixed: バグ修正 / 堅牢化
  - Deprecated / Removed / Security: 該当があれば記載

0.1.0 — 2026-04-24
------------------

Added
- 初期リリース: KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、開発向けツール群を追加。
- 実行・監視ランチャー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に基づく DB 切替（paper_trading の場合は paper_sqlite_path を使用し、本番 DB と分離）。
    - BrokerClientFactory によるブローカークライアント生成。
    - ExecutionEngine の起動、スレッド実行 / 停止監視、PID ファイル管理、停止フラグ（data/stop_requested.flag）対応。
    - RiskManager のデフォルト設定（max_position_pct 等）を用意し、初期ポートフォリオ現金を broker.get_available_cash() で取得して設定。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境に関わらず本番 sqlite_path を使用する挙動を明示。
    - 停止フラグ検知、check_once() の例外をキャッチしてループ継続。
- 設定管理 / ウィザード / 検証
  - config.py: Settings クラスを追加。.env 自動読み込み（.env, .env.local、環境変数優先）機能を実装。
    - .env パースは export 構文、クォート、行内コメント等に対応。
    - 各種プロパティを提供（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視しきい値等）。
    - PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実施。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。
    - 質問形式で必須項目・任意項目を入力、シークレットはマスク表示、最終確認後に .env を書き出す。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性チェック、DB パスや config/*.yaml の存在・パース（PyYAML があればパース検証）を実施。
    - --strict オプションで警告も失敗扱いにできる。
    - 本番環境（KABUSYS_ENV=live）向けのガード（LINE 設定確認、KILL_FLAG_CLEAR_ON_START 警告）。
- ログ & プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: クロスプラットフォームでプロセス優先度と CPU affinity を設定するユーティリティを追加。
    - Windows / POSIX(nice) に対応。アクセス権限エラー等は警告でスキップ。
- ポートフォリオ構築関連（純粋関数）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選定（signal_rank でタイブレーク）。
    - calc_equal_weights, calc_score_weights: 等金額配分、スコア重み配分（全スコア 0 の場合は等分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限による候補除外ロジック（sell_codes を除外できる）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームはフォールバックして 1.0。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数決定。
    - lot_size（単元株）対応、cost_buffer（手数料・スリッページ見積り）に基づく aggregate cap、可用現金を超えた場合のスケーリングと残余配分ロジックを実装。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、平均/最大/P95 レイテンシを計算・出力。
    - CLI オプション --from/--to/--db、デフォルト DB は data/paper_trading.db。
    - P95 計算、しきい値（稼働率・成功率・送信率・P95 レイテンシ）による PASS/FAIL 判定を実装。

Changed
- ログ挙動の標準化: 全起動スクリプトから setup_logging を呼ぶ前提でログ構成を統一。
- DB 初期化: run_execution/run_monitoring は monitoring テーブル存在を保証するため init_monitoring_db を呼び、冪等に初期化する設計。
- Execution 起動ロジック: 停止フラグがすでに存在する場合は起動を中止する安全策を追加。
- .env 自動読み込み: OS 環境変数を保護する protected ロジックを導入し、.env.local で OS 変数を上書きできる仕組みを採用。

Fixed / Hardened
- 設定パーサの堅牢化: .env パーサは export プレフィックス、クォート内のバックスラッシュエスケープ、行内コメントの取り扱いを正しく処理するよう改善。
- ログハンドラの二重登録防止: setup_logging は既存ハンドラをクリーンアップしてからハンドラを追加するようにして、二重出力を防止。
- プロセス優先度設定の例外耐性: set_process_priority / set_cpu_affinity はアクセス権限エラーや未対応 OS を安全に扱い、警告を出してスキップする。
- モニタリングループの例外隔離: SystemMonitor.check_once() 内での例外がループを壊さないように catch してログ出力し次回ポーリングに進むようにした。

Deprecated
- なし（初回リリース）

Removed
- なし（初回リリース）

Security
- 設定ウィザード・.env 書き出しでシークレットはマスク表示し、.env を Git にコミットしない旨を README コメントで注意喚起するテンプレートを出力。

Notes（備考）
- monitoring が「環境に関係なく」本番 sqlite_path を使用するという挙動はソース中で明示されているため、開発時に意図せず本番 DB を操作しないよう注意してください。ペーパートレード用の隔離 DB は Execution 側で settings.is_paper に応じて使用されます。
- 一部の機能（config/*.yaml のパース検証等）は外部ライブラリ（PyYAML）の有無によって挙動が変わります。validate_config は PyYAML 未インストール時に YAML 検証をスキップして警告を出します。

今後の改善候補（コードから推測）
- position_sizing の価格フォールバック（price が欠損した場合の扱い改善）
- lot_size を銘柄毎に管理する拡張（stocks マスタの導入）
- monitoring の test/dry-run モード（本番 DB 操作回避）
- paper_verification_report の出力を CSV/JSON にエクスポートするオプション追加

以上。