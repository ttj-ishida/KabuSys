# Changelog

すべての主要な変更は "Keep a Changelog" のガイドラインに従って記録しています。  
このファイルはコードベースの内容から推測して作成した変更履歴です。実際のコミット履歴とは差異がある可能性があります。

なお、現在のパッケージバージョンは src/kabusys/__init__.py に定義された __version__= "0.1.0" に基づいています。

## [Unreleased]
- 注意事項 / 既知の未完了点
  - kabusys.ai.news_nlp モジュールの実装が途中で切れている箇所があり（ファイル末尾で処理が中断）、実運用の前に残りのロジック（記事の取得、API 呼び出しループ、結果の DB 書き込みなど）の完成と追加テストが必要です。
  - portfolio.risk_adjustment.apply_sector_cap にて price が欠損（0.0）の場合のエクスポージャー過少見積りに関する TODO を残しています。将来的に前日終値や取得原価でのフォールバック実装を検討してください。

---

## [0.1.0] - 2026-04-17
初期公開（コードベースの現状を反映した最初のリリース想定）

### Added
- 実行コントロール / エンジン
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。プロセス優先度設定、SQLite / DuckDB 接続、ブローカーファクトリの利用、スレッドでのセッション実行、停止フラグ（data/stop_requested.flag）による安全停止に対応。
  - Execution 側は paper_trading 環境時に paper 専用 DB（data/paper_trading.db または PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。

- 監視
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する挙動を明記。
  - init_monitoring_db 呼び出しで監視用テーブルの初期化（冪等）を保証。

- 設定・環境変数管理
  - config.Settings クラスを追加。アプリケーション設定をプロパティ経由で取得する API を提供（env 判定、パス、閾値、API トークン等）。
  - .env 自動ロード機能を追加（プロジェクトルートを .git または pyproject.toml から自動検出）。読み込み順は OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーの実装: export 付き行のサポート、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定(select_candidates)、等金額・スコア重み計算(calc_equal_weights / calc_score_weights)。
  - portfolio.position_sizing: position sizing ロジック（risk_based / equal / score 対応）、単元株（lot_size）丸め、aggregate cap スケーリング、cost_buffer による保守的見積り。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた乗数(calc_regime_multiplier)。

- リサーチ / ファクター計算
  - research.factor_research: DuckDB を用いたモメンタム、ボラティリティ、バリュー系ファクター計算（mom 1/3/6m、MA200 乖離、ATR20、20日平均売買代金、PER/ROE 等）。SQL を活用して効率的に計算。
  - research.feature_exploration: 将来リターン計算(calc_forward_returns)、IC（calc_ic）、ランク関数(rank)、ファクター統計要約(factor_summary)。外部ライブラリに依存せず標準ライブラリのみで実装。

- AI / ニュース NLP
  - ai.news_nlp: ニュース記事を銘柄ごとに集約して OpenAI (gpt-4o-mini) に投げ、銘柄別センチメント ai_score を ai_scores テーブルに書き込むワークフローを設計。バッチ処理、トークン肥大化対策（記事数・文字数制限）、リトライ（429/5xx/タイムアウト）とエクスポネンシャルバックオフ、レスポンスバリデーション、スコアクリッピング（±1.0）等を想定。
  - calc_news_window ユーティリティを実装（JST ベースのニュースウィンドウを UTC naive datetime で返す）。

- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシなどを集計・判定（PASS/FAIL）して標準出力に表示。欠損テーブルに対しては安全に N/A を扱うフォールバックを実装。
  - レポートの閾値（稼働率/成立率/送信率/P95 レイテンシ）を定義。

- ユーティリティ
  - utils.process_priority: クロスプラットフォームなプロセス優先度設定ユーティリティを追加（Windows / POSIX(nice) を吸収、失敗時は警告でスキップ）。CPU affinity 設定も提供（set_cpu_affinity）。

- DB 接続
  - DuckDB と SQLite の両方を併用する設計。DuckDB は主に時系列データ（prices_daily, raw_financials 等）の分析用、SQLite は監視や注文ログ等の永続化に使用。

### Changed
- 環境分離ポリシー
  - Execution は paper_trading 環境で paper 専用 DB を使用するように明確化。Monitoring は常に production sqlite_path を参照する仕様（KABUSYS_ENV に依存しない）を明記。

- 設定の厳密化
  - Settings のプロパティで列挙型的な値検証を導入（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。不正値は ValueError を発生させるため、早期発見が可能。

### Fixed
- .env パースの堅牢化
  - クォート内エスケープや export 指定、インラインコメントの扱いを適切に処理することで、.env による設定読み込みの誤解釈を減少させる実装を追加。

- 監視・実行の停止ハンドリング
  - data/stop_requested.flag を用いた外部制御（プロセス停止）の実装を追加。KeyboardInterrupt でも安全にクローズ処理を行う。

### Removed
- （なし）

### Deprecated
- （なし）

### Security
- OpenAI API キーは明示的に引数で渡すか環境変数 OPENAI_API_KEY を期待する設計。未設定の場合は明確なエラーを出すようにしている。

---

補足／開発ノート
- news_nlp の残り実装（_fetch_articles の呼び出し以降）が未完成のため、該当機能を実運用に投入する前に完全実装と単体テストを推奨します。
- apply_sector_cap の price 欠損時の扱いに注意。将来的な拡張（前日終値やマスタからのフォールバック）を検討してください。
- ユニットテストや統合テストはコード中の前提（DuckDB テーブルスキーマ、SQLite テーブル存在など）に対して整備が必要です。特に DuckDB の executemany に関する制約（空パラメータ列の送信）など実行時に遭遇しやすい落とし穴への注意を推奨します。