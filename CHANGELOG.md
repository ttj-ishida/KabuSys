CHANGELOG
=========

すべての重要な変更を記録します。フォーマットは Keep a Changelog に準拠しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-21
--------------------

### Added
- 初回リリース: パッケージ kabusys (バージョン 0.1.0)
  - パッケージ公開情報: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

- 環境設定・自動ロード
  - kabusys.config.Settings: 環境変数から設定を取得するクラスを追加。
  - .env 自動読み込み機能:
    - プロジェクトルートを .git または pyproject.toml から検出して .env / .env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサは export 形式・クォート・インラインコメント等に対応し、OS 環境変数は protected として上書きを制御。
  - 必須設定の検証: JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID を取得するプロパティ（未設定時は ValueError）。
  - システム設定の検証: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の妥当性チェック。
  - データベースパス設定（duckdb / sqlite）を Path 型で取得。

- データ取得・保存 (kabusys.data)
  - J-Quants API クライアント (data/jquants_client.py)
    - レート制限対応: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
    - リトライ戦略: 指数バックオフ + 最大 3 回リトライ（HTTP 408/429/5xx 等を対象）。429 時は Retry-After を優先。
    - 認証: refresh token から id_token を取得する get_id_token、401 受信時の自動リフレッシュを実装（1 回のみ）。
    - ページネーション対応とページ間でのトークンキャッシュ。
    - データ取得関数: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を提供。
    - DuckDB への保存関数: save_daily_quotes / save_financial_statements / save_market_calendar を提供。ON CONFLICT DO UPDATE による冪等保存。
    - 型変換ユーティリティ: _to_float / _to_int を実装し不正データを安全に扱う。
    - UTC タイムスタンプ（fetched_at）で取得時刻を記録し、look-ahead バイアスの追跡を可能に。

  - ニュース収集モジュール (data/news_collector.py)
    - RSS フィード収集と前処理を実装（デフォルトに Yahoo Finance のビジネス RSS を含む）。
    - URL 正規化: トラッキングパラメータ削除（utm_*, fbclid 等）、クエリソート、フラグメント除去。
    - 記事 ID は正規化後の URL の SHA-256 等で生成して冪等性を確保。
    - defusedxml を用いた安全な XML パース（XML Bomb 等対策）。
    - レスポンスサイズ制限（最大 10 MB）や SSRF/非 HTTP スキーム対策、バルク INSERT のチャンク化などの安全策を実装。
    - DB への冪等保存（ON CONFLICT DO NOTHING 相当）と挿入数の正確な返却を想定。

- リサーチ機能 (kabusys.research)
  - factor_research.py:
    - calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials を参照して各種ファクター（モメンタム、MA200乖離、ATR、avg_turnover、PER/ROE 等）を計算。
    - 営業日ベースの窓や、データ不足時の None 扱いなどを考慮。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算。サンプル不足時は None を返す。
    - factor_summary / rank: 基本統計量のサマリーとランク付けユーティリティを提供。
  - research パッケージの __init__ で主要関数をエクスポート。

- 戦略層 (kabusys.strategy)
  - feature_engineering.build_features:
    - research 側の生ファクターを取得し、ユニバースフィルタ（最低株価・平均売買代金）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - DuckDB の features テーブルへ日付単位の置換（BEGIN/DELETE/INSERT/COMMIT）で原子性を保証（冪等）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して component スコア（momentum/value/volatility/liquidity/news）を算出。
    - シグモイドや平均化、欠損は中立値 0.5 補完の方針で final_score を計算。
    - デフォルト重みと閾値（default weights / 0.60）を提供。ユーザー重みは検証後に正規化。
    - Bear レジーム判定（ai_scores の regime_score の平均が負）により BUY シグナル抑制。
    - エグジット判定（stop_loss: -8% 未満 / score_drop: final_score < threshold）を実装。positions の価格が取得できない場合は判定をスキップして安全性を優先。
    - signals テーブルへ日付単位の置換で原子性を保証（BUY と SELL の整合性処理、SELL 優先）。

- トランザクション・ロギング・堅牢性
  - DuckDB への複数行挿入はトランザクションでラップし、例外時に ROLLBACK を試みログ出力。
  - 複数箇所で入力バリデーション・数値の有限性チェック（math.isfinite）を実施。
  - 多くの処理で操作が冪等になるよう設計（DELETE / INSERT の日付単位置換、ON CONFLICT）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Known limitations / Notes
- signal_generator の SELL 判定について、トレーリングストップや時間決済（保有 60 営業日超）などはいくつか未実装。これらは positions テーブルに peak_price / entry_date 等の情報が必要であり、将来の拡張点として明示。
- news_collector の記事→銘柄紐付け（news_symbols）や AI ニューススコアの生成は外部処理を想定しており、現状では AI スコア未登録時に中立 0.5 を使用する実装。
- research モジュールは外部依存（pandas 等）を避けて標準ライブラリ + duckdb で実装しているため、大量データの処理は工夫が必要な場合がある。

脚注
----
- 本 CHANGELOG はコード内容から推測して作成しています。実際のリリースノートや配布物と差異がある可能性があります。必要に応じて修正・詳細追記を行ってください。