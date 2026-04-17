Keep a Changelog 準拠の形式で、コード内容から推測した変更履歴を日本語で作成しました。必要に応じて日付やバージョン番号は調整してください。

CHANGELOG.md
===========

すべての重要な変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。

Unreleased
----------

- なし

[0.1.0] - 2026-04-17
--------------------

Added
- 初期リリース: KabuSys のコア機能群を追加。
- 実行・監視スクリプト
  - run_execution.py を追加。ExecutionEngine を起動するエントリポイントを提供。KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite (data/paper_trading.db デフォルト) を使用し、本番 DB と分離する。停止フラグ (data/stop_requested.flag) と PID ファイル管理をサポート。
  - run_monitoring.py を追加。SystemMonitor のポーリングループを起動。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。監視は環境に関係なく本番 sqlite_path を使用する設計。
- 設定・環境変数管理
  - config.py を追加。.env 自動読み込み機能（.env, .env.local）を実装。export 形式やクォート、インラインコメント、既存 OS 環境変数の保護（protected）に対応。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを実装し、各種設定プロパティを提供（DB パス、PID/kill flag パス、各種閾値、環境判定メソッド等）。PAPER_FILL_MODE のバリデーションを追加。
- ポートフォリオ構築ライブラリ
  - portfolio.portfolio_builder: シグナル選別 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
  - portfolio.risk_adjustment: セクター集中制限 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier) を実装。未知レジームは警告を出してフォールバック。
  - portfolio.position_sizing: 株数決定ロジック (calc_position_sizes) を実装。risk_based / equal / score の割当方式に対応し、単元株（lot_size）で丸め、aggregate cap と cost_buffer によるスケール処理を実装。
- リサーチ / ファクター計算
  - research.factor_research: モメンタム、ボラティリティ、バリュー系ファクター計算関数（calc_momentum, calc_volatility, calc_value）を追加。DuckDB の prices_daily / raw_financials テーブルを用いて計算。
  - research.feature_exploration: 将来リターン計算 (calc_forward_returns)、IC（Spearman）計算 (calc_ic)、ファクター統計要約 (factor_summary)、ランク生成 (rank) を実装。標準ライブラリのみでの実装、horizon 検証等の入力チェックあり。
  - research パッケージは zscore_normalize を外部モジュール（kabusys.data.stats）からエクスポート。
- AI / ニュース NLP（実験的）
  - ai.news_nlp モジュールを追加。raw_news テーブルからニュースを集約し、OpenAI（gpt-4o-mini）でバッチスコアリングして ai_scores テーブルへ書き込むためのフローを実装（バッチサイズ、トークン対策、リトライ／指数バックオフ、JSON バリデーション、スコアクリップ等を設計）。処理窓計算（calc_news_window）や score_news の雛形を実装。※ファイル末尾が途中で切れているため、一部処理は未完または継続実装が必要。
- ユーティリティ
  - utils.process_priority: クロスプラットフォームでのプロセス優先度設定 (set_process_priority) と CPU affinity 設定 (set_cpu_affinity) を追加。Windows / POSIX（Linux, Darwin, FreeBSD）に対応し、許可不足などは警告でスキップするフェイルセーフ実装。
- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成ツールを追加。期間指定や DB パス指定オプションを持ち、稼働率・注文成功率・送信率・レイテンシ（P95）などを算出して PASS/FAIL 判定を出力。SQL のテーブル未存在等のエラーに対して耐性あり。

Changed
- なし（初回リリースのため新規追加が中心）

Fixed
- .env の解析とロードに関する堅牢性を向上
  - export キーワード対応、クォート内バックスラッシュエスケープ、インラインコメントのルール明確化、既存 OS 環境変数を上書きしない保護機構を実装。
- ポジションサイズ計算の丸め・上限処理や aggregate スケールダウンロジックにおける端数配分アルゴリズムを実装し、残余キャッシュを有効活用する仕組みを導入。
- apply_sector_cap: unknown セクターの扱い（制限適用外）を明確化。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーが未設定の場合は明示的に例外を投げる（score_news）。API キーは環境変数 OPENAI_API_KEY または引数で供給する必要あり。

Notes / Known issues / TODO
- ai.news_nlp モジュールはロジックの多くを実装しているが、ファイル末尾が切れているため完全実装・統合テストが必要。部分失敗時の DB トランザクション方針（部分更新の保護）は設計方針に記載あり。
- position_sizing.calc_position_sizes の価格欠損時の扱いについて要改善（price が欠損/0 の場合は過少見積りになりうる — TODO コメントあり）。
- run_monitoring は「監視は本番 sqlite_path を使用する」と明記しているため、開発環境での誤操作に注意。paper_trading 用の DB 分離は run_execution 側で実施。
- .env 自動ロードはプロジェクトルート探索に依存する（.git または pyproject.toml）。配布後に CWD に依存しないことを意図しているが、特別な配置環境では自動ロードを無効化するためのフラグが提供されている（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- 実行環境依存の優先度設定や CPU affinity は権限不足や未対応 OS でスキップされるため、意図した効果が得られない場合がある。

著作・バージョニング
- パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に合わせています。

（必要であれば、各ファイルに対応する個別の変更ログ（細かな実装差分）を追記します。）