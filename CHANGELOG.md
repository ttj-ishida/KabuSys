CHANGELOG
=========

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。

現在のバージョン
----------------

- 0.1.0 - 2026-03-20

0.1.0 - 2026-03-20
------------------

Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - 高頻度売買ではなく日本株の自動売買フレームワークの基盤を提供。
  - 以下の主要コンポーネントを実装:
    - kabusys.config
      - .env/.env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用フック）。
      - .env パーサの実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
      - Settings クラスでアプリ設定を提供（必須キー取得の検証、env/log_level の値検査、パス類は Path に変換）。
      - 環境変数の保護機構: .env の上書き時に OS 環境変数を保護する protected セットを利用。
      - 必須環境変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は ValueError を送出）。
    - kabusys.data.jquants_client
      - J-Quants API クライアント:
        - 固定間隔レートリミッタ（120 req/min）を実装。
        - 冪等的な DuckDB 保存関数（raw_prices/raw_financials/market_calendar）を提供（ON CONFLICT を使用）。
        - ページネーション対応の取得関数（fetch_*）。
        - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 の場合は Retry-After 優先。
        - 401 受信時はリフレッシュトークンから ID トークンを自動更新して 1 回リトライ。
        - 取得時刻 fetched_at を UTC ISO8601 で記録し、look-ahead bias のトレースを可能に。
        - 入力パースユーティリティ（_to_float/_to_int）で不正値を安全に扱う。
    - kabusys.data.news_collector
      - RSS ニュース収集モジュール:
        - RSS 取得、テキスト前処理、URL 正規化、記事 ID を SHA-256（先頭 32 文字）で生成して冪等性を担保。
        - defusedxml による XML パースで XML Bomb 等に対する防御。
        - 受信最大バイト数制限（10MB）や URL トラッキングパラメータ除去、クエリソート等の正規化。
        - SSRF 対策方針（スキーム制限やホスト検証の想定）。
        - バルク INSERT のチャンク処理でパフォーマンス配慮。
    - kabusys.research
      - 研究用途のファクター計算・解析モジュール（本番発注系 API にはアクセスしない設計）:
        - factor_research: calc_momentum / calc_volatility / calc_value
          - prices_daily / raw_financials を用いた各種ファクター（モメンタム、MA200乖離、ATR、出来高比率、PER/ROE 等）。
          - ウィンドウやデータ不足時の None 扱いを明確化（必要行数未満は None）。
        - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
          - 将来リターン（ホライズン指定可能）、Spearman IC（ランク相関）、要約統計量を標準ライブラリのみで実装。
          - rank() は同順位の平均ランクを返す（丸めによる ties を防ぐため round で正規化）。
        - research.__init__ で主要関数を公開。
    - kabusys.strategy
      - feature_engineering.build_features
        - research の生ファクターを取得して統合、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
        - 指定カラムを Z スコア正規化し ±3 でクリップ（外れ値抑制）。
        - features テーブルに日付単位で置換（DELETE → INSERT をトランザクションで実行し冪等性・原子性を確保）。
      - signal_generator.generate_signals
        - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントから final_score を計算。
        - デフォルト重み・閾値を実装（重みの補完／正規化ロジックあり、無効値はログで警告して無視）。
        - シグナル生成フロー: BUY（閾値超過）と SELL（ストップロス -8% / スコア低下）を生成。
        - Bear レジーム判定（ai_scores の regime_score 平均が負の場合。ただしサンプル数が 3 未満なら Bear としない）。
        - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）。
    - パッケージ初期化とエクスポート（kabusys/__init__.py、strategy/__init__.py、research/__init__.py）を整備。

Security
- news_collector: defusedxml を利用して XML 関連攻撃を防止。受信データ上限（10MB）によるメモリ DoS 対策。
- jquants_client: HTTP リトライ制御や 401 時の安全なトークン更新を実装。RateLimiter により API レート制限順守。
- config: .env 読み込み時に OS 環境変数を protected として上書きを防止（重要情報保護）。

Performance / Reliability
- DuckDB へのデータ保存はバルク executemany と ON CONFLICT を利用して効率的かつ冪等に実行。
- feature_engineering と signal_generator は日付単位で DELETE → INSERT をトランザクションで実行し、原子性を保証。
- news_collector はバルク INSERT のチャンクングサイズを導入し SQL 長制限やパラメータ数上限に配慮。
- J-Quants クライアントは最小インターバルを挟む固定間隔のスロットリングでリクエスト間隔を均す。

Notes / Known limitations
- 未実装の売却条件:
  - トレーリングストップ（直近最高値から -10%）と時間決済（保有 60 営業日超過）は positions テーブルに peak_price / entry_date が必要であり、現バージョンでは未実装。
- ai_scores による Bear 判定はサンプル数が少ない場合は保守的に動作（_BEAR_MIN_SAMPLES=3）。小サンプルだと判定を行わない。
- features / factor の一部はデータ不足時に None を返す設計（欠損値は中立 0.5 で補完してシグナル計算）。
- news_collector の SSRF / IP 判定は方針を示しているが、運用環境に応じた追加検証（DNS/TLS 等）が必要。
- get_id_token は settings.jquants_refresh_token を既定値として使用。CI/デプロイ時は環境変数の設定が必要。
- _to_int は "1.9" のような小数文字列を意図的に None にして誤切り捨てを避ける挙動。

Behavioral details / usage tips
- 自動 .env 読み込み順序: OS 環境変数 > .env.local > .env。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- Settings.env は "development" / "paper_trading" / "live" のいずれかのみ許容。LOG_LEVEL も標準レベルに制限。
- signal_generator の重みはユーザ指定で上書き可能。無効な値はスキップされ、合計が 1.0 でなければ再スケールされる。合計が 0 以下の場合はデフォルト重みにフォールバック。
- build_features および generate_signals は外部 API や execution 層に依存しない（研究/計算層と取引実行層を分離）。

Deprecated / Removed
- （初版のため該当なし）

開発者向け備考
- 研究モジュールは pandas 等の外部ライブラリに依存せず実装されているため、軽量・移植性が高い。しかし大規模データ解析では性能検討が必要。
- DuckDB のテーブルスキーマ（raw_prices, raw_financials, prices_daily, features, ai_scores, signals, positions, market_calendar 等）は想定されており、マイグレーションスクリプト等は別途準備する必要がある。

今後の予定（例）
- execution 層の実装（kabu API との発注連携、安全な注文管理）。
- ニュース記事から銘柄へのマッピング強化（NLU/キーワード照合）。
- 追加の売却ルール（トレーリングストップ、時間決済）の実装。
- 単体テストと統合テストの拡充（特にネットワーク周りと DB 操作のモック化）。

以上。