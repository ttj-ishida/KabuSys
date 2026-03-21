Changelog
=========
すべての注目すべき変更点をこのファイルで管理します。フォーマットは Keep a Changelog に準拠します。

[0.1.0] - 2026-03-21
--------------------

Added
- 初回公開: kabusys パッケージ（バージョン 0.1.0）。
- パッケージ構成:
  - kabusys.config: 環境設定読み込み・管理（Settings クラス）。
    - .env / .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - .env 解析器: export 構文、シングル/ダブルクォート内のエスケープ、行内コメント処理に対応。
    - 必須環境変数取得用の _require ユーティリティ。
    - 環境値検証: KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の妥当性チェック。
    - パス設定（DUCKDB_PATH/SQLITE_PATH）の Path 返却（expanduser 対応）。
  - kabusys.data:
    - jquants_client: J-Quants API クライアント。
      - レート制御: 固定間隔スロットリングで 120 req/min を順守する RateLimiter 実装。
      - 再試行ロジック: 指数バックオフ（最大 3 回）、408/429/5xx 対象。429 の Retry-After ヘッダ尊重。
      - 401 の自動リフレッシュ: トークン期限切れ時に ID トークンを自動更新して 1 回だけリトライ。
      - モジュールレベルの ID トークンキャッシュ（ページネーション間で共有）。
      - ページネーション対応の fetch_* API（daily_quotes / financial_statements / market_calendar）。
      - DuckDB への保存関数（save_daily_quotes 等）: ON CONFLICT DO UPDATE による冪等保存。
      - 型変換ユーティルティ: _to_float / _to_int（安全な変換ルールを実装）。
    - news_collector: RSS ニュース収集モジュール（research/data pipeline 用）。
      - デフォルト RSS ソース（例: Yahoo Finance ビジネスカテゴリ）。
      - 記事 URL 正規化（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化、フラグメント削除）。
      - 受信サイズ上限（MAX_RESPONSE_BYTES=10MB）、バルク INSERT のチャンク処理。
      - XML／RSS パースに defusedxml を使用する想定（XML 攻撃対策）。
  - kabusys.research:
    - factor_research: calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials を参照して各種ファクターを計算。
      - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、相対ATR、出来高比率）、バリュー（PER/ROE）。
      - データ不足時に None を返すことで安全な欠損扱い。
    - feature_exploration: 将来リターン計算(calc_forward_returns)、IC（Spearman）計算(calc_ic)、統計サマリー(factor_summary)、ランク付け(rank)。
      - horizons のバリデーション、効率的な単一クエリ取得。
  - kabusys.strategy:
    - feature_engineering.build_features:
      - research 側で計算した raw factor をマージ・ユニバースフィルタ（最低株価/平均売買代金）適用・Zスコア正規化・±3 でクリップして features テーブルに日付単位で UPSERT（トランザクションで原子性保証）。
      - ルックアヘッドバイアス回避: target_date 時点のデータのみを使用。
    - signal_generator.generate_signals:
      - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を計算し、重み付き合算で final_score を算出。
      - Bear レジーム検知（ai_scores の regime_score 平均が負 → BUY 抑制、サンプル閾値あり）。
      - BUY/SELL シグナル生成（閾値、ストップロス条件、保有ポジションのエグジット条件）。signals テーブルへ日付単位で置換。
      - weights の外部入力を受け付け、検証・補完・再スケール処理を実装（不正値はスキップ）。
  - パッケージ公開 API: kabusys.__init__ にて __version__ と主要サブモジュール名を公開。

Changed
- 設計方針として、DB 書き込みはトランザクション + バルク挿入で原子性・効率を確保する実装になっている（features / signals の日付単位置換など）。
- 欠損値・異常値に対する防御的実装を徹底（math.isfinite チェック、None 補完、中立値 0.5 のデフォルト補完など）。

Fixed
- —（初回リリースのため過去のバグ修正履歴は無し）

Security
- news_collector では defusedxml を使用する想定で XML パースの脆弱性対策を行う方針を採用。
- URL 正規化でトラッキングパラメータを除去、受信スキームを限定することで SS R F やトラッキングの影響を軽減する設計（コードコメントに記載）。
- J-Quants API 実装で 401 リフレッシュ時の無限再帰を avoid（allow_refresh フラグ）し、安全にトークン更新を行う。

Notes
- execution / monitoring パッケージは __all__ に含まれているが、今回のコードベースでは具体的な実装（API 呼び出し・発注ロジック・監視機能）は含まれていない。これらは今後のリリースで追加予定。
- 一部のセキュリティ/健全性対策（SSRF 防止の具体的ソケット/IP 検査、news_collector の完全なダウンロード制御など）は設計コメントとして明示されており、実装は段階的に追加される想定。
- DuckDB スキーマ（tables: raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals など）はコードの期待に沿った形で事前作成されている前提。

Contributing
- バグ報告・機能提案は issue を作成してください。外部 API キーや機密情報は .env に設定して管理してください（.env.example を参照のこと）。

LICENSE
- リポジトリに含まれる LICENSE を参照してください。