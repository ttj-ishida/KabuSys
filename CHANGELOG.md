Keep a Changelog
=================

すべての注目すべき変更はこのファイルで記録します。  
このプロジェクトは、https://keepachangelog.com/ja/ のガイドラインに従います。

[0.1.0] - 2026-03-20
-------------------

Added
- パッケージ初期リリース（kabusys 0.1.0）。
- パッケージ API エントリポイントを追加
  - src/kabusys/__init__.py にて __version__="0.1.0" および公開モジュール一覧（data, strategy, execution, monitoring）。
- 環境設定管理
  - src/kabusys/config.py
    - .env/.env.local の自動読み込み機能（プロジェクトルート判定: .git または pyproject.toml）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - export KEY=val, クォート付き値（エスケープ対応）、コメント処理など堅牢な .env パース機能。
    - 必須環境変数の検出（_require）とエラーメッセージ。
    - 許容する環境 (development, paper_trading, live) とログレベル検証。
    - デフォルト DB パス (duckdb/sqlite) の設定取得。
- Data レイヤー（J-Quants クライアント等）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアント（ページネーション対応、fetch_*/save_* 系関数）。
    - 固定間隔のレートリミッタ実装（120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx 対応、Retry-After 優先）。
    - 401 レスポンス時にトークン自動リフレッシュと 1 回の再試行。
    - モジュールレベルの ID トークンキャッシュ（ページネーション間共有）。
    - DuckDB への冪等保存（ON CONFLICT DO UPDATE）: raw_prices / raw_financials / market_calendar。
    - レスポンス → 型変換ユーティリティ (_to_float, _to_int)。
    - fetched_at を UTC ISO 形式で記録し、Look-ahead バイアスのトレースを容易に。
- ニュース収集モジュール
  - src/kabusys/data/news_collector.py
    - RSS フィード取得および raw_news への冪等保存（デフォルト RSS: Yahoo Finance）。
    - defusedxml を使った安全な XML パース（XML Bomb 等の防御）。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、ソートされたクエリ）。
    - 非 http/https スキーム拒否（SSRF 対策）と受信サイズ上限（MAX_RESPONSE_BYTES=10MB）。
    - 記事 ID を正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を確保。
    - バルク INSERT のチャンク化と 1 トランザクションでの保存.
- Research（因子計算 / 解析）
  - src/kabusys/research/factor_research.py
    - calc_momentum, calc_volatility, calc_value を実装。
    - DuckDB のウィンドウ関数を活用した営業日ベースのファクター計算（MA200、ATR20、出来高比率、PER 等）。
    - データ不足時の安全な None ハンドリング。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns（複数ホライズン対応）、calc_ic（Spearmanランク相関）、factor_summary、rank を提供。
    - 外部依存を使わず標準ライブラリのみで統計処理を実装。
  - src/kabusys/research/__init__.py にて主要関数をエクスポート。
- Strategy（特徴量エンジニアリング・シグナル生成）
  - src/kabusys/strategy/feature_engineering.py
    - research で計算した生ファクターをマージし、ユニバースフィルタ（最低株価=300円、20日平均売買代金>=5億円）適用。
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへの日付単位の置換（トランザクション＋バルク挿入で原子性）。
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合して各銘柄の最終スコア（final_score）を計算。
    - momentum/value/volatility/liquidity/news コンポーネントを計算し、重み付け合算（デフォルト重みを持つ）。
    - Bear レジーム判定（AI の regime_score 平均 < 0 かつサンプル数閾値以上で判定）により BUY を抑制。
    - BUY（閾値 default=0.60）と SELL（ストップロス -8%、スコア低下）シグナルの生成。
    - positions / prices_daily / ai_scores を参照し、signals テーブルへ日付単位の置換（トランザクション＋バルク挿入）。
  - src/kabusys/strategy/__init__.py にて build_features / generate_signals を公開。
- ロギングと注意喚起
  - 各処理での logger.debug/info/warning により実行時状況を可視化。
  - 不正・無効パラメータ時に警告を出す設計（例: generate_signals の weights 検証など）。

Changed
- 初回公開のため該当なし。

Fixed
- 初回公開のため該当なし。

Removed
- 初回公開のため該当なし。

Security
- news_collector で defusedxml を使用、HTTP スキームチェック、受信サイズ制限など複数の安全対策を導入。
- J-Quants クライアントは再試行ポリシーとトークン自動更新の実装で認証／通信の堅牢性を確保。

Notes / 既知の制限・今後の作業
- 一部エグジット条件は未実装（feature_engineering / signal_generator 内の docstring に記載）
  - トレーリングストップ（peak_price が positions に必要）、時間決済（保有 60 営業日超）などは未実装。
- features / signals / positions 等のスキーマはこの変更履歴に含まれないため、DuckDB スキーマの定義は別途必要。
- ai_scores の供給（AI モデルの実行・更新）は本リリースに含まれない。AI スコア未登録時は中立値や補完ロジックで扱う実装あり。
- zscore_normalize の実装本体は data.stats にて提供される想定（本差分では参照されているが実装ファイルは提示外）。
- .env パースは多くの実運用ケースを想定しているが、極端なケース（破損したバイナリファイル等）では予期せぬ挙動となる可能性がある。

開発者向けメモ
- 自動 .env ロードはパッケージ配布後も安全に動作するよう __file__ 起点でプロジェクトルートを探索する実装になっている。
- J-Quants API 呼び出しは _RateLimiter による固定間隔スロットリング方式を採用（単純で安全だが、より複雑なバースト制御が必要な場合は改善検討）。

（ここまでが 0.1.0 の変更内容です）