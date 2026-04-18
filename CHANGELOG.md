# Changelog

すべての重要な変更は Keep a Changelog の方針に従って記載しています。  
このファイルはコードベースの内容から推測して作成しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

- なし

## [0.1.0] - 2026-04-18

Added
- 基本機能を初期リリースとして実装・公開
  - 実行スクリプト
    - run_execution.py: ExecutionEngine を起動するエントリポイントを追加（スレッドで実行、停止フラグ対応、paper_trading 用 DB 分離機能）。(src/kabusys/run_execution.py)
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加（MONITOR_POLL_INTERVAL 環境変数対応、停止フラグ対応）。(src/kabusys/run_monitoring.py)
  - 設定・検証・ウィザード
    - config.py: 環境変数読み込み・アクセス用 Settings クラスを実装。.env 自動読み込み、変数検証、paper_trading と live/dev のフラグ判定等を提供。(.env の export 形式やクォート・エスケープ対応のパーサを含む) (src/kabusys/config.py)
    - config_setup.py: 対話式の .env 作成/更新ウィザードを実装（既存値取り込み、シークレットマスク表示、書き出し）。(src/kabusys/config_setup.py)
    - validate_config.py: 起動前の設定検証 CLI を追加（必須環境変数、KABUSYS_ENV、DBパス、config/*.yaml 等の存在/パースチェック、--strict オプション）。(src/kabusys/validate_config.py)
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - portfolio.portfolio_builder: 候補選定（スコア順）、等金額/スコア重み計算を実装。(src/kabusys/portfolio/portfolio_builder.py)
    - portfolio.risk_adjustment: セクター制限（apply_sector_cap）、レジームに応じた資金乗数（calc_regime_multiplier）を実装。(src/kabusys/portfolio/risk_adjustment.py)
    - portfolio.position_sizing: 各種配分メソッド（risk_based / equal / score）に基づく発注株数決定ロジック、lot 単位丸め、aggregate cap スケーリング、cost_buffer を考慮した調整を実装。(src/kabusys/portfolio/position_sizing.py)
    - package エクスポートを提供。(src/kabusys/portfolio/__init__.py)
  - ユーティリティ
    - utils.logging_setup: stdout ストリームハンドラ + 日次ローテート FileHandler をルートロガーに設定する共通ユーティリティ（ログディレクトリ作成失敗時はファイル出力をスキップ）。(src/kabusys/utils/logging_setup.py)
    - utils.process_priority: Windows / POSIX の差分を吸収したプロセス優先度設定（nice/Windows priority）と CPU affinity 設定ユーティリティを実装（権限不足時は警告を出してスキップ）。(src/kabusys/utils/process_priority.py)
  - ツール
    - tools.paper_verification_report: Paper Trading 用 SQLite DB から稼働率・注文成功率・レイテンシ等を集計し検証レポートを出力する CLI を実装。期間指定（--from/--to）や --db オプションに対応、P95 計算、閾値による PASS/FAIL 判定を行う。(src/kabusys/tools/paper_verification_report.py)
  - 研究モジュール（部分実装）
    - research.factor_research: DuckDB を用いたファクター計算モジュール（モメンタム / MA200 / ATR / 流動性等の計算方針を記載、calc_momentum 等の実装を開始）。(src/kabusys/research/factor_research.py)
  - パッケージメタ情報
    - __init__.py にバージョン文字列 __version__ = "0.1.0" を追加。パッケージ公開のための __all__ を設定。 (src/kabusys/__init__.py)

Changed
- 環境変数ロードの挙動を明確化
  - OS 環境変数を保護しつつ .env/.env.local の読み込み順を定義（OS > .env.local > .env）。既存の OS 環境変数は上書きされない。 (src/kabusys/config.py)
- run_monitoring と run_execution における DB 接続方針を明示
  - run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用の SQLite を使用して本番 DB と完全に分離する。 (src/kabusys/run_execution.py)
  - run_monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使用する設計を明示（監視データは本番に集約）。 (src/kabusys/run_monitoring.py)

Fixed
- 環境変数パーサの挙動改善
  - export プレフィックス、シングル/ダブルクォート値、バックスラッシュエスケープ、インラインコメントの扱いをサポートして parsing を堅牢化。(src/kabusys/config.py)
- ロギング設定でログディレクトリ生成に失敗した場合でもプロセスを継続してコンソールログのみで動作するように修正（ファイルハンドラ作成失敗時は警告出力）。(src/kabusys/utils/logging_setup.py)
- run_monitoring の MONITOR_POLL_INTERVAL 無効値処理
  - 環境変数が整数に変換できないか 1 未満の値の場合、警告を出してデフォルト（60 秒）にフォールバックする。(src/kabusys/run_monitoring.py)

Security
- .env の取り扱いについて明確化
  - config_setup によって生成される .env ファイルは決して Git にコミットしない旨を明記。 (src/kabusys/config_setup.py)

Notes / 注意事項
- run_monitoring は設計上、KABUSYS_ENV に関係なく settings.sqlite_path（本番用監視 DB）を使用します。開発/検証環境で監視データを分離したい場合は設定の調整またはソースの改修が必要です。
- process_priority や CPU affinity の設定は OS/権限に依存します。権限不足や実装されていない環境では警告がログに出力され、処理は継続します。
- research.factor_research モジュールは設計方針と一部ロジックを含みますが、実運用向けの完成には追加実装が必要です（calc_momentum の途中実装など）。
- paper_trading モードは MockBrokerClient を用い、データは data/paper_trading.db に保存されます（本番 DB と完全に分離）。

---

この CHANGELOG はコードの現状から推測して作成したものです。実際のリリースノートとして使用する場合は、実際のコミット履歴やリリース日・著者等の情報で適宜補完してください。