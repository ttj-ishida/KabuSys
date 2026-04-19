# CHANGELOG

すべての重要な変更は「Keep a Changelog」の形式に従って記載しています。  
このファイルは、与えられたコードベースの内容から機能追加・改善点・修正点を推測して作成したものです。

全般的な注記
- 本リリースはローカル開発・ペーパートレード・本番運用を想定した自動売買システムの初期公開相当と推定されます。
- DuckDB と SQLite を組み合わせた分析/運用データ設計、.env ベースの設定管理、ログ出力の統一化、プロセス優先度設定、ペーパートレード専用 DB 分離など、運用を意識したユーティリティ群が含まれます。

## [0.1.0] - 2026-04-19
初回リリース（推定）

### 追加 (Added)
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV により paper_trading モードで MockBroker を使用し、ペーパートレード用 DB(data/paper_trading.db) に記録するように分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ（data/stop_requested.flag）検知や例外ハンドリングを備える。
- 設定管理・検証ツール
  - config.py: Settings クラスを導入。.env 自動ロード（.env, .env.local）・キー必須チェック・各種設定プロパティ（DB パス、ログレベル、Paper Trading 関連等）を提供。.env の読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行う。
  - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加（項目定義・既存値読み込み・保存機能）。
  - validate_config.py: .env と config/*.yaml の起動前検証を行う CLI を追加。--strict オプションで警告をエラー扱いにできる。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: シグナル選定（select_candidates）と重み計算（calc_equal_weights, calc_score_weights）を実装。
  - portfolio/risk_adjustment.py: セクター集中制限適用関数（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py: 株数算出ロジック（risk_based / equal / score）や単元丸め、aggregate cap によるスケールダウンを実装。
  - portfolio/__init__.py: 上記機能を公開するパッケージ化。
- ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテーション (TimedRotatingFileHandler) を組み合わせ、ログディレクトリ自動作成・失敗時フォールバックを実装。
  - utils/process_priority.py: psutil を利用してクロスプラットフォームにプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを追加。Windows / POSIX を吸収。
- モニタリング関連
  - monitoring.monitoring_db.init_monitoring_db を起動スクリプトで呼び出して監視テーブルの存在を保証（冪等）。（ファイルは参照されているがソースは今回提供コードの外）
  - SystemMonitor の呼び出しにより定期的な状態記録を行う構成を導入（実装詳細は別モジュール）。
- データベース統合
  - DuckDB 接続（分析用）と SQLite 接続（監視 / 発注履歴）を双方で利用する設計を採用。起動スクリプトから duckdb.connect / sqlite3.connect を行う。
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB を解析して稼働率・注文成功率・送信率・レイテンシなどを集計するレポート生成ツールを追加。閾値（例: 稼働率 >= 99% 等）で PASS/FAIL 判定を行う。
- 研究用モジュール（下地）
  - research/factor_research.py: DuckDB を使ったファクター計算の枠組みを追加（モメンタム・MA200乖離・ATR 等の計算を想定）。（ファイルは途中で切れているが基本設計と定数が追加されている）
- パッケージ管理
  - __version__ = "0.1.0" を追加（パッケージバージョン定義）。

### 変更 (Changed)
- .env 読み込み仕様を強化
  - export KEY=val 形式やシングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応した独自パーサーを導入。
  - OS 環境変数を保護するため .env の上書きルール（.env → .env.local の順、既存 OS 環境変数を protected として扱う）を導入。
- 起動時のログ／優先度設定
  - すべての起動スクリプトで setup_logging と set_process_priority を最初に呼び出して一貫したログ・プロセス設定を行うように変更。
- ExecutionEngine の DB 分離動作
  - KABUSYS_ENV=paper_trading 時には paper_sqlite_path を使用して本番 DB から完全に分離するようにした（ペーパートレード専用 DB）。

### 修正 (Fixed)
- 環境変数の不正値取り扱いに対する堅牢化
  - MONITOR_POLL_INTERVAL が不正（非整数や 0 以下）だった場合に警告を出してデフォルト値にフォールバックする処理を追加。
  - Settings.paper_fill_mode の検証で無効値は ValueError を発生させるようにし、誤設定を早期検出可能に。
- ロギングのフォールバック挙動
  - ログディレクトリ作成に失敗した場合にファイルハンドラをスキップしてコンソール出力のみ続行するよう改善（運用環境での起動失敗を回避）。

### 非推奨 (Deprecated)
- 該当なし（初期リリース相当のため非推奨扱いはなし）

### 削除 (Removed)
- 該当なし

### セキュリティ (Security)
- 環境変数読み込み時に OS 環境変数を保護（protected）する扱いを導入し、実行環境の意図しない上書きを防止する仕様を採用。

---

開発・運用メモ（コードからの注記）
- stop_requested.flag / execution.pid / kill.flag 等のファイルベースの Kill Switch / PID 管理を採用しており、外部プロセスマネージャや運用オペレーションからの停止制御が可能。
- position_sizing の aggregate cap や lot_size 処理では端数処理（単元丸め）や残余配分ロジックを実装しているため、実運用での注文量算出に配慮している。
- risk_adjustment.apply_sector_cap は price_map の欠損（0.0）時に過少推定が起きる可能性がある旨を TODO コメントで指摘しており、将来的なフォールバック価格導入を想定している。
- research/factor_research.py はファクター計算の骨格を用意しているが、ファイル末尾が切れており実装途中の可能性あり。

変更履歴に誤りや追記が必要な点があれば、対象ファイルや意図されているリリース方針を教えてください。必要に応じて日付やカテゴリの分割・詳細化を行います。