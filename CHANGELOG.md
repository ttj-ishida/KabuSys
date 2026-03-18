CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。

[Unreleased]
-----------

- 現時点で未リリースの変更はありません。

[0.1.0] - 2026-03-18
-------------------

Added
- パッケージ初版リリース: kabusys 0.1.0
  - パッケージ公開情報
    - src/kabusys/__init__.py にてバージョン "__version__ = '0.1.0'" を定義し、主要サブパッケージ（data, strategy, execution, monitoring）をエクスポート。

- 環境設定/ロード機能（src/kabusys/config.py）
  - .env ファイルと OS 環境変数の読み込みを自動化（プロジェクトルートを .git または pyproject.toml で検出）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
  - .env 行パーサを実装（コメント・export プレフィックス対応、クォート内エスケープ処理、インラインコメント処理）。
  - protected オプションを用いた上書き保護機構を実装（テストや既存環境変数保護用）。
  - Settings クラスを提供し、必須値チェック（_require）、値検証（KABUSYS_ENV の制約、LOG_LEVEL の制約）、パス展開（duckdb/sqlite パス）などを実装。

- Data 層（src/kabusys/data）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - レート制限対応（120 req/min、固定スロットリングの RateLimiter 実装）。
    - 冪等・ページネーション対応のフェッチ関数:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーションキーを適切に扱う）。
    - リトライ/バックオフ実装（最大 3 回、408/429/5xx をリトライ対象、429 の Retry-After 優先）。
    - 401 発生時の自動トークンリフレッシュ処理（1 回のみリフレッシュしてリトライ）。
    - DuckDB への保存ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等性保持。
    - データ型変換ユーティリティ (_to_float, _to_int) により空値と不正値を安全に扱う。
    - fetched_at に UTC タイムスタンプを記録（Look-ahead bias トレーサビリティ）。

  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィード取得と記事保存ワークフローを実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
    - セキュリティ/堅牢性施策:
      - defusedxml を使用した XML パース（XML Bomb 等を防止）。
      - SSRF 対策: リダイレクト時のスキーム検証、ホストがプライベートアドレスかどうかの検査（_is_private_host）および専用のリダイレクトハンドラを導入。
      - URL スキーム検証（http/https のみ許可）。
      - 最大受信バイト数制限（MAX_RESPONSE_BYTES=10MB）、gzip の解凍後サイズ検査（Gzip bomb 対策）。
      - レスポンスサイズ超過・パース失敗時はログ出力して安全にスキップ。
    - データ前処理/ID 生成:
      - URL 正規化とトラッキングパラメータ除去（_normalize_url）。
      - 正規化 URL の SHA-256（先頭32文字）による記事 ID 生成（_make_article_id）で冪等性を保証。
      - テキスト前処理（URL 除去、空白正規化）。
      - pubDate の RFC2822 パースと UTC 正規化（失敗時は現在時刻で代替）。
    - DB 保存:
      - INSERT ... RETURNING を用いた新規挿入 ID の取得（チャンク/トランザクション処理で効率化）。
      - news_symbols の一括保存と重複除去ロジック（チャンク単位のトランザクション、ON CONFLICT DO NOTHING）。
    - 銘柄コード抽出ユーティリティ（4桁数字パターン）と既知銘柄セットによるフィルタリング。

  - スキーマ定義（src/kabusys/data/schema.py）
    - DuckDB 用テーブル DDL を用意（Raw Layer の定義を含む）。
    - raw_prices, raw_financials, raw_news を含む DDL を実装（raw_executions など Execution 層のテーブル定義も追加開始）。

- Research 層（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev の計算（移動平均、LAG を使った過去終値参照、データ不足時は None）。
    - calc_volatility: 20日 ATR（true range 計算）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。NULL伝播を考慮して正確にカウント。
    - calc_value: raw_financials から直近の財務データを取得して PER / ROE を計算（report_date <= target_date の最新レコード使用）。PBR/配当は未実装。
    - DuckDB の prices_daily / raw_financials テーブルのみ参照する設計（外部 API にはアクセスしない）。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: target_date の終値から指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。ホライズンは 1〜252 の整数で検証。
    - calc_ic: Spearman ランク相関（IC）を計算。NaN/None/非有限値を除外し、有効レコードが 3 未満なら None を返す。
    - rank: 同順位は平均ランクとするランク付け（round による丸めで ties の検出誤差を抑制）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー関数。
    - 研究用関数は pandas 等に依存せず標準ライブラリと duckdb のみで実装。

  - 研究パッケージエクスポート（src/kabusys/research/__init__.py）
    - calc_momentum, calc_volatility, calc_value, zscore_normalize（kabusys.data.stats から）, calc_forward_returns, calc_ic, factor_summary, rank を公開。

Misc / Infrastructure
- ロギング: 各モジュールで logger を利用し操作状況・警告を詳細に出力するよう設計。
- テストフック: news_collector._urlopen のモックによりネットワークアクセスを置換可能（テスト容易性を考慮）。

Notes / Known limitations
- strategy/, execution/, monitoring/ パッケージはプレースホルダ（__init__.py は存在するが実装は含まれていない）。
- 一部 DDL（raw_executions の定義など）はスニペットが途中までであり、リリース時に完全なテーブル設計が必要。
- J-Quants クライアントとニュース収集はネットワーク IO を伴うため、運用環境では適切な環境変数（API トークン、タイムアウト、プロキシ等）の設定が必要。
- calc_value は EPS が 0 または欠損の場合に PER を None としている（設計上の判断）。

Upgrade notes
- 既存環境からのアップグレード手順は特になし（初版リリース）。DuckDB スキーマが既に存在する場合は DDL の互換性を確認してください。

セキュリティ関連
- RSS パーサで defusedxml を採用、SSRF 向けリダイレクトチェック、プライベート IP 検査、サイズ制限等を導入済み。
- J-Quants クライアントの認証トークンは自動リフレッシュ処理で扱われるが、refresh token は環境変数（JQUANTS_REFRESH_TOKEN）により安全に管理すること。

貢献・フィードバック
- 不具合報告や改善提案は Issue を立ててください。テストケースや再現手順があると助かります。

以上。