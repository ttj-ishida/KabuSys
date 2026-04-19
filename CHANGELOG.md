CHANGELOG
=========

この CHANGELOG は Keep a Changelog のフォーマットに従っています。  
各リリースで追加された機能、変更点、修正点、および重要な注意事項を日本語で記載しています。  
（内容は提供されたコードベースから推測して作成しています）

フォーマット:
- Added: 新機能
- Changed: 仕様変更 / 挙動変更
- Fixed: バグ修正
- Security: セキュリティ関連

Unreleased
----------
- 設定検証やポジション計算の追加改善（例: 銘柄別単元対応、価格フォールバックなど）を予定。
- research.calc_momentum 実装の完了や追加ファクターの実装予定。
- テストカバレッジおよびドキュメント整備の強化。

[0.1.0] - 2026-04-19
--------------------

Added
- 全体
  - 初期リリースを公開（バージョン 0.1.0）。
  - パッケージ情報: kabusys パッケージを提供（__version__ = "0.1.0"）。
- 設定・環境管理
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env パーサの実装: export 形式、クォート、エスケープ、インラインコメント等に対応した堅牢なパーサ。
  - Settings クラスを導入し、環境変数アクセスを統一（J-Quants / kabu API / DB パス / 各種閾値 等）。
  - config_setup: 対話式ウィザードで .env を作成・更新する CLI を追加（secret マスク表示、デフォルト値、選択肢対応）。
  - validate_config: 起動前に .env と config/*.yaml を検証する CLI を追加（--strict オプションで警告を FAIL 扱いに可能）。
- 実行・監視スクリプト
  - run_execution: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper 専用 SQLite（data/paper_trading.db など）を使用し本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（Mock ブローカー対応）。
    - エンジンの PID ファイル管理と停止フラグ（data/stop_requested.flag）検出による安全停止。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する実装。
    - 停止フラグ検知でループを終了、KeyboardInterrupt をハンドリングしてクリーンに終了。
- ロギング・プロセス制御ユーティリティ
  - utils.logging_setup: ルートロガー設定ユーティリティを追加。
    - stdout への StreamHandler と、日次ローテーション（TimedRotatingFileHandler）でログをファイルに出力（デフォルト logs/、30日保持）。
    - ログディレクトリ作成失敗時はファイル出力を無効化してコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR の環境変数対応。
  - utils.process_priority: Windows / POSIX を吸収するプロセス優先度・CPU affinity 設定ユーティリティを追加。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(N) を提供。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア／ランクで候補選定。
    - calc_equal_weights / calc_score_weights: 等重およびスコア加重配分ロジック（スコア全0 の場合は等重フォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中を抑える候補フィルタ。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数。
  - portfolio.position_sizing
    - calc_position_sizes: 複数の allocation_method ("risk_based", "equal", "score") に対応した株数計算。
    - aggregate cap（利用可能現金を超えた場合のスケールダウン）や lot_size（単元）丸め、コストバッファ考慮を実装。
    - 手数料／スリッページ等を考慮した保守的な配分ロジック。
- リサーチ / ファクター計算（基盤）
  - research.factor_research: DuckDB 接続を利用して各種ファクター（Momentum, Value, Volatility, Liquidity）を計算する方針でモジュールを追加。（関数スケルトン・定数定義あり）
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成 CLI を追加。
    - 稼働率、注文成功率（Fill Rate）、送信率、レイテンシ（平均 / 最大 / P95）などの集計。
    - パス／フェイル基準（稼働率 99% 等）で PASS/FAIL 判定。
    - --from / --to / --db オプション対応。PAPER_TRADING_SQLITE_PATH 環境変数を尊重。
- DB 関連
  - DuckDB と SQLite を併用する設計（duckdb_path / sqlite_path 設定）。
  - init_monitoring_db を経由して監視テーブルの初期化（冪等）を担保（起動スクリプトから呼び出し）。
- その他の実施上の配慮
  - run_execution / run_monitoring 起動時にプロセス優先度を最初に high にセットする挙動。
  - 設定検証で PyYAML 未インストール時は YAML 検証をスキップして警告を出す等のフォールバック。

Changed
- 初期リリースにつき、主に新規実装。既存挙動の後方互換性破壊はなし。

Fixed
- 初期リリースにつき、既知のバグ修正履歴はなし（ただし各所に入力検証や例外ハンドリングを実装）。

Security
- 機密値（J-Quants リフレッシュトークン、KABU_API_PASSWORD 等）は .env により管理し、config_setup でマスク表示。  
- .env は絶対に Git にコミットしないよう README・テンプレートで注意喚起（config_setup のヘッダ）。

注意事項（Known issues / TODO）
- position_sizing.py:
  - TODO: 銘柄ごとの単元（lot_size）を銘柄マスタ（stocks マスタ）から取得できるように拡張予定（現在は全銘柄単一単元想定）。
- risk_adjustment.apply_sector_cap:
  - price_map に欠損（0.0）がある場合、エクスポージャーが過少見積りされる可能性がある旨の注記あり。将来的に前日終値や取得原価などのフォールバックを検討。
- research.factor_research:
  - ファイル末尾で実装途中の箇所あり（calc_momentum の途中）。ファクター計算ロジックの残り実装が必要。
- ログディレクトリ作成やプロセス優先度設定は環境や権限に依存するため、失敗時は警告を出して安全にフォールバックする設計だが、運用時に想定されるログ保管先や権限を確認することを推奨。
- validate_config は config/*.yaml の内容検証に PyYAML を必要とする。インストールされていない場合は YAML の検証がスキップされる（警告）。

リリースノート作成にあたっての補足
- 本 CHANGELOG は提供されたコード内容から推測して作成しています。実運用でのリリースノート作成時には、実際のコミット履歴・運用上の変更点・外部依存のバージョン等を合わせて確定してください。