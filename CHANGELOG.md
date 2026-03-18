CHANGELOG
=========

すべての注目すべき変更を記録します。これは Keep a Changelog の形式に準拠しています。
セマンティックバージョニングを使用します。  

フォーマットの説明:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティに関する修正・強化
- Performance: パフォーマンス改善

0.1.0 - 初期リリース (初版)
--------------------------

リリース日: 未設定（初期リリース）

Added
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。
  - パッケージ公開 API を __all__ で定義（data, strategy, execution, monitoring）。
  - バージョン情報を __version__ = "0.1.0" に設定。

- 環境設定 / ロード
  - 環境変数・設定管理モジュールを追加（src/kabusys/config.py）。
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動検出して読み込み。
    - export KEY=val 等の書式やクォート/エスケープ、行内コメント処理に対応した .env パーサ実装。
    - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等の設定を安全に取得。
    - 必須項目未設定時に明示的に ValueError を発生させる _require() を実装。

- データ取得・永続化（J-Quants）
  - J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）。
    - 固定間隔（120 req/min）に基づく RateLimiter を実装しレート制限を遵守。
    - 再試行（指数バックオフ、最大3回）や 401 のトークン自動リフレッシュ、429 の Retry-After 優先処理を実装。
    - ページネーション対応の fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar を実装。
    - DuckDB への冪等保存関数 save_daily_quotes、save_financial_statements、save_market_calendar を実装（ON CONFLICT DO UPDATE を使用）。
    - レスポンスパースおよび型変換用ユーティリティ _to_float/_to_int を実装。
    - fetched_at に UTC ISO 時刻を記録して Look-ahead Bias をトレース可能に。

- ニュース収集
  - RSS ベースのニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
    - RSS フィード取得（fetch_rss）と記事前処理（URL 除去、空白正規化）、日時パースを実装。
    - defusedxml を利用した XML パース（XML Bomb 等への耐性）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）や gzip 解凍後のサイズチェックを導入。
    - リダイレクト先のスキーム / ホスト検査と SSRF ブロッキングハンドラを実装（_SSRFBlockRedirectHandler, _is_private_host）。
    - URL 正規化とトラッキングパラメータ除去、記事ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保。
    - raw_news へのバルク挿入（チャンク分割、トランザクション、INSERT ... RETURNING による挿入件数の正確取得）を実装（save_raw_news）。
    - 記事と銘柄コードの紐付け処理（extract_stock_codes, save_news_symbols, _save_news_symbols_bulk）を実装。銘柄抽出は既知コードセットでフィルタし重複排除。

- データベーススキーマ（DuckDB）
  - DuckDB 用スキーマ定義モジュールを追加（src/kabusys/data/schema.py）。
    - Raw Layer の DDL を実装（raw_prices、raw_financials、raw_news、raw_executions の定義を含む。raw_executions は途中までの定義を含む）。
    - 各列に対する制約（NOT NULL, CHECK, PRIMARY KEY）を定義し、基本的なデータ整合性を確保。

- 研究（Research）モジュール
  - ファクター計算・特徴量探索モジュールを追加（src/kabusys/research/*）。
    - factor_research.py:
      - calc_momentum: mom_1m/mom_3m/mom_6m、200日移動平均乖離率(ma200_dev) を計算。
      - calc_volatility: 20日 ATR（atr_20）、atr_pct、20日平均出来高/売買代金、volume_ratio を計算。
      - calc_value: raw_financials の最新財務データと株価を組み合わせて PER と ROE を計算（EPS 不在またはゼロは None）。
      - DuckDB の prices_daily / raw_financials テーブルのみ参照し外部 API 呼び出しを行わない設計。
    - feature_exploration.py:
      - calc_forward_returns: 指定日から各ホライズン（デフォルト 1,5,21 営業日）先の将来リターンを一括 SQL で計算。
      - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。小数丸めを考慮したランク処理と ties の扱いに対応。
      - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
      - rank: 同順位は平均ランクを用いるランク関数を実装。
    - research パッケージの __init__.py で主要なユーティリティ（calc_momentum 等、zscore_normalize の re-export）を公開。

Changed
- なし（初期リリースのため変更履歴はなし）。

Fixed
- なし（初期リリースのため修正履歴はなし）。

Security
- RSS 取得時およびリダイレクト検査に SSRF 対策を導入（スキーム検証、プライベートIP/ループバック/リンクローカルの拒否）。
- XML パースに defusedxml を使用し、XML 関連の脆弱性（XML Bomb 等）に対処。
- .env 読み込みはプロジェクトルート基準で実行し、外部（意図しないディレクトリ）での自動読み込みリスクを低減。自動ロードは環境変数で無効化可能。

Performance
- J-Quants クライアントで固定間隔のスロットリングを導入し、レート制限に従いつつ過剰な待機を避ける実装。
- ニュース保存でチャンク化バルク INSERT、トランザクションまとめを行い DB オーバーヘッドを低減。
- calc_forward_returns 等の計算は可能な限り単一 SQL でまとめて取得し Python 側の処理を最小化。

Notes / Design decisions
- research モジュールは外部依存（pandas など）を避け、標準ライブラリと DuckDB の SQL で完結するよう設計されています（軽量で再現性の高い解析を意図）。
- J-Quants クライアントは 401 時の自動トークンリフレッシュを行うが、無限再帰を避けるため get_id_token からの内部呼び出しには allow_refresh フラグを利用。
- DuckDB への保存処理は冪等性を重視し、PK に対する ON CONFLICT 戻し処理を行っています。
- news_collector は記事の一意性を URL 正規化 + SHA256 による ID で担保し、トラッキングパラメータ等の差分での重複挿入を防ぎます。

今後（予定）
- execution / strategy / monitoring パッケージの実装（現在はパッケージ空殻）。
- schema モジュール内での Execution Layer / Feature Layer の完全な DDL 定義と初期化ユーティリティ。
- 単体テスト・統合テストの追加と CI の整備。
- ドキュメント（DataSchema.md, StrategyModel.md 等）との整合性確認とリリースノート拡充。

お問い合わせ
- この CHANGELOG の内容や実装方針について質問があればお知らせください。