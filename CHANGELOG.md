# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」準拠です。  
バージョン番号はパッケージ内の __version__ に準拠しています。

なお、本 CHANGELOG はコードベースからの推測に基づき作成しています（コミット履歴そのものではありません）。

## [Unreleased]

## [0.1.0] - 2026-04-17

Added
- 初回リリース: KabuSys パッケージを追加。基本的な自動売買 / 監視 / ツール群を実装。
  - パッケージ version: 0.1.0 (src/kabusys/__init__.py)
- 環境設定・読み込み
  - .env 自動読み込み機能を追加。プロジェクトルートの検出は .git または pyproject.toml を基準とし、CWD に依存しない実装（src/kabusys/config.py）。
  - .env のパースを強化: export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ、インラインコメント取り扱いなどに対応（src/kabusys/config.py）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（src/kabusys/config.py）。
  - Settings クラスを追加し、各種設定値（J-Quants / kabu API / DB パス / monitoring 閾値 / env 判定等）をプロパティで提供（src/kabusys/config.py）。
  - PAPER_FILL_MODE のバリデーション実装（有効値: instant / partial / never / reject）（src/kabusys/config.py）。
- .env 対話式ウィザード
  - config_setup CLI を追加。対話形式で .env を作成・更新、シークレットはマスク表示、保存前確認あり（src/kabusys/config_setup.py）。
  - 出力される .env のテンプレートを整備（コメント付き、Git にコミットしない旨の注意を含む）（src/kabusys/config_setup.py）。
