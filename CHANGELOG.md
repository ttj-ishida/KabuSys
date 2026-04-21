CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （現在のブランチ / 開発中の変更があればここに記載）

[0.1.0] - 2026-04-21
-------------------

Added
- 初回公開リリース。
- 実行エントリスクリプト:
  - run_execution.py — ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV による paper_trading モード検出、専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用する分離設計、エンジンのデーモンスレッド起動・停止フロー、実行用 PID ファイル管理、停止フラグ（data/stop_requested.flag）による外部停止をサポート。
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能、監視用 DB 初期化、停止フラグ検出、例外安全なループ実行を実装。
- 設定関連:
  - config.py — 環境変数読み込み・設定管理を実装。自動 .env ロード（プロジェクトルート検出: .git / pyproject.toml 基準）、.env と .env.local の読み込み順序と上書きルール、値検証ユーティリティ（必須 env のチェック、PAPER_FILL_MODE の妥当性チェック、KABUSYS_ENV / LOG_LEVEL 等の検証）を提供。Settings クラスでプロパティ経由の安全な取得を可能に。
  - config_setup.py — 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。シークレットマスクやデフォルト、選択肢サポート、保存前確認を実装。.env 作成テンプレートを出力（.env を絶対にコミットしない旨の注意を含む）。
  - validate_config.py — 起動前の設定検証 CLI を追加。必須環境変数、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パスの親ディレクトリ確認、config/*.yaml 存在および YAML パース（PyYAML がない場合はスキップ）を実施。--strict により警告を FAIL 扱いにできる。
- ロギング・ユーティリティ:
  - utils/logging_setup.py — 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。環境変数 LOG_DIR / LOG_LEVEL による設定、ログディレクトリ作成失敗時のフォールバック（コンソールのみ）を考慮。
- プロセス制御ユーティリティ:
  - utils/process_priority.py — Windows / POSIX の差分を吸収してプロセス優先度設定（high/normal/low）を提供。CPU affinity 設定関数も実装。アクセス権限がない場合は警告を出して安全にスキップ。
- ポートフォリオ構築モジュール:
  - portfolio/portfolio_builder.py — シグナル選定（スコア降順、同点タイブレーク）、等金額・スコア加重の重み計算を実装。スコア全ゼロ時は等配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py — セクター集中上限チェック（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。unknown セクター取り扱い、既存保有の売却予定除外、レジーム未知値のフォールバックを明記。
  - portfolio/position_sizing.py — 株数決定ロジックを実装（risk_based / equal / score）。単元株丸め、per-position 上限、aggregate cap によるスケーリング、cost_buffer 考慮、残余キャッシュを用いたロット単位での再配分ロジックを実装。価格欠損時の挙動や将来の拡張（銘柄別 lot_size）に関する TODO 注記あり。
  - portfolio/__init__.py でエクスポートを整理。
- リサーチ・ファクタモジュール（骨組み）:
  - research/factor_research.py — DuckDB 接続を受け取ってモメンタム等のファクタを計算する設計を追加（関数の仕様・定数・ドキュメントを含む）。（注: ファイル末尾での実装途中の箇所あり — モデル計算ロジックは続きが存在することを示唆）
- Paper Trading 検証ツール:
  - tools/paper_verification_report.py — Paper Trading の SQLite ログから検証レポートを生成する CLI を追加。稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL を判定する。閾値はソース内定数で定義（稼働率 99% 等）。P95 計算、日付フィルタ（--from/--to）、DB パス優先順位（--db > 環境変数 > デフォルト）をサポート。
- パッケージ情報:
  - __init__.py に __version__ = "0.1.0" を設定。

Changed
- N/A（初回リリースのため履歴変更なし）

Fixed
- N/A（初回リリースのため bugfix 履歴なし）

Deprecated
- N/A

Removed
- N/A

Security
- N/A

Notes / Important behaviors
- .env 自動ロードはデフォルトで有効。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで無効化可能。
- .env 読み込みは OS 環境変数を保護（読み込み時に既存の OS 環境変数を上書きしない）し、.env.local は .env を上書きする挙動になっている。
- run_monitoring は Monitoring 用 DB 初期化に当たり、KABUSYS_ENV にかかわらず本番 sqlite_path を使用（monitoring は常に本番 DB を参照する設計）。
- run_execution は paper_trading モード時に paper_trading 用 DB を使用して本番 DB と分離する。
- process_priority と logging_setup は権限やファイルシステムの制限を考慮し、失敗した場合は警告を出して処理を継続する（堅牢性重視）。
- position_sizing と risk_adjustment 内に将来的な改善点（例: price フォールバック、銘柄別 lot_size）はコメントで明示済み。

既知の TODO / 制約
- research/factor_research.py にて実装の続き（calc_momentum の本体以降）が存在します。完全なファクタ計算ロジックは今後の実装対象。
- position_sizing の price 欠損時のフォールバック未実装（前日終値など）。コメントにて将来の拡張を示唆。
- config/*.yaml の厳密なスキーマ検証は未実装（PyYAML があれば YAML のパース確認は行うが、スキーマチェックは未対応）。

以上。