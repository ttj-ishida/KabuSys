# CHANGELOG

すべての変更は Keep a Changelog の規約に準拠して記載しています。  
このファイルはコードベース（src/kabusys 以下）から機能・設計を推測して作成した初版の変更履歴です。

全般:
- DuckDB を中心としたローカルデータ駆動型の日本株自動売買／研究フレームワーク。
- 外部発注 API や本番口座への直接アクセスを持たない設計（DB テーブルを通じた入出力に依存）。
- 冪等性（同一日付の DB 書き換え時に DELETE→INSERT を行う）とトランザクションを多用してデータ整合性を保証。

## [0.1.0] - 2026-03-22

### Added
- パッケージ基盤
  - 初期バージョンを定義（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開 API を整備（data, strategy, execution, monitoring 等を __all__ に列挙）。

- 環境設定 / config
  - .env ファイルおよび環境変数の自動読み込み機能を実装（プロジェクトルートは .git / pyproject.toml から探索）。
  - .env パーサ（クォート・エスケープ・コメント処理・export プレフィックス対応）を実装。
  - 自動ロードを一時的に無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - OS 環境変数を保護する protected オプションを用いた .env 上書き挙動。
  - Settings クラスを実装し、以下の設定値をプロパティとして提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）と LOG_LEVEL（DEBUG, INFO, ... の検証）
  - 必須設定未設定時には ValueError を送出する _require 実装。

- 戦略（strategy）
  - feature_engineering.build_features(conn, target_date)
    - research の生ファクターを統合、ユニバースフィルタ（最低株価300円・20日平均売買代金5億円）を適用。
    - 指数の正規化（z-score 正規化）、±3 でクリップし features テーブルへ日付単位で UPSERT（トランザクション）を行う。
    - DuckDB を利用し prices_daily / raw_financials を参照。
  - signal_generator.generate_signals(conn, target_date, threshold=0.60, weights=None)
    - 正規化済みファクターと ai_scores を統合して各銘柄の最終スコアを計算。
    - コンポーネントスコア（momentum, value, volatility, liquidity, news）計算ロジックを実装（シグモイド変換・補完ルールあり）。
    - Bear レジーム（AI の regime_score 平均が負）判定により BUY を抑制。
    - ストップロス（-8%）およびスコア低下による SELL 判定を実装（positions / prices を参照）。
    - 日付単位の signals テーブル置換（トランザクション）で出力。weights の検証と再スケーリング機能を有する。

- Research（研究用ユーティリティ）
  - factor_research:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200日MA乖離率を計算（不足時は None）。
    - calc_volatility(conn, target_date): 20日 ATR / 相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value(conn, target_date): 最新財務データ（raw_financials）と当日株価から PER / ROE を計算。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=[1,5,21]): 各銘柄の将来リターン（複数ホライズン）を一括取得。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンの IC を計算（有効レコード < 3 の場合は None）。
    - factor_summary(records, columns): 各カラムの基本統計量（count, mean, std, min, max, median）を算出。
    - rank(values): 平均順位（同順位は平均ランク）を返すユーティリティ。
  - いずれも外部ライブラリ（pandas 等）には依存せず、DuckDB + 標準ライブラリで実装。

- バックテスト（backtest）
  - simulator.PortfolioSimulator:
    - メモリ上でのポートフォリオ状態管理、買い/売りの擬似約定ロジック（スリッページ・手数料考慮）。
    - SELL は保有全量クローズ、BUY は割当 alloc をもとに株数を計算。平均取得単価（cost_basis）更新。
    - mark_to_market により DailySnapshot を記録（終値欠損時は 0 として評価し WARNING）。
  - metrics.calc_metrics / BacktestMetrics:
    - CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades 等の計算。
  - engine.run_backtest(conn, start_date, end_date, ...):
    - 本番 DB から必要テーブルを抽出してインメモリ DuckDB にコピーしバックテスト実行（signals の生成・擬似約定・positions 書込を含む）。
    - DB のコピーは日付範囲でフィルタ（prices_daily, features, ai_scores, market_regime）し、market_calendar は全件コピー。
    - シミュレータの positions を generate_signals が参照するため、positions の冪等書込機能を提供。
    - デフォルトのスリッページ率 0.001（0.1%）、手数料率 0.00055（0.055%）、最大ポジ比 20% を採用。

### Changed
- （初版のため過去からの変更はなし。設計上の挙動説明を記載）
  - DB 書込は原子性を保つためトランザクション（BEGIN/COMMIT/ROLLBACK）で保護。ROLLBACK 失敗時は警告ログ。
  - 欠損データや非有限値（NaN, ±Inf）への耐性を重視（多くの計算は None を返し、上位ロジックで中立値 0.5 に補完）。

### Fixed
- —（初版リリースのため該当なし）

### Deprecated
- —（初版リリースのため該当なし）

### Removed
- —（初版リリースのため該当なし）

### Security
- .env 読み込み時に OS 環境変数を protected として扱い、必要に応じて .env.local による上書きを制御。
- 重要なシークレット（トークン / パスワード / Slack トークン等）は Settings の必須プロパティとして明示。未設定時は起動時に例外を投げる。

### Notes / Known limitations
- エグジットロジック（_generate_sell_signals）では以下の条件は未実装:
  - トレーリングストップ（peak_price に依存。positions テーブルに peak_price/entry_date が必要）
  - 時間決済（保有 60 営業日超過）などのルール
- calc_value は PBR・配当利回りを未実装（現バージョンは PER / ROE のみ）。
- feature_engineering では per を逆数スコアに変換して正規化対象から除外する設計になっている（_NORM_COLS に未含）。
- generate_signals:
  - AI ニューススコアが未登録の場合は中立（0.5）で補完。
  - weights の合計が 1 でない場合は再スケーリング。無効値・負値・未知キーは無視する。
- バックテスト用の DB コピーは例外時に該当テーブルをスキップする（警告ログ）。コピー失敗は実行継続するが結果に影響する可能性あり。
- 研究コードは pandas 等を使わずに実装されているため、大規模データでのパフォーマンスや利便性面で改善余地あり。
- DuckDB / テーブルスキーマ（prices_daily, features, signals, positions, raw_financials, ai_scores, market_calendar, market_regime 等）に依存。予めスキーマ初期化（kabusys.data.schema.init_schema 等）が必要。

---

今後の予定（想定）
- エグジットロジックの拡張：トレーリングストップ、時間決済、部分利確など。
- 研究／分析機能の拡張：追加ファクター、IC の期間集約、可視化ユーティリティ（必要に応じて pandas/matplotlib 等の導入検討）。
- execution 層との統合：実運用時の注文送信・状態管理、取引所制約の反映。
- テストカバレッジの整備（ユニット / 統合テスト）、CI 経由での環境変数取り扱いの改善。

（この CHANGELOG はコードの実装内容から推測して作成しています。実際の変更履歴やリリースノートとして使用する場合は、開発履歴に基づいて適宜修正してください。）