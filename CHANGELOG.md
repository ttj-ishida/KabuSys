CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。形式は「Keep a Changelog」に準拠します。

[0.1.0] - 2026-03-19
--------------------

Added
- 初期リリースとして基本機能を実装。
- パッケージエントリポイント
  - src/kabusys/__init__.py: パッケージ情報と __version__ = "0.1.0" を追加。
- 設定・環境変数管理
  - src/kabusys/config.py:
    - .env / .env.local を自動読み込み（OS 環境変数優先、.env.local が .env を上書き）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
    - .git または pyproject.toml を基準にプロジェクトルートを探索するロジックを実装（CWD 非依存）。
    - .env の行パース処理を強化（export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメント処理などに対応）。
    - Settings クラスを実装（J-Quants / kabu API / Slack / DB パス / 環境・ログレベル検証等のプロパティを提供）。
    - env 値と LOG_LEVEL の妥当性チェック（許容値は定義済み）。
- データ取得・保存（J-Quants）
  - src/kabusys/data/jquants_client.py:
    - J-Quants API クライアントを実装（ページネーション対応）。
    - 固定間隔の RateLimiter（120 req/min）を実装。
    - リトライ（指数バックオフ、最大試行回数、408/429/5xx を考慮）、429 の Retry-After を尊重。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ。
    - fetch_* 系関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を実装。
    - DuckDB への保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（冪等化：ON CONFLICT DO UPDATE / DO NOTHING）。
    - データ変換ユーティリティ _to_float / _to_int を実装（安全な型変換）。
    - fetched_at は UTC で記録し、Look-ahead バイアス防止に配慮。
- ニュース収集
  - src/kabusys/data/news_collector.py:
    - RSS フィードからの記事収集パイプラインを実装（デフォルトソースに Yahoo Finance）。
    - defusedxml を用いた安全な XML パース、受信サイズ制限（MAX_RESPONSE_BYTES）、SSRF 対策（HTTP/HTTPS 検証）等を考慮。
    - URL 正規化（トラッキングパラメータ削除、スキーム/ホスト小文字化、フラグメント除去、クエリソート）を実装。
    - 記事 ID を URL 正規化後の SHA-256 ハッシュで生成し冪等性を確保。
    - バルク挿入のチャンク処理、高速化とトランザクションの考慮。
- リサーチ（研究）機能
  - src/kabusys/research/factor_research.py:
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials を参照して各種ファクター（モメンタム、ATR、avg_turnover、PER/ROE 等）を計算。
    - 移動平均やウィンドウ集計における欠損制御や最小カウント条件を厳密に処理。
  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを計算。パフォーマンス目的でスキャン範囲を限定。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装（同順位は平均ランクで処理、サンプル数不足時は None を返す）。
    - rank, factor_summary: ランキング・統計要約（count/mean/std/min/max/median）を提供。外部ライブラリに依存せず標準ライブラリのみで実装。
  - src/kabusys/research/__init__.py: 上記ユーティリティの公開。
- 特徴量エンジニアリング
  - src/kabusys/strategy/feature_engineering.py:
    - build_features(conn, target_date): research モジュールの生ファクターを取得し統合、ユニバースフィルタ（最低株価・最低売買代金）適用、選択カラムの Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップして features テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性を保証）。
    - ユニバースフィルタの実装（_MIN_PRICE=300、_MIN_TURNOVER=5e8）。
- シグナル生成（戦略）
  - src/kabusys/strategy/signal_generator.py:
    - generate_signals(conn, target_date, threshold=0.60, weights=None): features と ai_scores を組み合わせ最終スコアを算出し、BUY / SELL シグナルを生成して signals テーブルへ日付単位で置換。
    - コンポーネントスコア計算: momentum/value/volatility/liquidity/news を定義（シグモイド変換、欠損値は中立 0.5 補完）。
    - 重みのマージ・検証・再スケーリング（未知キーや非数値は無視）。
    - Bear レジーム検知（ai_scores の regime_score 平均が負かつサンプル数閾値以上）。
    - エグジット判定（ストップロス -8% とスコア低下）を実装。positions / prices の欠損処理やログ記録あり。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）、冪等的な DB 書き込み。
- パッケージ構成
  - src/kabusys/strategy/__init__.py: build_features, generate_signals を公開。
  - src/kabusys/research/__init__.py: 研究用関数群を公開。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- news_collector に defusedxml を採用し XML 爆弾等に対する対策を実施。
- RSS 受信サイズ制限・URL スキーム検証・IP/SSRF を考慮する設計（注: 実運用時の追加検証を推奨）。

Notes / 注意事項
- DuckDB スキーマ（テーブル名 / カラム）はコード内で参照されています。実運用前に required schema を用意してください（例: prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar 等）。
- J-Quants の認証には JQUANTS_REFRESH_TOKEN を環境変数で設定する必要があります（settings.jquants_refresh_token が必須）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。配布後の挙動や CI 環境では KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で制御できます。
- 一部の機能（トレーリングストップ、時間決済など）はコメントで将来実装候補として記載されています。

Authors
- 初期実装：コードベースの作成者（ソースコード内コメント・設計に準拠）

References
- StrategyModel.md / DataPlatform.md 等の設計参照がコード内コメントに記載されています。必要に応じて設計ドキュメントを参照してください。

[0.1.0]: https://example.com/release/0.1.0