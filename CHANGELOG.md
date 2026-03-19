# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
頻繁な参照のため、主要な追加機能・設計指針・セキュリティ対策を中心に記載しています。コードベースはバージョン情報により初期リリースとして扱われます（kabusys.__version__ = "0.1.0"）。

## [Unreleased]
- （現時点では未リリースの変更はありません）

## [0.1.0] - 初期リリース
初回公開リリース。日本株自動売買システムの基本的なデータ取得・保存、研究用特徴量計算、環境設定機構、およびニュース収集の基盤機能を実装。

### 追加 (Added)
- パッケージ初期化
  - src/kabusys/__init__.py によりパッケージを定義（version = 0.1.0、公開モジュール一覧 __all__ を設定）。

- 環境設定読み込み・管理 (src/kabusys/config.py)
  - .env / .env.local からの自動読み込み（OS 環境変数を優先、.env.local は上書き）。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）により CWD に依存しない自動ロードを実現。
  - .env ファイルの行解析で export プレフィックス・引用符・インラインコメント等に対応。
  - 環境変数保護（protected set）を考慮した上書き挙動を提供。
  - 必須環境変数取得ヘルパ（_require）と Settings クラスを実装。主要設定:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live 検証）
    - LOG_LEVEL（DEBUG/INFO/... の検証）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - Raw レイヤー等のテーブルDDLを定義（raw_prices, raw_financials, raw_news, raw_executions 等の骨格を含む）。
  - データ型・制約（CHECK/PRIMARY KEY）を含む定義でデータ整合性を担保。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 株価日足、財務データ、マーケットカレンダー取得のエンドポイント実装（ページネーション対応）。
  - レート制限対策: 固定間隔スロットリング（120 req/min）を実装する内部 RateLimiter。
  - リトライロジック: 指数バックオフ、最大 3 回、ネットワーク/一部 HTTP ステータス(408/429/5xx) に対応。
  - 401 (Unauthorized) 受信時は自動で id_token をリフレッシュして 1 回リトライ。
  - id_token のモジュールレベルキャッシュ（ページネーション間で共有）。
  - JSON デコード失敗やネットワーク例外に対するエラーハンドリングとログ出力。
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE による保存
    - save_financial_statements: raw_financials テーブルへ冪等保存
    - save_market_calendar: market_calendar テーブルへ冪等保存
  - 型変換ユーティリティ: _to_float / _to_int（不正値・空文字は None、"1.0" のような表現への慎重な処理）

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得 → 前処理 → raw_news への冪等保存フローを実装。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等の防御）。
    - SSRF 対策: リダイレクト先のスキーム検証・ホストがプライベート/ループバックでないかを検査。_SSRFBlockRedirectHandler と _is_private_host を提供。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）・gzip 解凍後サイズ検査（Gzip bomb 対策）。
  - 記事ID の冪等生成: 正規化 URL の SHA-256（先頭32文字）を使用。
  - URL 正規化: トラッキングパラメータ（utm_*, fbclid 等）除去、クエリソート、フラグメント削除。
  - テキスト前処理（URL 除去・空白正規化）。
  - raw_news へのバルク挿入（チャンク化）と INSERT ... RETURNING を用いた挿入済みIDの取得（重複はスキップ）。
  - news_symbols への紐付け保存（チャンク挿入・トランザクション管理・ON CONFLICT DO NOTHING）。
  - 銘柄コード抽出ユーティリティ: 正規表現で 4 桁数値を抽出し known_codes でフィルタ（重複除去）。

- 研究用モジュール (src/kabusys/research/)
  - feature_exploration (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: DuckDB の prices_daily を参照し、指定日から各ホライズン先のリターンを一括で取得（LEAD を利用）。horizons 引数検証（正の整数かつ <=252）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。データ不足（有効ペア < 3）時は None を返す。ties は平均ランクで扱う。
    - rank: 値リストを平均ランクに変換（round(v,12) による丸めで ties 検出を安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算（None と非有限値を除外）。
    - 設計方針: pandas 等の外部依存を避け、標準ライブラリのみで実装。
  - factor_research (src/kabusys/research/factor_research.py)
    - calc_momentum: mom_1m/mom_3m/mom_6m と 200 日移動平均乖離 ma200_dev を計算。必要行数が不足する場合は None。
    - calc_volatility: 20 日 ATR（true_range の平均）、atr_pct（ATR/close）、20 日平均売買代金 avg_turnover、volume_ratio（当日出来高/20日平均）を計算。true_range は high/low/prev_close のいずれかが NULL なら NULL として厳密に扱う。
    - calc_value: raw_financials から target_date 以前の最新財務データを取得し、PER（close / EPS）および ROE を計算（EPS が 0 または欠損時は None）。
    - DuckDB のウィンドウ関数（LAG/AVG/COUNT/ROW_NUMBER）を活用した高効率な実装。

- パッケージ公開（src/kabusys/research/__init__.py）
  - 研究用 API の公開: calc_momentum, calc_volatility, calc_value, zscore_normalize（別モジュール参照）, calc_forward_returns, calc_ic, factor_summary, rank

### 変更 (Changed)
- （初期リリースのため既存機能の変更点はありません）

### 修正 (Fixed)
- （初期リリースのため修正履歴はありません）

### 非推奨 (Deprecated)
- （該当なし）

### 削除 (Removed)
- （該当なし）

### セキュリティ (Security)
- ニュース収集における複数の防御導入:
  - defusedxml による安全な XML パース
  - SSRF 対策（リダイレクト検査・プライベートアドレス拒否）
  - レスポンスサイズ上限と Gzip 解凍後の検査（DoS 対策）
- J-Quants クライアントの認証・リトライ周りにおいて、401 リフレッシュとトークンキャッシュ設計により不正トークンの再利用による障害を低減。

### 既知の制約 / 注意点
- research モジュールは pandas などに依存しない設計のため、非常に大規模データでの最適化は今後の課題。
- calc_forward_returns のホライズンは営業日ベースの連続レコード数を想定しており、カレンダー日と混同しないこと。
- save_* 系は DuckDB のテーブルスキーマ（PRIMARY KEY, 列名）に依存するため、スキーマ変更時は保存ロジックの更新が必要。
- news_collector の URL 正規化は既知トラッキングパラメータのプレフィックスに基づく除去を行うが、未列挙パラメータが残る可能性がある。
- 一部モジュール（execution, strategy）のパッケージ初期化は存在するが、具体的なロジックは未実装（骨組みのみ）。

---

今後の予定（例）
- strategy / execution の実装（発注ロジック、ポジション管理、kabuステーション API 統合）
- monitoring / Slack 通知の統合（settings で定義した Slack 設定を利用）
- ベンチマーク・ユニットテスト充実化、CI ワークフロー追加

（完）