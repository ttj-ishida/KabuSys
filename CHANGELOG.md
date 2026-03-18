CHANGELOG
=========
本プロジェクトは Keep a Changelog の形式に準拠して変更履歴を管理します。
http://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

(現時点では未リリースの差分はありません)

0.1.0 - 2026-03-18
------------------

Added
- パッケージ初期リリース (version 0.1.0)
  - src/kabusys/__init__.py にてパッケージエントリを定義。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数を自動で読み込む仕組みを実装。
    - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を探索して実行（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env パーサーの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内でのエスケープ処理対応。
    - インラインコメントの扱い（クォート外で '#' の前がスペース/タブの場合にコメントとみなす）を実装。
  - 環境変数必須チェック用の _require と Settings クラスを提供。
    - J-Quants / kabuステーション / Slack / DB パス等の設定プロパティを実装。
    - KABUSYS_ENV と LOG_LEVEL に対するバリデーションを実装（許容値チェック）。
    - is_live / is_paper / is_dev の便利プロパティを提供。

- J-Quants クライアント (kabusys.data.jquants_client)
  - API 呼び出しのための HTTP ユーティリティを実装。
    - 固定間隔スロットリングによるレート制限実装（120 req/min）。
    - 再試行ロジック（指数バックオフ、最大3回）を実装。HTTP 429 の場合は Retry-After を優先。
    - 401 エラー受信時は自動でリフレッシュトークンを使った id_token 更新を 1 回行って再試行。
    - モジュールレベルでの id_token キャッシュを実装（ページネーション間で共有）。
    - ページネーション対応の取得関数を実装（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
  - DuckDB への保存ユーティリティを提供（冪等性を確保するため ON CONFLICT を使用）。
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - レコードの変換ユーティリティ _to_float / _to_int を提供（空値や不正入力に対する堅牢な変換）。
  - Look-ahead-bias 対策として fetched_at を UTC で記録する設計。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードの取得と前処理、DuckDB への保存ワークフローを実装。
    - fetch_rss: RSS 取得、XML パース（defusedxml を使用して XML Bomb 等を防御）。
    - preprocess_text: URL 除去、空白正規化などのテキスト前処理。
    - _normalize_url/_make_article_id: トラッキングパラメータ除去（utm_* 等）、URL 正規化、SHA-256 による記事 ID 生成（先頭32文字）で冪等性確保。
    - SSRF に対する多層防御:
      - URL スキーム検証（http/https のみ許可）。
      - ホストがプライベート/ループバック/リンクローカルでないことを検証（直接 IP 解析 + DNS 解決による A/AAAA チェック）。
      - リダイレクト時にスキーム/プライベートアドレスを検査するカスタム HTTPRedirectHandler を導入。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - DB 保存はチャンク化とトランザクションで行い、INSERT ... RETURNING を使って実際に挿入された ID を返す実装（save_raw_news / save_news_symbols / _save_news_symbols_bulk）。
    - 銘柄コード抽出ユーティリティ extract_stock_codes（正規表現で 4 桁コードを抽出し known_codes でフィルタ、重複除去）。
    - run_news_collection により複数ソースを順次取得・保存・銘柄紐付け（1 ソース失敗時も他を継続）。

- DuckDB スキーマ初期化 (kabusys.data.schema)
  - DataSchema.md に基づくテーブル定義を実装（Raw / Processed / Feature / Execution 層の設計）。
  - raw_prices / raw_financials / raw_news / raw_executions 等の DDL を追加（各種型/チェック制約、PK 定義を含む）。

- リサーチ・ファクター計算 (kabusys.research)
  - feature_exploration:
    - calc_forward_returns: 指定日の終値から各ホライズン（デフォルト 1,5,21 営業日）の将来リターンを計算（1クエリで複数ホライズンを取得）。
    - calc_ic: Spearman ランク相関（IC）を計算。データ不足や定数分散の場合は None を返す。
    - rank: 同順位（ties）は平均ランクを採る実装。丸め（round(v, 12)）で浮動小数点の ties 検出漏れ防止。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
    - 標準ライブラリのみで実装する方針（外部依存を避ける）。
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m と 200 日移動平均乖離率 (ma200_dev) を計算。データ不足時は None。
    - calc_volatility: 20 日 ATR（真のレンジを NULL 伝播で扱う）、atr_pct、20日平均売買代金、出来高比率を計算。ウィンドウ不足時は None。
    - calc_value: raw_financials から最新財務データを取得して PER（EPS 不在/0 の場合は None）および ROE を算出。
    - 全て DuckDB 接続を受け取り prices_daily / raw_financials のみを参照。実運用 API にはアクセスしない設計。
  - kabusys.research.__init__ にて、calc_momentum/calc_value/calc_volatility/calc_forward_returns/calc_ic/factor_summary/rank と data.stats.zscore_normalize を公開。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- ニュース収集での SSRF 対策、defusedxml による XML パースの安全化、レスポンスサイズおよび gzip 解凍後サイズチェックを導入。
- J-Quants クライアントでのトークンリフレッシュ制御・再試行ポリシーにより、認証失敗や一時的な障害時の堅牢性を向上。

Notes / Implementation details
- 多くの処理は DuckDB 接続を受け取り SQL ウィンドウ関数等を活用して効率的に実装している（prices_daily/raw_financials/raw_prices/raw_news などのテーブル参照）。
- NewsCollector の HTTP 周りは _urlopen をモジュール内部で切り出しており、テスト時にモック差し替えが可能。
- DB への保存は基本的に冪等性を重視（ON CONFLICT DO UPDATE / DO NOTHING）、さらに INSERT ... RETURNING で実際に挿入された件数/ID を正確に把握可能。
- 設定は Settings インスタンス経由で取得し、必須設定が未提供の場合は ValueError を投げることで起動時の早期検出を可能にしている。

Acknowledgements
- この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートとして公開する前に、必要に応じて実装差分やプロジェクト方針に合わせて修正してください。