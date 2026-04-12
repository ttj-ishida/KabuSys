CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained under
Semantic Versioning.

[unreleased]: https://example.com/project/compare/v0.1.0...HEAD
[0.1.0]: https://example.com/project/releases/tag/v0.1.0

Unreleased
---------
- なし（初版リリース以降の未リリース変更はここに記載します）

0.1.0 - 2026-04-12
-----------------
Added
- 初回リリース。
- 実行・監視用エントリポイントを追加
  - run_execution: ExecutionEngine を起動するスクリプト。ブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の run_session 実行を行う。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。
- 環境設定管理モジュールを追加（kabusys.config）
  - .env 自動読み込み機能（プロジェクトルートの .env / .env.local を自動ロード、OS 環境変数は保護）。
  - export KEY=val、クォート文字列、インラインコメント等に対応する堅牢な .env パーサ実装。
  - 必須環境変数チェック用の _require()、KABUSYS_ENV / LOG_LEVEL 等のバリデーション（許容値チェック）を提供。
  - 各種パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH 等）や監視設定（PID ファイル等）を Settings で一元管理。
- 監視関連
  - monitoring モジュールと DB 初期化関数（init_monitoring_db）を用いた監視ループの実装。
  - run_monitoring は環境にかかわらず本番 sqlite_path を使用する設計（監視は本番 DB を参照）。
  - MONITOR_POLL_INTERVAL の不正値時にデフォルトへフォールバックするロジックを追加。
- Execution エンジン関連
  - BrokerClientFactory による本番／ペーパー（Mock）ブローカ選択。
  - paper_trading 環境では専用の SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
  - RiskManager に渡すデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec 等）を実装。初期ポートフォリオ値は broker.get_available_cash() で取得して設定。
- ポートフォリオ構築モジュール（kabusys.portfolio）
  - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全0時は等配分にフォールバックして警告を出す。
  - risk_adjustment: セクター集中制限 apply_sector_cap、市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装。unknown セクターの扱い、レジーム未定義時のフォールバックロジックあり。
  - position_sizing: allocation_method（risk_based / equal / score）に基づく株数計算を実装。単元株（lot_size）丸め、コストバッファ（cost_buffer）を使った保守的見積り、aggregate cap によるスケーリングと再配分ロジックを実装。
- リサーチ／ファクター計算（kabusys.research）
  - factor_research: calc_momentum, calc_volatility, calc_value を実装。DuckDB に対する SQL ベースの集計・ウィンドウ処理でファクターを計算。
  - feature_exploration: calc_forward_returns, calc_ic（Spearman ランク相関）および rank, factor_summary を実装。外部依存ライブラリに頼らない実装方針。
  - research パッケージの __all__ で主要関数と zscore_normalize をエクスポート。
- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols から銘柄別に記事を集約し、OpenAI API（gpt-4o-mini）でセンチメントスコアを計算して ai_scores テーブルへ書き込む処理を実装。
  - バッチサイズ、記事数および文字数上限、スコアクリップ（±1.0）、最大リトライ・指数バックオフなどの堅牢化を導入。
  - ニュース回収ウィンドウの計算 calc_news_window（JST 基準 → UTC 変換）を提供し、ルックアヘッドバイアスを避ける設計。
  - API キーが未設定時の明示的なエラーを実装。
- ツール
  - tools/paper_verification_report: ペーパートレーディング用検証レポート生成ツールを追加。稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを算出し、PASS/FAIL 判定を行う。期間フィルタと DB パスのコマンドライン指定をサポート。
- ユーティリティ
  - utils/process_priority: プラットフォーム差を吸収するプロセス優先度設定（Windows の HIGH_PRIORITY_CLASS / POSIX の nice 値）および set_cpu_affinity を実装。権限不足や未対応 OS の場合は警告を出して安全にスキップ。

Changed
- ログの初期レベルを INFO に設定するエントリポイント（run_execution, run_monitoring, tools）を採用。
- .env 自動ロードはプロジェクトルート検出に基づく実装へ変更（__file__ を起点に親ディレクトリを走査し .git / pyproject.toml を判定）。CWD に依存しないためパッケージ配布後も安定動作。

Fixed
- .env のパース改善:
  - export プレフィックス対応、シングル／ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの正しい扱いを実装。
  - override / protected オプションにより OS 環境変数を保護しつつ .env.local を上書き可能に。
- position_sizing の資金スケールダウン時の端数配分（lot 単位）ロジックを実装し、残余キャッシュで再配分する仕組みを導入。
- factor_research 等の SQL クエリでデータ不足時に None を返すなど、欠損耐性を向上。

Security
- Settings._require により必須環境変数が未設定の場合は起動時に明示的に失敗するようにして誤構成による誤動作を防止。

Notes / Known limitations
- research パッケージは DuckDB 内の prices_daily / raw_financials テーブルのみを参照する設計で、外部の発注 API にはアクセスしない。
- news_nlp は OpenAI API を利用するため、実行には OPENAI_API_KEY が必要。API 呼び出し失敗時は部分的にスキップしてフェイルセーフで継続する設計だが、運用時はレート制限やコストに注意してください。
- position_sizing は現時点で全銘柄共通の lot_size（デフォルト 100）を想定。将来的に銘柄別 lot_size のマスタ対応を検討。
- run_monitoring は監視用 DB に production の sqlite_path を使用するため、監視をテスト環境で分離したい場合は設定の調整が必要。

Developers
- パッケージバージョンは kabusys.__version__ = "0.1.0" に設定。
- 今後の変更は Unreleased セクションに追加し、リリース時にバージョンと日付を明記してください。