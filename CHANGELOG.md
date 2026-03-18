# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

なお、このリポジトリの初期公開バージョンは 0.1.0 です。本ファイルはソースコードから推測できる機能・設計上の要点を記載しています。

## [Unreleased]
- 開発中の変更点はここに記載します。

## [0.1.0] - 2026-03-18

### Added
- パッケージ基盤
  - kabusys パッケージの初期構成を追加。バージョンは `0.1.0`。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定読み込み (kabusys.config)
  - .env / .env.local を自動読み込みする仕組みを実装（プロジェクトルート検出は .git または pyproject.toml を参照）。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を用意。
  - .env パース処理を実装：コメント、export プレフィックス、クォート／エスケープの取り扱い、インラインコメント判定などに対応。
  - Settings クラスを提供し、J-Quants トークンやKabuステーションの設定、Slack、DBパス、実行環境（development/paper_trading/live）やログレベルなどの取得・バリデーションを行うプロパティ群を実装。
  - 必須環境変数未設定時は ValueError を送出する `_require` を実装。

- Data レイヤー (kabusys.data)
  - J-Quants API クライアント（data/jquants_client.py）
    - レート制限（120 req/min）を守る固定間隔スロットリング `_RateLimiter` を実装。
    - リトライ（指数バックオフ）対応、対象ステータスコード（408, 429, >=500）で再試行。
    - 401 Unauthorized 時は自動でリフレッシュトークンを使って ID トークンを更新して 1 回リトライ。
    - ページネーション対応（pagination_key を追跡）で fetch_daily_quotes / fetch_financial_statements を実装。
    - JPX マーケットカレンダー取得関数 fetch_market_calendar を実装。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を提供。冪等性を担保するため INSERT ... ON CONFLICT DO UPDATE を利用。
    - 型変換ユーティリティ `_to_float`, `_to_int` を実装（非数・空値の扱いや "1.0" のような float 文字列を厳密に扱う挙動を含む）。
    - id_token のモジュールレベルキャッシュと強制更新オプションを実装。

  - ニュース収集モジュール（data/news_collector.py）
    - RSS フィード取得と記事保存のワークフローを実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
    - セキュリティ対策:
      - defusedxml を利用した XML パース（XML Bomb 等の防御）。
      - SSRF 対策: リダイレクト検査用ハンドラ、接続前のホスト検査、ホスト名→IPの検査でプライベート/ループバック/リンクローカルを拒否。
      - URL スキーム検証（http/https のみ許可）。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後のサイズ検証（Gzip bomb 対策）。
      - トラッキングパラメータ（utm_* 等）除去、URL 正規化、SHA-256 ハッシュから記事ID を生成（先頭32文字）。
    - DB保存はチャンク分割とトランザクションで行い、INSERT ... RETURNING により実際に挿入された件数を返す実装。
    - 記事から日本株4桁銘柄コードを抽出するユーティリティ extract_stock_codes を提供（既知銘柄セットでフィルタ、重複除去）。

  - スキーマ定義（data/schema.py）
    - DuckDB 用の基本スキーマ定義（Raw Layer）を追加: raw_prices, raw_financials, raw_news などの CREATE TABLE DDL を実装。
    - 実行履歴用テーブル raw_executions のスキーマ開始（途中まで記載）。

- Research レイヤー (kabusys.research)
  - 特徴量探索（research/feature_exploration.py）
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、単一クエリで取得、結果は list[dict]）。
    - Spearman ランク相関（Information Coefficient）計算 calc_ic（結合、None/非有限値除外、最小サンプル数判定）。
    - ランク変換ユーティリティ rank（同順位は平均ランク、丸めで ties 検出精度向上）。
    - factor_summary による基本統計量（count, mean, std, min, max, median）を提供。
    - 標準ライブラリのみで実装し、DuckDB の prices_daily テーブルのみ参照する設計方針を明記。
  - ファクター計算（research/factor_research.py）
    - Momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離）を calc_momentum で計算。
    - Volatility/Liquidity: 20日 ATR, 相対ATR, 20日平均売買代金, 出来高比率を calc_volatility で計算（true_range の NULL 伝播制御を考慮）。
    - Value: raw_financials と当日の株価を組み合わせて PER, ROE を calc_value で計算（report_date <= target_date の最新財務データを選択）。
    - 各関数は prices_daily / raw_financials のみ参照し、本番発注等の外部サイドエフェクトを持たない設計。

  - research パッケージ初期公開 (research/__init__.py)
    - calc_momentum, calc_volatility, calc_value, zscore_normalize（data.stats から）、calc_forward_returns, calc_ic, factor_summary, rank を __all__ に公開。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- ニュース収集で多数の防御策を導入:
  - defusedxml を用いた XML パース、安全なリダイレクトハンドリング、プライベートIP/ホスト拒否、受信サイズ制限、gzip 解凍後サイズ検証、URLスキーム検査などにより外部入力による攻撃リスクを低減。
- J-Quants クライアントは 401 時のトークン自動更新を行うが、更新処理で無限ループとならないよう allow_refresh フラグで制御。

### Notes / Implementation details
- 多くの関数は DuckDB 接続を引数に取り、ローカルデータベース（prices_daily, raw_financials, market_calendar など）を直接参照/更新する設計。
- research モジュールは標準ライブラリのみでの実装を目指しており、pandas 等の外部依存を避けている（軽量で移植性の高い実装）。
- save_* 関数群は冪等性（ON CONFLICT ... DO UPDATE / DO NOTHING）を意識して実装されているため、複数回実行しても重複データの上書き・スキップが行われる。
- .env パースはシェルライクな記法（export プレフィックスやクォート・エスケープ）を考慮して実装されているが、極端なケースでの互換性は要確認。

---

開発・利用中に気づいた点や追加したい要望があればお知らせください。リリースノートを拡張して追記します。