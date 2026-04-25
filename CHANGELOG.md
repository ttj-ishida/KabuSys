# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。歴史の可読性を優先し、後から変更された箇所の要点を記録します。

現在のリポジトリには初期リリース相当の実装が含まれているため、以下はコードベースの内容から推測して作成した変更履歴です。

なお日付は本リポジトリ状態を取得した日付を使用しています。

## [Unreleased]

### Added
- ドキュメント化された開発ツール・ユーティリティ群を追加
  - 対話式の `.env` 作成/更新ウィザード（kabusys.config_setup）を追加。必須項目のマスク入力やデフォルト値の案内を備える。
  - 設定検証 CLI（kabusys.validate_config）を追加。必須環境変数や config/*.yaml の存在・パース検査、`--strict` フラグをサポート。
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）を追加。稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL を判定。
- 実行用スクリプトを追加
  - 実行エンジン起動スクリプト（kabusys.run_execution）を追加。KABUSYS_ENV による paper_trading 時の DB 分離（data/paper_trading.db の利用）や Mock ブローカーの選択を想定。
  - 監視ポーリングループ起動スクリプト（kabusys.run_monitoring）を追加。環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き、停止フラグ（data/stop_requested.flag）での安全停止をサポート。
- 設定管理・読み込み機能（kabusys.config）を追加
  - プロジェクトルート検出（.git / pyproject.toml）に基づく自動 `.env` ロードを実装（無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート）。
  - 複雑な .env パースロジックを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理など）。
  - 各種設定プロパティを提供（DB パス、LINE トークン、KABUSYS_ENV 判定、PAPER_FILL_MODE バリデーション、閾値設定 など）。
- ロギング・プロセス制御ユーティリティを追加（kabusys.utils）
  - 統一ログ設定ユーティリティ（kabusys.utils.logging_setup）を追加。stdout への StreamHandler と日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。LOG_DIR/LOG_LEVEL の優先解決に対応。
  - プロセス優先度・CPU affinity 設定ユーティリティ（kabusys.utils.process_priority）を追加。Windows/Linux/macOS を考慮し psutil を利用。権限不足時のフォールバックと警告出力あり。
- ポートフォリオ構築・リスク調整・ポジションサイジングモジュールを追加（kabusys.portfolio）
  - 候補選定・重み付け: select_candidates, calc_equal_weights, calc_score_weights を追加。スコアが全て 0 の場合のフォールバック処理あり。
  - セクター上限適用: apply_sector_cap を追加。既存保有からセクターごとの時価を算出し上限超過セクターの候補除外を実施（"unknown" セクターは制限免除）。
  - レジーム乗数: calc_regime_multiplier を追加。regime に応じた投下資金乗数（bull/neutral/bear）と未知レジームのフォールバックを実装。
  - ポジションサイズ計算: calc_position_sizes を追加。risk_based / equal / score の割当方式、lot_size（単元）丸め、aggregate cap（利用可能現金でスケーリング）、cost_buffer を用いた保守的見積り等を実装。
- リサーチモジュール（kabusys.research.factor_research）の骨組みを追加
  - Momentum / Value / Volatility / Liquidity 等のファクター計算方針と定数を定義。DuckDB 接続を受け価格/財務テーブルから計算する設計。

### Changed
- なし（初期導入のため "追加" が主）

### Fixed
- なし（新規実装中心）

### Security
- `.env` の生成スクリプトで .env を Git にコミットしない旨を明記（config_setup の書き出しヘッダに説明を追加）。

---

## [0.1.0] - 2026-04-25

初回公開リリース（コードベースの現状をパッケージ化）。主な内容は上記 Unreleased と同一。

### Added
- 監視/実行の起動スクリプト
  - run_monitoring: SystemMonitor のポーリング監視ループ起動、MONITOR_POLL_INTERVAL による調整、stop flag による終了処理、例外発生時のログ保護。
  - run_execution: ExecutionEngine の起動フロー、paper_trading 時の DB 分離、リスク/オーダー関連コンポーネントの組み立て、daemon スレッドでの実行と停止処理。
- 設定管理ライブラリ（robust .env パーサ、自動ロード、Settings クラス）
- 設定ウィザード（.env 作成/更新）
- 設定検証ツール（必須環境変数・YAML ファイルの存在とパース検査、live 環境向けの追加警告）
- ロギング設定ユーティリティ（stdout + 日次ローテーション、ログディレクトリ作成フォールバック）
- プロセス優先度・CPU affinity 設定ユーティリティ（プラットフォーム差を吸収）
- ポートフォリオ構築・リスク調整・ポジションサイジングロジック
- Paper Trading 検証レポート生成スクリプト（稼働率・注文指標・レイテンシ・PASS/FAIL 判定）
- DuckDB / SQLite を利用する分析・監視のための DB 初期化呼び出し（監視テーブルの冪等初期化など）
- パッケージメタ情報（kabusys.__version__ = "0.1.0"）

### Changed
- N/A（初期リリース）

### Fixed
- N/A（初期リリース）

### Notes / Implementation details
- run_execution は KABUSYS_ENV が `paper_trading` の場合に paper_sqlite_path を使用し、本番 SQLite DB と完全に分離する設計。
- run_monitoring は監視用 DB のパスとして Settings.sqlite_path（本番想定）を参照する仕様（監視データは環境に依存せず本番 DB を使用する設計になっている点に注意）。
- Settings には PAPER_FILL_MODE のバリデーション、KILL_FLAG_CLEAR_ON_START 等の安全ガード設定が含まれる。
- logging_setup はログディレクトリ作成に失敗した場合、ファイル出力をやめて stdout のみで継続するフォールバックを持つ。
- process_priority / set_cpu_affinity は権限不足や非対応環境での例外を捕捉して警告を出す安全設計。

---

過去の変更履歴が存在しないため、上記は「このコードベースを初回リリースした」想定で作成しました。  
差分（将来的なバージョン）を反映する場合は、変更点を箇条で追加し、該当バージョンに移動してください。必要であれば、より詳細なリリースノート（各関数の API 変更点、既知の制限・ TODO、互換性注意点など）も作成します。どの粒度で記載するか指示ください。