CHANGELOG
=========

すべての重要な変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

注: 以下の変更点はコードベースの内容から推測して記載したものであり、実際のコミット履歴ではありません。

Unreleased
----------

- なし

0.1.0 - 2026-04-19
------------------

Added
- プロジェクト初版リリース。
- 起動スクリプトを追加:
  - run_execution.py — ExecutionEngine の起動スクリプト。KABUSYS_ENV=paper_trading の場合は専用の Paper Trading DB（デフォルト: data/paper_trading.db）と MockBrokerClient を使用して本番 DB と分離する。
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag により制御。
- 環境設定関連 CLI を追加:
  - config_setup.py — 対話式 .env 作成/更新ウィザード（シークレット入力のマスク、既存値の取り込み、.env ファイルへの書き込み）。
  - validate_config.py — .env と config/*.yaml の静的検証ツール（--strict オプションで警告を失敗扱いにできる）。
- 設定管理モジュールを追加:
  - config.py — 環境変数の読み込み（.env/.env.local 自動読み込み、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）、型/値検証、Settings クラスによるプロパティアクセス。PAPER_FILL_MODE 等の妥当性チェックを含む。
- ロギング & プロセス運用ユーティリティを追加:
  - utils/logging_setup.py — ルートロガー設定（stdout StreamHandler と 日次ローテートの TimedRotatingFileHandler、デフォルト logs/ ディレクトリ、30 日保持）。
  - utils/process_priority.py — Windows / POSIX を吸収するプロセス優先度設定（high/normal/low）および CPU affinity 設定。
- ポートフォリオ構築関連の純粋関数群を追加（DB非依存）:
  - portfolio/portfolio_builder.py — シグナル選定（select_candidates）、等金額/スコア加重の重み計算（calc_equal_weights, calc_score_weights）。
  - portfolio/risk_adjustment.py — セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。未知レジームはフォールバック（警告）。
  - portfolio/position_sizing.py — 発注株数計算（risk_based / equal / score）、単元株丸め、aggregate cap のスケーリングロジック、cost_buffer による保守的見積り。
- リサーチ用モジュール（骨格）を追加:
  - research/factor_research.py — DuckDB 接続を受けるファクター計算モジュールの実装開始（モメンタム等の定数とインターフェースを定義）。
- Paper Trading 検証レポート生成スクリプトを追加:
  - tools/paper_verification_report.py — paper_trading DB から稼働率・注文成功率・送信率・レイテンシ等を集計してレポート出力。閾値に基づく PASS/FAIL 判定を実装（デフォルト閾値: 稼働率 99.0%、成立率 90.0%、送信率 95.0%、P95 レイテンシ 200 ms）。
- パッケージメタ:
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を追加。

Changed
- （初版のため過去バージョンからの変更はなし）

Fixed
- （初版のため過去バージョンからの修正はなし）

Security
- 環境変数取り扱い:
  - config_setup の .env 書き出しテンプレートでは .env を絶対にコミットしない旨を明記。
  - config.py の _require() により必須環境変数未設定時は明示的にエラーを出すことで、誤動作による誤発注リスクを低減。

Notes / Implementation details
- DB / ファイル:
  - DuckDB は分析用（デフォルト: data/kabusys.duckdb）、SQLite は監視・発注履歴用（デフォルト: data/monitoring.db）。paper_trading 時は PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
  - run_execution は起動前に data/stop_requested.flag をチェックし、フラグが立っている場合は起動せず終了する。実行中もフラグで停止を受け付ける。run_monitoring も同様に停止フラグを監視する。
- ログ:
  - setup_logging は既存ハンドラをクリアしてから設定を行うため、複数回呼んでも二重出力を防止する。
  - コンソール出力は stdout を使用（cron 等からのリダイレクト運用を想定）。
- 環境変数パーサ:
  - config._parse_env_line は export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い等を高精度で処理する実装になっている。
- Fail-safe / フォールバック:
  - run_monitoring は MONITOR_POLL_INTERVAL が不正（0 以下や非数）な場合にデフォルト 60 秒へフォールバックし警告を出す。
  - portfolio の calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックし警告を出す。
  - process_priority / set_cpu_affinity は権限不足や未サポート環境では警告を出してスキップする。

今後の改善案（示唆）
- position_sizing の価格フォールバック（価格欠損時の前日終値等）。
- 銘柄ごとの lot_size をサポートするための拡張（stocks マスタ参照）。
- research モジュールの完全実装（ファクター計算ロジックの SQL 実装完了）。
- モニタリング/実行のユニットテスト整備と e2e テストスイート追加。

--- 

更新履歴に記載漏れや誤りがあれば指摘してください。必要に応じて日付や項目を調整します。