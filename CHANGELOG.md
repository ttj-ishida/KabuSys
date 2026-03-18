Keep a Changelog 準拠 — 変更履歴

すべての変更は慣例に従いカテゴリ別に記載しています（Added / Changed / Fixed / Security 等）。
バージョン番号はパッケージ内の __version__ に合わせて作成しています。

Unreleased
----------
（なし）

[0.1.0] - 2026-03-18
--------------------
Added
- パッケージ初期リリース (kabusys 0.1.0)
  - Python パッケージの基礎構成を追加（src/kabusys/__init__.py、__version__ = "0.1.0"）。
- 設定管理
  - 環境変数・.env ファイルの自動読み込み機能を追加（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を自動読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env の行パースを厳密化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメント処理等）。
    - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live） / ログレベル等の設定アクセスを統一。
    - 必須環境変数未設定時には分かりやすい例外を発生。
- データ収集クライアント（J-Quants）
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
    - レート制限（固定間隔スロットリング、120 req/min）を実装。
    - リトライ（指数バックオフ、最大再試行回数）、429 の Retry-After を考慮。
    - 401 受信時にリフレッシュトークンで自動再取得して 1 回リトライする仕組み。
    - ページネーション処理対応（pagination_key）。
    - 取得データを DuckDB に冪等に保存するユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）。fetched_at（UTC）を付与して取得時刻を記録。
    - 型変換ユーティリティ（_to_float / _to_int）実装。
- ニュース収集
  - RSS ベースのニュース収集モジュールを実装（src/kabusys/data/news_collector.py）。
    - RSS 取得・XML パース（defusedxml で安全に処理）、gzip 解凍、最大受信サイズ制限（MAX_RESPONSE_BYTES）を実装。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）と記事 ID 生成（SHA-256 先頭32文字）。
    - SSRF 対策：URL スキーム検証、ホストのプライベート IP 判定、リダイレクト事前検査用ハンドラを実装。
    - テキスト前処理（URL 除去・空白正規化）と銘柄コード抽出（4桁数字、既知コードフィルタ）。
    - DuckDB への保存はトランザクションでチャンク挿入（INSERT ... RETURNING を用いて実際に挿入されたレコードを返す）。news_symbols のバルク保存ユーティリティも実装。
    - デフォルト RSS ソースとして Yahoo Finance のビジネスカテゴリを用意。
- 研究用（Research）機能
  - 特徴量探索モジュール（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定日から複数ホライズン（例: 1/5/21 営業日）先の将来リターンを DuckDB 上で一括算出。
    - calc_ic: スピアマンランク相関（IC）計算。ランクは同順位を平均ランクで処理し、十分なデータが無ければ None を返す。
    - factor_summary, rank: ファクターの基本統計（count/mean/std/min/max/median）とランク付けユーティリティ。
    - 実装方針として pandas 等に依存せず標準ライブラリ + duckdb で処理。
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200日移動平均乖離率）を DuckDB 上で算出。データ不足時は None。
    - calc_volatility: atr_20（20日 ATR）, atr_pct, avg_turnover, volume_ratio などボラティリティ/流動性指標を算出。true_range の NULL 伝播制御などを実装。
    - calc_value: raw_financials の直近財務データと当日の株価を組み合わせて PER/ROE を算出（EPS がゼロ/欠損なら PER は None）。
    - 各関数は prices_daily / raw_financials のみ参照し、本番 API にはアクセスしない設計。
  - research パッケージの __init__ で上記ユーティリティを再エクスポート（zscore_normalize は外部 data.stats から利用）。
- スキーマ初期化
  - DuckDB 用スキーマ定義の雛形を追加（src/kabusys/data/schema.py）。
    - raw_prices / raw_financials / raw_news / raw_executions を含む DDL（チェック制約・PRIMARY KEY 等）を用意。
    - DataLayer 構成（Raw / Processed / Feature / Execution）をドキュメント化。
- モジュール化とログ
  - 各モジュールで logging を使用し操作状況や警告を出力。例外時に詳細ログを残す実装。

Security
- ニュース収集における SSRF 対策を実装（スキーム制限、プライベートアドレス判定、リダイレクト検査）。
- XML パースに defusedxml を使用して XML 攻撃を緩和。
- .env 読み込みでファイル読み込みエラー時に warnings 発出（安全にフォールバック）。

Changed
- （初版のため変更履歴は特になし）

Fixed
- （初版のため修正履歴は特になし）

Notes / Design decisions
- Research モジュールは外部に副作用を持たない設計（DB の prices_daily/raw_financials のみ読み取り）。発注や実際の取引 API にはアクセスしない。
- J-Quants クライアントは取得時刻（fetched_at）を UTC で記録し、Look-ahead bias を監査可能にする方針。
- DuckDB への保存は冪等性を重視（ON CONFLICT ... DO UPDATE / DO NOTHING を活用）。
- 一部モジュール（strategy, execution）のパッケージ初期化は用意されているが、具象機能は今後実装予定。

開発者向け補足
- 環境依存の動作（.env 自動読み込み）をテストで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- news_collector._urlopen はテストで差し替え可能（モック用フックあり）。

お問い合わせや不明点があれば、どのモジュールについて詳しく記載するかを指定してください。追加でリリースノートの英語版や個別 API の仕様書も作成できます。