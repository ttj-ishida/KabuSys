# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

現在のバージョン: 0.1.0 (初期リリース)

## [Unreleased]

なし

## [0.1.0] - 2026-03-20

初期リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py によるパッケージ定義とバージョン (0.1.0)。
  - public API として data, strategy, execution, monitoring をエクスポート。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートの検出は .git / pyproject.toml を基準に探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑止。
    - 高度な .env パーサ（コメント、`export KEY=val`、クォートとエスケープ対応、インラインコメントの扱い）。
    - 環境変数必須チェック（_require）と例外による明示的エラー。
    - settings オブジェクトにより J-Quants / kabu / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベル等の取得を提供。
    - env/log_level の妥当性検証。

- データ取得・保存（J-Quants クライアント）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアント実装（株価日足、財務データ、マーケットカレンダーの取得）。
    - 固定間隔のレートリミッタ（120 req/min）実装。
    - リトライ（指数バックオフ、最大 3 回、408/429/5xx 等のハンドリング）。429 の場合は Retry-After を尊重。
    - 401（Unauthorized）受信時はトークンを自動リフレッシュして 1 回リトライする安全策。
    - ページネーション対応。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を提供し、ON CONFLICT による冪等性を確保。
    - 型変換ユーティリティ（_to_float / _to_int）を実装し、データ品質を保つ。

- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィードからニュースを取得して raw_news に保存する機能。
    - URL 正規化（トラッキングパラメータ除去、キーソート、スキーム/ホスト小文字化、フラグメント除去）。
    - 記事 ID は正規化 URL の SHA-256 ハッシュを用いて冪等性を保証。
    - defusedxml を用いた安全な XML パース（XML Bomb 等への耐性）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES）によるメモリ DoS 対策。
    - バルク INSERT のチャンク処理による効率化とトランザクション処理。
    - デフォルトの RSS ソース（Yahoo Finance のビジネスカテゴリ）を定義。

- リサーチ（因子計算・解析）
  - src/kabusys/research/factor_research.py
    - Momentum, Value, Volatility, Liquidity 等の定量ファクター計算（prices_daily / raw_financials を使用）。
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を提供（200 日移動平均のデータ不足を考慮）。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を提供（ATR の NULL 伝播制御）。
    - calc_value: target_date 以前の最新財務データを用いた per / roe の算出。
    - DuckDB を想定した SQL とウィンドウ関数で効率的に計算。

  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 将来リターン（複数ホライズン）を一括取得するユーティリティ。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）。
    - rank: 同順位は平均ランクになるランク化ユーティリティ（丸めによる ties 保護を実装）。
    - すべて標準ライブラリのみで実装（pandas 等へ依存しない設計）。

  - src/kabusys/research/__init__.py に主要 API を再エクスポート。

- 特徴量エンジニアリング
  - src/kabusys/strategy/feature_engineering.py
    - research モジュールで計算済みの生ファクターをマージ・フィルタ・正規化して features テーブルに保存する処理（build_features）。
    - ユニバースフィルタ（最低株価: 300 円、20 日平均売買代金 >= 5 億円）を実装。
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）と ±3 クリップで外れ値の影響を抑制。
    - 日付単位の置換（DELETE + bulk INSERT）をトランザクションで行い冪等性を保証。
    - ルックアヘッドバイアス防止（target_date 時点のデータのみ使用）という設計方針を明示。

- シグナル生成
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合し final_score を計算、BUY/SELL シグナルを生成して signals テーブルに保存する（generate_signals）。
    - 重み付き合算モデル（デフォルト重み momentum/value/volatility/liquidity/news を実装）、ユーザー重みのバリデーション・再スケール処理。
    - コンポーネントスコア計算（momentum/value/volatility/liquidity/news）とシグモイド変換、欠損コンポーネントは中立値 0.5 で補完。
    - Bear レジーム判定（ai_scores の regime_score 平均が負でサンプル数 >= 3 の場合）による BUY 抑制。
    - SELL シグナル（エグジット）判定: ストップロス（-8%以上）とスコア低下による判定を実装。
    - positions / prices_daily / features / ai_scores を参照して売買判定を行い、日付単位の置換をトランザクションで実行。
    - ロギングで判定の理由やデータ欠損の警告を出力。

- strategy パッケージのエクスポート
  - src/kabusys/strategy/__init__.py で build_features / generate_signals を公開。

### Changed
- 初回リリースのため過去変更はなし（ベースライン実装）。

### Fixed
- 初回リリースのため該当なし。

### Security
- news_collector: defusedxml による安全な XML パースを採用し、RSS パース時の XML 攻撃に対処。
- news_collector: 外部 URL の正規化とトラッキングパラメータ除去、受信サイズ上限を導入して SSRF / DoS のリスクを低減。
- jquants_client: トークン自動リフレッシュとキャッシュで認証周りの安全かつ再現可能な動作を実現。

### Notes / Limitations
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装（コード内に TODO として説明あり）。これらは positions テーブルに peak_price / entry_date 等の追加が必要。
- news_collector の URL/ネットワーク関連の詳細バリデーション（IP ブロックやホワイトリスト等）は将来的な強化対象。
- DuckDB テーブルスキーマや外部依存（Slack, kabu API, J-Quants トークン等）は本リリースでは提供せず、運用環境で適切に設定する必要があります。
- 外部モジュール（kabusys.data.stats の zscore_normalize など）は本リリースの想定実装に依存しているため、統合時の互換性確認を推奨。

---

貢献・バグ報告・改善提案は Issue を通じてお願いします。