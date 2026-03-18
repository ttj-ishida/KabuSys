# Changelog

すべての重要な変更は「Keep a Changelog」規約に従って記載します。  
生成元: リポジトリのソースコードを解析して推測した初期リリース内容。

フォーマット:
- Added: 新機能
- Changed: 変更点（後方互換性に注意）
- Fixed: バグ修正
- Security: セキュリティ関連の改善

## [Unreleased]

（現時点の開発中の変更はありません。次回リリース時に項目を移動してください。）

## [0.1.0] - 2026-03-18

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージエントリポイント: src/kabusys/__init__.py による version と公開モジュール定義。
- 環境設定管理
  - src/kabusys/config.py
    - .env/.env.local の自動読み込み（プロジェクトルートの探索は .git または pyproject.toml に基づく）。
    - 高度な .env パーサ実装（コメント、クォート、export 付き行、インラインコメント処理などに対応）。
    - 環境変数の保護（既存 OS 環境変数を上書きしない挙動、.env.local の上書きサポート）。
    - settings オブジェクトにより J-Quants / kabu API / Slack / DB パス / 実行環境（development/paper_trading/live）などをプロパティとして公開。
    - 無効な KABUSYS_ENV / LOG_LEVEL に対する検証と例外投げ。
- データ取得クライアント
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアント実装（ID トークン取得、ページネーション対応の取得関数）。
    - RateLimiter によるレート制限（120 req/min）遵守。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx を対象、429 の Retry-After 尊重）。
    - 401 発生時の自動トークンリフレッシュ（1 回のみ）とリトライ。
    - ページネーションの安全な処理（pagination_key の重複チェック）。
    - DuckDB への冪等保存関数（raw_prices / raw_financials / market_calendar）を提供。ON CONFLICT DO UPDATE を利用して重複を排除。
    - 型変換ユーティリティ (_to_float / _to_int) による堅牢な数値変換。
- ニュース収集モジュール
  - src/kabusys/data/news_collector.py
    - RSS フィード取得 + 前処理 + DuckDB 保存ワークフローを実装。
    - URL 正規化とトラッキングパラメータ除去（_normalize_url / _make_article_id）。
    - 記事ID は正規化 URL の SHA-256（先頭32文字）で冪等性確保。
    - defusedxml を用いた XML パース（XML Bomb 等の緩和）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時の検証用ハンドラ（_SSRFBlockRedirectHandler）。
      - プライベート / ループバック / リンクローカルアドレスの検出とブロック。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後の追加チェック。
    - コンテンツの前処理（URL 除去、空白正規化）。
    - raw_news / news_symbols へのバルク挿入（チャンク処理、トランザクション、INSERT ... RETURNING を用いて実際に挿入された件数を正確に取得）。
    - テキストからの銘柄コード抽出ユーティリティ（4桁数値、既知コードセットとの照合）。
    - run_news_collection により複数ソースの独立処理・部分失敗耐性を実装。
- 研究（Research）モジュール
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、SQL で一括取得）。
    - 情報係数（IC）計算 calc_ic（スピアマンランク相関、欠損・非有限値対応、最小サンプル数チェック）。
    - ランキング関数 rank（同順位は平均ランク、丸めで浮動小数の ties 対策）。
    - ファクター統計 summary 関数 factor_summary（count/mean/std/min/max/median を算出）。
    - 設計方針として外部ライブラリに依存せず標準ライブラリのみで実装、DuckDB の prices_daily テーブルのみ参照。
  - src/kabusys/research/factor_research.py
    - モメンタム calc_momentum（1M/3M/6M リターン、MA200 乖離）。
    - ボラティリティ calc_volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比）。
    - バリュー calc_value（raw_financials の最新財務データと株価から PER/ROE を計算）。
    - 充分なデータが無い場合は None を返す方針。DuckDB の prices_daily / raw_financials のみ参照。
  - src/kabusys/research/__init__.py による主要関数のエクスポート（zscore_normalize を含む）。
- DuckDB スキーマ定義
  - src/kabusys/data/schema.py にて Raw レイヤ等のテーブル DDL を定義（raw_prices / raw_financials / raw_news / raw_executions 等の初期定義を含む）。
- API デザインとドキュメント的注記
  - 各モジュールに詳細な docstring と設計方針、注意点（Look-ahead bias 回避、外部 API へのアクセス禁止など）が記載。

Changed
- 初期リリースのため互換性変更は無し（このリリースでの設計方針と API を確定）。

Fixed
- 初回リリースにおける「実装上の堅牢化」事項（例: .env 読み込みのエラーハンドリングや .env ファイルオープン失敗時の警告、RSS gzip 解凍失敗時のフォールバックなど）を実装済み。

Security
- ニュース収集における SSRF 緩和（スキーム検証、リダイレクト先の事前検証、プライベート IP ブロック、defusedxml の使用）。
- 外部 API 呼び出しに対するレート制御とリトライ（J-Quants クライアント）、401 時の安全なトークンリフレッシュ。

Notes / Implementation decisions
- Research モジュールは外部ライブラリ（pandas 等）に依存しない実装を優先しているため、計算は SQL + 標準ライブラリで完結する。
- DuckDB 接続を明示的に受け取る設計（副作用を避け、テスト・再現性を向上）。
- DB 操作は可能な限り冪等に実装（ON CONFLICT、INSERT ... RETURNING を活用）。
- .env 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑止可能。

開発者向け補足
- 空のパッケージサブモジュールが存在: src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py（将来の拡張ポイント）。
- ログは各モジュールで logger.getLogger(__name__) を使用。運用時は settings.log_level に基づく設定を推奨。

以上。リリース内容に不明点や追記希望があれば、ソースコードの該当箇所を指定していただければ追記・修正します。