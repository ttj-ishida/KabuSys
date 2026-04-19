CHANGELOG
=========

本ファイルは Keep a Changelog の形式に準拠しています。  
主な追加・変更点はコードベースから推測して記載しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-19
-------------------

Added
- 初期リリース: KabuSys 自動売買システムのコア機能群を追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB と分離して実行可能。
  - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag により制御。
- 設定関連
  - config.py: 環境変数および .env を読み込む Settings クラスを実装。自動 .env ロード（.env, .env.local）や必須環境変数チェック用のヘルパを提供。PAPER_FILL_MODE 等のバリデーションを実装。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加（CLI）。
  - validate_config.py: .env と config/*.yaml を起動前に検証する CLI を追加。--strict オプションで警告を FAIL 扱いにできる。
- ロギング・プロセス制御
  - utils/logging_setup.py: stdout 出力用 StreamHandler と日次ローテーションのファイルハンドラをルートロガーに設定するユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップするフェールセーフを実装。
  - utils/process_priority.py: Windows/Linux/macOS を吸収するプロセス優先度（nice / priority_class）および CPU affinity 設定ユーティリティを追加。権限不足などを安全にハンドリング。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）・等金額・スコア加重の重み計算（calc_equal_weights, calc_score_weights）を追加。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を追加。
  - portfolio/position_sizing.py: 発注株数算出ロジックを追加（risk_based, equal, score の各方式をサポート）。単元株（lot_size）丸め、ポジション上限、aggregate cap によるスケーリング、手数料/スリッページのバッファ考慮などを実装。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し PASS/FAIL を判定する。閾値はソース内定数で調整可能。
- データ / 研究
  - research/factor_research.py: ファクター計算モジュールの骨子を追加（モメンタム・MA200乖離・ATR 等の計算を想定）。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
- パッケージ情報
  - __init__.py: パッケージバージョン __version__ = "0.1.0" を追加。

Changed
- 監視/起動の振る舞い
  - run_monitoring: 監視は KABUSYS_ENV にかかわらず監視用 sqlite_path（デフォルト data/monitoring.db）を使用するよう明示。
  - run_execution: 起動時に既に停止フラグが立っている場合は起動を中止する安全措置を追加。バックグラウンドスレッドで engine.run_session を実行し、停止フラグで engine.stop() を呼び出して安全に終了させる。
- DB 初期化
  - init_monitoring_db を起動フローに組み込み、監視テーブル存在を冪等に保証（monitoring 用テーブル確認・作成）。

Fixed
- .env パーサの堅牢化（config._parse_env_line）
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱いなどに対応。無効行のスキップ処理を実装。
- ロギング設定の二重登録回避
  - setup_logging は既存ハンドラを flush/close してから削除し、再設定することでハンドラの二重登録を防止。
- 環境変数の上書き制御
  - _load_env_file で override / protected オプションを用意し、OS 環境変数を保護しつつ .env.local からの上書きなどを制御可能に。
- プロセス優先度・CPU affinity
  - クロスプラットフォームでの実行を考慮し、未対応 OS の場合は警告を出してスキップする安全な実装に。権限不足等の例外をキャッチしてログ出力。

Security
- 機密トークンの取り扱い
  - config_setup のウィザード/保存実装で JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD をシークレットとし、表示時にマスクする（ファイル自体は .env として保存されるため Git 応答は README 等で注意喚起）。

Notes / その他
- Paper Trading 分離: paper_trading モードでは本番用 SQLite を汚染しないよう専用 DB を用いる設計になっており、本番/ペーパートレードの完全分離を意図。
- モジュール設計:
  - 多くのアルゴリズム（ポートフォリオ構築、リスク調整、ポジションサイズ決定、ファクター計算）は純粋関数として実装され、DB 参照箇所を明確に分離しているためユニットテストが容易。
- 未完成/TODO:
  - research/factor_research.py はモメンタム計算実装の続きを想定（ファイル末尾が途中で終了）。将来的に DuckDB SQL と Python ロジックで詳細実装が続く想定。
  - position_sizing: 銘柄別の lot_size を将来的に導入するための拡張コメントあり。

今後の予定（推測）
- factor_research の各ファクター実装完了、ユニットテスト追加
- ExecutionEngine と Broker クライアント周りのテストおよびドキュメント整備
- 追加の CLI / モニタリング通知（LINE 通知連携）の強化

---

注: 上記は提供されたソースコードの内容から構造・意図を推測して作成した CHANGELOG です。実際のリリースノートや履歴管理ポリシーに合わせて編集してください。