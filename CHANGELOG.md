# Changelog

すべての重要な変更点は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースの現状（初期リリース相当）から推測して作成しています。

全般
- バージョンポリシー: セマンティックバージョニングに準拠（パッケージの __version__ は 0.1.0）。

## [0.1.0] - 2026-03-18 (推定)
初期リリース（コードベースから推測）。以下の主要機能群と設計方針が含まれます。

### Added
- パッケージ基盤
  - kabusys パッケージの初期構成。公開 API として data, strategy, execution, monitoring を __all__ に定義。
  - __version__ = "0.1.0" を設定。

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動ロード: プロジェクトルート（.git または pyproject.toml）を基に .env / .env.local をプロセス起動時に自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォート、エスケープ、行内コメント処理を考慮したパースロジックを実装。
  - 環境変数取得ヘルパ: _require により必須変数が未設定時に明示的エラーを出力。
  - Settings によるプロパティ化された設定:
    - J-Quants / kabuステーション / Slack / DB パス等の取得メソッドを提供。
    - env と log_level の検証（許容値チェック）と is_live / is_paper / is_dev のブール判定。

- データ取得・保存 (kabusys.data)
  - J-Quants クライアント (jquants_client)
    - API 呼び出しユーティリティを実装（HTTP リクエスト、JSON パース）。
    - レート制限 (120 req/min) を固定間隔スロットリングで制御する _RateLimiter を実装。
    - リトライロジック（指数バックオフ、最大 3 回）と 408/429/5xx に対する再試行。
    - 401 を受けた場合にリフレッシュトークンで id_token を自動更新して 1 回リトライする仕組みを実装。
    - ページネーションサポートを備えた fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を追加。
    - DuckDB への冪等保存関数を追加:
      - save_daily_quotes: raw_prices に ON CONFLICT DO UPDATE で保存（fetched_at を記録）。
      - save_financial_statements: raw_financials に同様に保存。
      - save_market_calendar: market_calendar に同様に保存（取引日/半日/SQ フラグを解釈して保存）。
    - 型変換ユーティリティ _to_float / _to_int を提供（不正値は None）。

  - ニュース収集 (news_collector)
    - RSS フィードから記事を収集し raw_news に保存するフローを実装。
    - セキュリティ対策:
      - defusedxml による XML パース（XML BOM 攻撃対策）。
      - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト先の事前検証、プライベート IP 判定（DNS の A/AAAA 解決を行いプライベート/ループバック/リンクローカルを拒否）。
      - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
      - URL 正規化とトラッキングパラメータ削除（utm_*, fbclid 等）。
    - 記事 ID は URL 正規化後の SHA-256（先頭32文字）で生成して冪等性を確保。
    - fetch_rss: RSS をパースして記事リストを返す。失敗の際はログ出力と空リスト返却の方針。
    - DB 保存:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING と INSERT ... RETURNING を用い、新規挿入 ID のリストを返す。チャンク挿入とトランザクション制御を実装。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付け（news_symbols）をまとめて安全に保存。
    - 銘柄コード抽出ユーティリティ extract_stock_codes（4桁数字、known_codes によるフィルタ・重複排除）。
    - 高レベル統合 run_news_collection: 複数ソースを順次処理し、各ソースの成功数を返す。ソース単位でのエラーハンドリングに対応。

  - DuckDB スキーマ定義 (data.schema)
    - Raw Layer の DDL を追加（raw_prices, raw_financials, raw_news 等の CREATE TABLE 文を定義）。
    - 各テーブルに制約（PRIMARY KEY / CHECK / NOT NULL / 型）を設け、データ整合性を重視。

- リサーチ / ファクター計算 (kabusys.research)
  - feature_exploration モジュール:
    - calc_forward_returns: 指定日から各ホライズン（デフォルト [1,5,21]）の将来リターンを DuckDB の prices_daily テーブルから一括取得して計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（ties 平均ランク処理・有効レコードが3未満は None）。
    - rank, factor_summary: ランク変換（同順位は平均ランク、丸め処理で数値誤差対策）と各ファクター列の基本統計量（count/mean/std/min/max/median）。
    - 設計方針: 標準ライブラリのみで実装し、DuckDB の prices_daily テーブルのみ参照。本番 API にはアクセスしない。
  - factor_research モジュール:
    - calc_momentum: mom_1m/mom_3m/mom_6m と 200日移動平均乖離率(ma200_dev) を計算。窓内データ不足時は None を返す。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金(avg_turnover)、出来高比(volume_ratio) を計算。true_range の NULL 伝播を制御して正確にカウント。
    - calc_value: raw_financials から直近財務データを取得し PER（EPS が 0 または欠損なら None）と ROE を計算。price と財務の結合を実行。
    - 定数やスキャン範囲の設計（安全マージンとして calendar day のバッファを採用）を明示。

- モジュールエクスポート
  - kabusys.research.__init__ で主要関数（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）を __all__ に追加。

### Changed
- （初期リリースのため該当なし。設計上の決定点を README 等に反映予定）

### Fixed
- （初期リリースのため該当なし）

### Security
- ニュース収集モジュールに SSRF と XML インジェクション対策を導入（_SSRFBlockRedirectHandler, defusedxml）。
- RSS レスポンスサイズ上限と gzip 解凍後の再チェックを実装し、DoS/Gzip-bomb の緩和を図る。
- J-Quants クライアントはトークンリフレッシュ時の無限再帰を回避する設計（allow_refresh フラグ）。

### Performance
- DuckDB へのバルク挿入はチャンク化してトランザクションでまとめ、オーバーヘッドを低減。
- calc_forward_returns などは複数ホライズンを1クエリで取得することでクエリ回数を削減。
- API レート制御は最小間隔スロットリング方式で簡潔に実装。

### Notes / Design Decisions
- Research モジュールは外部ライブラリ（pandas 等）に依存しない純粋 Python 実装を意図しているため、軽量でテストしやすい反面、大規模データでの最適化（ベクトル化等）は今後の課題。
- DuckDB を中心としたローカル分析パイプラインを想定。保存関数は冪等性を重視して ON CONFLICT を使用している。
- 環境変数の自動読み込みはプロジェクトルート判定に基づくため、パッケージ配布後も CWD に依存しない動作を目指すが、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

### Breaking Changes
- （初期リリースのため該当なし）

データ不足や外部依存（J-Quants、RSS）に起因する例外は各モジュールでログ出力や例外伝播の方針が異なります。運用時はログレベルや Settings の設定（KABUSYS_ENV / LOG_LEVEL 等）を適切に構成してください。