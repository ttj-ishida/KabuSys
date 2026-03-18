Keep a Changelog に準拠した形式で、コードベースから推測した変更履歴を日本語で作成しました。

全般注意:
- 初回リリース相当の内容をまとめています（パッケージバージョン: 0.1.0）。
- 記載はソース内の実装・設計コメントから推測しています。実際の変更履歴やリリースノートと差異がある場合があります。

Unreleased
---------
（ありません）

[0.1.0] - 2026-03-18
-------------------

Added
- 基本パッケージの初期実装を追加
  - src/kabusys/__init__.py にてパッケージ名とバージョンを定義（__version__ = "0.1.0"）。
  - パッケージ内主要サブパッケージをエクスポート: data, strategy, execution, monitoring。

- 環境設定・.env 自動読み込み機能（src/kabusys/config.py）
  - プロジェクトルート（.git または pyproject.toml）から .env/.env.local を自動検出して読み込み。
  - .env のパース機能を実装（コメント、export プレフィックス、クォート内のエスケープ、インラインコメント処理等に対応）。
  - .env.local を .env より優先して上書きする動作を実装。既存 OS 環境変数は保護（protected）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB / システム設定等の必須変数取得メソッドを実装（必須変数未設定時は ValueError を送出）。
  - KABUSYS_ENV（development/paper_trading/live）の検証、LOG_LEVEL の検証、is_live/is_paper/is_dev のヘルパーを実装。

- データ取得・保存機能（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアント実装:
    - RateLimiter（固定間隔スロットリング）でレート制限（120 req/min）を順守。
    - 再試行（指数バックオフ）ロジックを実装（最大3回。HTTP 408/429/5xx 等を対象）。
    - 401 時にはリフレッシュトークンで自動トークン更新を1回行って再試行。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
    - DuckDB への冪等保存関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT での更新を行い重複を排除。
    - 数値変換ユーティリティ（_to_float, _to_int）で堅牢な変換ルールを実装。

- ニュース収集機能（src/kabusys/data/news_collector.py）
  - RSS フィード取得と前処理機能を実装:
    - RSS 取得（fetch_rss）: defusedxml を使用した安全な XML パース、gzip 解凍対応、Content-Length/サイズ上限チェック（MAX_RESPONSE_BYTES）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、リダイレクト先検査用ハンドラ（_SSRFBlockRedirectHandler）、ホストがプライベートアドレスかどうかの検査（_is_private_host）。
    - URL 正規化（トラッキングパラメータ除去）と記事 ID 生成（SHA-256 の先頭32文字）。
    - テキスト前処理（URL 除去、空白正規化）。
    - DB 保存: save_raw_news（チャンク化、トランザクションまとめ、INSERT ... RETURNING で新規挿入 ID を返す）、save_news_symbols / _save_news_symbols_bulk（重複排除、チャンク化、トランザクション）。
    - 銘柄コード抽出ユーティリティ（4桁コード検出と known_codes フィルタリング）。
    - run_news_collection により複数ソースを順次収集・保存し、各ソースのエラーを独立して扱う実装。

- リサーチ / ファクター関連機能（src/kabusys/research/）
  - feature_exploration モジュール:
    - calc_forward_returns: DuckDB の prices_daily を参照して任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで計算。
    - calc_ic: ファクター値と将来リターンのスピアマン（ランク）相関を計算（ties を平均ランクで処理）。有効サンプル数が3未満の場合は None を返却。
    - rank: 同順位は平均ランクとするランク付け（丸めで浮動小数の tie 検出漏れを回避）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - factor_research モジュール:
    - calc_momentum: mom_1m/mom_3m/mom_6m と 200日移動平均乖離率(ma200_dev) を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（atr_20）, 相対 ATR（atr_pct）, 20日平均売買代金(avg_turnover), 出来高比(volume_ratio) を計算。true_range の NULL 伝播を考慮。
    - calc_value: raw_financials から最新財務データを取得して PER (close/eps) と ROE を計算。価格が取得できる日付で left join する実装。
  - research パッケージの __all__ で主要ユーティリティを再エクスポート（zscore_normalize 等を含む）。

- DuckDB スキーマ初期定義（src/kabusys/data/schema.py）
  - Raw レイヤー用テーブル DDL を追加（raw_prices, raw_financials, raw_news, raw_executions の定義を含む。コメントに3層構造の説明あり）。
  - テーブル定義に制約（PRIMARY KEY / CHECK）を付与しデータ整合性を強化。

Changed
- （初期リリースのため過去変更はありません。設計方針として「本番発注 API にはアクセスしない」「DuckDB のみ参照/保存」「外部依存を最小化」等がドキュメント化されています。）

Fixed
- （なし／初期実装）

Security
- RSS/XML 周りの安全対策を導入
  - defusedxml の使用により XML エンティティ攻撃 (XXE/XML Bomb) を軽減。
  - リダイレクト時のスキーム/ホスト検証、プライベートアドレス拒否により SSRF を防止。
  - レスポンスサイズ上限の導入（MAX_RESPONSE_BYTES）と gzip 解凍後の再チェックでメモリ DoS を軽減。
- API クライアントでトークン管理とリフレッシュを実装し、不正/期限切れトークン時の安全な再認証を保証。

Performance
- API クライアントで固定間隔のレートリミッタを実装しレート制限を厳守（120 req/min）。
- NewsCollector / DB 保存でチャンク化・バルク挿入を行いトランザクション数を削減（_INSERT_CHUNK_SIZE）。
- DuckDB 保存処理で冪等性（ON CONFLICT）を採用し重複書き込みコストを削減。

Internals / Testability
- _urlopen や内部ユーティリティはモックしやすい構成とコメントあり（テスト用差し替えが想定）。
- ログ出力を適切に配置（info/warning/debug/exception）し、運用時のトラブルシュートに配慮。

Breaking Changes
- なし（初回リリース）

Notes / Known limitations（コードから推測）
- 外部依存を極力避ける方針のため、データ処理は標準ライブラリ + duckdb が中心（pandas 等には依存していない）。
- 一部テーブル定義（raw_executions 等）の完全な DDL が切れている箇所があるため、スキーマ全体は追加実装・確認が必要。
- get_id_token は settings.jquants_refresh_token に依存するため、環境変数の設定が必須。

今後の改善候補（推奨）
- feature_exploration / factor_research のベンチマークと大規模データでの最適化（SQL プランやインデックス検討）。
- 単体テスト・統合テストの整備（外部依存のモック、回帰テスト）。
- ドキュメント整備（各 API の利用例、DB スキーマ図、実行手順）。

-- End of CHANGELOG --