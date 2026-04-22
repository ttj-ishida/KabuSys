CHANGELOG
=========

このファイルは「Keep a Changelog」形式に準拠しています。
※コードベースから推測して作成しています（自動生成や差分ではありません）。

Unreleased
----------
- なし

0.1.0 - 2026-04-22
------------------

Added
- プロジェクト初版リリース。以下の主要コンポーネントを追加。
  - 起動スクリプト / 実行エントリ
    - run_execution.py：ExecutionEngine 起動スクリプト（スレッド実行、停止フラグ対応、paper_trading 用 DB 分離、pid ファイル管理）
    - run_monitoring.py：SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 環境変数で間隔指定）
  - 設定関連 CLI / ユーティリティ
    - config_setup.py：.env を対話式に作成・更新するウィザード
    - validate_config.py：.env および config/*.yaml の起動前検証ツール（--strict オプション対応）
    - config.py：環境変数読み込み・解析ロジック（.env/.env.local の自動ロード、複雑なクォート／コメント処理、設定プロパティ群）
  - ポートフォリオ構築
    - portfolio.portfolio_builder：候補選定（スコアソート）、等金額／スコア加重ウェイト計算
    - portfolio.position_sizing：複数配分方式（risk_based / equal / score）の株数決定、lot_size 単位丸め、aggregate cap によるスケーリング、cost_buffer 対応
    - portfolio.risk_adjustment：セクター上限適用（既存保有を考慮）、レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear）
  - モニタリング・実行用 DB 周り
    - monitoring_db 初期化呼び出しを起動時に行うことで監視テーブルの存在を保証（冪等）
    - DuckDB / SQLite の両対応（DuckDB を分析に使用）
  - ツール
    - tools.paper_verification_report：Paper Trading 検証レポート生成（稼働率、注文成功率、送信率、P95 レイテンシ等に基づく PASS/FAIL 判定）
  - ユーティリティ
    - utils.logging_setup：StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を用いた統一ログ設定、ログディレクトリ作成の耐障害性を考慮
    - utils.process_priority：プラットフォーム差分吸収（Windows・POSIX）によるプロセス優先度設定／CPU affinity（set_cpu_affinity）ユーティリティ（アクセス権限不足時は警告でスキップ）

Changed / Design decisions (ドキュメント化している挙動)
- run_monitoring は KABUSYS_ENV に依らず「本番用の sqlite_path（Settings.sqlite_path）」を参照する設計になっている点を明記。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と完全分離する設計。
- .env ローダーは以下をサポート／挙動定義：
  - export KEY=val フォーマット対応
  - シングル／ダブルクォートでの値とバックスラッシュエスケープ処理
  - クォートなし値における inline コメント扱い（# の直前がスペース／タブの場合）
  - 自動ロード順: OS 環境 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）
- Settings では env/log_level 等の妥当性チェックを行い、無効値は ValueError で通知する。

Fixed / Robustness improvements
- ログ設定時にログディレクトリ作成に失敗した場合でもコンソール出力（stdout）のみで継続するフォールバック実装を追加。
- process_priority・set_cpu_affinity はアクセス権限や未サポート環境で例外にならないよう警告でスキップする実装。
- ExecutionEngine 起動の際に停止フラグ存在時は起動をスキップする安全処理を追加。
- position_sizing の aggregate cap 適用で、小数スケールの残差処理を行い残りキャッシュで lot 単位を追加配分するロジックを導入（資金配分の再現性保持のためソート順を安定化）。

Security
- .env ファイル生成時に注意喚起（.env を Git にコミットしない）を README 相当のコメントとして config_setup の出力に含めている。

Notes / 未実装・将来の改善メモ（コード内コメントより推測）
- portfolio.position_sizing: 将来的には銘柄ごとの lot_size を stocks マスタで扱う拡張を想定している（現在は全銘柄共通で指定）。
- portfolio.risk_adjustment.apply_sector_cap: price が欠損（0.0）だとエクスポージャー過少見積りの懸念があるため、前日終値等のフォールバック価格導入を検討する旨の TODO コメントあり。
- research.factor_research モジュールはファクター計算の設計があり、DuckDB の prices_daily / raw_financials を用いる想定（コード断片あり）。

互換性 / 既知の挙動
- KABUSYS_ENV の既定値は "development"。不正値は起動時にエラーになるため注意。
- PAPER_FILL_MODE 等一部環境変数は厳密な有効値チェックを行う（無効値で例外を投げる）。
- run_monitoring のポーリング間隔は MONITOR_POLL_INTERVAL 環境変数（秒）で上書き可能。0 以下や非整数はデフォルト（60 秒）にフォールバックして警告を出す。

Acknowledgements
- 本 CHANGELOG はソースコードの内容から推測して記載しています。運用ポリシーやリリース履歴と若干の差異がある可能性があります。必要であれば差分やコミット履歴に基づく正確な CHANGELOG を生成します。