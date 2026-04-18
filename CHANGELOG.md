Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

[Unreleased]
------------

（現在のリポジトリ状態から推測された最初の公開リリースを下に記載しています）

[0.1.0] - 2026-04-18
-------------------

Added
- 基本アーキテクチャと主要コンポーネントを追加（初回公開）。
  - 実行エンジン / 実行スクリプト
    - src/kabusys/run_execution.py
    - ExecutionEngine の起動スクリプトを実装。プロセス優先度を "high" に設定し、スレッドでエンジンを起動／監視する。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - 起動時／実行中に data/stop_requested.flag による停止制御を行う。
    - execution.pid を使った PID 管理（設定によりパスを変更可能）。
    - BrokerClientFactory によるブローカークライアント生成を想定（MockBroker 対応）。
    - リスク管理（RiskManager）に初期パラメータを設定、初期ポートフォリオ値をブローカーから取得して使用。
  - 監視（Monitoring）/ 監視スクリプト
    - src/kabusys/run_monitoring.py
    - SystemMonitor を用いたポーリングループを実装。デフォルトポーリング間隔 60 秒、MONITOR_POLL_INTERVAL 環境変数で上書き可能。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用する設計（監視データは本番 DB に格納）。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。
  - 設定管理
    - src/kabusys/config.py: 環境変数／.env 自動ローディング、.env/.env.local の読み込み順序、保護された OS 環境変数の上書き防止などを実装。
    - Settings クラスで主要設定（DB パス、KABUSYS_ENV 判定、ログレベル、paper_trading 用設定など）を提供。
    - .env のパースはクォート、エスケープ、コメントを考慮した堅牢な実装。
  - 設定支援ツール
    - src/kabusys/config_setup.py: 対話式ウィザードで .env を作成／更新する CLI を提供。秘密項目はマスク表示。
    - src/kabusys/validate_config.py: 起動前チェック用 CLI。必須環境変数、DB パス、config/*.yaml の存在・パース確認、KABUSYS_ENV による追加ガードなどを行う。--strict オプションで警告を FAIL 扱いにできる。
  - ロギング／プロセス制御ユーティリティ
    - src/kabusys/utils/logging_setup.py: ルートロガー設定ユーティリティ。stdout への StreamHandler と 日次ローテーションのファイルハンドラ（TimedRotatingFileHandler、30 日分保持）をセットアップ。ログディレクトリ作成失敗時はファイル出力をフォールバックしてコンソール出力のみで継続。
    - src/kabusys/utils/process_priority.py: psutil を用いたプロセス優先度設定（Windows/Linux/macOS 対応）と CPU affinity 設定ユーティリティ。権限不足などを考慮して失敗時は警告出力してスキップ。
  - ポートフォリオ構成（純粋関数群）
    - src/kabusys/portfolio/portfolio_builder.py: 候補選定、等分配・スコア加重の重み計算。
    - src/kabusys/portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、市場レジームに基づく乗数（calc_regime_multiplier）。
    - src/kabusys/portfolio/position_sizing.py: 発注株数決定（risk_based / equal / score）、単元株（lot_size）での丸め、利用可能現金に応じたスケーリング（aggregate cap）、コストバッファの考慮。
    - これらはメモリ内の純粋関数として設計され、DB 参照を行わない。
  - Paper Trading 検証ツール
    - src/kabusys/tools/paper_verification_report.py: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）からデータを集計してレポートを標準出力に生成。稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを評価し PASS/FAIL を判定する。
    - P95 計算、閾値（稼働率 99% など）を定義。
  - 研究用ファクター計算スケルトン
    - src/kabusys/research/factor_research.py: DuckDB 接続を受け取り prices_daily / raw_financials を用いてモメンタム等のファクターを計算するための骨組みを追加（関数群と定数定義を含む）。（実装途中の箇所あり）
  - パッケージ情報
    - src/kabusys/__init__.py: バージョン 0.1.0 を定義。

Changed
- （初回リリースのため過去の変更は無し。将来的にバージョン間差分をここに記載します）

Fixed
- .env 読み込み処理での例外ハンドリングと保護（ファイルオープン失敗時に警告を出す）を実装し、信頼性を向上。

Security
- .env 作成ウィザードのヘッダに「.env は絶対に Git にコミットしないこと」という注意を明記。
- validate_config により本番環境（KABUSYS_ENV=live）での未設定な通知先（LINE）や危険な設定（KILL_FLAG_CLEAR_ON_START=1）に対する警告を出すようにして、運用上のヒューマンエラー検出を支援。

Other notes / Known limitations
- monitoring（run_monitoring）は意図的に常に本番用 sqlite_path を使用する実装になっている（KABUSYS_ENV に依存しない）。運用に応じて変更する必要がある場合は設計を見直してください。
- research/factor_research.py はモメンタム等の計算ロジックの骨組みを含むが、ソース末尾が途中で切れている（実装継続が必要）。
- process_priority と CPU affinity は権限不足や未対応プラットフォームで失敗する可能性があり、その場合は警告でスキップする設計。
- position_sizing の価格欠損（price が 0.0 や None）の扱いに関する TODO コメントあり：将来的にフォールバック価格（前日終値等）の利用を検討すること。

Authors
- KabuSys 開発チーム（コード内の構成とコメントから推測して作成）

References
- 各モジュール内の docstring とコメントに従って実装と挙動を推測して作成しました。実際の変更履歴管理はコミット履歴（git log）に基づく運用を推奨します。