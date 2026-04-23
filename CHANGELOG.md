# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

- ルール: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

- （現在未リリースの変更はここに記載）

## [0.1.0] - 2026-04-23

初回公開リリース。本リポジトリに含まれる主要機能・ユーティリティを実装しました。

### Added
- 実行エントリ / デーモン起動スクリプト
  - run_execution.py: ExecutionEngine を起動するランナー。KABUSYS_ENV=paper_trading 時にペーパートレード用 MockBroker を利用し、paper_trading 用 SQLite DB を分離して使用する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。停止は data/stop_requested.flag ファイルで制御。

- 設定・環境管理
  - config.py: .env 自動読み込み機能（.env → .env.local、OS 環境変数の保護）、厳密な .env パース（export 句、クォート・エスケープ、コメントの扱い）および Settings クラス（J-Quants、kabu API、DB パス、Paper Trading 設定、監視しきい値 等）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化に対応。
  - config_setup.py: 対話式ウィザードで .env を生成/更新する CLI。必須項目・デフォルト値・シークレットマスク表示などを提供。
  - validate_config.py: 起動前チェック用 CLI。.env と config/*.yaml（存在する場合）の整合性チェック、必須環境変数や本番運用時の注意喚起を行う。--strict オプションで警告を失敗扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: ルートロガーの統一設定。コンソール（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続する。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でプロセス優先度（high/normal/low）と CPU affinity 設定を行うユーティリティ。アクセス権限や未サポート環境では安全にフォールバックし、警告を出力してスキップする。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: シグナルの候補選定（スコア降順・タイブレーク）と等重・スコア重み計算。
  - portfolio/risk_adjustment.py: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - portfolio/position_sizing.py: 発注株数算出ロジック（allocation_method: risk_based / equal / score）、単元株丸め、per-stock 上限・aggregate cap、コストバッファを用いた保守的見積りとスケールダウンロジック。

- 監視・検証ツール
  - monitoring 初期化呼び出し（init_monitoring_db）を各起動スクリプトから実行して監視テーブルの存在を保証。
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成ツール。稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計して PASS/FAIL 判定を出力。P95 計算や日付フィルタ（期間指定）をサポート。PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで DB 指定可能。

- リサーチ（ファクター）基盤
  - research/factor_research.py（部分実装）: DuckDB を用いたファクター計算基盤（Momentum / Value / Volatility / Liquidity）を想定した設計。prices_daily / raw_financials テーブルを用いて日付・銘柄ベースのファクターを返すことを目的とする（モジュール化、ドキュメント記述を含む）。

- パッケージメタ
  - __init__.py にてパッケージバージョン __version__ = "0.1.0" を設定。

### Changed
- DB・環境分離
  - 実行（execution）コンポーネントは本番 DB とペーパートレード用 DB を分離（settings.is_paper を使用）。これにより paper_trading 時は data/paper_trading.db が利用され、本番データと完全に分離される設計を採用。
- ログ挙動の一貫化
  - すべての起動スクリプトから setup_logging() を呼び出す想定により、ログの出力形式・ローテーションが統一。

### Fixed
- 環境変数パースの堅牢化
  - .env パースにおいて、export プレフィックスやクォート内のバックスラッシュエスケープ、インラインコメントの取り扱いを正しく処理するよう改善。空行・コメント行は無視する。
- プロセス優先度設定の失敗耐性
  - 権限不足や未サポート環境で例外を暴露せず警告ログに留める実装に改善。

### Documentation
- 各モジュールに日本語ドキュメント文字列（docstring）を充実させ、設計方針・引数・戻り値・注意事項を明記。

### Notes / Implementation details
- 停止制御はファイルベース（data/stop_requested.flag, data/kill.flag）で行う設計。実運用では外部プロセスや運用手順でこれらのファイルを操作することでプロセス制御が可能。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値に対し警告を出してデフォルトにフォールバックする挙動をとる（time.sleep に負の値が渡らないようにするため）。
- position_sizing の aggregate cap 処理では lot_size 単位で丸め、スケールダウン後の残余キャッシュを使って fractional 残差の大きい順に追加配分するロジックを実装。価格欠損時には警告・スキップする。
- calc_regime_multiplier は未知レジームに対してデフォルトで 1.0 を返し警告ログを出力する。

---

著者注: 本 CHANGELOG は提示されたコードベースの実装・注釈から推測して作成しています。実際のリリース履歴や変更履歴が既に存在する場合は、公式の履歴に合わせて調整してください。