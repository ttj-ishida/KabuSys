CHANGELOG
=========

すべての重要な変更点をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠し、安定した公開リリース履歴を示します。

リンク: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-20
-------------------

Added
- 初回公開: KabuSys 日本株自動売買ライブラリの初期実装を追加。
  - パッケージ構成:
    - kabusys: パッケージエントリ（version=0.1.0, __all__ に data/strategy/execution/monitoring を公開）
  - 設定/環境管理:
    - src/kabusys/config.py
      - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
      - .env パース機能を実装（export プレフィックス対応、クォート内のエスケープ、インラインコメント処理）。
      - OS 環境変数を保護する protected オプション（.env.local は override=True で上書き可能だが OS 環境変数は保護）。
      - Settings クラスを追加し、J-Quants / kabuAPI / Slack / DB パス / 実行環境（development/paper_trading/live）等のプロパティを提供。
      - env / log_level の検証（許容値チェック）と is_live/is_paper/is_dev フラグを提供。
  - データ取得・保存:
    - src/kabusys/data/jquants_client.py
      - J-Quants API クライアント実装。
      - 固定間隔スロットリングによるレート制限（120 req/min）を実装する RateLimiter。
      - 再試行（指数バックオフ、最大3回）と 401 自動リフレッシュのロジックを実装。
      - fetch_* API（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）を実装（ページネーション対応）。
      - DuckDB へ冪等保存する save_* 関数を実装（raw_prices / raw_financials / market_calendar、ON CONFLICT DO UPDATE を使用）。
      - 型変換ユーティリティ _to_float / _to_int を提供（堅牢な空値・フォーマット処理）。
  - ニュース収集:
    - src/kabusys/data/news_collector.py
      - RSS フィードからの記事収集処理を実装（デフォルトに Yahoo Finance のカテゴリRSSを含む）。
      - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）と記事 ID 生成（SHA-256 ベース）で冪等性を確保。
      - defusedxml を使用した XML の安全なパース、受信サイズ上限（10MB）、HTTP スキーム/SSRF 対策などの防御措置を設計。
      - バルク INSERT チャンク（_INSERT_CHUNK_SIZE）とトランザクションまとめでパフォーマンス/一貫性を確保。
  - 研究系ユーティリティ:
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算 calc_forward_returns（複数ホライズン対応、入力検証、パフォーマンス配慮のクエリ）。
      - スピアマンIC（calc_ic）／ランク関数（rank）／ファクター統計要約（factor_summary）を実装。
      - pandas 等に依存せず、標準ライブラリのみで実装。
    - src/kabusys/research/factor_research.py
      - モメンタム（calc_momentum）、ボラティリティ（calc_volatility）、バリュー（calc_value）ファクター計算を実装。
      - prices_daily / raw_financials を参照して、MA200、ATR20、出来高比、PER/ROE 等を計算。データ不足時の None ハンドリング。
  - 戦略関連:
    - src/kabusys/strategy/feature_engineering.py
      - 研究環境で算出した生ファクターをマージし、ユニバースフィルタ（最低株価・平均売買代金）を適用。
      - 指数的に Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ、features テーブルへ日付単位の置換（トランザクションで原子性確保）。
    - src/kabusys/strategy/signal_generator.py
      - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
      - デフォルト重み・閾値を持ち、ユーザー重みは検証・正規化して合計 1.0 に再スケール。
      - Bear レジーム判定（ai_scores の regime_score 平均が負の場合）で BUY を抑制。
      - BUY（threshold 超）と SELL（ストップロスやスコア低下）を生成し signals テーブルへ日付単位で置換（トランザクション）。
      - SELL 優先ポリシー（SELL 銘柄は BUY から除外してランクを再付与）。
  - パッケージ公開:
    - src/kabusys/strategy/__init__.py で build_features / generate_signals を公開。
    - src/kabusys/research/__init__.py で研究用 API をまとめて公開。

Changed
- 初回リリースのため該当なし（設計・実装内容の集約）。

Fixed
- .env パースの堅牢化:
  - export プレフィックス、クォート内のエスケープ、インラインコメントの適切な扱いを実装して不正な行をスキップ。
- DuckDB 書き込みの原子性確保:
  - feature_engineering / signal_generator / jquants_client の save 系でトランザクションと ROLLBACK のフォールバックログを実装。

Security
- RSS パーシングに defusedxml を使用して XML Bomb 等を防御。
- ニュース収集で受信サイズ上限（10MB）、URL 正規化、追跡パラメータ除去、HTTP/HTTPS スキームの前提などを導入し SSRF・メモリDoS を軽減。
- J-Quants クライアントの HTTP エラー再試行は Retry-After を尊重（429 時）し、トークン自動リフレッシュは再帰を避ける設計。

Known limitations / TODO
- execution パッケージ（発注層）は初期状態では実装がない、または空のエントリ（将来的に発注 API 実装予定）。
- 一部戦略条件（トレーリングストップ、時間決済など）は positions テーブルに追加情報（peak_price / entry_date）を持たせる必要があり、未実装。
- news_collector 内の低レベルネットワーク/ホスト検証ロジックは設計注記を含むが、運用に合わせた評価が必要。
- research の一部関数は DuckDB のスキーマ（prices_daily, raw_financials, features, ai_scores, positions, signals 等）に依存するため、スキーマ準備が必須。

Notes
- DuckDB を使ったデータベース操作は SQL 実行を直接行うため、実行環境の DuckDB バージョンや SQL 方言に依存する可能性があります。README やスキーマ定義を参照してください。