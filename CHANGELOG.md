# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。

現在のリリース方針:
- 重大変更は Breaking changes として明示します。
- 初回公開バージョンは 0.1.0 としてリリースしています。

## [Unreleased]
次回リリースに向けた変更はここに記載します。

## [0.1.0] - 2026-03-20
初回公開リリース — 基本的なデータ取得・保存、ファクター計算、特徴量生成、シグナル生成、環境設定などのコア機能を実装。

### Added
- パッケージ基礎
  - kabusys パッケージを追加。バージョン情報を src/kabusys/__init__.py にて `__version__ = "0.1.0"` として管理。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に定義。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート検出機能を実装（.git または pyproject.toml を探索）し、作業ディレクトリに依存しない自動ロードを実現。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - .env パーサーの強化:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応。
    - クォート外のインラインコメント判定ロジックを改善（直前がスペース/タブの場合にコメントとみなす）。
  - .env 読み込み時の上書き制御（override）と保護された OS 環境変数（protected）の取り扱いを実装。
  - 必須環境変数取得用の `_require` を提供（未設定時は ValueError を発生）。
  - Settings に J-Quants / kabu / Slack / DB パス / ログレベル / 環境（development, paper_trading, live）等のプロパティを定義。値検証（有効な env・log level のチェック）を実装。

- データ取得・保存 (src/kabusys/data/)
  - J-Quants API クライアント (jquants_client.py)
    - 固定間隔レートリミッタ実装（120 req/min 想定）。
    - HTTP リトライロジック（指数バックオフ、最大 3 回、ステータス 408/429/5xx を対象）。
    - 401 受信時の ID トークン自動リフレッシュ（1 回のみ）とモジュールレベルのトークンキャッシュ。
    - ページネーション対応の fetch_* 関数（daily quotes / financial statements / market calendar）。
    - DuckDB への保存用関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT（冪等）で更新するようにしている。
    - JSON→数値変換ユーティリティ `_to_float` / `_to_int` を実装し、文字列／欠損値・不正値を安全に処理。
  - ニュース収集モジュール (news_collector.py)
    - RSS フィード収集ロジック、記事正規化、raw_news への冪等保存の下地を実装。
    - デフォルト RSS ソースを定義（例: Yahoo Finance）。
    - セキュリティ対策: defusedxml を利用した XML 解析（XML Bomb 等の防御）、受信サイズ制限（最大 10 MB）、HTTP スキーム検証など。
    - URL 正規化機能（トラッキングパラメータの除去、スキーム/ホスト小文字化、フラグメント除去、パラメータソート）。
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を確保。
    - 大量挿入対策としてチャンク化してバルク INSERT を行う設計。

- リサーチ（research）モジュール (src/kabusys/research/)
  - ファクター計算・分析ツールを実装:
    - factor_research.py: calc_momentum, calc_volatility, calc_value — DuckDB の prices_daily / raw_financials を用いたファクター計算。
    - feature_exploration.py: calc_forward_returns（将来リターン計算）、calc_ic（Spearman ランク相関による IC 計算）、factor_summary（基本統計量）、rank（同順位は平均ランクにするランク付け）。
  - 基本方針として外部ライブラリ（pandas 等）に依存せず、DuckDB SQL + 標準ライブラリで完結する実装。

- 戦略（strategy）モジュール (src/kabusys/strategy/)
  - feature_engineering.py
    - 研究環境で算出した生ファクターを統合・正規化して features テーブルへ保存する build_features(conn, target_date) を実装。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（外部ユーティリティ zscore_normalize を利用）し ±3 でクリップ。
    - 日付単位での置換（DELETE + INSERT トランザクション）により冪等性と原子性を担保。
  - signal_generator.py
    - features と ai_scores を統合して最終スコア（final_score）を算出し、BUY / SELL シグナルを生成する generate_signals(conn, target_date, ...) を実装。
    - デフォルト重み・閾値（threshold=0.60）を実装。外部から渡された重みの検証とスケーリング処理を追加。
    - コンポーネントスコア: momentum, value, volatility, liquidity, news を算出（シグモイド変換・欠損は中立値 0.5 補完）。
    - Bear レジーム（AI レジームスコアの平均が負かどうか）判定により BUY を抑制するロジックを実装。
    - SELL 条件（ストップロス -8% / final_score の閾値割れ）を実装。SELL を優先して BUY から除外するポリシー。
    - signals テーブルへの日付単位置換（トランザクション＋バルク挿入）で冪等性を担保。

- パッケージエクスポート
  - strategy, research モジュールの公開 API を __init__ でまとめてエクスポート。

### Changed
- なし（初回リリースのため過去バージョンからの変更は無し）。

### Fixed
- なし（初回リリース）。ただし以下の設計上の注意点・改善点を反映済み:
  - .env パーサーや数値変換での実運用で想定される欠損/文字列バリエーションに対処する実装改善を行ったため、運用上のエラー発生リスクを低減。

### Security
- news_collector で defusedxml を採用し、XML パーサーに対する脆弱性（XML Bomb 等）に対策。
- ニュース取得時の受信サイズ上限を設け、メモリ DoS を軽減。
- J-Quants クライアントは認証トークンの自動リフレッシュを行うが、無限再帰を防ぐため allow_refresh フラグで制御。

### Notes / Migration / Compatibility
- Settings.env の値は "development", "paper_trading", "live" のいずれかに制限されており、不正な値を設定すると ValueError が発生します。CI や運用スクリプトで env 値を設定する際は注意してください。
- デフォルトの DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  いずれも環境変数（DUCKDB_PATH / SQLITE_PATH）で上書き可能。
- J-Quants API の利用には環境変数 `JQUANTS_REFRESH_TOKEN` が必須です。
- kabu ステーション関連の API パスワードは `KABU_API_PASSWORD` を必須としているため、実行環境にて設定してください。
- news_collector の記事 ID は正規化 URL に基づくハッシュを用いるため、URL 正規化ルールに依存して ID が決まります。既存のストアと連携する場合は互換性を確認してください。

---

開発・運用上の追加情報や既知の制限があれば、次回以降のリリースノートに追記します。