- 設定検証 CLI
  - validate_config CLI を追加。必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DUCKDB/SQLite パス親ディレクトリ確認、config/*.yaml の存在と（PyYAML がある場合は）パース検証、KABUSYS_ENV=live 時の追加ガードを実装（--strict オプションで警告を FAIL 扱い可能）（src/kabusys/validate_config.py）。
- 実行 / 監視スクリプト
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）:
    - 起動時にプロセス優先度を "high" に設定（utils/process_priority を利用）。
    - 環境が paper_trading の場合は専用の paper_sqlite_path を使用して本番 DB と分離。
    - BrokerFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで起動。停止フラグ (data/stop_requested.flag) により安全に停止可能。
    - execution.pid 書き出しをサポート。
  - SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境に依らず本番 sqlite_path を参照し monitoring テーブルを初期化（init_monitoring_db）。
    - stop フラグでループ終了、KeyboardInterrupt ハンドリング、接続クローズ処理を実装。
- 監視 DB 初期化
  - init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）（参照箇所: run_execution, run_monitoring）。
- プロセス優先度 / CPU 固定ユーティリティ
  - psutil を用いたクロスプラットフォーム優先度設定機能を追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX(Linux, Darwin, FreeBSD) に対応した優先度(nice/HIGH_PRIORITY_CLASS 等) を設定。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を提供（アクセス権限や未対応環境では警告を出してスキップ）。
    - 失敗時に例外を投げず警告でフォールバックする安全設計。
- ポートフォリオ構築ロジック（純粋関数群）
  - 候補選定・重み付け: select_candidates, calc_equal_weights, calc_score_weights（src/kabusys/portfolio/portfolio_builder.py）。
    - スコア降順、同点は signal_rank でタイブレーク。
    - 全スコアが 0 の場合は等金額配分にフォールバック（警告ログ）。
  - セクター集中制限・レジーム乗数: apply_sector_cap, calc_regime_multiplier（src/kabusys/portfolio/risk_adjustment.py）。
    - セクター別既存エクスポージャ計算（売却予定銘柄は除外）、上限超過セクターの新規候補除外。
    - レジームに応じた資金乗数を返す（bull/neutral/bear をサポート、未知のレジームはフォールバック）。
  - 株数決定・リスク制限・単元丸め: calc_position_sizes（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method 支持（risk_based / equal / score）。
    - 単元（lot_size）丸め、1銘柄上限・aggregate cap のスケールダウンロジック、cost_buffer（手数料・スリッページ見積り）を考慮した保守的見積り。
    - aggregate cap 超過時はスケーリング→lot 単位で残差再配分する高度なロジックを実装。
- 研究用ファクター計算（DuckDB ベース）
  - factor_research モジュールを追加（src/kabusys/research/factor_research.py）。
    - モメンタム（1M/3M/6M リターン、MA200 乖離）計算（欠損データに対する None ハンドリング）。
    - ボラティリティ/流動性ファクター（ATR20、相対 ATR、20日平均売買代金、出来高比率）を実装（DuckDB SQL を使用し効率的に計算）。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルのみ参照する設計（本番 API へのアクセスなし）。
- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出して PASS/FAIL 判定を表示。
    - P95 計算、期間フィルタリング、DB 不存在時のエラーメッセージなどを実装。
- パッケージ公開補助
  - portfolio モジュールから主要関数をエクスポートする __all__ を整備（src/kabusys/portfolio/__init__.py）。

Changed
- 設計上の安全策とフォールバックを多数導入
  - env 値やコマンドライン引数の不正値に対して警告しデフォルトにフォールバックする実装を追加（例: MONITOR_POLL_INTERVAL、不正な PAPER_FILL_MODE、LOG_LEVEL）。
  - プロセス優先度や CPU affinity の設定はアクセス権限がない場合に警告を出してスキップするよう変更（安全に稼働することを優先）。
  - DB 初期化は冪等（既存テーブルがあっても安全に実行）となるよう構成（init_monitoring_db 呼び出し）。

Fixed
- 安定性および堅牢性の改善
  - .env パーサーを強化することで、クォートやエスケープ、コメント含みの値を正しく読み込めるようにした（以前の単純パースでの破壊的解釈を回避）。
  - run_monitoring のポーリング間隔取得で 0 以下や非整数を扱った場合に ValueError を防ぎ、ログ警告後にデフォルトへフォールバックする実装を追加（src/kabusys/run_monitoring.py）。
  - ExecutionEngine 起動中の停止フラグ処理を強化し、スレッド停止の待機ロジックを実装（src/kabusys/run_execution.py）。
  - Paper verification report は対象テーブルが存在しない・OperationalError が発生する場合にも耐性を持ち、該当指標を N/A または 0 として扱うようにした（src/kabusys/tools/paper_verification_report.py）。

Security
- シークレット設定（トークン・パスワード）の取り扱いに注意書きを追加（.env を絶対にリポジトリへコミットしない旨）（src/kabusys/config_setup.py）。
- config_setup のインタラクティブ表示ではシークレット値をマスクして表示。

Notes / Known limitations
- 一部機能は環境依存（psutil の優先度設定、CPU affinity）であり、実行権限やプラットフォームにより効果が異なる。失敗時はログ警告でフォールバックする設計のため致命的ではないが期待どおり動作しないことがある（src/kabusys/utils/process_priority.py）。
- position_sizing の lot_size は現在グローバル固定（デフォルト 100）。銘柄別単元を持たせる拡張は TODO（src/kabusys/portfolio/position_sizing.py）。
- factor_research は DuckDB の prices_daily / raw_financials テーブル構造に依存する。テーブルスキーマ不一致やデータ不足時は None を返す等の保護ロジックを含むが、事前データ準備が必要。

----

参考: コード内で参照される主なファイル
- src/kabusys/config.py
- src/kabusys/config_setup.py
- src/kabusys/validate_config.py
- src/kabusys/run_execution.py
- src/kabusys/run_monitoring.py
- src/kabusys/utils/process_priority.py
- src/kabusys/portfolio/*.py
- src/kabusys/research/factor_research.py
- src/kabusys/tools/paper_verification_report.py

（この CHANGELOG はソースコードから推測して作成しています。より詳細な変更履歴はコミットログを参照してください。）