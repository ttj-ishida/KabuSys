# CHANGELOG

すべての重要な変更を Keep a Changelog の形式で記録します。  
このファイルはコードベースの現状から推測して作成しています。

フォーマット:
- Unreleased: 次のリリースに向けた未リリースの変更
- 各リリースは日付付きで「Added / Changed / Fixed / Deprecated / Removed / Security」に分類

---

## [Unreleased]

- なし（現状は v0.1.0 が最新の公開リリース相当の状態として推定）

---

## [0.1.0] - 2026-04-20

### Added
- 全体
  - 初期パッケージリリース相当の機能群を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 設定関連
  - Settings クラスを追加し、環境変数経由でアプリ設定を一元管理（J-Quants / kabu API / DB パス / LINE / 監視閾値等）。
  - .env ファイル自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env の読み込み挙動:
    - `.env` → `.env.local` の順で読み込み（OS 環境変数は保護され上書きされない）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` 環境変数で自動読み込みを無効化可能。
  - 設定ウィザード CLI を追加（`kabusys.config_setup`）:
    - 対話式で .env を生成・更新する。
    - シークレット項目はマスク表示。
  - 設定検証 CLI を追加（`kabusys.validate_config`）:
    - 必須環境変数や DB パス、config/*.yaml の存在や YAML パースを検査。
    - `--strict` オプションで警告を失敗扱いにする機能。

- 実行 / 監視ランナー
  - ExecutionEngine 起動スクリプト `run_execution.py` を追加。
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離して使用。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - エンジンは別スレッドで実行し、停止フラグや PID ファイル管理に対応。
  - SystemMonitor ポーリングループ起動スクリプト `run_monitoring.py` を追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番用 `sqlite_path` を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検出時にループを終了。

- ツール
  - Paper Trading 検証レポート生成ツール `kabusys.tools.paper_verification_report` を追加。
    - 稼働率、注文成功率、送信率、レイテンシ (avg / max / P95) 等を集計して PASS/FAIL 判定。
    - 期間指定オプション（--from / --to / --db）をサポート。
    - デフォルト DB パスは `data/paper_trading.db`（環境変数 `PAPER_TRADING_SQLITE_PATH` で上書き可）。
    - 判定閾値（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）を定義。

- ポートフォリオ構築（純関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - select_candidates（スコア降順、同点は signal_rank によるタイブレーク）
    - calc_equal_weights（等配分）
    - calc_score_weights（スコア正規化, スコア全て 0.0 の場合は等配分にフォールバック）
  - `kabusys.portfolio.risk_adjustment`:
    - apply_sector_cap（セクター集中制限、当日売却予定銘柄の除外対応、unknown セクターは上限不適用）
    - calc_regime_multiplier（レジームに応じた資金乗数: bull/neutral/bear をマップ、未知レジームはフォールバック）
  - `kabusys.portfolio.position_sizing`:
    - calc_position_sizes（risk_based / equal / score の割当方式を実装）
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合のスケールダウン）や cost_buffer を考慮した安全弁を実装

- ユーティリティ
  - ログ設定ユーティリティ `kabusys.utils.logging_setup` を追加:
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30世代保持）をルートロガーに設定。
    - 既存ハンドラをクリアして二重設定を防止。
    - LOG_DIR/LOG_LEVEL の解決順をサポートし、ファイルハンドラ作成失敗時はコンソール出力にフォールバック。
  - プロセス優先度 / CPU affinity ユーティリティ `kabusys.utils.process_priority` を追加:
    - Windows / POSIX の差分を吸収して優先度設定（high/normal/low）を行う。
    - CPU affinity を最初の N コアに固定する機能を提供。
    - 権限不足時は警告を出して安全にスキップ。

- データリサーチ
  - 研究用モジュール `kabusys.research.factor_research` の基盤を追加（モメンタム等のファクター計算設計、DuckDB を使った実装方針を明記）。一部未完の実装（ファイル末尾が途切れていることを示唆）。

- DB 初期化
  - 監視用 DB の初期化ヘルパー（init_monitoring_db）を利用して、監視テーブル存在の保証を行う呼び出しを実装（冪等性を考慮）。

### Changed
- .env パーサーを強化:
  - `export KEY=val` 形式をサポート。
  - シングル/ダブルクォート値のエスケープ処理を考慮して値を正しく抽出。
  - クォートなし値のインラインコメント判定を空白直前の `#` のみをコメントと見なすロジックに改良。
  - .env 読み込み時に OS 環境変数を保護する `protected` 機構を導入（.env.local による上書きを制御）。
- Settings の振る舞い:
  - 環境 `KABUSYS_ENV` のバリデーションを強化（development/paper_trading/live のみ許可）。
  - PAPER_FILL_MODE の検証を追加（instant/partial/never/reject のみ許可）。
  - paper_trading 用の SQLite パスを分離して `paper_sqlite_path` を導入。
  - 監視しきい値（CPU/MEM/DISK）や kill_flag 関連設定を Settings で一元管理。
- run_monitoring.py / run_execution.py の動作:
  - 起動時にプロセス優先度を最初に High に設定する処理を追加。
  - 停止フラグの検出（data/stop_requested.flag）による優雅な停止に対応。
  - run_monitoring は MONITOR_POLL_INTERVAL の値検証（1 未満はデフォルトにフォールバック）を実装。
  - run_execution は paper_trading 環境時に MockBrokerClient を利用し、paper_trading 用 DB に記録して本番 DB と分離する挙動を実装。
- logging_setup:
  - stdout を利用する設計に（StreamHandler を sys.stdout に設定）し、cron等でのリダイレクト運用を考慮。
  - ディレクトリ作成失敗時にファイル出力をスキップするフォールバックを明示的に実装。
- position_sizing:
  - aggregate cap のスケーリング時に小数端数の取り扱い（lot_size 単位での再配分）を導入して再現性のある配分を実現。

### Fixed
- 環境自動ロードの安全性向上:
  - プロジェクトルート検出を .git または pyproject.toml に依存させて、配布後の挙動で CWD に依存しないように修正。
- ログハンドラ二重追加の回避:
  - setup_logging 内で既存ハンドラを flush/close ののち削除してから再設定するようにした。
- process_priority のプラットフォーム互換性:
  - Windows の定数が存在しない環境でもモジュールロードが失敗しないよう getattr フォールバックを採用。
  - 権限不足や未実装機能発生時に警告を出して処理をスキップするよう例外ハンドリングを追加。

### Deprecated
- なし（初期リリース相当のため）

### Removed
- なし

### Security
- 環境変数や .env の取り扱いに関する注意文やガードを追加（.env を絶対に Git にコミットしない旨を config_setup の出力に記載）。

---

注記:
- 上記 CHANGELOG は提示されたソースコードを基に推測して作成しています。実際の履歴・コミットメッセージと差異がある可能性があります。必要であれば、より正確にするために Git のコミット履歴やリリースノートの元データを提供してください。