# Changelog

すべての注目すべき変更はこのファイルに記録されます。  
フォーマットは「Keep a Changelog」に準拠します。

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-19
初回公開リリース

### Added
- パッケージ基礎
  - パッケージ名: kabusys、バージョン: 0.1.0 (src/kabusys/__init__.py)。
  - パッケージ公開 API の __all__ 定義: data, strategy, execution, monitoring。

- 設定管理
  - 環境変数読み込み・管理モジュールを追加 (src/kabusys/config.py)。
    - プロジェクトルートの自動検出: .git または pyproject.toml を基準に __file__ から親ディレクトリを探索してプロジェクトルートを特定。
    - .env/.env.local 自動読み込み（優先順位: OS 環境変数 > .env.local > .env）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサ: export プレフィックス対応、シングル/ダブルクォート内のエスケープ対応、コメント処理など堅牢なパース処理。
    - 環境設定ラッパー Settings を提供。J-Quants / kabuステーション / Slack / データベースパス等のプロパティを定義（必須キーは _require により未設定時に ValueError を送出）。
    - KABUSYS_ENV / LOG_LEVEL の値検証（有効値セットの検査）とヘルパー is_live/is_paper/is_dev。

- データ取得・保存（J-Quants）
  - J-Quants API クライアントを実装 (src/kabusys/data/jquants_client.py)。
    - 固定間隔スロットリングによるレート制御（120 req/min）を実装する RateLimiter。
    - リトライロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx 対応）と 401 時の自動トークンリフレッシュ（1 回だけ）を実装。
    - ページネーション対応で fetch_* 系関数を実装: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への保存ユーティリティを提供: save_daily_quotes, save_financial_statements, save_market_calendar。いずれも冪等性を考慮し ON CONFLICT DO UPDATE を利用。
    - 生データの型変換ユーティリティ: _to_float, _to_int（空文字列や不正値を None で扱う）。

- ニュース収集
  - RSS ベースのニュース収集モジュールを追加 (src/kabusys/data/news_collector.py)。
    - デフォルト RSS ソース定義（例: Yahoo Finance のビジネスカテゴリ）。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、クエリソート、フラグメント除去）と記事 ID 生成方針（正規化後の URL の SHA-256 先頭 32 文字）により冪等性を確保。
    - defusedxml により XML 攻撃対策、受信最大バイト数上限（10MB）によるメモリ DoS 対策、SSRF を考慮した URL チェック、バルク INSERT のチャンク化等の安全対策を導入。
    - raw_news への冪等保存（ON CONFLICT DO NOTHING）や news_symbols への紐付けを想定した設計。

- リサーチ（研究用）機能
  - ファクター計算モジュールを追加 (src/kabusys/research/factor_research.py)。
    - Momentum（mom_1m, mom_3m, mom_6m）、ma200_dev、Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）、Value（per, roe）を DuckDB 上の SQL ウィンドウ関数等で計算。
    - データ不足時の None ハンドリング（ウィンドウサイズ未満で None を返す等）。
  - 特徴量探索ユーティリティを追加 (src/kabusys/research/feature_exploration.py)。
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）に対応した将来リターン計算（LEAD を利用、最大ホライズンに応じたスキャン範囲最適化）。
    - calc_ic: スピアマンのランク相関（IC）計算、サンプル不足時は None。
    - factor_summary / rank: ファクターの統計サマリーとランク付けユーティリティ（同順位は平均ランクで処理、丸めによる ties の安定化）。

- 戦略（Strategy）機能
  - 特徴量エンジニアリングモジュールを追加 (src/kabusys/strategy/feature_engineering.py)。
    - research で計算した生ファクターを読み込み、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 ≥ 5 億円）を適用。
    - 指定カラム群の Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップし features テーブルへ日次で置換（トランザクション + バルク挿入で原子性確保）。
    - ルックアヘッドバイアス対策として target_date 時点までのデータのみを使用。
  - シグナル生成モジュールを追加 (src/kabusys/strategy/signal_generator.py)。
    - features と ai_scores を統合してコンポーネントスコア（momentum, value, volatility, liquidity, news）を算出。最終スコア final_score を重み付き合算で計算（デフォルト重みを採用、ユーザ指定重みは検証・正規化）。
    - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完。
    - Bear レジーム判定（ai_scores の regime_score 平均が負でかつサンプル数閾値を満たす場合）により BUY シグナルを抑制。
    - エグジット条件（SELL シグナル）判定を実装:
      - ストップロス（終値が平均取得価格より -8% 以下）優先判定
      - final_score が閾値未満（デフォルト閾値 0.60）でのエグジット
    - signals テーブルへ日次で置換（トランザクション + バルク挿入で原子性確保）。
    - positions / prices_daily / ai_scores / features に依存するため、DuckDB の該当テーブルが前提。

### Changed
- （初回リリースのため変更履歴なし）

### Fixed
- （初回リリースのため修正履歴なし）

### Security
- ニュース XML のパースに defusedxml を採用し、XML 脅威への対策を実施。
- RSS / URL 処理で受信サイズ上限や SSRF 関連の検討が行われている。

### Notes / Known limitations
- signal_generator の SELL 条件で、トレーリングストップ（peak_price に基づく）や保有期間による時間決済は未実装（コメントで未実装箇所あり）。positions テーブルに peak_price / entry_date 等を保持する仕組みが必要。
- news_collector の実装は安全対策を多く考慮しているが、外部の RSS 仕様差異や文字エンコーディング等の実運用ケースで追加調整が必要となる可能性あり。
- DuckDB のスキーマ（テーブル定義: raw_prices/raw_financials/prices_daily/features/ai_scores/positions/signals/market_calendar 等）は本リポジトリに含まれていないため、実行前に適切なスキーマ作成が必要。
- 外部依存を最小化する設計方針のため、リサーチモジュールは pandas 等を使用せず標準ライブラリ + DuckDB SQL で実装。大規模データや複雑集計でパフォーマンスチューニングが必要な場合は別途検討。

---

（この CHANGELOG はコード内コメントおよび実装から推測して作成しています。実運用上の変更やリリース手順に合わせて適宜更新してください。）