CHANGELOG.md
=============

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

## [0.1.0] - 2026-04-25

### Added
- 基本リリースとして自動売買システム「KabuSys」のコアユーティリティとランタイムスクリプトを追加。
  - パッケージ情報:
    - src/kabusys/__init__.py — バージョン 0.1.0 を設定。
- 起動スクリプト:
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止はプロジェクト直下 data/stop_requested.flag によるフラグ検知で制御。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化。
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 用の専用 SQLite（data/paper_trading.db など）と MockBroker を使用して本番 DB と分離。
    - 停止フラグ検知・PID ファイル管理・別スレッドでのエンジン実行を実装。
- 設定管理:
  - src/kabusys/config.py
    - .env 自動ロード（.env → .env.local、OS 環境変数を保護）と堅牢な .env パーサーを実装。
    - Settings クラスで環境変数のラップと検証を提供（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等のバリデーション）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能を追加。
- 設定関連 CLI:
  - src/kabusys/config_setup.py
    - .env を対話式に作成/更新するウィザードを追加。シークレットのマスク表示、デフォルト値表示、保存の確認等を実装。
  - src/kabusys/validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数やパス、config/*.yaml の存在と YAML パース（PyYAML があれば）をチェック。--strict オプションで警告を失敗扱いにできる。
- ロギング/プロセスユーティリティ:
  - src/kabusys/utils/logging_setup.py
    - 全スクリプトで共通利用するログ設定ユーティリティを追加。
    - stdout への StreamHandler（stderr ではなく stdout）、日次ローテートの TimedRotatingFileHandler（30 日保持）をルートロガーへ設定。既存ハンドラの二重設定防止のため一度クリアする。
    - LOG_DIR/LOG_LEVEL の解決順を実装（引数 > 環境変数 > デフォルト）。
  - src/kabusys/utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定を提供（set_process_priority, set_cpu_affinity）。
    - 起動スクリプトでは開始直後に set_process_priority("high") を呼ぶようになっている。
- ポートフォリオ構築モジュール:
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）と重み計算（calc_equal_weights, calc_score_weights）を追加。スコアが全て 0 の際は等分配にフォールバック。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中上限適用（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。未知レジームはフォールバックして 1.0 を返す。
  - src/kabusys/portfolio/position_sizing.py
    - 各種配分方式（risk_based / equal / score）に対応した株数決定ロジックを実装。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金でのスケーリング）、cost_buffer を考慮した保守的なコスト見積りを実装。
  - src/kabusys/portfolio/__init__.py でエクスポートを提供。
- リサーチ系ユーティリティ（着手中）:
  - src/kabusys/research/factor_research.py
    - DuckDB を用いたファクター計算基盤（モメンタム/MA/ATR など）の骨子を追加（関数 calc_momentum 等開始）。
- ツール:
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成する CLI を追加。
    - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を集計し PASS/FAIL 判定（閾値はファイル内で定義）する機能を実装。--from/--to/--db オプションをサポート。

### Changed
- ログ出力について:
  - ログのデフォルト出力先を stdout にし、cron 等からのリダイレクト運用を考慮（logging_setup）。
- .env ロード順と保護:
  - OS 環境変数を保護する仕組み（protected set）を導入し、.env.local は .env の上書きとして扱う。

### Fixed
- MONITOR_POLL_INTERVAL の不正値対策:
  - run_monitoring 内で MONITOR_POLL_INTERVAL を int に変換し、1 未満の値や不正な文字列が渡された場合はワーニングを出してデフォルト（60 秒）にフォールバックすることで time.sleep による例外発生を防止。
- .env 読み込みの堅牢化:
  - config._load_env_file でファイル読み込み失敗時に警告を出して継続するようにし、テスト時やパッケージ配布後も安全に動作するよう改善。
  - .env の各行パースを robust に実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理）。
- DuckDB / YAML 非存在時の挙動:
  - validate_config で PyYAML が見つからない場合は YAML 検証をスキップして警告を出すようにし、環境に依存しない動作を確保。
- フォールバックと安全弁の強化:
  - 複数箇所で外部依存や欠損データに対して安全なフォールバックを実装（例: calc_score_weights が全スコア 0 の場合、calc_regime_multiplier が未知レジームのとき等）。

### Deprecated
- なし（初期リリース）

### Removed
- なし（初期リリース）

### Security
- .env の扱いに関する注意書きを config_setup が出力するようにし、.env を絶対に Git にコミットしない旨を明示。
- Secrets（J-Quants トークン、kabu API パスワード等）は Settings/ウィザードでシークレット扱い（UI マスク）にして保存時の注意を促す。

補足メモ
- Paper Trading（シミュレーション）と Live（本番）の DB を明確に分離する設計を採用。KABUSYS_ENV により実行時の振る舞い（MockBroker の利用、DB パスの切替等）を切替可能。
- 実行スクリプトは起動時にプロセス優先度を "high" に上げることを試みる（権限不足等は警告としてスキップ）。
- ログローテーションやディレクトリ作成失敗の際はファイルハンドラをスキップしてコンソールログのみで継続する方針。
- 一部モジュール（research/*.py）は計算ロジックの骨組みがあり、今後さらにファクター群や集計処理が実装される想定。

---  
（以上）