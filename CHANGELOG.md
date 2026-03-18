# Changelog

すべての重要な変更点をここに記録します。  
このファイルは「Keep a Changelog」およびセマンティックバージョニングに準拠しています。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- セキュリティ (Security)
- 非互換 (Removed / Breaking Changes)

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システム「KabuSys」の基本モジュール群を実装しました。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py: パッケージ定義とバージョン設定（__version__ = 0.1.0）。主要サブパッケージを __all__ で公開。

- 環境変数・設定管理
  - src/kabusys/config.py:
    - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索して判定）。
    - ロード優先順: OS 環境変数 > .env.local > .env。
    - 自動読み込みを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env パーサーを実装（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い等に対応）。
    - Settings クラスを実装し、J-Quants / kabu API / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベル等のプロパティを提供。必須環境変数未設定時には ValueError を送出。

- データ取得・保存（J-Quants）
  - src/kabusys/data/jquants_client.py:
    - J-Quants API クライアントを実装。主な機能:
      - API 呼び出しのページネーション対応（pagination_key）。
      - モジュールレベルの ID トークンキャッシュ（ページ間でトークン共有）。
      - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
      - リトライロジック（指数バックオフ、最大3回、408/429/5xx を対象）。429 の場合は Retry-After を尊重。
      - 401 応答時は自動的にリフレッシュトークンで ID トークンを再取得して 1 回リトライ。
      - JSON デコード失敗時やネットワークエラーの適切な例外処理。
    - データ取得関数:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）。
    - DuckDB への保存関数（冪等化）:
      - save_daily_quotes -> raw_prices テーブルへ ON CONFLICT DO UPDATE。
      - save_financial_statements -> raw_financials テーブルへ ON CONFLICT DO UPDATE。
      - save_market_calendar -> market_calendar テーブルへ ON CONFLICT DO UPDATE。
    - ユーティリティ: 安全な float/int 変換関数 _to_float / _to_int（"1.0" のような文字列を適切に扱い、小数部がある場合は None を返す挙動を採用）。

- ニュース収集（RSS）
  - src/kabusys/data/news_collector.py:
    - RSS フィードからの記事収集・前処理・DB 保存ワークフローを実装。
    - セキュリティと堅牢性:
      - defusedxml を使った XML パース（XML Bomb 等への対策）。
      - SSRF を防ぐための複数の検査: URL スキーム検証、リダイレクト先検査（カスタム RedirectHandler）、ホストがプライベート/ループバックでないことの確認。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と解凍後サイズチェック（gzip 対応、Gzip bomb 対策）。
      - ヘッダの Content-Length チェックおよび実際に MAX_RESPONSE_BYTES+1 バイト読み込んでの超過確認。
    - 実用機能:
      - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid 等）。
      - 記事IDは正規化 URL の SHA-256 の先頭32文字を採用し冪等性を確保。
      - テキスト前処理（URL 除去、空白正規化）。
      - DB 保存はチャンク INSERT(+ RETURNING) を行い、挿入された記事 ID を正確に取得。トランザクションでまとめて処理。
      - 銘柄コード抽出（4桁数字の検出と known_codes によるフィルタリング）、news_symbols への紐付けを一括挿入する内部ユーティリティ。
      - デフォルト RSS ソースとして Yahoo Finance のカテゴリフィードを設定。

- DuckDB スキーマ定義
  - src/kabusys/data/schema.py:
    - Raw / Processed / Feature / Execution レイヤーに分けるスキーマ設計に基づく DDL を実装。
    - raw_prices, raw_financials, raw_news, raw_executions などの CREATE TABLE 文を定義（各種型チェック、PRIMARY KEY、DEFAULT を含む定義を用意）。

- リサーチ / ファクター計算
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算: calc_forward_returns（単一クエリで複数ホライズン取得、リードウィンドウ利用）。
    - IC（Information Coefficient）計算: calc_ic（Spearman の ρ をランク計算から算出、データ不足時は None）。
    - ランク関数 rank（タイの平均ランク処理、丸めで浮動小数誤差を吸収）。
    - ファクター統計サマリー: factor_summary（count/mean/std/min/max/median）。
    - 設計上、標準ライブラリのみで実装し、DuckDB の prices_daily を参照。実際の発注等にはアクセスしないことを明示。
  - src/kabusys/research/factor_research.py:
    - Momentum, Volatility, Value 等の定量ファクター計算を実装:
      - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。ウィンドウ不足時は None を返す。
      - calc_volatility: ATR20（true range の平均）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。NULL 伝播を考慮した true_range の算出。
      - calc_value: raw_financials から target_date 以前の最新財務を JOIN して PER/ROE を算出（EPS 0 または NULL の場合は PER を None）。
    - 各関数は DuckDB 接続を受け取り、prices_daily / raw_financials のみを参照する設計。

- パッケージエクスポート（research）
  - src/kabusys/research/__init__.py: 主要なユーティリティ・計算関数を公開（calc_momentum 等と zscore_normalize のインポート）。

- プレースホルダ
  - src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py: パッケージプレースホルダを配置（将来の実装場所）。

### Security
- RSS フィード取得時の SSRF 対策を多数実装（スキーム検証、プライベートアドレス検査、リダイレクトハンドリング）。
- XML パースに defusedxml を利用し、XML 関連攻撃を軽減。
- J-Quants API クライアントでの認証トークン管理とリフレッシュの安全な実装により、認証周りのエラーからの自動回復を改善。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Breaking Changes
- （初回リリースにつき該当なし）

---

注意:
- この CHANGELOG は提供されたコードベースの内容から推測して作成した初期リリースの要約です。実際のコミット履歴や変更履歴がある場合は差分に基づき調整してください。
- 今後のリリースでは、各モジュールごとの追加・修正点をこの形式で記録してください。