# CHANGELOG

すべての重要な変更は Keep a Changelog のフォーマットに従って記載しています。  

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システム「KabuSys」の基本機能を実装・公開。

### Added
- パッケージ基盤
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。公開モジュール: data, strategy, execution, monitoring。
  - バージョン情報 __version__ = "0.1.0" を設定。

- 環境設定
  - 環境変数・設定管理モジュールを追加（src/kabusys/config.py）。
    - .env/.env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする機能。
    - 行パースで export 構文、クォート文字列、インラインコメントなどに対応する堅牢なパーサを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
    - Settings クラスを提供。J-Quants / kabu API / Slack / DB パス等のプロパティ（必須チェック・デフォルト値・入力検証を含む）。
    - KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL の検証ロジックを備える。

- データ取得 & 永続化（DuckDB）
  - J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）。
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（内部 RateLimiter）。
    - リトライ（指数バックオフ、最大3回）、429 の Retry-After ヘッダ優先、408/429/5xx を対象。
    - 401 を検知した場合の自動トークンリフレッシュ（1 回のみ）と ID トークンのモジュールレベルキャッシュ。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
    - DuckDB への保存関数 save_daily_quotes / save_financial_statements / save_market_calendar（ON CONFLICT を利用した冪等保存）。
    - 型変換ユーティリティ _to_float / _to_int を実装し、入力の堅牢な正規化を行う。

  - RSS ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
    - RSS フィード取得（gzip 対応）、XML パース（defusedxml を利用）による安全な処理。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時にスキームとホストを検査するカスタム RedirectHandler。
      - ホスト名→IP の DNS 解決を行いプライベート/ループバック/リンクローカル/マルチキャストを拒否。
    - レスポンスサイズ制限（最大 10 MB）と Gzip 展開後の再チェック（Gzip bomb 対策）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）、記事 ID を正規化 URL の SHA-256 先頭 32 文字で生成し冪等性を担保。
    - テキスト前処理（URL 除去、空白正規化）、銘柄コード（4 桁）抽出ユーティリティ。
    - DB 保存: save_raw_news（チャンク分割、INSERT ... RETURNING による新規挿入 ID の取得）および news_symbols 関連の一括保存ユーティリティ（トランザクション管理、チャンクサイズ制御）。

  - DuckDB スキーマ定義モジュールを追加（src/kabusys/data/schema.py）。
    - Raw レイヤー（raw_prices, raw_financials, raw_news, raw_executions など）の DDL を定義。
    - テーブル定義に PK / CHECK 制約 / fetched_at のデフォルト等を含め、後続処理の整合性・データ品質を考慮。

- 研究（Research）モジュール
  - 特徴量探索モジュール（src/kabusys/research/feature_exploration.py）。
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト 1,5,21 営業日）にわたる将来リターンを DuckDB の prices_daily テーブルに対して一括で計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。ties（同順位）の平均ランク処理を採用、十分なレコードがない場合は None を返す。
    - rank / factor_summary: ランク関数（同順位平均処理）および基本統計量（count/mean/std/min/max/median）集計。

  - ファクター計算モジュール（src/kabusys/research/factor_research.py）。
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日移動平均乖離）を計算。過去データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（平均 True Range）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率などを計算。true_range の NULL 伝播を考慮した実装。
    - calc_value: 最新の財務データ（raw_financials）と当日の株価を組み合わせて PER / ROE を算出（EPS が 0 または欠損時は None）。
    - 上記関数はいずれも DuckDB の prices_daily / raw_financials に対して SQL ウィンドウ関数を駆使して実行し、本番 API へのアクセスは行わない設計。

- 公開 API 統合（src/kabusys/research/__init__.py）
  - 研究系ユーティリティのエクスポートを実装（calc_momentum 等と zscore_normalize の再エクスポート）。

### Security
- RSS パーサに defusedxml を採用し XML 関連攻撃（XML Bomb 等）に対策。
- RSS フェッチ時に SSRF 対策（スキーム検証・プライベート IP 検出・リダイレクト検査）を実装。
- J-Quants API クライアントにおける認証トークンの自動リフレッシュは 1 回に制限し、無限再帰を抑止。
- DB 書き込みは ON CONFLICT（Upsert）やトランザクションで冪等性と整合性を担保。

### Performance & Reliability
- J-Quants クライアントのレートリミットをモジュールで管理し、API レート制限を遵守。
- ページネーション、チャンク挿入、INSERT ... RETURNING を用い DB 操作の効率化と正確な挿入確認を実現。
- RSS の読み取りは最大バイト数でメモリ DoS を防止。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Notes / Requirements
- 本リリースでは外部依存ライブラリとして duckdb、defusedxml を使用。
- research/strategy モジュールは DuckDB 上の prices_daily / raw_financials を前提としており、本番の発注 API にはアクセスしない設計（安全性の観点）。
- .env 自動読み込みはパッケージ配布後も __file__ を基点にプロジェクトルートを探索するため、CWD に依存しない。

---

今後の予定（参考）
- strategy / execution / monitoring モジュールの具体的な発注ロジック・モニタリング機能の実装。
- Feature layer / Execution layer のスキーマ拡張と ETL ジョブの充実。
- テストカバレッジ追加および CI 統合。