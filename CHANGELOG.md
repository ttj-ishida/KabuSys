KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠します。  
「Unreleased」には直近の差分（このコードベースから推測される追加・改良点）を記載し、下位に初回リリースとして 0.1.0 を記述しています。

## [Unreleased]

### Added
- 環境設定の自動読み込み強化
  - プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動ロードする機能を追加。
  - OS環境変数を保護するための protected 機構を導入し、.env.local が OS 環境変数を上書きしないように制御。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を導入。

- .env パーサの拡張
  - export プレフィックス（export KEY=val）やシングル/ダブルクォート内のバックスラッシュエスケープ、行内コメント処理に対応。
  - 無効行やコメントを無視する堅牢なパース処理を実装。

- 対話式設定ウィザード（config_setup）
  - python -m kabusys.config_setup による .env の初期生成・更新ウィザードを追加。秘密キーはマスク表示。
  - デフォルト値・選択肢・説明を表示して対話的に生成可能。生成後に .env を書き出す機能を提供。

- 設定検証 CLI（validate_config）
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在チェックなどを実行する CLI を追加。
  - PyYAML が存在する場合は config/*.yaml のパース検証を行う。--strict により警告をエラー扱いにするオプションを追加。

- 実行スクリプト
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。Paper Trading（KABUSYS_ENV=paper_trading）の場合は paper_trading 用 DB を使用し MockBroker を利用する想定。
  - run_monitoring: システム監視ループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグファイル（data/stop_requested.flag）で安全に停止可能。

- ロギングユーティリティ（utils.logging_setup）
  - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を組み合わせた統一ロギング設定を提供。
  - ログレベル/ログディレクトリ解決順（引数 > 環境変数 > デフォルト）を明確化。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールログのみ継続。

- プロセス優先度ユーティリティ（utils.process_priority）
  - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収してプロセス優先度（high/normal/low）を設定する関数を追加。
  - CPU affinity を設定する set_cpu_affinity 関数を追加（最初 N コアに固定）。権限不足や未対応環境では警告ログを出してスキップ。

- ポートフォリオ構築モジュール（kabusys.portfolio）
  - 候補選定、等配分・スコア加重配分（select_candidates / calc_equal_weights / calc_score_weights）を実装。
  - セクター集中制限（apply_sector_cap）、市場レジームに応じた投下乗数（calc_regime_multiplier）を実装。
  - ポジションサイズ計算（calc_position_sizes）を実装。risk_based / equal / score の allocation_method をサポートし、lot_size（単元）丸め、aggregate cap によるスケールダウン、残差のロット単位配分ロジックを備える。

- Paper Trading 検証ツール（tools.paper_verification_report）
  - ペーパートレード用 SQLite DB から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計して検証レポートを生成するスクリプトを追加。
  - レポートは閾値（稼働率、成功率、P95 等）に基づき PASS/FAIL を判定する。

- research/factor_research の骨組み
  - DuckDB 接続を受け、prices_daily / raw_financials を参照してモメンタム等のファクターを計算する目的のモジュールの実装を開始（モメンタム算出関数 calc_momentum の追加）。※ファイル末尾が未完のため継続実装が必要。

### Changed
- 設定管理 API をクラス化
  - Settings クラスを通じて各種環境変数（J-Quants / kabu API / DB パス / 監視閾値 / システムフラグ等）をプロパティとして取得可能に整理。
  - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の値検証（不正値時は例外）を追加。

- 監視と実行の DB 分離
  - run_execution は paper_trading モード時に paper_sqlite_path を使用して運用データを本番 DB から分離する動作を明文化。
  - run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する仕様を明記（監視 DB は本番 DB を参照する想定）。

### Fixed
- MONITOR_POLL_INTERVAL の不正値処理
  - 環境変数 MONITOR_POLL_INTERVAL が 0 以下や非整数の場合にデフォルト値にフォールバックして警告を出すように修正（time.sleep に渡すエラー回避）。

### Deprecated
- なし

### Security
- 環境変数の秘密値（パスワード・トークン）についてウィザード表示でマスクするなど、取り扱い注意を明示。

---

## [0.1.0] - 2026-04-18

初期リリース — 基本機能を実装。

### Added
- 基本的なパッケージ構成（kabusys）とバージョン情報（__version__ = "0.1.0"）。
- 環境設定読み込み・管理（.env パーサ、Settings クラス）。
- 実行 / 監視用スクリプトのエントリポイント（run_execution, run_monitoring）。
- 設定ウィザード（config_setup）と検証ツール（validate_config）。
- ロギング設定ユーティリティ（stdout + 日次ローテーション）。
- プロセス優先度 / CPU affinity 設定ユーティリティ（psutil ベース）。
- ポートフォリオ構築（候補選定・重み算出・ポジションサイズ計算）とリスク調整（セクター上限・レジーム係数）。
- Paper Trading 向け検証レポート生成ツール。
- 研究モジュール（factor_research）の基礎（モメンタム等のファクター計算方針と途中実装）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

---

注記 / TODO（コードから推測）
- research/factor_research.py はモメンタム計算の実装が途中で終わっている（ファイル末尾に不完全な行あり）。追加のファクター実装・単体テストが必要。
- ExecutionEngine や BrokerClientFactory など本体のコンポーネントは本ログに示された呼び出しインターフェースで統合されているが、実際のブローカー接続・注文処理の詳細やテストは別途確認が必要。
- logging_setup はログディレクトリ作成失敗時にファイル出力をスキップする実装になっているため、運用環境では LOG_DIR の書き込み権限を事前に整備することを推奨。

この CHANGELOG は現行コードベースからの機能・変更点を推測して作成しています。より正確な差分（コミット履歴や過去リリースノート）を用意いただければ、より細かく正確な履歴に更新できます。