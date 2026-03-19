Keep a Changelog
=================

この CHANGELOG は Keep a Changelog の形式に従い、このコードベースの現状（バージョン 0.1.0）から推測される主要な変更・実装内容を日本語でまとめたものです。記載はソースコードの実装内容に基づいて推測しています。

フォーマット:
- 変更はカテゴリ別（Added / Changed / Fixed / Security / Performance 等）に整理しています。
- 日付はこのスナップショット作成日を使用しています。

[Unreleased]
-----------

- —（現時点では未リリースの変更はありません）

0.1.0 - 2026-03-19
------------------

Added
- パッケージ初期リリース。
  - パッケージ名: kabusys、__version__ = 0.1.0、公開モジュール: data, strategy, execution, monitoring をエクスポート。
- 環境設定管理（kabusys.config）
  - プロジェクトルート自動検出: .git または pyproject.toml を基準にパスを探索し .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
  - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォート内のエスケープ対応、インラインコメントの扱い、コメント判定ルールなどを実装。
  - .env/.env.local 読み込み時の上書きルール（.env.local は上書き、既存 OS 環境変数は保護）。
  - Settings クラスによる環境変数アクセスラッパー: 必須キー取得（_require により未設定時は ValueError）、env/log_level のバリデーション（有効値集合を定義）、パス系設定は Path に変換。
- データ層 - J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティ _request を実装。JSON デコードの検出、エラーハンドリング、ページネーション対応。
  - レート制限（_RateLimiter）を実装: デフォルト 120 req/min（最小間隔 60/120 秒）でスロットリング。
  - リトライロジック実装: 最大 3 回、指数バックオフ、HTTP 408/429/5xx を対象、429 の場合は Retry-After を優先。
  - 401 Unauthorized に対する自動トークンリフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ。
  - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）。
  - DuckDB への保存関数（冪等）: save_daily_quotes, save_financial_statements, save_market_calendar。ON CONFLICT を用いた upsert により重複を排除。
  - 値変換ユーティリティ _to_float / _to_int（空文字や変換失敗は None、float 文字列の int 変換は小数部検査を実施）。
- データ層 - ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得（fetch_rss）と記事保存（save_raw_news, save_news_symbols, _save_news_symbols_bulk）を実装。
  - セキュリティ・堅牢化: defusedxml を用いた XML パース、最大受信バイト数制限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後のサイズ検査、SSRF 対策（スキーム検証・ホストのプライベートアドレスチェック・リダイレクト時検査）。
  - URL 正規化機能: トラッキングパラメータ除去（utm_* 等）、スキーム/ホスト小文字化、フラグメント削除、クエリのソート。
  - 記事 ID 生成: 正規化 URL の SHA-256 の先頭 32 文字を記事 ID として使用（冪等性確保）。
  - テキスト前処理: URL 除去、空白正規化（連続空白を単一スペースに）、先頭末尾トリム。
  - 銘柄コード抽出: 4 桁数字パターン（\b\d{4}\b）を検出し、known_codes にあるもののみ採用、重複除去。
  - DB 保存はチャンク化（_INSERT_CHUNK_SIZE = 1000）かつトランザクションで実行。INSERT ... RETURNING を用いて実際に挿入された ID / 件数を返す。
- データスキーマ（kabusys.data.schema）
  - DuckDB 用の DDL 定義（Raw Layer のテーブル例: raw_prices, raw_financials, raw_news, raw_executions 等）を実装。初期化用モジュールとしてスキーマ管理を提供。
- 研究（research）モジュール
  - feature_exploration:
    - calc_forward_returns: 指定日から各ホライズン（デフォルト [1,5,21]）の将来リターンを DuckDB の prices_daily テーブルを参照して一括 SQL で取得。
    - calc_ic: スピアマンのランク相関（ρ）を計算。欠損や非有限値を除外し、有効レコード < 3 の場合は None を返す。
    - rank: 同順位は平均ランクで扱う（比較前に round(v, 12) で丸めて浮動小数点の ties 検出漏れを抑制）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算（None 値・非有限値を除外）。
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200日移動平均乖離率）を計算。データ不足時は None。
    - calc_volatility: 20日 ATR（true_range の平均）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、volume_ratio（当日 / 平均）を計算。true_range の NULL 伝播を明確に制御。
    - calc_value: raw_financials から target_date 以前の最新財務データを取得し PER（EPS が 0/欠損時は None）と ROE を計算。
  - research パッケージは kabusys.data.stats の zscore_normalize を含む各関数を __all__ でエクスポート。
- その他
  - strategy / execution / monitoring パッケージの雛形 (__init__.py が存在) を含む（今後の拡張を想定）。

Changed
- （初回リリースのため変更履歴はなし）

Fixed
- （初回リリースのため修正履歴はなし）

Security
- ニュース収集での SSRF 対策:
  - URL スキーム検証（http/https のみ許可）。
  - ホスト名/IP のプライベートアドレス判定（直接 IP または DNS 解決による A/AAAA レコード検査）。プライベート判定時は拒否。
  - リダイレクト時にも検査を実施する専用リダイレクトハンドラを導入。
- XML パースは defusedxml を利用し XML Bomb 等に対する防御を実装。
- API クライアントでの認証トークン自動リフレッシュは 401 の場合に限定し、無限再帰を防ぐガード（allow_refresh フラグ）を実装。

Performance
- J-Quants クライアントでレート制限に従った固定間隔スロットリングを実装し、API レート制限違反を防ぐ。
- DuckDB への保存はバルク実行（executemany / チャンク挿入）かつ ON CONFLICT による upsert を利用し、重複排除とパフォーマンスの両立を図る。
- ニュースの銘柄紐付けは重複除去後にチャンク化して一括 INSERT（トランザクション）することでオーバーヘッドを削減。

Notes / Known limitations（推測）
- strategy / execution / monitoring の具体的実装は現状スケルトンであり、発注ロジックや監視機能は未実装（パッケージの骨組みのみ）。
- DuckDB スキーマの一部（execution 関連など）はファイル断片化によりスニペットが途中で終わっているが、主要な Raw Layer テーブル定義は含まれている。
- 外部依存を極力抑える設計（research モジュールは標準ライブラリのみで実装）だが、実際の運用では pandas 等の利用で開発効率を上げる余地がある。

参照
- パッケージバージョン: src/kabusys/__init__.py に __version__ = "0.1.0"
- 主なファイル:
  - src/kabusys/config.py
  - src/kabusys/data/jquants_client.py
  - src/kabusys/data/news_collector.py
  - src/kabusys/data/schema.py
  - src/kabusys/research/feature_exploration.py
  - src/kabusys/research/factor_research.py
  - src/kabusys/research/__init__.py

この CHANGELOG はソースコードの実装内容から推測して作成しています。差分やリリースノートとして公式に使用する場合は、実際の変更履歴やコミットログと照合してください。