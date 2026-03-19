# CHANGELOG

すべての注記は Keep a Changelog に準拠します。セマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買プラットフォーム「KabuSys」の基本機能群を実装しました。

### Added
- パッケージ基盤
  - パッケージ情報と公開 API を定義（src/kabusys/__init__.py）。
  - バージョンを "0.1.0" として設定。

- 環境設定管理
  - .env ファイルおよび OS 環境変数から設定を読み込む自動ローダーを実装（src/kabusys/config.py）。
    - プロジェクトルート検出は __file__ を基点に .git または pyproject.toml を探索して行うため、CWD に依存しない設計。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
  - .env 行パーサーの強化:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理、コメント判定の細かな扱い。
  - Settings クラスを導入しアプリ設定をプロパティで提供:
    - J-Quants / kabuステーション / Slack / DB パス 等の必須設定取得（未設定時は ValueError）。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許可リスト: development/paper_trading/live、DEBUG/INFO/...）。
    - is_live / is_paper / is_dev の便利プロパティ。

- データ取得クライアント（J-Quants）
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
    - レート制限（120 req/min）を守る固定間隔スロットリング _RateLimiter。
    - HTTP リクエストのリトライ（指数バックオフ、最大 3 回）と 401 時の自動トークンリフレッシュ処理を実装。
    - ページネーション対応の取得関数:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務四半期データ）
      - fetch_market_calendar（JPX マーケットカレンダー）
    - DuckDB への冪等保存ユーティリティ:
      - save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を使用）
    - 型変換ユーティリティ _to_float / _to_int を実装し入力の堅牢化を図る。
    - 取得時の fetched_at を UTC ISO8601 で記録し look-ahead bias のトレーサビリティを確保。

- ニュース収集（RSS）
  - RSS ニュース収集・前処理・DB 保存パイプラインを実装（src/kabusys/data/news_collector.py）。
    - RSS フェッチ（fetch_rss）: defusedxml を用いた安全な XML パース、gzip 解凍対応、Content-Length / 実際のバイト長による最大受信サイズチェック（MAX_RESPONSE_BYTES = 10 MB）。
    - URL 正規化と記事 ID 生成:
      - トラッキングパラメータ（utm_*, fbclid 等）を除去して正規化し、SHA-256（先頭32文字）で記事IDを生成。
    - SSRF／安全対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時にスキームとホストを事前検証する _SSRFBlockRedirectHandler。
      - ホスト名／IP を検査してプライベート/ループバック/リンクローカル/マルチキャストを拒否。
    - テキスト前処理（URL除去、空白正規化）。
    - DB 保存:
      - save_raw_news: チャンク化＆トランザクションで INSERT ... ON CONFLICT DO NOTHING を行い、INSERT RETURNING で実際に挿入された記事IDを返す。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをバルク挿入（ON CONFLICT DO NOTHING）し、実挿入数を返す。
    - 銘柄コード抽出ユーティリティ extract_stock_codes（4桁数字パターンに基づき、known_codes によるフィルタ）。
    - run_news_collection: 複数 RSS ソースを順次処理し、個別のソースで発生したエラーはそのソースのみスキップして継続する堅牢な集約ジョブを実装。
    - デフォルト RSS ソースとして Yahoo Finance のカテゴリフィードを登録。

- 研究（Research）モジュール
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定基準日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを DuckDB の prices_daily テーブルを用いて一度のクエリで取得。
      - horizons の入力検証（正の整数かつ <= 252）。
      - 結果は銘柄ごとの辞書リストで返却。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。結合・NaN/非有限値の除外、3 件未満で None を返す。
    - rank: 同順位は平均ランクとするランク変換（round(v, 12) による丸めで ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（true range の単純平均）、相対ATR (atr_pct)、20日平均売買代金、出来高比 (volume_ratio) を計算。true_range の欠損伝播を制御し適切にカウントを行う。
    - calc_value: raw_financials から基準日以前の最新財務を取得して PER（EPS が 0/欠損なら None）と ROE を計算。prices_daily と結合して返却。
    - 各関数は DuckDB 接続を受け取り prices_daily / raw_financials のみ参照する設計（外部 API へアクセスしない）。

- スキーマ（DuckDB）
  - DuckDB 用のスキーマ定義と初期化モジュールを追加（src/kabusys/data/schema.py）。
    - Raw Layer のテーブル DDL（raw_prices, raw_financials, raw_news, raw_executions 等）を定義（堅牢な型・チェック制約・PK を含む）。
    - DataSchema.md に基づく三層/四層構造（Raw / Processed / Feature / Execution）の設計を反映。

### Security
- RSS ニュース収集での SSRF 緩和:
  - URL スキーム制限（http/https のみ）、リダイレクト時の事前検査、DNS 解決結果の IP 判定によるプライベートアドレス拒否を実装。
- XML パースに defusedxml を採用し XML Bomb 等の攻撃に対する耐性を確保。
- レスポンスサイズ上限（10 MB）と gzip 解凍後の検査によりメモリ DoS を防止。
- J-Quants クライアントは 401 自動リフレッシュの制御や再帰回避、リトライ対象コードの限定等の堅牢化を実施。

### Performance
- J-Quants API 呼び出しに対して固定間隔スロットリング（RateLimiter）を実装しレート制限を確実に遵守。
- News 保存処理はチャンク化とトランザクションで一括 INSERT を行いオーバーヘッドを低減。
- 抽出・変換処理は可能な限り単一クエリ（DuckDB ウィンドウ関数等）で完結する実装を採用し I/O を削減。

### Internal / Other
- ロギングを各モジュールに設置し、処理状況や警告・例外を記録するようにした。
- 各モジュールの設計方針（look-ahead bias 回避、外部 API 非依存、冪等性重視など）をコードドキュメントに明示。

### Known limitations / Notes
- 現バージョンでは PBR・配当利回り等のバリューファクターは未実装（calc_value の注記参照）。
- News の記事IDは URL 正規化に依存するため、原典の URL 構造が大きく変わると識別が変わる可能性あり。
- 外部ライブラリ（pandas 等）には依存せず標準ライブラリ中心で実装しているため、大量データ処理時は最適化余地あり。

---

開発・運用上の詳細や API 仕様、DB スキーマ、研究向けドキュメント（StrategyModel.md, DataPlatform.md, DataSchema.md 等）はコード内コメントで記載しています。今後のリリースで追加機能（発注/実行レイヤー、戦略管理 UI、さらなる特徴量、テストカバレッジの強化など）を予定しています。