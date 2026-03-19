Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-19
--------------------

Added
- パッケージ初回リリース "KabuSys"（バージョン 0.1.0）。
  - パッケージの公開 API を定義（kabusys.__init__.py の __all__ により data, strategy, execution, monitoring を公開）。
- 環境設定管理（kabusys.config）
  - .env/.env.local ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env パーサ実装（コメント、export 形式、シングル/ダブルクォート、エスケープに対応）。
  - .env.local は .env を上書きする動作（ただし OS 環境変数は保護）。
  - 自動読み込みの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD の導入。
  - 必須設定取得ヘルパ _require と型/値検証（KABUSYS_ENV, LOG_LEVEL の妥当性チェック）を提供。
  - DB パス等を pathlib.Path で扱うユーティリティを提供。
- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - API レート制限（120 req/min）を守る固定間隔レートリミッタを実装。
  - リトライ戦略（指数バックオフ、最大3回）、429 の Retry-After を尊重する実装。
  - 401 受信時の自動トークンリフレッシュ（1回のみ）と ID トークンのモジュールキャッシュ。
  - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
  - DuckDB への冪等保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）
    - ON CONFLICT DO UPDATE による重複回避。
    - 値変換ヘルパ _to_float / _to_int を提供（不正値の安全処理）。
  - HTTP 通信の JSON パースエラーやネットワーク例外に対する明確な扱い。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集・正規化・DB 保存ワークフローを実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
  - セキュリティ対策：
    - URL のスキーム検証（http/https のみ許可）。
    - SSRF 対策（リダイレクト先検査・ホストがプライベートアドレスか判定）を実装。_SSRFBlockRedirectHandler と _is_private_host を導入。
    - defusedxml を利用した XML パース（XML Bomb 等の緩和）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）をチェック、Gzip 解凍後も上限検証。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）および記事 ID（正規化 URL の SHA-256 の先頭32文字）生成。
  - テキスト前処理（URL 除去、空白正規化）。
  - 銘柄コード抽出（4桁数字の検出と known_codes によるフィルタリング）。
  - DB 保存はチャンク分割 + トランザクションで実行し、INSERT ... RETURNING を用いて実際に挿入された件数を返却。
- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw レイヤ等の初期テーブル定義（raw_prices / raw_financials / raw_news / raw_executions の DDL 等の雛形）を追加。
- リサーチ用ファクター計算（kabusys.research）
  - feature_exploration:
    - calc_forward_returns: 指定日から複数ホライズンの将来リターンを効率的に計算（単一クエリで取得、ホライズン上限検査）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）計算。欠損・同値処理を考慮。
    - factor_summary: ファクター列の基本統計（count/mean/std/min/max/median）を標準ライブラリのみで実装。
    - rank: 同順位は平均ランクを割り当てるランク計算（丸めにより ties 検出の安定化）。
  - factor_research:
    - calc_momentum: mom_1m/3m/6m と MA200 乖離率を計算（ウィンドウ不足時は None）。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算（true_range の NULL 伝播制御等）。
    - calc_value: raw_financials から最新の財務情報を取得して PER / ROE を計算（価格は指定日終値）。
  - 設計方針: DuckDB の prices_daily / raw_financials テーブルのみ参照し、本番発注 API 等にはアクセスしない。pandas 等外部ライブラリに依存せず標準ライブラリと duckdb で実装。
  - kabusys.research.__init__ で主要ユーティリティをエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
- 汎用設計上の注意・ログ出力
  - 各主要処理において logger で情報／警告／例外ログを出力するよう実装。

Security
- news_collector に SSRF 緩和、defusedxml 使用、レスポンスサイズ制限を導入。
- jquants_client の HTTP エラーハンドリングでトークン漏洩や無限再帰を避ける設計（allow_refresh フラグ、キャッシュ制御）。

Notes
- research モジュールは外部ライブラリに依存しない（pandas 等不使用）ため、軽量に動作することを意図しています。大規模データ処理では別途最適化が必要になる可能性があります。
- DuckDB のテーブル名 / カラム型や ON CONFLICT 句はスキーマ設計（DataSchema.md）に基づく想定で実装しています。実動作前にスキーマの初期化（DDL 実行）を行ってください。
- strategy / execution / monitoring パッケージは名前のみ定義されており、実装は今後追加予定です。

Acknowledgements
- 本リリースは KabuSys プロジェクトの初版として、データ取得・保存・リサーチ基盤・ニュース収集の基礎を提供します。今後のリリースで戦略実装・発注処理・モニタリング機能などを拡充予定です。