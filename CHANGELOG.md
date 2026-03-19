# Changelog

すべての注記は "Keep a Changelog" の形式に従い、重要な変更を記録します。  
このプロジェクトの初期バージョンは 0.1.0 です。

全般:
- リリースポリシー: 安定リリースは Semantic Versioning に準拠します（本リリースは v0.1.0）。
- 実装の説明や設計ノートは各モジュールの docstring に記載されています。

Unreleased
- なし

[0.1.0] - 2026-03-19
------------------------------------
Added
- パッケージ基盤
  - パッケージエントリポイントを提供（kabusys.__init__）。公開モジュール: data, strategy, execution, monitoring。
  - バージョン情報を設定: __version__ = "0.1.0"。

- 設定/環境変数管理（kabusys.config）
  - .env/.env.local 自動ロード機能を実装。プロジェクトルートを .git または pyproject.toml で探索して読み込むため、CWD に依存しない動作を実現。
  - .env ファイルの強力なパーサを実装（# コメント、export プレフィックス、シングル/ダブルクォート、エスケープ文字、インラインコメントの処理をサポート）。
  - .env の読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書き許可）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、主要設定にプロパティ経由でアクセス可能に（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - 設定値の検証: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/...）のバリデーションを実装。
  - データベースパス設定（DUCKDB_PATH, SQLITE_PATH）を Path 型で返却。

- データ取得 / 保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。日次株価、財務諸表、取引カレンダー等の取得機能を提供（ページネーション対応）。
  - レート制限対応: 固定間隔スロットリング（120 req/min）を _RateLimiter で実装。
  - 再試行ロジック: 指数バックオフ、最大 3 回、HTTP 408/429/5xx を対象。429 の場合は Retry-After ヘッダを尊重。
  - 認証トークン管理: リフレッシュトークンから ID トークンを取得する get_id_token、モジュールレベルのトークンキャッシュ、401 受信時の自動リフレッシュ（1 回のみ）を実装。
  - ページネーション対応関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）を提供。
  - DuckDB 保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT を使った冪等な保存を行い、fetched_at を UTC で記録。
  - 数値変換ユーティリティ _to_float / _to_int を追加し、入力の堅牢な取り扱いを実現。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集基盤を実装。デフォルト RSS ソースを設定（Yahoo Finance のビジネスカテゴリ等）。
  - XML パーサに defusedxml を使用して XML Bomb 等の脆弱性を緩和。
  - URL 正規化機能を実装（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
  - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）や SSRF を意識した入力制限等の防御的実装。
  - 記事 ID は URL 正規化後のハッシュにより冪等性を確保（設計ドキュメントに記載）。
  - raw_news / news_symbols 等への冪等保存を想定したバルク挿入の実装方針（チャンク化による SQL 長制限対策）。

- 研究用（kabusys.research）
  - 研究用ユーティリティ群を提供:
    - calc_momentum / calc_volatility / calc_value（kabusys.research.factor_research） — prices_daily / raw_financials を用いたファクター計算。
    - calc_forward_returns / calc_ic / factor_summary / rank（kabusys.research.feature_exploration） — 将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリ等を実装。
  - pandas 等の外部依存を避け、標準ライブラリ＋DuckDB SQL で実装。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features を実装。research モジュールの生ファクターを統合し、ユニバースフィルタ（最小価格、最小売買代金）を適用、Z スコア正規化（zscore_normalize を利用）および ±3 でのクリップを行い、features テーブルへ日付単位で置換（トランザクションで原子性保証）。
  - ルックアヘッドバイアスを防ぐため target_date 時点のデータのみを使用。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals を実装。features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出し、重み付け合算で final_score を算出。
  - デフォルトの重みと閾値（DEFAULT_WEIGHTS, DEFAULT_THRESHOLD）を提供。weights の検証・補完・再スケーリングを実装（未知キー・非数値は無視）。
  - Bear レジーム検知（ai_scores の regime_score 平均が負の場合、かつ十分なサンプル数がある場合）により BUY シグナルを抑制するロジックを実装。
  - エグジット（SELL）判定:
    - ストップロス（終値/avg_price - 1 <= -8%）を実装（優先度最優先）。
    - final_score が閾値未満になった場合の SELL（score_drop）。
    - トレーリングストップや時間決済は未実装だが設計に言及（positions テーブルに peak_price/entry_date が必要）。
  - signals テーブルへ日付単位置換（トランザクションで原子性保証）。保有銘柄に対する価格欠損時の処理や、features に存在しない保有銘柄を final_score=0 として扱う挙動を明確化。

Changed
- 初期リリースのため、従来の変更点は無し。

Fixed
- 初期リリースのため、既存バグ修正履歴は無し。

Security
- 外部データ取り込みにあたって以下の対策を実装／意識:
  - RSS パースに defusedxml を使用して XML 関連攻撃を緩和。
  - ニュース取得の受信サイズ上限（MAX_RESPONSE_BYTES）を適用しメモリ DoS を防止。
  - URL 正規化とトラッキングパラメータ除去を実装。HTTP/HTTPS スキーマの確認や SSRF を意識した入力検査を設計に明記。
  - J-Quants クライアントはレート制限・再試行・トークンリフレッシュを実装し、サービス拒否や認証失敗に対処。

Notes / Known limitations
- 一部の機能は設計メモで未実装（例: signal_generator のトレーリングストップ、時間決済）。
- news_collector の記事 ID の生成・ニュースと銘柄の紐付けロジックは設計方針を示しているが、実際の照合アルゴリズムやマッピングルールは追加実装が想定される。
- positions テーブルのスキーマ（peak_price, entry_date 等）や外部 execution 層との統合は別実装領域。現モジュール群は execution 層への直接依存を持たない設計。
- DuckDB スキーマ（tables の定義）はリポジトリ内別途定義されていることを前提。

作者注
- 各モジュールの docstring に設計方針・処理フロー・参考ドキュメントのセクション番号を明記しています。実運用にあたっては DB スキーマ、環境変数、外部 API の権限・レート制限を適切に設定してください。

--- 
（END）