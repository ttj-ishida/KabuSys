# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

現在の日付: 2026-04-19

## [Unreleased]

### Added
- 監視ループの起動スクリプトを追加（src/kabusys/run_monitoring.py）。
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
  - 停止フラグファイル（data/stop_requested.flag）でループを安全に終了。
  - SQLite（監視 DB）および DuckDB に接続して SystemMonitor を1周期ずつ実行。
  - プロセス優先度を起動直後に設定（高優先度）。

- 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
  - `KABUSYS_ENV=paper_trading` 時は paper trading 用 DB（data/paper_trading.db）を使用し、本番 DB と分離。
  - BrokerClientFactory によるブローカークライアント切替。ExecutionEngine を別スレッドで起動・監視。
  - 停止フラグ（data/stop_requested.flag）で実行エンジンを停止可能。PID ファイルの取り扱い。

- 環境設定管理モジュールを追加（src/kabusys/config.py）。
  - プロジェクトルート自動検出（.git または pyproject.toml）に基づいて .env を自動読み込み（.env / .env.local）。
  - .env パーサは export プレフィックス、引用符、エスケープ、インラインコメント等に対応。
  - 各種設定プロパティ（DB パス、API トークン、閾値、環境判定など）を型付きプロパティで提供。
  - env 値の検証（有効な KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。

- 設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
  - 対話式に .env を生成・更新するウィザード。既存値の再利用、シークレットのマスク表示などを実装。
  - 書き込みテンプレートとヘルプ文を含む .env ファイル生成ロジック。

- 設定検証 CLI を追加（src/kabusys/validate_config.py）。
  - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリチェック、config/*.yaml の存在・パースチェック（PyYAML がない場合は警告）。
  - 本番環境時の追加ガードチェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性等）。
  - --strict オプションで警告を失敗扱いにできる。

- Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
  - paper_trading DB から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し、PASS/FAIL を判定する。
  - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を導入。
  - 日付フィルタ、DB パス指定オプションをサポート。DB が無ければ分かりやすいエラーを出力。

- ポートフォリオ構築関連の純粋関数群を追加（src/kabusys/portfolio/*）。
  - portfolio_builder: シグナル選定（score 降順・タイブレーク）と重み計算（等金額 / スコア加重）。
  - risk_adjustment: セクターキャップ適用ロジック（既存ポジション時価ベース）とレジーム乗数（bull/neutral/bear）。
  - position_sizing: 発注株数計算（risk_based / equal / score）、単元株丸め、aggregate cap によるスケールダウンと残余配分処理。

- ロギングとプロセス制御ユーティリティを追加（src/kabusys/utils/*）。
  - logging_setup: StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション）をルートロガーに設定。ログディレクトリ自動作成／失敗時のフォールバック対応。
  - process_priority: Windows / POSIX を吸収したプロセス優先度設定（high/normal/low）、CPU affinity 設定機能。権限不足時は警告を出してスキップ。

- research 用モジュール（factor_research）の骨格を追加（src/kabusys/research/factor_research.py）。
  - ファクター計算の設計（モメンタム / Value / Volatility / Liquidity）とモメンタム計算関数の実装開始（関数定義・定数等）。DuckDB 接続を想定。

### Changed
- SQLite / DuckDB を組み合わせた運用設計。
  - 監視（monitoring）は環境にかかわらず本番 sqlite_path を使用する設計に明示。
  - Execution は paper_trading 環境時に専用 SQLite を使用して本番データと完全分離。

### Fixed
- 監視ポーリング間隔の不正設定に対してデフォルトにフォールバックする挙動を追加（無効な MONITOR_POLL_INTERVAL を警告し 60 秒を使用）。
- 各種ファイル操作や設定読み込みで発生し得るエラーを捕捉し、警告や情報として出力するように改善（ログファイルディレクトリ作成失敗時のフォールバック、psutil による優先度設定の権限エラーハンドリングなど）。
- Paper Trading レポートでデータ不足やテーブル欠如の際にプログラムがクラッシュしないよう保護。

---

## [0.1.0] - 2026-04-19

最初の公開バージョン。以下の主要機能を搭載。

### Added
- 基本パッケージ構成とバージョン情報（src/kabusys/__init__.py, __version__ = "0.1.0"）。
- 実行および監視の起動エントリ（run_execution, run_monitoring）。
- 環境設定管理（.env 読み書き/パース）と設定ウィザード（config_setup）。
- 設定検証ツール（validate_config）。
- ロギング設定ユーティリティ（logging_setup）。
- プロセス優先度・CPU affinity ヘルパー（process_priority）。
- ポートフォリオ構築・リスク調整・ポジションサイズ決定の純粋関数群（portfolio モジュール）。
- Paper Trading 検証レポート生成ツール（tools/paper_verification_report）。
- DuckDB を利用した研究（research/factor_research）の基盤コード。
- 監視 DB 初期化ユーティリティ呼び出しの統合（monitoring_db によるテーブル作成を前提）。

### Changed
- (初期リリース) プロジェクトルートの自動検出と .env 自動ロードの方針を採用（テスト用に自動ロードを無効化可能）。

### Notes
- .env ファイルは絶対にリポジトリにコミットしないこと（config_setup の生成ヘッダに注意喚起あり）。
- 一部の機能（factor_research の詳細実装、銘柄マスタに基づく lot_size の柔軟化など）は今後の拡張予定。

---

（注）上記はコードベースの内容から推測して作成した変更履歴です。実際のリリース日やバージョン運用方針はプロジェクトのリリース管理に従って調整してください。