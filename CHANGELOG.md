CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。  
このプロジェクトは Keep a Changelog の慣習に従います。  

フォーマット:
- Unreleased: 未リリースの変更（ここには現在ありません）
- 各バージョン見出しは [バージョン] - 日付（YYYY-MM-DD）

Unreleased
----------

（なし）

[0.1.0] - 2026-04-25
-------------------

Added
- 初回リリースを公開。
- 実行／監視用エントリポイントを追加。
  - run_execution.py: ExecutionEngine の起動スクリプト。プロセス優先度設定、SQLite/DuckDB 接続、Broker クライアント生成、ExecutionEngine のスレッド実行、停止フラグ検知、paper_trading 用 DB 分離などを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ検知でループ終了。
- 環境設定・管理機能を実装。
  - config.py: .env の自動読み込み（プロジェクトルート検出：.git / pyproject.toml）、強力な行パーサ（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント対応）、Settings クラス（各種環境変数ラッパ、バリデーション）を提供。
  - config_setup.py: 対話式ウィザードで .env を初期作成／更新する CLI を追加（既存値の再利用、シークレットマスク、保存テンプレート出力）。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認と YAML のパース検証（PyYAML があれば実行）を実施。--strict オプションで警告も失敗扱いに可能。
- ポートフォリオ構築・リスク調整・ポジションサイズ計算モジュールを追加（純粋関数群）。
  - portfolio/portfolio_builder.py: 候補選定（スコア降順・タイブレーク）と配分重み（等金額・スコア加重）計算。スコア全ゼロ時に等配分へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。sell_codes を考慮したエクスポージャー評価、未知レジームにはフォールバック。
  - portfolio/position_sizing.py: allocation_method（risk_based, equal, score）に基づく株数算出、単元株（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金を超える場合のスケールダウンと端数配分）を実装。cost_buffer を考慮した保守的見積。
  - portfolio/__init__.py で主要関数を公開。
- 解析／リサーチ補助モジュールを追加（骨格）。
  - research/factor_research.py: DuckDB を使ったモメンタム等のファクター計算ユーティリティの実装（モメンタム計算等の方針と定数を含む。実装途中の箇所あり）。
- ツールを追加。
  - tools/paper_verification_report.py: Paper Trading 用 SQLite DB から稼働率・注文成功率・送信率・レイテンシ等を集計してレポート出力する CLI を追加。P95 計算、期間フィルタ --from/--to、閾値による PASS/FAIL 判定を実装。
- 監視 DB 初期化ユーティリティ呼び出しを統一。
  - init_monitoring_db を起動時に呼ぶことで monitoring テーブルの存在を保証（冪等）。
- ロギング／プロセスユーティリティを追加／改善。
  - utils/logging_setup.py: ルートロガーに StreamHandler(stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。ログディレクトリ作成失敗時のフォールバックや既存ハンドラのクリーンアップ処理を実装。
  - utils/process_priority.py: psutil を用いたクロスプラットフォームのプロセス優先度設定（Windows と POSIX の差分を吸収）。CPU affinity 設定ユーティリティも提供。権限不足等は警告でスキップ。
- バージョン情報を追加。
  - __init__.py に __version__ = "0.1.0" を設定。

Changed
- なし（初回リリース）。

Fixed
- なし（初回リリース）。ただし実装では堅牢性向上のために各所で例外ハンドリングや finally での接続クローズ処理を導入。

Notes / Implementation details
- run_monitoring は KABUSYS_ENV にかかわらず「本番」用 sqlite_path（Settings.sqlite_path）を使う設計になっている点に注意。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使い、本番 DB と完全に分離している。BrokerClientFactory により MockBroker を利用する想定。
- .env パーサは export 形式やクォート内のバックスラッシュエスケープ、インラインコメントの取り扱いに対応。プロジェクトルートが見つからない場合は自動ロードをスキップ。
- position_sizing の一部（価格欠損時のフォールバック等）や factor_research の詳細実装には TODO/未完成箇所があり、将来的な拡張が想定されている。
- paper_verification_report の閾値や判定基準（稼働率99% 等）は定数化されているため、将来調整可能。

Known issues
- research/factor_research.py は一部実装が途中（ファイル末尾で切れている）ため、完全なファクター計算を行う用途では注意が必要。
- 一部の機能（ブローカークライアントの具象実装、ExecutionEngine の内部等）はこの差分からは参照されるが、本 changelog 作成時点のコードリストに全実装が含まれていない可能性があるため、統合テストでの確認を推奨。

Acknowledgements
- 初回公開に含まれる多くのユーティリティは運用・監視・検証ワークフローを想定して設計されています。今後の改善（テスト追加、エラーハンドリング強化、パフォーマンスチューニング等）を予定しています。