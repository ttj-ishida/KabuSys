CHANGELOG
=========

このファイルは Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に準拠して作成されています。
セマンティックバージョニングに従います。  

※ 以下はリポジトリ内のコードから推測して作成した変更履歴（初回リリース向けの要約）です。

Unreleased
----------
- 今後の変更点や修正をここに記載します。

0.1.0 - 2026-03-18
------------------
初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装・公開しました。主要な追加点・設計方針は以下のとおりです。

Added
- パッケージ構成
  - kabusys パッケージの公開（__all__ = ["data", "strategy", "execution", "monitoring"]）。
  - バージョン情報: 0.1.0

- 環境設定（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートを .git / pyproject.toml で検出）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パース機能強化: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理（クォート無しの場合は空白直前の # をコメント扱い）。
  - Settings クラスによるプロパティアクセス:
    - J-Quants / kabu ステーション / Slack / DB パス等の必須設定検証（未設定時は ValueError）。
    - KABUSYS_ENV の検証（development/paper_trading/live）。
    - LOG_LEVEL の検証（DEBUG/INFO/...）。
    - is_live / is_paper / is_dev フラグ。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制限制御（120 req/min）を固定間隔スロットリングで実装（_RateLimiter）。
  - 再試行（リトライ）ロジックを実装（指数バックオフ、最大 3 回、408/429/5xx を再試行対象）。
  - 401 Unauthorized 発生時のトークン自動リフレッシュを1回許可しリトライ。
  - ID トークンのモジュールレベルキャッシュ（ページネーション間で再利用）。
  - ページネーション対応の fetch_daily_quotes / fetch_financial_statements。
  - market calendar 取得（fetch_market_calendar）。
  - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を提供。fetched_at を UTC で記録し、ON CONFLICT による upsert を実施。
  - 型変換ユーティリティ（_to_float, _to_int）を用意し不正データを安全に扱う。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集機能を実装（fetch_rss）。
  - セキュリティ対策:
    - defusedxml を使用した XML パース（XML Bomb 対策）。
    - HTTP(S) 以外のスキーム拒否（SSRF 対応）。
    - リダイレクト時にスキームとホストの事前検証を行うカスタムリダイレクトハンドラ（_SSRFBlockRedirectHandler）。
    - ホストがプライベートアドレスかを判定してアクセス拒否。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策。gzip 解凍後もサイズ検査を実施（Gzip Bomb 対策）。
  - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid 等）による記事ID生成（SHA-256 の先頭32文字）。
  - 記事テキストの前処理（URL 除去、空白正規化）。
  - DuckDB への冪等保存（save_raw_news）: INSERT ... ON CONFLICT DO NOTHING + RETURNING id で実際に挿入された記事 ID を返す。チャンク（_INSERT_CHUNK_SIZE）＆1トランザクションで挿入。
  - 記事と銘柄コードの紐付け保存（save_news_symbols / _save_news_symbols_bulk）。重複除去・チャンク挿入・トランザクションを使用。
  - 銘柄コード抽出ユーティリティ（extract_stock_codes）: 4桁数字パターンを既知コードセットでフィルタ、重複除去。

- スキーマ（kabusys.data.schema）
  - DuckDB 用 DDL 定義（raw_prices / raw_financials / raw_news / raw_executions のスキーマ定義を含む）。
  - Raw / Processed / Feature / Execution 層を想定した設計（DataSchema.md に準拠）。

- 研究・特徴量（kabusys.research）
  - feature_exploration モジュール:
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト [1,5,21]）への将来リターンを DuckDB の prices_daily から一度のクエリで計算。horizons のバリデーション（正の整数かつ <= 252）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。有効レコード < 3 の場合は None を返す。ランク計算は rank 関数を使用。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算（None 及び非有限値を除外）。
    - rank: 同順位は平均ランク、丸め誤差対策として round(v, 12) を用いる。
  - factor_research モジュール:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を計算。履歴不足時は None。
    - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。true_range の NULL 伝播を厳格に扱う実装。
    - calc_value: raw_financials から基準日以前の最新財務データを取得し、PER（EPS ≠ 0 の場合）・ROE を計算。
  - 研究用 API は外部発注等にアクセスしない設計、標準ライブラリのみでの実装（feature_exploration の一部）。

Changed
- 初回リリースのため変更履歴はありません。

Fixed
- 初回リリースのため過去の修正履歴はありませんが、.env パースや RSS 処理で堅牢性向上を図る実装を導入。

Security
- RSS/HTTP 周りで SSRF 対策を実装（スキーム検証、プライベートホスト検査、リダイレクト時検査）。
- XML パーサに defusedxml を使用して XML 関連の脆弱性を軽減。
- ネットワーク・API クライアントでリトライ・バックオフと 401 リフレッシュ制御を実施し、一貫した認証管理を行う。

Performance
- J-Quants API クライアントでレート制限(_RateLimiter)を実装し API 制限を遵守。
- fetch_* はページネーションに対応し、モジュールレベルでトークンをキャッシュしてページ間で再利用。
- DB 保存はバルク INSERT / チャンク処理 / トランザクション / ON CONFLICT を活用して効率化。
- ニュースの紐付け処理は重複除去後に一括挿入することでオーバーヘッドを低減。

Notes / Known limitations
- research.feature_exploration は標準ライブラリのみで実装しているため、大規模データ処理や高度な統計手法に最適化された外部ライブラリ（pandas 等）は使用していません。
- .env の自動読み込みはプロジェクトルート検出に依存する（.git / pyproject.toml）。配布後の利用シナリオでは KABUSYS_DISABLE_AUTO_ENV_LOAD で制御可能。
- raw_executions テーブル定義など一部スキーマの継続実装が残っている可能性あり（ファイル末尾が途中で切れている箇所を検出）。

Breaking Changes
- 初回リリースのため該当なし。

Migration notes
- 既存の環境で利用する際は .env.example を参考に必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を設定してください。
- DuckDB を使用するため、データベースファイル（デフォルト: data/kabusys.duckdb）への書き込み権限を確認してください。

Contributing
- バグ報告、改善提案はリポジトリの Issue にお願いします。セキュリティ上の問題は公開の Issue ではなく、プライベートな報告手段（MAINTAINERS が指定する連絡先）を用いてください。

-- End of CHANGELOG --