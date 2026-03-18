# CHANGELOG

すべての変更は Keep a Changelog のガイドラインに従って記載されています。  
このファイルはリポジトリ内のソースコードから推測して作成した初期の変更履歴（日本語）です。

最新: Unreleased

## [Unreleased]

（なし）

---

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージの公開 API を __all__ で整理（data, strategy, execution, monitoring）。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルと OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出（.git または pyproject.toml により判定）によりカレントワーキングディレクトリに依存しない読み込みを実現。
  - .env/.env.local の優先順（OS 環境変数 > .env.local > .env）、.env.local は上書き (override) を許可。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
  - .env ラインのパース実装（コメント、export プレフィックス、クォート中のエスケープ処理に対応）。
  - 必須環境変数取得のユーティリティ _require と Settings クラスを公開（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス等）。
  - KABUSYS_ENV のバリデーション（development, paper_trading, live）と LOG_LEVEL の検証。
  - convenience プロパティ is_live / is_paper / is_dev。
- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API からのデータ取得ユーティリティを実装（株価日足、財務データ、マーケットカレンダー）。
  - 固定間隔スロットリングによるレート制限実装（120 req/min を想定した _RateLimiter）。
  - ページネーション対応で全ページを取得するロジック（pagination_key の追跡）。
  - リトライロジック（指数バックオフ、最大試行回数 _MAX_RETRIES=3、408/429/5xx を対象）。429 の場合は Retry-After を優先。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ実装。
  - JSON パースエラーやネットワークエラーの扱いを明確化。
  - DuckDB へ保存する冪等な保存関数を追加（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT による upsert を使用。
  - 型安全な変換ユーティリティ _to_float / _to_int を実装。
- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS からニュースを収集して DuckDB の raw_news テーブルへ保存する機能を実装。
  - URL 正規化（トラッキングパラメータ除去、ソート、スキーム/ホスト小文字化、フラグメント削除）と記事ID生成（正規化 URL の SHA-256 の先頭 32 文字）を実装。
  - SSRF 対策：
    - リダイレクト前後でスキーム（http/https のみ）とホストのプライベートアドレス判定を行う _SSRFBlockRedirectHandler / _is_private_host を実装。
    - 初回接続前にホストの事前検証を実施。
  - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - defusedxml を使った XML パース（XML Bomb 対策）。
  - テキスト前処理（URL 除去、空白正規化）と RSS pubDate の堅牢なパース（UTC正規化）。
  - DB 挿入はチャンク化およびトランザクションで行い、INSERT ... RETURNING により実際に挿入された記事IDを返す（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - 記事中の銘柄コード抽出ユーティリティ（4 桁数字の検出と known_codes によるフィルタリング）。
  - デフォルト RSS ソースを追加（DEFAULT_RSS_SOURCES: Yahoo Finance ビジネスカテゴリ）。
  - 統合収集ジョブ run_news_collection を実装（ソースごとに独立したエラーハンドリング、銘柄紐付け処理）。
- スキーマ定義 (src/kabusys/data/schema.py)
  - DuckDB 用のスキーマ定義を実装（raw_prices、raw_financials、raw_news、raw_executions などの DDL を定義）。
  - レイヤー構造（Raw / Processed / Feature / Execution）に合わせた設計を明記。
- 研究（Research）モジュール (src/kabusys/research/)
  - 特徴量探索モジュール feature_exploration を追加。
    - 将来リターン計算 calc_forward_returns（単一クエリで複数ホライズンを処理、営業日/カレンダー日レンジの最適化）。
    - IC（Information Coefficient）計算 calc_ic（Spearman の ρ、rank ユーティリティを提供）。
    - factor_summary（count/mean/std/min/max/median の算出）。
    - rank（同順位は平均ランク、丸めによる ties 対応）。
    - 研究モジュールは標準ライブラリのみを依存とする方針を明記（pandas 等に依存しない実装）。
  - factor_research にてファクター計算を提供（calc_momentum, calc_volatility, calc_value）。
    - Momentum: mom_1m/mom_3m/mom_6m、MA200 乖離率（cnt_200 により 200 日未満は None）。
    - Volatility: 20 日 ATR（true range の NULL 伝播制御に注意）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率、必要行数未満は None。
    - Value: raw_financials から target_date 以前の最新財務を結合して PER / ROE を算出（EPS が 0/NULL の場合は PER を None に）。
    - 各関数は DuckDB 接続を受け取り prices_daily/raw_financials テーブルのみ参照する設計（本番発注 API にはアクセスしないことを明記）。
  - research パッケージの __init__ で主要 API をエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
- その他
  - duckdb 型注釈や logging を適切に使用してデバッグ情報/統計情報をログ出力。
  - 多くの関数で入力検証・境界条件チェック（None 値、ゼロ除算、データ不足時の None 戻し）を実装。

### 変更 (Changed)
- 設計・実装上の注意点をコードコメントとして整理し、Look-ahead Bias 回避や冪等性、トランザクション処理、SSRF 対策などを明文化。

### 修正 (Fixed)
- 初期リリースのため過去のバグ修正履歴はなし（実装段階で一般的な入力検証やエラー処理を盛り込むことで現場での問題を低減）。

### セキュリティ (Security)
- RSS フィード取得時の SSRF 対策を実装（スキーム検証、プライベート IP 検査、リダイレクト前後検査）。
- XML パースに defusedxml を使用し XML 関連の脆弱性に備える。
- 受信サイズ上限設定（MAX_RESPONSE_BYTES）によるメモリ DoS 対策。
- ニュース URL 正規化によりトラッキングパラメータを除去し、ID 決定の一貫性を確保。

### 既知の制限 (Known limitations)
- 研究モジュールは標準ライブラリ実装のため、Pandas 等の高速実装は未採用。大規模データではパフォーマンス改善の余地あり。
- 一部の DB 操作は DuckDB の SQL 機能（INSERT ... RETURNING、ON CONFLICT）に依存しており、他 DB への移植時に変更が必要。
- news_collector のホスト名のプライベート判定は DNS 解決失敗時に安全側で通過させる実装（注記あり）。環境によってはより厳格なポリシーが必要。

---

（追記やバグ修正、新機能は Unreleased セクションに順次記載してください。）