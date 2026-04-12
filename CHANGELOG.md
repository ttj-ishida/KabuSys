CHANGELOG
=========

すべての重要な変更は Keep a Changelog に準拠して記載します。  
このファイルは人間と自動化されたツールの両方で読みやすいことを目的としています。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

Unreleased
----------
（現時点の変更はありません）

[0.1.0] - 2026-04-12
--------------------

Added
- パッケージ初期リリース。
- 実行エントリ:
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（デフォルト data/paper_trading.db）を使用し、MockBrokerClient を使った完全分離のペーパートレードが可能。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。
- 設定管理:
  - config.py: 環境変数・.env ファイル自動読み込み機能を追加。プロジェクトルートを .git / pyproject.toml から自動検出して .env / .env.local を読み込む。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env パーサを実装（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの制御等をサポート）。
  - Settings クラスを実装し、各種設定（DBパス、PID ファイルパス、閾値、環境判定、paper_trading の挙動など）をプロパティ経由で取得できるように。入力値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を追加。
- ポートフォリオ構築:
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）と重み算出（calc_equal_weights, calc_score_weights）を追加。スコア全ゼロ時のフォールバック挙動を明記。
  - portfolio/risk_adjustment.py: セクター集中制限の適用関数 apply_sector_cap と市場レジームに基づく乗数 calc_regime_multiplier を追加。
  - portfolio/position_sizing.py: 発注株数の計算 calc_position_sizes を追加。risk_based / equal / score の配分方式をサポートし、単元株丸め、個別・全体上限、cost_buffer による保守的見積り、スケールダウン・残差分配ロジックを実装。
  - portfolio/__init__.py に上記 API をエクスポート。
- リサーチ / ファクター:
  - research/factor_research.py: Momentum, Volatility, Value 等のファクター計算（calc_momentum, calc_volatility, calc_value）を DuckDB 経由で実装。200 日移動平均、ATR、出来高指標、財務データ結合などをサポート。
  - research/feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク関数（rank）、ファクター統計サマリ（factor_summary）を実装。外部依存を使わず標準ライブラリのみで実装。
  - research/__init__.py で zscore_normalize（kabusys.data.stats 由来）と上記関数を公開。
- AI / ニュース:
  - ai/news_nlp.py: raw_news を OpenAI（gpt-4o-mini）へ投げて銘柄別センチメントを算出し ai_scores テーブルへ書き込む処理を実装。バッチ（最大 20 銘柄）、JSON Mode の期待レスポンス、リトライ（429/5xx/タイムアウト/ネットワーク断に対する指数バックオフ、最大リトライ回数設定）、スコアのクリッピング（±1.0）、タイムウィンドウの厳密な定義（JST→UTC 変換）などを含む。API キーは引数または環境変数 OPENAI_API_KEY で解決。
- ツール:
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均・最大・P95）を算出し PASS/FAIL 判定を行う CLI（期間指定可）を提供。閾値はファイル内定数で管理。
- ユーティリティ:
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。Windows と POSIX（Linux, Darwin, FreeBSD）の差分を吸収。アクセス権限や未対応プラットフォームでは安全にスキップしロギングする。
  - utils パッケージ骨格を追加。
- パッケージ情報:
  - __init__.py に __version__ = "0.1.0" を追加し、主要サブパッケージを __all__ で公開。

Changed
- N/A（初回リリースのため変更履歴はありません）

Fixed
- N/A（初回リリースのため修正履歴はありません）

Deprecated
- N/A

Removed
- N/A

Security
- N/A

脚注 / 注意事項
- DuckDB と SQLite を併用する設計: リサーチ系は DuckDB、監視や履歴は SQLite を想定。
- run_execution/run_monitoring は実運用向けにプロセス優先度設定や PID ファイルパス管理を組み込んでいるため、コンテナや権限の制約下での挙動に注意が必要。
- .env 自動ロードはプロジェクトルート検出に依存するため、パッケージ配布後や特殊な配置では KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にして手動で環境変数を制御してください。
- OpenAI API を利用する機能は API キーの管理と呼び出し制限に留意してください（エラーハンドリングはあるが完全な回復性は保証しません）。

今後の予定（例）
- 銘柄毎の lot_size をマスタで管理する拡張。
- position_sizing の手数料/スリッページ推定ロジックの強化（price フォールバック処理）。
- ai/news_nlp の部分失敗時におけるトランザクション性向上（より細かい DB 保護）。
- テストの追加（ユニット／統合）および CI ワークフロー整備。