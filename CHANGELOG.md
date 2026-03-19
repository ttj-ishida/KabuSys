# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
今回のリリースはコードベースから推測した初期リリースの内容です。

全般的な方針：
- DuckDB をデータ層に採用し、SQL + Python でファクター計算・シグナル生成を実装
- 冪等性を重視（テーブル単位の日付置換、ON CONFLICT/DO UPDATE、INSERT DO NOTHING など）
- ルックアヘッドバイアス防止（target_date 時点のデータのみを参照、fetched_at の記録等）
- 本番の発注層には依存しない（strategy 層は signals テーブルへ書き込むのみ）
- セキュリティ・堅牢性に配慮（XML 脆弱性対策、URL 正規化・SSRF 対策、入力検証等）

## [Unreleased]
- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-19

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を定義（src/kabusys/__init__.py）。
  - エクスポート: data, strategy, execution, monitoring を __all__ に追加。

- 設定管理
  - 環境変数管理モジュールを追加（src/kabusys/config.py）。
    - .env/.env.local を自動ロード（プロジェクトルートは .git または pyproject.toml を探索して判定）。
    - export KEY=val 形式、クォートやエスケープ、インラインコメントの扱いに対応したパーサ実装。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 必須変数取得時の検証（_require）と Settings クラスによるプロパティアクセスを提供。
    - 設定のバリデーション: KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL の検証。
    - デフォルトパス: duckdb / sqlite のデフォルトパスを設定。

- データ取得/保存（J-Quants 統合）
  - J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）。
    - レート制限（120 req/min）を固定間隔スロットリングで遵守する RateLimiter 実装。
    - リトライポリシー: 指数バックオフ、最大 3 回、408/429/5xx に対応。
    - 401 時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ。
    - ページネーション対応（pagination_key を使ったループ）。
    - 保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を追加し、DuckDB へ冪等保存（ON CONFLICT DO UPDATE）を実装。
    - 型変換ユーティリティ（_to_float / _to_int）による堅牢な入力処理。
    - fetched_at を UTC ISO フォーマットで記録し、データ取得タイミングを追跡可能に。

- ニュース収集
  - RSS ベースのニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）を実装。
    - 記事 ID を正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性確保。
    - defusedxml を用いた XML 脆弱性対策（XML Bomb などの緩和）。
    - HTTP レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を軽減。
    - SSRF 対策やトラッキングパラメータ除去など、セキュリティに配慮した前処理を実装。
    - バルク INSERT のチャンク処理で SQL 長やパラメータ数を抑制。

- 研究（research）モジュール
  - ファクター計算群を提供（src/kabusys/research/factor_research.py）。
    - モメンタム（1/3/6ヶ月）、MA200 乖離、ATR（20日）、avg_turnover、volume_ratio、PER/ROE の計算を実装。
    - データ不足チェック（例: MA200 のデータが 200 行未満なら None）を実装。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）。
    - 将来リターン計算（複数ホライズンの fwd_1d / fwd_5d / fwd_21d 等）。
    - IC（Spearman の ρ）計算、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）。
    - 外部依存なし（pandas 等を使わず標準ライブラリのみ）で実装。
  - research パッケージの public API を __init__.py で整備。

- 戦略（strategy）モジュール
  - 特徴量作成モジュール（src/kabusys/strategy/feature_engineering.py）。
    - research で計算した raw factors をマージし、ユニバースフィルタ（最低株価 / 平均売買代金）を適用。
    - 指定列を Z スコア正規化（zscore_normalize 呼び出し）し ±3 でクリップ。
    - features テーブルへ日付単位で置換（BEGIN/DELETE/INSERT/COMMIT を使い原子性を担保）。
  - シグナル生成モジュール（src/kabusys/strategy/signal_generator.py）。
    - features と ai_scores を統合して各種コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - final_score を重み付き和で計算。デフォルト重みと閾値を実装（デフォルト閾値 0.60）。
    - Bear レジーム判定（AI の regime_score 平均が負の場合に BUY 抑制）を実装。
    - 保有ポジションのエグジット判定（ストップロス -8% / スコア低下）を実装し SELL シグナルを生成。
    - signals テーブルへ日付単位で置換（買い・売りを分けて挿入）。
    - ユーザー指定 weights の検証・フォールバック・再スケーリング処理を実装。
  - strategy パッケージ __init__ で build_features / generate_signals を公開。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- news_collector で defusedxml を利用し XML 攻撃を緩和。
- ニュースの URL 正規化・トラッキングパラメータ除去・スキーム検証等により SSRF やトラッキングの影響を低減。
- J-Quants クライアントでトークン取扱い・自動リフレッシュを実装し、401 のハンドリング時の再帰を防止（allow_refresh フラグ）。

### Known issues / Not implemented
- signal_generator にて、以下の SELL 条件はまだ未実装（コメントで言及）:
  - トレーリングストップ（peak_price / entry_date が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
- news_collector の実装は URL 正規化や XML パース周りのユーティリティまで示されているが、RSS フィード取得 → DB 紐付けの完全なワークフローは今後の実装の余地あり（コード断片からの推測）。
- 一部モジュールは外部サービスに依存（J-Quants）するため、API キーやネットワーク状況によって挙動が変わる点に注意。

### BREAKING CHANGES
- なし（初回リリース）

---

注: 上記は提示されたソースコードのコメント・実装から推測して作成した CHANGELOG です。実際のリリースノートとして使用する場合は、実際のコミット履歴や公開日、著者情報に基づいて調整してください。