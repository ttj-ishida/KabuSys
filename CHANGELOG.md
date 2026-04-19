CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の書式に準拠しています（日本語訳）。
重要な変更点・追加機能はリリース単位で記載しています。コードベースから推測できる機能・振る舞いをまとめたため、実際の変更履歴と差異がある可能性があります。

Unreleased
----------

追加・改善（推定）
- .env パーサーの堅牢化:
  - export 付きの行、シングル/ダブルクォート内のエスケープ、インラインコメントの扱い、空行・コメント行の無視に対応。
- 環境設定の自動ロード制御:
  - プロジェクトルート検出ロジック（.git / pyproject.toml）を導入し、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード停止対応。
- ロギング設定の強化:
  - stdout 出力を標準にした StreamHandler と日次ローテーション（TimedRotatingFileHandler）をルートロガーに統一設定。ログディレクトリ作成失敗時はファイル出力をスキップして継続。
- プロセス優先度 / CPU affinity ユーティリティの追加:
  - Windows / POSIX を吸収する set_process_priority()，set_cpu_affinity() を提供。権限不足や未対応 OS を安全にハンドリング。
- 監視・実行スクリプトの利便性向上:
  - run_monitoring: MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は常に本番用 sqlite_path を使用。停止フラグファイル検出で安全に終了。
  - run_execution: KABUSYS_ENV=paper_trading 時は Mock ブローカーと別 SQLite（data/paper_trading.db）で完全分離。実行はスレッドで行い停止フラグでエンジン停止。起動時にプロセス優先度を high に変更。
- Paper Trading 検証レポート生成ツールの改善:
  - P95 計算、稼働率・注文成功率・送信率・レイテンシ等の指標を算出するレポート CLI を提供。日付フィルタ、DBパス指定オプションをサポート。
- ポートフォリオ構築関連（純粋関数群）の追加/改善:
  - 候補選定(select_candidates)、等金額/スコア重み(calc_equal_weights, calc_score_weights)。
  - セクター集中制限 apply_sector_cap（既存保有からセクター比率算出、"unknown" セクターは除外しない挙動など）。
  - レジーム乗数 calc_regime_multiplier（bull/neutral/bear をマッピング、未知値は警告後フォールバック）。
  - ポジションサイジング calc_position_sizes（risk_based / equal / score、lot_size に基づく丸め、aggregate cap スケーリング、cost_buffer を加味した保守的見積もり、残差に基づく追加配分ロジック）。
- 設定ウィザード CLI（.env 作成/更新）の追加:
  - 対話式で .env を生成・更新。秘密情報は表示をマスク。保存前に内容確認を実施。
- 設定検証ツール validate_config:
  - 必須環境変数、KABUSYS_ENV 値、ログレベル、DBパス（親ディレクトリ存在確認）、config/*.yaml 存在・パース確認（PyYAML 未インストール時はスキップ）、本番環境向けの追加警告を出力。--strict で警告を FAIL 扱い可能。

v0.1.0 - Initial release (推定)
-------------------------------

Added
- 基本構成
  - プロジェクトの初期バージョンとして下記コンポーネントを実装。
- 設定管理
  - kabusys.config.Settings クラスによる環境変数経由の設定取得（デフォルト値、型変換、バリデーションを含む）。
  - 自動 .env ロード（.env / .env.local、OS 環境変数保護）。
- 起動スクリプト / ランタイム
  - run_execution.py: ExecutionEngine の起動スクリプト（paper_trading の DB 分離、BrokerFactory 経由でブローカークライアント生成、OrderManager/RiskManager/Reconciler の組み立て）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 対応、停止フラグ検出、監視 DB 初期化）。
- ログ / プロセス管理ユーティリティ
  - kabusys.utils.logging_setup: 一貫したログ構成（コンソール + ファイル日次ローテーション）。
  - kabusys.utils.process_priority: クロスプラットフォームの優先度設定と CPU affinity。
- ポートフォリオ構築モジュール
  - kabusys.portfolio.*: 候補選定、重み算出、リスク制御（セクター上限・レジーム乗数）、ポジションサイズ計算（lot 丸め・スケーリングロジック）。
- モニタリング / テストツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成（稼働率・約定率・レイテンシ等の指標、閾値による PASS/FAIL 判定）。
- 開発支援ツール
  - config_setup.py: 対話式 .env ウィザード。
  - validate_config.py: 起動前の設定検証 CLI。
- パッケージ基本情報
  - __version__ = "0.1.0" を設定。

Changed
- 既定値とフォールバックの整備:
  - 各種パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）、ログレベルのデフォルトを明示。
- Paper Trading の分離:
  - ペーパートレーディング実行時は本番 DB を使用しないよう分離を強化。

Fixed
- .env の読み込み時に IO エラーが発生した場合の警告出力を追加。
- ログディレクトリ作成失敗時にファイルハンドラ作成をスキップしてもプロセスを継続するように修正。

Security
- .env ファイル生成時に "絶対に Git にコミットしないこと" をファイルヘッダへ明記。

Notes / 実装上の注意
- 一部モジュール内に TODO コメントあり（例: apply_sector_cap の価格欠損時のフォールバック、position_sizing の銘柄別 lot_size 拡張など）。
- factor_research モジュールはファイル末尾で未完の箇所がある（truncated / 未完了の関数実装が推測される）。
- プロセス優先度・CPU affinity は権限やプラットフォームによっては実行できない可能性があるため、失敗時は警告を出してスキップする実装になっている。
- モニタリングは監視用 DB に対して常に本番 sqlite_path を使用する設計（KABUSYS_ENV に依存しない）。

今後の提案（推奨改良）
- factor_research の関数実装完了とユニットテスト追加。
- .env パーサーのユニットテスト追加（エスケープ・コメント処理等の網羅）。
- position_sizing の銘柄別 lot_size 対応と価格フォールバックロジックの追加。
- validate_config の YAML 構文チェックを CI に組み込み、自動検出を強化。
- ログや DB パスの権限周りの検証・ remediation をドキュメント化。

--- 

（注）本 CHANGELOG は提示されたソースコードの内容から推測して作成しています。実際のコミット単位の履歴や作者による公式な変更履歴がある場合はそちらを優先してください。