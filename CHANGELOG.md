CHANGELOG
=========

すべての重要な変更を追跡します。フォーマットは "Keep a Changelog" に準拠しています。
リリースごとの主な追加・変更点を日本語で記載しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-25
--------------------

Added
- 初回公開リリース。
- 起動スクリプト / ランナーを追加
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite（data/paper_trading.db デフォルト）を使用する分離を実装。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）検知で安全に停止するロジックを追加。実行中は execution.pid に PID を書き込む想定。
    - エンジンをデーモンスレッドで起動し、停止フラグまたはスレッド終了で安全終了。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバックして警告）。
    - 監視では環境にかかわらず本番 sqlite_path を参照する挙動を規定。
    - 停止フラグ検知でループ終了。KeyboardInterrupt を捕捉してクリーンに終了。

- 設定管理・ウィザード・検証ツールを追加
  - config.py
    - プロジェクトルートの自動検出（.git または pyproject.toml）に基づく .env 自動読み込み機能を追加（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env / .env.local の読み込み順序と上書き保護（OS 環境変数は protected として上書きを制御）。
    - .env 行パーサーを強化し、export プレフィックス、クォート（シングル／ダブル）内のバックスラッシュエスケープ、インラインコメントの扱いを適切に処理。
    - Settings クラスを導入し、J-Quants / kabu API / DB パス /監視閾値などの設定プロパティを提供。
    - Paper Trading 用設定（paper_sqlite_path、paper_fill_mode 等）や env 判定ヘルパー（is_live/is_paper/is_dev）を追加。
  - config_setup.py
    - 対話式ウィザードを実装し、.env の初期作成・更新を支援。
    - シークレット入力をマスク表示、選択肢・デフォルト値の提示、保存確認を実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml の基本的な整合性チェックを行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス親ディレクトリチェック、YAML ファイルの存在・パースチェック（PyYAML がインストールされている場合）。
    - --strict オプションで警告を FAIL 扱いにできる。

- 分析・レポート・ツールを追加
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite を解析して検証レポート（稼働率、注文成功率、送信率、レイテンシ等）を生成するスクリプトを追加。
    - P95 レイテンシ計算、閾値（稼働率, fill/send %, P95 latency）による PASS/FAIL 判定を実装。
    - --from/--to/--db オプションで期間・DB パスを指定可能。

- ポートフォリオ構築（純粋関数群）を追加
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（スコア降順、同点は signal_rank でタイブレーク）。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコアが 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存ポジションのセクター別時価を計算して上限を超えるセクターの新規候補を除外）。
    - レジームに応じた乗数 calc_regime_multiplier（'bull','neutral','bear' をサポート、未知レジームはフォールバックして 1.0）。
  - portfolio/position_sizing.py
    - position sizing ロジック calc_position_sizes を追加。
    - risk_based / equal / score の allocation_method を実装。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）に基づくスケールダウン、残差分の lot 単位での再配分アルゴリズムを実装。
    - cost_buffer による保守的コスト見積り対応。

- ユーティリティを追加・改善
  - utils/logging_setup.py
    - 標準化されたログ初期化ユーティリティを追加。
    - コンソール出力は stdout を使用。TimedRotatingFileHandler による日次ローテーション（30 日保持）を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続（堅牢化）。
  - utils/process_priority.py
    - プラットフォーム差分（Windows / POSIX）を吸収してプロセス優先度を設定するユーティリティを追加。
    - set_process_priority(level) で high/normal/low をサポート（Windows の優先度クラス、POSIX の nice 値を使用）。
    - set_cpu_affinity(cpu_count) によりプロセスの CPU affinity を固定する補助関数を追加。
    - アクセス権限不足等の例外を安全にハンドリングして警告ログを出力。

Changed
- ロギング方針を統一
  - すべての起動スクリプトから utils.logging_setup.setup_logging を呼び出して一貫したログ出力を実現。
- .env の読み込みロジック
  - .env.local を .env の上書きとしてサポートし、OS の環境変数は保護（protected）されるように変更。
- DB 初期化
  - 起動時に monitoring 用テーブルの初期化（init_monitoring_db）を行い、存在保証（冪等）を確保。

Fixed
- .env パーサーの堅牢性向上
  - クォートされた値内のバックスラッシュエスケープ処理とインラインコメントの適切な無視を実装して解析ミスを修正。
  - export KEY=val 形式や行頭のコメント、空行を正しく無視。
- ポートフォリオ関連のフォールバック処理
  - calc_score_weights は全銘柄スコアが 0 の場合に等金額配分にフォールバックして警告を出力。
  - apply_sector_cap は "unknown" セクター（マップ未定義）を上限判定から除外。
- ログ出力先・回転処理の失敗耐性
  - ログディレクトリ作成やファイルハンドラ作成に失敗してもコンソールログで継続するように修正。

Security
- 特記事項なし

Notes / Usage Tips
- 環境変数の自動ロードはプロジェクトルートが特定できる場合にのみ行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading を行う際は KABUSYS_ENV=paper_trading を設定すると、実取引データベースとは分離された data/paper_trading.db が使用されます。
- ログはデフォルトで logs/ 以下に app_name.log として日次ローテーションされます。ログディレクトリは LOG_DIR 環境変数または setup_logging の引数で変更可能です。
- 実行中に安全に停止するにはプロジェクトルート/data/stop_requested.flag を作成してください（run_execution/run_monitoring が検知して停止します）。

ライセンス、貢献、その他のメモはリポジトリ内の README を参照してください。