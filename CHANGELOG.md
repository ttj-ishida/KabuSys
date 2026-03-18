CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは "Keep a Changelog" の慣習に従います。
安定バージョンは SemVer に従います。

Unreleased
----------

（現在なし）

[0.1.0] - 2026-03-18
--------------------

初回リリース。日本株自動売買システム "KabuSys" の基本コンポーネントを実装しました。
主要な追加点、設計方針、安全対策、既知の制約を以下に列挙します。

Added
- パッケージ基盤
  - kabusys パッケージを追加。パッケージバージョンは 0.1.0。
  - パッケージ公開 API として data, strategy, execution, monitoring を __all__ に定義。

- 環境設定（src/kabusys/config.py）
  - .env/.env.local の自動ロード機能を実装（読み込み順: OS 環境 > .env.local > .env）。
  - auto load を無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（主にテスト用）。
  - .env ファイルパーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応、インラインコメントの扱いなどをサポート）。
  - 必須値チェック用の Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - デフォルト値や検証ロジックを実装（KABUSYS_ENV の許容値、LOG_LEVEL の許容値、データベースファイルパスのデフォルトなど）。
  - settings 単一インスタンスをエクスポート。

- データ取得/保存（src/kabusys/data/）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - レート制限（120 req/min）のための固定間隔スロットリング実装（_RateLimiter）。
    - 冪等性を考慮した DuckDB への保存関数（ON CONFLICT DO UPDATE を使用した save_* 関数群）。
    - ページネーション対応のフェッチ関数（fetch_daily_quotes, fetch_financial_statements）。
    - トークン管理: リフレッシュトークンから ID トークンを取得する get_id_token、モジュールレベルのトークンキャッシュを実装。401 受信時にトークン自動リフレッシュを行い1回リトライ。
    - 再試行/バックオフ: ネットワークエラーや 408/429/5xx に対する指数バックオフ、最大リトライ回数の実装。429 の場合は Retry-After ヘッダを優先。
    - 軽量な HTTP 実装に urllib を採用し、JSON デコードエラーやタイムアウトを明示的に取り扱う。
    - 型変換ユーティリティ (_to_float / _to_int) を提供し、不正データ耐性を向上。
  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィード収集（fetch_rss）、記事前処理（URL 除去・空白正規化）、記事ID 生成（正規化 URL の SHA-256 の先頭32文字）を実装。
    - セキュリティ対策: defusedxml による XML パース、安全なリダイレクト検査ハンドラ（SSRF 対策）、HTTP レスポンスサイズ上限チェック（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後の再チェック、許可スキームは http/https のみ。
    - トラッキングパラメータ除去（utm_* など）、URL 正規化、記事の一意化、raw_news への冪等保存（INSERT ... ON CONFLICT DO NOTHING + RETURNING を利用）を実装。
    - 銘柄抽出ユーティリティ（4桁の数字パターンと既知コードセットに基づく extract_stock_codes）を実装。
    - バルク挿入のチャンク処理とトランザクション管理（チャンクサイズ制御、トランザクションのコミット/ロールバック）により DB オーバーヘッドを抑制。
    - run_news_collection により複数ソースの統合収集を実装（ソースごとにエラーハンドリング）。
  - スキーマ定義（src/kabusys/data/schema.py）
    - DuckDB 用の DDL を実装（Raw レイヤーの raw_prices, raw_financials, raw_news などを定義）。3 層（Raw / Processed / Feature / Execution）の方針に基づく設計。
    - 各テーブルに対する NOT NULL / CHECK / PRIMARY KEY 制約を明示。

- リサーチ / ファクター計算（src/kabusys/research/）
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: DuckDB 上の prices_daily を参照し、複数ホライズン（デフォルト 1,5,21 営業日）を同時取得する効率的なクエリを実装。
    - IC（Information Coefficient）計算（calc_ic）: Spearman ランク相関を自前で計算、データ不足（有効ペア < 3）の場合は None を返す。
    - ランク付けユーティリティ（rank）: 同順位は平均ランクを割り当て、丸め誤差対策のため round(..., 12) を適用。
    - ファクター統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。
    - 研究用関数は外部ライブラリに依存せず標準ライブラリのみで実装（pandas 等を使わない設計）。
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum ファクター（calc_momentum）: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。データ不足時は None を返す。
    - Volatility / Liquidity（calc_volatility）: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。true range の NULL 伝播を適切に扱う設計。
    - Value（calc_value）: raw_financials と prices_daily を結合して PER, ROE を計算。最新報告日以前の最新財務データを取得。
    - スキャン範囲のバッファ設計（営業日→カレンダー日換算の余裕）により週末や祝日を吸収する実装。
  - research パッケージの __init__ で主要関数を再エクスポート（calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize）。

- ロギング / エラーハンドリング
  - 各モジュールで logging を利用し、情報/警告/例外発生箇所を記録。
  - DB トランザクション失敗時は rollback を行い例外を再送出。

- 実装/設計上の配慮（ドキュメント文字列）
  - 各モジュール・主要関数に詳細な docstring を付与。設計方針・安全対策・想定入力・戻り値・制約を明示。

Security
- ニュース取得での SSRF 対策（リダイレクト事前検査・最終 URL の再検証・プライベート IP 判定）。
- XML パースに defusedxml を使用（XML 脆弱性対策）。
- 外部取得データのサイズ制限（MAX_RESPONSE_BYTES）によるメモリ DoS 対策。
- J-Quants クライアントにおける認証トークンの自動更新と 401 ハンドリング。

Performance / Reliability
- DuckDB 側でウィンドウ関数を活用して一度に複数ホライズン/移動平均等を計算することで読み取り回数を抑制。
- fetch 系のページネーション対応とモジュール内トークンキャッシュにより効率的な API 呼び出しを実現。
- raw_news / news_symbols のバルク挿入をチャンク化して SQL 長制限やパラメータ数上限を回避。

Known limitations / Notes
- research モジュールは標準ライブラリのみで実装しているため、大規模データ処理では pandas 等を導入した方が高速化できる可能性がある。
- news_collector の _is_private_host は DNS 解決失敗時に「非プライベート」と見なす設計になっている（安全側のトレードオフ）。必要に応じてポリシーを厳格化することを推奨。
- DuckDB の SQL 文は DuckDB 固有の機能（ウィンドウ関数、ROW_NUMBER 等）に依存しているため、他 DB へ移植する場合はクエリの書き換えが必要。
- strategy/ execution パッケージはスケルトン（__init__.py が空）であり、具体的な発注ロジック・ポジション管理はこれからの実装対象。
- RSS からの pubDate は UTC に正規化して naive datetime（tzinfo=None）で返す設計。用途に応じて timezone-aware に変更可能。

Acknowledgements / Other
- 主要な設計決定や仕様はコード内ドキュメント（docstring）に詳細を記載しています。運用時の API キー管理 (.env / 環境変数) や DB バックアップなどの運用ポリシーは別途整備してください。

[0.1.0]: https://example.com/releases/0.1.0 (初回リリース)