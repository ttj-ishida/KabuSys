# Changelog

すべての主要な変更は Keep a Changelog の方針に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- なし（初期リリースは 0.1.0）

## [0.1.0] - 2026-03-18
初回公開リリース。日本株自動売買システム "KabuSys" のコアライブラリ群を追加しました。主な追加機能・設計方針は以下の通りです。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py: パッケージ名とバージョン（0.1.0）、公開モジュールを定義。

- 環境設定管理
  - src/kabusys/config.py:
    - .env / .env.local ファイルと環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env のパース実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理に対応）。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 設定値取得用 Settings クラスを提供（J-Quants / kabuステーション / Slack / DB パス / システム環境判定など）。
    - 値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と必須環境変数チェック用ユーティリティ。

- データ取得・保存（J-Quants）
  - src/kabusys/data/jquants_client.py:
    - J-Quants API クライアント実装（token 刷新、ページネーション対応）。
    - レート制御（120 req/min 固定間隔スロットリング）と汎用リトライ（指数バックオフ、HTTP 408/429/5xx のリトライ）。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルのトークンキャッシュ。
    - fetch_* 系関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を実装。
    - DuckDB へ冪等に保存する save_* 関数（raw_prices/raw_financials/market_calendar）を実装し、ON CONFLICT による更新をサポート。
    - 型/変換ユーティリティ (_to_float/_to_int)。

- ニュース収集
  - src/kabusys/data/news_collector.py:
    - RSS フィード取得と記事保存パイプラインを実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化）、記事ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
    - XML パースに defusedxml を利用して XML Bomb 等の攻撃に対策。
    - SSRF 対策: スキーム検証、プライベートアドレス判定、リダイレクトハンドラによる事前検証。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍時の追加チェック（Gzip bomb 対策）。
    - テキスト前処理（URL 除去、空白正規化）、銘柄コード抽出（4桁数字、既知コードセットフィルタ）。
    - DB 書き込みはチャンク化・トランザクション化し、INSERT ... RETURNING を利用して実際に挿入された件数を返す。

- DuckDB スキーマ定義
  - src/kabusys/data/schema.py:
    - DataSchema に基づくテーブル DDL（raw_prices, raw_financials, raw_news, raw_executions などの定義の雛形）を提供。
    - スキーマ定義は Raw / Processed / Feature / Execution の層構造を想定。

- リサーチ用特徴量/解析モジュール
  - src/kabusys/research/factor_research.py:
    - モメンタム（1M/3M/6M リターン、MA200 乖離率）、ボラティリティ（20日 ATR、ATR 比率、出来高/売買代金指標）、バリュー（PER, ROE）などの計算関数を実装。
    - 各関数は DuckDB 接続を受け取り prices_daily/raw_financials テーブルのみ参照。
    - データ不足時は None を返す安全設計。
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン calc_forward_returns、IC（スピアマン順位相関）calc_ic、列の統計サマリ factor_summary、ランク付け rank を実装。
    - rank は同順位を平均ランクで扱い、丸めによる ties 検出漏れを防ぐため round(..., 12) を使用。
  - src/kabusys/research/__init__.py:
    - 公開 API として主要関数をエクスポート（calc_momentum/calc_value/calc_volatility/zscore_normalize 等）。

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリースだが、多数のエッジケースに対する防御的実装を含む）
  - .env パーサーは export プレフィックス、クォート内エスケープ、インラインコメント処理などに対応。
  - jquants_client/_request は JSON デコード失敗や HTTP エラー、ネットワークエラーに対してわかりやすいログ・例外を提供。
  - news_collector は RSS のさまざまなレイアウト（content:encoded の名前空間、guid fallback 等）に対処。

### Security
- SSRF 対策（news_collector）:
  - URL スキーム検証（http/https のみ許可）。
  - プライベート・ループバック・リンクローカルアドレスを拒否（IP 直接判定および DNS 解決して A/AAAA を確認）。
  - リダイレクト時に転送先を事前検証する _SSRFBlockRedirectHandler を導入。
- XML 攻撃対策:
  - defusedxml を使用して XML パースを行い、外部実体展開などを無効化。
- API 認証保護:
  - id_token のキャッシュと自動リフレッシュは安全に行い、401 による無限再試行を防止。

### Performance
- API レートリミット制御（固定間隔スロットリング）を導入し、J-Quants の 120 req/min を厳守可能に。
- fetch_* はページネーション対応で全件を結合取得。
- DB 保存処理はバルク/チャンク挿入、トランザクションまとめ、ON CONFLICT を使った冪等化によりオーバーヘッドを低減。
- news_collector の挿入はチャンクサイズ制御（_INSERT_CHUNK_SIZE）を用意。

### Notes / Implementation details
- DuckDB 接続を前提にした SQL 利用（ウィンドウ関数、LAG/LEAD、AVG OVER 等）で特徴量・集約を計算。
- Look-ahead bias を避けるため、外部データ取得時に fetched_at を UTC で記録する設計。
- 外部ライブラリへの依存は必要最小限（duckdb, defusedxml）に限定。
- 本リリースの目標は「データ取得・整備・特徴量計算」の基盤整備であり、発注（execution）や監視（monitoring）等の実装は今後拡張予定。

---

今後の予定（例）
- 0.2.0: strategy / execution 層の実装（kabuステーション API 統合、発注ロジック、ポジション管理）
- 0.2.x: テストカバレッジ拡充、型注釈の強化、パフォーマンス改善（並列フェッチ等）

フィードバックや不具合報告は issue を通じてお願いします。