CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。

フォーマットの意味:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Removed / Deprecated / Security: 該当する場合に記載

Unreleased
----------

- ドキュメント/コード内の TODO や未実装部分に関する注記を追加。
  - research/factor_research.py の実装が途中で切れている箇所がある（開発継続の余地あり）。
- 一部のチェック・ログ出力の微調整 / 警告メッセージの改善予定。

[0.1.0] - 2026-04-18
--------------------

Added
- 実行エントリスクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、ブローカーファクトリの利用、ステータス PID ファイル、停止フラグの監視、スレッドでのエンジン実行を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き、停止フラグ検知、SQLite/DuckDB 接続、監視 DB の初期化を実装。

- 設定・環境関連
  - config.py: Settings クラスを導入。.env 自動読み込み（.env, .env.local、OS 環境変数優先）および多数の設定プロパティ（DB パス、KABUSYS_ENV、ログレベル、paper trading 関連設定など）を実装。PAPER_FILL_MODE の検証と paper_sqlite_path の分離設定を追加。
  - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加（シークレット入力、選択肢、既存値の再利用、.env の書き出しテンプレートなど）。

- 設定検証ツール
  - validate_config.py: .env と config/*.yaml の軽量検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス存在の親ディレクトリチェック、YAML パース（PyYAML がある場合）の実行、live 環境向けの追加警告を実装。--strict オプションで警告を失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定するユーティリティを追加。ログディレクトリの自動作成、既存ハンドラのクリーンアップ、ログレベル解決の仕様を実装。
  - utils/process_priority.py: Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。CPU affinity 設定ユーティリティも提供。権限不足や未対応 OS 時は警告を出して安全にスキップ。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: 候補選定（score 降順 + signal_rank によるタイブレーク）、等金額配分、スコア加重配分を実装。スコア全0 の場合は等配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装。unknown セクターの扱い、レジームマップ（bull/neutral/bear）を定義。
  - portfolio/position_sizing.py: 発注株数の算出ロジックを実装（risk_based / equal / score の allocation_method をサポート）。単元株（lot_size）丸め、per-position 上限、aggregate cap（投下合計が available_cash を超える場合のスケーリング）を実装。コストバッファ（手数料/スリッページ想定）を考慮したスケーリングロジックを実装。複数の安全弁（価格欠損チェック、0 値回避）を備える。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite データベースを集計して検証レポートを生成する CLI を追加。システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均・最大・P95）を計算し、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づき PASS/FAIL を判定。DB が存在しない／テーブル欠如時のフォールバック処理を実装。P95 計算と日付フィルタ（ISO8601 UTC 文字列変換）を実装。

- research/factor_research.py (部分実装)
  - DuckDB 接続を受け取り prices_daily/raw_financials を参照して各種ファクター（Momentum, Value, Volatility, Liquidity）を計算する設計を追加。モメンタム計算のための定数（21/63/126/200 日など）と calc_momentum の骨格を実装（実装途中で切れている箇所あり）。

- パッケージメタ
  - __version__ = "0.1.0" を設定（文字列定義によるバージョン管理）。

Changed
- .env 読み込みの振る舞い
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメントの取り扱い、.env.local による上書きルール（OS 環境変数を保護）など、堅牢なパーサーを実装。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml を起点）を探索して行う。プロジェクトルートが特定できない場合は自動読込をスキップできる（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

- DB/ファイル分離方針
  - paper_trading 環境では paper_trading 用の専用 SQLite（data/paper_trading.db）を使用し、本番 sqlite_path と完全に分離。監視テーブルは起動時に init_monitoring_db() で冪等に初期化。

Fixed
- エラー耐性の向上
  - run_monitoring / run_execution のループ内で予期しない例外が発生してもログ出力して次ポーリングへ回復する仕組みを追加。
  - ログディレクトリ作成失敗やファイルハンドラ作成失敗時にフォールバックしてコンソール出力のみで継続するように改善。
  - process_priority や cpu_affinity の設定で権限不足や未対応 API が発生した際の例外捕捉と警告ログを追加。

Notes / Known issues
- research/factor_research.py の calc_momentum 実装が途中で終わっているため、ファクター計算の一部は未完成。
- position_sizing.calc_position_sizes 内で price の欠損（0.0）によりエクスポージャーが過少評価される可能性がある旨の TODO コメントあり。将来的に前日終値や取得原価でのフォールバックが想定されている。
- run_monitoring と run_execution はファイルベースの stop/kill フラグによる制御を行う設計。オーケストレーション環境での運用時はファイル配置・権限に注意。

Acknowledgements
----------------
- SQLite / DuckDB を組み合わせたローカル分析・監視アーキテクチャを採用。
- paper trading と本番を明確に分離する設計により、安全なローカル検証を重視。

今後の予定（例）
- factor_research の完全実装（Momentum / Value / Volatility / Liquidity）
- 単体テスト・統合テストの追加
- monitoring / execution のコンテナ化・systemd ユニット化など運用面の整備
- ポジションサイズ算出での銘柄別 lot_size サポート、価格フォールバックロジックの実装

-----