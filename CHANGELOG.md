# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に従います。

- リリース日付はパッケージの __version__（0.1.0）に対応する最初の公開とみなしています。

## [0.1.0] - 2026-03-19

### 追加 (Added)
- 基本パッケージ構成を追加
  - パッケージ初期化: src/kabusys/__init__.py を追加し、バージョン `0.1.0` と公開サブパッケージ ("data", "strategy", "execution", "monitoring") を定義。

- 設定・環境変数管理
  - src/kabusys/config.py に Settings クラスを実装。J-Quants / kabu API / Slack / DB パスなど主要設定を環境変数経由で取得するユーティリティを提供。
  - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を探索）。優先順位は OS 環境 > .env.local > .env。
  - .env パーサーは export プレフィックス対応、クォート内のエスケープ、インラインコメント処理をサポート。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能。
  - 設定値のバリデーションを実装（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と、必須変数未指定時のエラー (`_require`)。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py を実装。
  - API 呼び出しに対する固定間隔レートリミッタ（120 req/min）を実装。
  - 再試行ロジック（指数バックオフ、最大3回）を実装し、408/429/5xx をリトライ対象に含める。
  - 401 Unauthorized 受信時にリフレッシュトークンで自動再取得を行う仕組みを実装（1回まで）。ID トークンのモジュールレベルキャッシュを導入しページネーション間で共有。
  - ページネーション対応の取得関数を実装: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
  - DuckDB への永続化用関数を実装（冪等化: ON CONFLICT DO UPDATE）: save_daily_quotes, save_financial_statements, save_market_calendar。
  - 型変換ヘルパー _to_float/_to_int を実装。文字列数値や空値への堅牢な扱いを提供。

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py を実装。
  - RSS フィード取得 (fetch_rss) と記事前処理 (preprocess_text)、URL 正規化（トラッキングパラメータ除去）、記事ID 生成（正規化 URL の SHA-256 の先頭 32 文字）を実装。
  - defusedxml を用いた安全な XML パース、gzip 圧縮対応、最大受信サイズ制限（10 MB）を導入し、XML Bomb やメモリ DoS を考慮。
  - SSRF 対策を導入: リダイレクト時の検査用ハンドラ、アクセス前のホストがプライベートアドレスかの判定、許可スキームの制約（http/https のみ）。
  - DB 保存のための関数を実装（トランザクションでバルク挿入、ON CONFLICT DO NOTHING、INSERT ... RETURNING を使用）: save_raw_news（挿入された記事ID を返す）、save_news_symbols、内部バルク保存 `_save_news_symbols_bulk`。
  - 銘柄コード抽出ユーティリティ extract_stock_codes（4桁数字を抽出し既知銘柄セットと照合）を実装。
  - 統合収集ジョブ run_news_collection を実装し、ソース毎のエラーハンドリングとシンボル紐付け処理を提供。
  - デフォルト RSS ソースとして Yahoo Finance ビジネスカテゴリを登録（DEFAULT_RSS_SOURCES）。

- リサーチ（ファクター／特徴量探索）
  - src/kabusys/research/factor_research.py を実装。
    - モメンタム: calc_momentum（1M/3M/6M リターン、200日移動平均乖離率）。
    - ボラティリティ・流動性: calc_volatility（20日 ATR、相対ATR、20日平均売買代金、出来高比）。
    - バリュー: calc_value（最新財務データと当日の株価から PER/ROE を算出）。
    - DuckDB の prices_daily / raw_financials テーブルを用いた SQL ベースの計算を採用。
  - src/kabusys/research/feature_exploration.py を実装。
    - 将来リターン計算: calc_forward_returns（複数ホライズンを1クエリで取得、ホライズンの妥当性チェック）。
    - IC（Information Coefficient）計算: calc_ic（Spearman の ρ をランクを使って算出、データ不足時は None を返す）。
    - ランキング変換: rank（同順位は平均ランク、丸めによる ties 検出漏れ対策で round を利用）。
    - ファクター統計サマリー: factor_summary（count/mean/std/min/max/median を計算）。
  - src/kabusys/research/__init__.py で主要関数をエクスポート（calc_momentum 等と zscore_normalize の統合）。

- DuckDB スキーマ初期化
  - src/kabusys/data/schema.py に DuckDB 用 DDL を追加（Raw Layer 例: raw_prices, raw_financials, raw_news, raw_executions 等）。各カラムに型・チェック制約・主キーを定義。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### セキュリティ (Security)
- ニュース収集時の SSRF 対策を複数レイヤーで実装:
  - リダイレクト先のスキーム・ホスト検証ハンドラ（_SSRFBlockRedirectHandler）。
  - ホストがプライベート / ループバック / リンクローカル / マルチキャストでないことを確認する関数 `_is_private_host`。
  - fetch_rss の入口でスキーム・ホスト検証を実施。
- XML パースに defusedxml を使用して XML 関連攻撃を軽減。
- RSS レスポンスサイズに上限を設け、gzip 解凍後も検査を行い Gzip bomb を抑止。

### 既知の制約 / 注意点 (Known issues / Notes)
- 外部分析用のリサーチモジュールは標準ライブラリのみで実装しているため、大規模データ処理に最適化された pandas 等の機能は利用していない。
- DuckDB テーブル定義は schema.py にあり、実行時に適切な初期化ロジックを呼び出す必要がある（この changelog の対象コードには初期化呼出しは含まれていない）。
- .env の自動ロードはプロジェクトルート検出に依存するため、配布後や特定の環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD` により無効化して明示的に設定を行うことを想定。

---

Initial release: 基本的なデータ取得・保存、ニュース収集、リサーチ（因子計算・特徴量探索）、設定管理のコア機能を提供します。今後は strategy / execution / monitoring 層の拡充、テストカバレッジの追加、API 呼び出し・DB 操作の監視機能を追加予定です。