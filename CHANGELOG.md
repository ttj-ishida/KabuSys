# Changelog

すべての変更は「Keep a Changelog」形式に従います。  
フォーマット: https://keepachangelog.com/ja/

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-18
初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主な追加点は以下の通りです。

### 追加
- パッケージ基盤
  - src/kabusys/__init__.py
    - パッケージのバージョン（0.1.0）と公開サブパッケージを定義。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env のパース実装（export 句、クォート、インラインコメント対応）。
    - .env 読み込みの優先順位: OS環境変数 > .env.local > .env。自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 必須環境変数取得ヘルパ（_require）と Settings クラスを提供（J-Quants トークン、kabu API、Slack、DBパス、実行環境判定、ログレベル検証等）。
    - KABUSYS_ENV と LOG_LEVEL の値検証ロジック。

- データ取得・永続化（J-Quants）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装。
    - RateLimiter によるレート制限（120 req/min）の実装。
    - リトライロジック（指数バックオフ、最大3回、HTTP 408/429/5xx 等を対象）。
    - 401 受信時の自動トークンリフレッシュ（1回のみリフレッシュして再試行）。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
    - DuckDB へ冪等的に保存する save_* 関数（ON CONFLICT DO UPDATE）を実装。
    - 型変換ユーティリティ (_to_float, _to_int) を実装（不正値や小数を含む文字列の扱いを明確化）。

- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィード収集モジュールを実装（デフォルト: Yahoo Finance ビジネスカテゴリ）。
    - セキュリティ対策:
      - defusedxml による XML パース（XML Bomb 等への耐性）。
      - SSRF 対策: URL スキーム検証、プライベートホスト検出、リダイレクト時の事前検証ハンドラ。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック。
    - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント除去）。
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
    - テキスト前処理（URL 除去、空白正規化）。
    - raw_news / news_symbols への冪等保存（チャンク挿入、INSERT ... RETURNING、トランザクション処理）。
    - 銘柄コード抽出ロジック（4桁数字、known_codes によるフィルタリング）。
    - run_news_collection による統合ジョブ（各ソース独立エラーハンドリング、記事保存→銘柄紐付けの流れ）。

- DuckDB スキーマ & 初期化
  - src/kabusys/data/schema.py
    - DataSchema.md に基づく DuckDB 用 DDL を定義（Raw / Processed / Feature / Execution 層のテーブル群を設計）。
    - raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義（制約・チェック付き）。

- リサーチ・ファクター群
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、200日移動平均乖離）、ボラティリティ（20日 ATR、ATR比率、出来高比率）、バリュー（PER, ROE）等の計算関数を実装。
    - DuckDB を利用した SQL ウィンドウ関数ベースの実装（データ不足時は None を返す扱い）。
    - パフォーマンス配慮のためスキャン範囲をカレンダーバッファで限定。
  - src/kabusys/research/feature_exploration.py
    - 将来リターンの計算（calc_forward_returns、複数ホライズン対応、ホライズン入力検証）。
    - IC 計算（calc_ic: スピアマンランク相関、同順位は平均ランク処理）。
    - ランク付けユーティリティ（rank: ties の平均ランク、丸め誤差対策）。
    - ファクター統計サマリー（factor_summary: count/mean/std/min/max/median）。
  - src/kabusys/research/__init__.py
    - 主要関数のエクスポート（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize）。

- その他
  - 一部空のパッケージ初期化ファイルを配置（strategy, execution）。

### 変更
- N/A（初回リリースのため過去バージョンからの変更はなし）

### 修正
- N/A（初回リリース）

### セキュリティ
- news_collector:
  - defusedxml の採用、SSRF ガード、応答サイズ制限、リダイレクト時のホストチェックなど多数の安全対策を導入。
- jquants_client:
  - レート制限の強制、リトライ・トークンリフレッシュの制御で API 誤用や無限再帰を回避。

### 既知の制限・注意点
- research モジュールは外部ライブラリ（pandas 等）に依存せず標準ライブラリと DuckDB のみで実装されているため、大規模データに対するメモリ・性能チューニングが将来的に必要になる可能性があります。
- news_collector の extract_stock_codes は単純に 4 桁の数字を抽出するため、誤検出（文脈上株コードでない数字）を含む可能性があります。known_codes によりフィルタリングすることを推奨します。
- schema.py の DDL は Raw 層の主要テーブルを定義していますが、実運用に伴うインデックスやパーティショニングは今後の検討事項です。

---

作業内容の詳細や個別関数の使用例・設計意図は各ソースファイル内の docstring / コメントに記載しています。必要であれば CHANGELOG に追記するための補足情報（例: リリース日変更、タグ付け）をご指示ください。