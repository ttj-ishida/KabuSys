# CHANGELOG

すべての変更は「Keep a Changelog」形式に従い、重要な変更はセマンティックバージョニングを想定して記載しています。

注: この CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のコミット履歴ではない点にご留意ください。

## [Unreleased]

### Added
- 全体
  - パッケージ初期実装に対するドキュメントコメント・設計注記を多数追加し、各モジュールの責務と入力/出力仕様を明確化。
- 設定管理 (kabusys.config)
  - .env 自動読み込み機能を提供（プロジェクトルート検出 .git / pyproject.toml を使用）。OS環境変数 > .env.local > .env の優先順位で読み込む。
  - .env パーサを強化し、export プレフィックス、クォート、インラインコメント、エスケープシーケンスを正しく扱うように実装。
  - 必須環境変数未設定時に明確なエラーを投げる `_require()` を提供。
  - PAPER_FILL_MODE・KABUSYS_ENV・LOG_LEVEL 等の入力検証と既定値を実装。
  - paper_trading 用 DB パス (PAPER_TRADING_SQLITE_PATH) をサポート。
- 実行関連
  - run_execution: ExecutionEngine 起動スクリプトを追加。実行時にプロセス優先度を設定し、paper_trading 環境では本番 DB と分離した専用 SQLite（data/paper_trading.db）を使用する。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能、停止フラグファイル検知で安全に終了。
- 監視
  - 監視用 DB 初期化ユーティリティおよび SystemMonitor の利用を前提とする起動フローを導入（duckdb と sqlite 両対応）。
- ツール
  - tools/paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95）などの指標を算出し PASS/FAIL 判定を行う。
- ポートフォリオ構築
  - portfolio モジュールを導入（portfolio_builder, position_sizing, risk_adjustment）。
    - 候補選定（select_candidates）、等金額・スコア加重重み計算（calc_equal_weights, calc_score_weights）。
    - セクター集中制限（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）。
    - ポジションサイズ計算（calc_position_sizes）：risk_based / equal / score の割当方法、単元株丸め、aggregat cap によるスケールダウンと端数処理を実装。
- リサーチ
  - research モジュールを追加（factor_research, feature_exploration）。
    - momentum / volatility / value ファクター計算（DuckDB を用いた SQL ベースの実装）。
    - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー、ランク付けユーティリティ等を実装。外部ライブラリに依存せず標準ライブラリ＋duckdb で完結。
- AI ニューススコアリング
  - ai/news_nlp: raw_news を OpenAI API（gpt-4o-mini）でスコアリングして ai_scores に書き込む処理を追加。以下に配慮:
    - タイムウィンドウ（JST→UTC 変換）で記事を集約
    - 銘柄ごとに記事数・文字数上限を設ける（トークン肥大化対策）
    - バッチ送信、429/ネットワーク断/タイムアウト/5xx への指数バックオフリトライ、レスポンスバリデーション、スコアクリップ（±1.0）
    - 部分失敗時に既存スコア保護のためコードを限定して更新
- ユーティリティ
  - utils/process_priority: Windows と POSIX 系で差異を吸収するプロセス優先度設定ユーティリティを提供。CPU affinity 設定関数も追加。権限不足や未対応 OS では安全にスキップして警告ログを出力。
- デフォルトバージョン
  - パッケージの __version__ を "0.1.0" として設定。

### Changed
- DB ハンドリング
  - duckdb と sqlite の併用を前提に起動フローを整理（monitoring 用テーブルは冪等に初期化）。
- ロギング
  - 起動スクリプトで logging.basicConfig(level=logging.INFO) を設定し、起動時に KABUSYS_ENV をログ出力するように変更。
- 安全性・ロバストネス
  - 各所でエラー時に例外をキャッチしてループ継続やフェイルセーフする実装を採用（例: monitoring loop の check_once() 例外捕捉、AI API 呼び出しのリトライ設計）。
- CLI / スクリプト
  - paper_verification_report に日付フィルタ (--from, --to) と DB パス指定オプション (--db) を実装。期間指定は内部で ISO8601 UTC 形式に変換してクエリに適用。
- ポートフォリオ計算
  - calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックして警告ログを出力するように変更。
  - calc_regime_multiplier は未知のレジームで警告を出して 1.0 にフォールバックするように調整。

### Fixed
- .env 読み込み
  - .env の読み込み時にファイルアクセス失敗時に明確な警告を出すよう改善（例外を警告に変換）。
- position_sizing
  - aggregate cap のスケールダウン処理で lot_size 単位の端数配分ロジックを追加し、残余キャッシュを活用して再配分するよう改善。
- process_priority
  - 未サポート OS や権限不足時に発生し得る例外を捕捉して安全にスキップするよう修正。

### Removed
- なし（このリリース相当では破壊的削除は確認できず）。

### Security
- OpenAI API キー未設定時に明確な ValueError を投げ、誤った無加工呼び出しが行われないように保護。

---

## [0.1.0] - 2026-04-17

初期公開リリース (推定)。上記 Unreleased に列挙した主要機能群を含むまとまったリリース相当。

- 主要機能
  - 自動売買実行エンジン（ExecutionEngine の起動スクリプト、ブローカーファクトリ、OrderManager、OrderRepository、RiskManager、Reconciler の組立て）
  - 監視サブシステム（SystemMonitor ポーリング、監視用 SQLite 初期化）
  - Portfolio construction（候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数）
  - Research ライブラリ（ファクター計算、forward returns、IC、統計サマリー）
  - AI ニュースセンチメント（OpenAI を使ったニューススコアリング）
  - ユーティリティ（.env ローダー、プロセス優先度 / CPU affinity）
  - 検証ツール（paper_verification_report）

- 品質改善
  - エラーハンドリングの強化、入力検証、ログ出力の整備。

- 互換性
  - paper_trading モードでは本番 DB と分離された専用 SQLite を使用。環境変数に依存する挙動は Settings クラスで集中管理。

---

その他の備考
- 各モジュールの詳細実装はコードコメントに記載の設計書（PortfolioConstruction.md 等）を参照する想定。
- 実際の変更履歴（コミットログ）に基づく正確な CHANGELOG を作成する場合は、git のコミットメッセージ・タグ付け情報の提供をお願いいたします。