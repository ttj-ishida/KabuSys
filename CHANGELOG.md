# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従って記載しています。

注: 以下は提供されたコードベースの内容から推測してまとめた変更履歴です。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-22
初回リリース。日本株自動売買システム「KabuSys」の基本機能群を実装しました。主な追加点・改善点は以下の通りです。

### Added
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV=paper_trading の場合は専用 MockBroker を使用し、paper_trading 用 SQLite（data/paper_trading.db）に記録する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイルによる終了制御を実装。
- 設定管理
  - config.py: 環境変数/.env ファイル読み込みと Settings クラスを実装。プロジェクトルート自動探索、.env/.env.local の読み込み順、環境値の検証（KABUSYS_ENV、LOG_LEVEL 等）を提供。
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新可能にする CLI。
  - validate_config.py: .env と config/*.yaml の事前検証用 CLI（--strict モード対応）。
- ログ・プロセスユーティリティ
  - utils/logging_setup.py: 標準出力（stdout）への StreamHandler と日次ローテーションするファイルハンドラをルートロガーに統一的に設定するユーティリティ。古いハンドラのクリーンアップやログディレクトリ作成のフェールセーフを実装。
  - utils/process_priority.py: Windows / POSIX の差分を吸収したプロセス優先度設定（set_process_priority）および CPU affinity 設定ユーティリティ。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選択 (select_candidates)、等分配 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。スコア全てが 0 の場合のフォールバック有り。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を実装。
  - portfolio/position_sizing.py: 発注株数算出ロジック（risk_based / equal / score）・単元株丸め・aggregate cap によるスケーリングを実装。
- Paper Trading ツール
  - tools/paper_verification_report.py: Paper Trading DB を解析して稼働率、注文成功率、送信率、レイテンシ（P95 など）を報告するレポートジェネレータ。閾値（稼働率 99%、成功率等）による PASS/FAIL 判定を提供。
- リサーチ
  - research/factor_research.py: ファクター計算モジュールの骨子（Momentum 等の計算ロジック）を実装（prices_daily / raw_financials を参照する設計）。

### Changed / Improved
- .env 読み込みロジックの強化
  - export プレフィックス対応、クォートとエスケープの取り扱い、インラインコメントルールを実装。OS 環境変数を保護する protected 機能（.env.local の上書き制御）を導入。
  - 自動ロード順: OS 環境変数 > .env.local > .env（自動ロードを KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- Settings の改善
  - paper_trading 環境向けに paper_sqlite_path / paper_fill_mode（入力検証あり）などを追加。監視閾値（cpu/memory/disk）や PID / kill flag 関連設定をプロパティ化。
  - KABUSYS_ENV や LOG_LEVEL の妥当性チェックを強化。
- 起動時の振る舞い
  - run_execution: paper_trading 環境では専用 DB を使用し、本番 DB と分離。エンジンは別スレッドで実行し、停止フラグの検出で安全に停止するループを実装。起動前に監視テーブルの初期化（init_monitoring_db）を行う。
  - run_monitoring: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明記（運用上の設計意図）。
  - 両スクリプトとも起動直後に set_process_priority("high") を呼び、優先度を上げる処理を追加。
- ロギング
  - logging_setup: コンソール出力は stdout を使用（cron 等でのリダイレクト対応）。既存ハンドラを安全に削除して二重出力を防止。ファイルハンドラ作成失敗時のフォールバックを明確化。
- position_sizing の改善
  - aggregate cap 適用時に cost_buffer（手数料・スリッページ見積り）を考慮した保守的見積り、スケールダウン後の lot_size 単位での再配分ロジックを追加。
- calc_score_weights:
  - 全スコアが 0 の場合に等金額配分へフォールバックし、警告ログを出すよう改善。
- Paper Verification レポート
  - P95 計算、各種クエリ（system_status / trade_logs / risk_logs）からの指標算出、期間フィルタ（ISO8601 UTC 形式）をサポート。DB 不在やテーブル欠如時の耐障害性を確保（OperationalError をキャッチしてデフォルト値を使用）。

### Fixed
- run_monitoring: MONITOR_POLL_INTERVAL の不正（0 や負値、非整数）に対してデフォルトへフォールバックし、警告ログを出すバリデーションを追加（time.sleep に渡す際の ValueError 回避）。
- logging_setup: ログディレクトリ作成に失敗した場合に明示的な警告を出し、ファイルハンドラへの落ち込みを防止。
- process_priority: 未対応 OS や権限不足時に例外で落ちないようハンドリングを追加。Windows / POSIX の差分を吸収。

### Security
- config_setup の .env 生成テンプレートに「.env を絶対に Git にコミットしないこと」を明記。ウィザードではシークレット項目をマスクして表示。
- Settings._require により必須環境変数未設定時に早期エラーを発生させることで不正な起動を防止。

### Documentation / UX
- 各スクリプトとモジュールに日本語のドキュメンテーション文字列（docstring）を追加して使い方や設計方針を明確化。
- validate_config: YAML がインストールされていない環境でも動作するようパースチェックをオプショナルにし、存在しない config ファイルに対しては警告メッセージを出す。

### Internal / Misc
- パッケージバージョンを __version__ = "0.1.0" に設定。
- モジュール間の DB 初期化（init_monitoring_db）呼び出しを冗長回避ではなく安全に呼ぶ（冪等）設計に統一。

---

今後の予定（想定）
- research/factor_research の続き実装（各ファクターの詳細実装・テスト）。
- ExecutionEngine / Monitoring の統合テストおよびより細かいメトリクスの収集。
- 銘柄単位の lot_size 対応や取引コストモデルの明確化。

もし特定ファイルや機能ごとに詳細な変更点（差分ベース）をより厳密に出したい場合は、その旨を教えてください。提供されたコードを基に追加で深掘りして記載します。