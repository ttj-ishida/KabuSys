# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに従います。セマンティックバージョニングを採用します。

現在のバージョン: 0.1.0

[Unreleased]

## [0.1.0] - 2026-03-18
初回リリース。以下の主要機能・モジュールを追加しました。

### Added
- パッケージ基盤
  - パッケージ初期化とバージョン情報を追加 (src/kabusys/__init__.py)。__version__ = "0.1.0" を設定し、主要サブパッケージを __all__ に公開（data, strategy, execution, monitoring）。

- 環境変数 / 設定管理
  - settings クラスによる環境変数ラッパーを追加 (src/kabusys/config.py)。
    - .env/.env.local の自動読み込み（プロジェクトルート検出：.git または pyproject.toml 基準）。
    - .env.local は .env を上書き。OS 環境変数を保護する protected 機能。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト向け）。
    - 必須環境変数取得時に未設定なら ValueError を送出する _require。
    - 利用可能な環境値検証（KABUSYS_ENV, LOG_LEVEL）と便利判定プロパティ（is_live / is_paper / is_dev）。

- Data モジュール: J-Quants API クライアント
  - J-Quants からのデータ取得・保存機能を追加 (src/kabusys/data/jquants_client.py)。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar：ページネーション対応でデータ取得。
    - レート制限管理（120 req/min 固定インターバル RateLimiter 実装）。
    - 再試行ロジック（指数バックオフ、最大3回）。408/429/5xx をリトライ対象。
    - 401 受信時は自動でリフレッシュトークンを使い ID トークンを更新して 1 回リトライ。
    - get_id_token（リフレッシュトークンからの ID トークン取得）。
    - DuckDB への冪等保存ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）：
      - ON CONFLICT DO UPDATE/DO NOTHING を利用して重複を抑制。
      - fetched_at を UTC で付与して look‑ahead bias のトレースを容易にする。
    - 型変換ユーティリティ（_to_float, _to_int）で不正値を安全に扱う。

- Data モジュール: ニュース収集
  - RSS フィードからのニュース収集機能を追加 (src/kabusys/data/news_collector.py)。
    - fetch_rss: RSS 取得・XML パース・記事抽出（defusedxml を使用）を実装。
    - セキュリティ対策:
      - SSRF 対策: リダイレクト時にスキームとホストを検証する _SSRFBlockRedirectHandler、事前にホストがプライベートかを判定する _is_private_host。
      - 許可スキームは http/https のみ（_validate_url_scheme）。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES）と gzip 解凍後の検査（Gzip bomb 対策）。
      - トラッキングパラメータ除去・URL 正規化 (_normalize_url)、SHA-256 (先頭32文字) による記事ID生成 (_make_article_id) で冪等性を確保。
    - preprocess_text による本文の前処理（URL 除去、空白正規化）。
    - extract_stock_codes による本文からの 4 桁銘柄コード抽出（known_codes によるフィルタ）。
    - DB 保存ユーティリティ:
      - save_raw_news: チャンク分割 + INSERT ... RETURNING で新規挿入された記事IDリストを返す。トランザクションで一括挿入（ロールバック処理あり）。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols への紐付けを重複排除して一括挿入（INSERT ... RETURNING を使用）。
    - fetch_rss の最終 URL 検証、Content-Length の事前チェック、gzip ヘッダハンドリング、XML パース失敗時の安全な低減動作。

- Data モジュール: スキーマ初期化
  - DuckDB 用スキーマ定義・初期化 (src/kabusys/data/schema.py)。
    - Raw Layer テーブル定義（raw_prices, raw_financials, raw_news, raw_executions 等）を追加（DDL ストリングを用意）。
    - DataLayer の 3 層構造（Raw / Processed / Feature / Execution）設計を注記。

- Research モジュール: ファクター計算・探索
  - ファクター計算 (src/kabusys/research/factor_research.py):
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200日移動平均乖離）を DuckDB のウィンドウ関数で算出。データ不足時は None を返す設計。
    - calc_volatility: 20 日 ATR, atr_pct（ATR/close）, avg_turnover, volume_ratio を計算。true_range の NULL 伝播を制御して正確なカウントを行う実装。
    - calc_value: raw_financials から最新の財務データを取得し PER / ROE を計算（EPS が 0 または欠損のときは None）。
    - SQL スキャン範囲にバッファ日数を導入して週末・祝日による欠落を吸収する工夫。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py):
    - calc_forward_returns: target_date の終値から各ホライズン先（デフォルト 1,5,21 営業日）までの将来リターンを一括クエリで取得。
    - calc_ic: factor_records と forward_records を code で結合してスピアマンのランク相関（IC）を計算。欠損や非有限値を除外し、サンプル数が 3 未満なら None を返す。
    - rank: 同順位は平均ランクを採用するランク変換実装（小数丸めで ties 検出を安定化）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー関数。
  - research パッケージの公開 API を整理 (src/kabusys/research/__init__.py)。

- その他
  - duckdb を利用したデータ操作を前提として設計。外部発注 API には依存しない（研究・特徴量計算は安全に実行可能）。
  - 複数箇所でログ出力を充実（logger.debug/info/warning/exception）し実行追跡を容易に。

### Changed
- 初回リリースのため変更履歴なし（初期追加のみ）。

### Fixed
- 初回リリースのため修正履歴なし。

### Security
- ニュース収集および外部 URL 取得周りに対する複数の保護策を導入：
  - SSRF 対策（リダイレクト検査、プライベート IP 判定、許可スキーム制限）。
  - XML パーサに defusedxml を使用し XML 攻撃対策。
  - レスポンスサイズ制限（Gzip 解凍後含む）でメモリ DoS 防止。

注記:
- research モジュールの関数設計は「DuckDB 接続を受け取り prices_daily/raw_financials のみを参照する」ことを前提としています。本番口座や発注 API へはアクセスしない設計です。
- ニュース記事の冪等性は URL 正規化＋ハッシュによって保証されます（tracking パラメータ除去）。
- .env 読み込みロジックはプロジェクトルートを探索して行います。そのため配布後・任意のカレントワーキングディレクトリでも期待通り動作するようにしています。

将来追加したい項目（TODO 的メモ）
- Strategy / Execution / Monitoring の具体的実装（現在はパッケージ構造のみ定義）。
- より詳細なテストカバレッジと統合テスト（ネットワーク・DB インテグレーション）。
- PBR・配当利回りなどの Value ファクターの追加。

---