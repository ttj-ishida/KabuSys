Keep a Changelog 準拠の CHANGELOG.md（日本語）を以下に作成しました。コードベースの内容から推測して記載しています。

------------------------------------------------------------
Keep a Changelog
All notable changes to this project will be documented in this file.

フォーマット: https://keepachangelog.com/ja/1.0.0/
------------------------------------------------------------

Unreleased
---------
- （現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-19
-------------------
Added
- パッケージ初期リリース
  - バージョン: 0.1.0

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時に MockBrokerClient を使用し、本番 DB と分離した paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用する挙動を実装。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止、PID ファイルの扱い、スレッドでのエンジン実行と監視を実装。
    - 起動時にプロセス優先度を高く設定する処理を追加。

  - run_monitoring.py
    - SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用し、停止フラグ検知でループ終了。
    - DB 初期化（監視テーブルの準備）と DuckDB 接続処理を組み込み。

- 設定管理
  - config.py
    - .env の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
    - .env のパースはクォート、エスケープ、コメント（#）に対応した堅牢な実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化機能を追加。
    - Settings クラスを実装し、環境変数の集中管理・検証を提供（J-Quants / kabu API / DB パス / paper_trading 用設定 / 監視閾値 等）。
    - KABUSYS_ENV と LOG_LEVEL、PAPER_FILL_MODE 等の妥当性チェックを実装。

  - config_setup.py
    - .env 初期作成・更新の対話式ウィザードを実装。
    - 多数の項目定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 設定、LOG_LEVEL、Kill Switch 設定など）を提供。
    - 既存 .env の読み込み・再利用、シークレット値のマスク表示、最終確認・保存機能を実装。

  - validate_config.py
    - 起動前に .env と config/*.yaml の基本的な妥当性をチェックする CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス検査、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードを実装。
    - --strict フラグで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルの選別（select_candidates）と重み計算（等金額 / スコア加重）を実装。
    - スコア全てが 0 の場合は等金額にフォールバックし警告を出す。

  - portfolio/risk_adjustment.py
    - セクター集中制限の適用（apply_sector_cap）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear とフォールバック挙動）。
    - セクターが unknown の扱い・既存ポジションの売却予定除外等の挙動を考慮。

  - portfolio/position_sizing.py
    - 各銘柄の発注株数決定ロジック（allocation_method: risk_based / equal / score）を実装。
    - 単元株（lot_size）による丸め、1 銘柄上限や aggregate cap（利用可能資金を超える場合のスケーリング）、cost_buffer（手数料/スリッページ見積り）を実装。
    - 価格欠損時のスキップやログ出力を考慮。

  - portfolio/__init__.py により主要 API を公開。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的ロギング設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装、ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。

  - utils/process_priority.py
    - プロセス優先度設定（set_process_priority）および CPU affinity 設定（set_cpu_affinity）ユーティリティを追加。
    - Windows と POSIX 系（Linux/Mac/FreeBSD）で差分を吸収する実装。権限不足や未対応 OS の場合は警告を出してスキップ。

- モニタリング DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を利用して監視テーブルの冪等な初期化処理を各起動スクリプトから実行（monitoring と execution 両方で保証）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード検証用レポート生成ツールを追加。
    - CLI で期間フィルタ（--from / --to）や DB パス指定（--db）を受け付け。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定を出力（閾値はソース内定数で設定）。
    - P95 計算、欠損テーブル（OperationalError）時のフォールバック処理を実装。

- リサーチ（骨組み）
  - research/factor_research.py
    - DuckDB を利用したファクター計算モジュールの初期実装（モメンタム、MA200 乖離、ATR、出来高/流動性等を想定）。
    - DuckDB 接続を受け prices_daily / raw_financials を参照する設計。

- パッケージ管理
  - __init__.py にてパッケージ名と __version__ = "0.1.0" を設定。

Changed
- 初回リリースにつき該当なし

Fixed
- 初回リリースにつき該当なし

Removed
- 初回リリースにつき該当なし

Security
- 初回リリースにつき該当なし

Notes / 実装上の注意
- .env 自動ロード機能はプロジェクトルートの検出に依存する（.git または pyproject.toml）。配布後にプロジェクトルートが特定できない場合は自動ロードをスキップする。
- PAPER_TRADING 用 DB は本番 DB と完全分離する設計（paper_trading と live/dev の切り分け）。
- process_priority / cpu_affinity の設定は権限不足やプラットフォーム制約で失敗することがあり、失敗時は警告でスキップする。
- research/factor_research.py は設計方針や定数が含まれているが、データアクセスや詳細な実装は DuckDB スキーマに依存するため、実運用時は prices_daily/raw_financials のスキーマ確認が必要。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力。ログディレクトリ作成に失敗した場合はコンソール出力のみとなる。

------------------------------------------------------------
今後のリリースでは、テストカバレッジ、ドキュメント（API リファレンス・運用手順）、および research モジュールの完成度向上（ファクター計算テスト、DuckDB スキーマ定義）を追加することを推奨します。