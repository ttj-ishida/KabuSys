# CHANGELOG

すべての注目すべき変更点を記録します。  
フォーマットは Keep a Changelog に準拠します。  

全般:
- バージョニング: セマンティックバージョンを採用しています。
- 依存: DuckDB をデータ永続化に使用します。research モジュールは外部データ解析ライブラリ（pandas 等）に依存せず標準ライブラリのみで実装されています。

## [0.1.0] - 2026-03-19

### Added
- パッケージ初期リリース (kabusys 0.1.0)
  - 基本パッケージメタ情報を追加
    - src/kabusys/__init__.py に __version__ = "0.1.0" と公開モジュールを定義。

- 環境設定 / ロード機能
  - src/kabusys/config.py
    - プロジェクトルート（.git または pyproject.toml）を基準に自動で .env / .env.local を読み込む自動ロード機能を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - .env の行パーサは以下に対応:
      - 空行・コメント行（#）を無視
      - export KEY=val 形式を許容
      - シングル／ダブルクォート内のバックスラッシュエスケープ対応
      - クォートなしの値中のインラインコメント判定（直前が空白/タブの場合のみ # をコメントとみなす）
    - 環境変数取得ユーティリティ Settings を提供（必須キー取得用の _require を含む）。
    - サポートされる設定:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN（必須）
      - SLACK_CHANNEL_ID（必須）
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV（development / paper_trading / live のみ許容、デフォルト development）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

- Data モジュール: J-Quants クライアント
  - src/kabusys/data/jquants_client.py
    - J-Quants API からのデータ取得（株価日足、財務データ、マーケットカレンダー）のクライアント実装。
    - レート制限制御: 固定間隔スロットリングで 120 req/min を遵守（内部 RateLimiter）。
    - リトライロジック: 指数バックオフ（最大3回）、408/429/5xx をリトライ対象。
    - 401 Unauthorized 受信時はリフレッシュ（get_id_token を呼び）して 1 回だけリトライ。
    - ページネーション対応（pagination_key を用いて全ページを取得）。
    - DuckDB への保存用関数（冪等保存）:
      - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE を用いて保存。
      - save_financial_statements: raw_financials に保存（ON CONFLICT DO UPDATE）。
      - save_market_calendar: market_calendar に保存（ON CONFLICT DO UPDATE）。
    - ユーティリティ: 安全な型変換関数 _to_float / _to_int を実装。

- Data モジュール: ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィードからニュース記事を収集し raw_news、news_symbols テーブルへ保存する機能。
    - セキュリティ設計:
      - defusedxml を使って XML パース（XML Bomb 等の防御）。
      - SSRF 対策: リダイレクト時や最終 URL のスキーム/ホスト検証、プライベート IP 判定（_is_private_host）を実装。リダイレクトチェック用にカスタム HTTPRedirectHandler を導入。
      - URL スキームは http/https のみ許可（その他は拒否）。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後サイズ検査を実施（Gzip bomb 対策）。
      - トラッキングパラメータ（utm_ 等）を除去して URL 正規化、正規化結果の SHA-256（先頭32文字）を記事IDとして冪等性を確保。
    - フォーマット・抽出:
      - content:encoded を優先して本文を取得、description をフォールバック。
      - テキスト前処理（URL 除去、空白正規化）。
      - 銘柄コード抽出: 正規表現で 4 桁の数字を抽出し、既知コード集合と照合。
    - DB 保存:
      - save_raw_news: INSERT ... RETURNING id を用いて実際に挿入された記事IDを返す。チャンク INSERT と 1 トランザクションでの処理。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols をチャンクで冪等に保存（ON CONFLICT DO NOTHING）し、挿入数を返す。
    - run_news_collection: 複数ソースを順に処理し、個々のソースで例外が発生しても他ソースは継続する堅牢なジョブ実装。

- Research モジュール: ファクター計算 / 特徴量探索
  - src/kabusys/research/factor_research.py
    - StrategyModel に基づく複数の定量ファクターを計算する関数を実装:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離率）。データ欠如時は None。
      - calc_volatility: atr_20（20日ATR）、atr_pct、avg_turnover（20日平均売買代金）、volume_ratio。真の true range の NULL 伝播を正確に扱う。
      - calc_value: raw_financials から target_date 以前の最新決算を取得して PER / ROE を算出（EPS が 0/欠損の場合は None）。
    - 全関数は DuckDB 接続を受け取り prices_daily / raw_financials のみ参照、外部 API にはアクセスしない設計。
    - パラメータに使用する定数（期間）をファイル内で定義。

  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定日の終値から指定ホライズン（営業日）後のリターンを一括で取得（LEAD を利用）。ホライズンはデフォルト [1,5,21]。
    - calc_ic: ファクター値と将来リターンの組で Spearman ランク相関（IC）を計算。レコード数 < 3 の場合は None。
    - rank: 同順位を平均ランクにするランク付け実装（丸め誤差対策に round(v,12) を使用）。
    - factor_summary: 各ファクター列について count/mean/std/min/max/median を計算（None は除外）。

  - src/kabusys/research/__init__.py
    - 公開 API として zscore_normalize（kabusys.data.stats 由来）および上記関数群を __all__ に追加。

- Data スキーマ
  - src/kabusys/data/schema.py
    - DuckDB 用 DDL を定義（Raw 層のテーブル定義を含む）。
      - raw_prices（PK: date, code、各種 CHECK 制約あり）
      - raw_financials（PK: code, report_date, period_type）
      - raw_news（PK: id）
      - raw_executions（定義開始。発注／約定系のスキーマを整備予定）
    - スキーマは DataSchema.md の層構造（Raw / Processed / Feature / Execution）に基づく設計。

- ユーティリティ
  - 各所に詳細なログ出力と警告（logger.warning/info/debug）を追加し、実行時のトラブルシュートを容易に。

### Changed
- （初回リリースのため変更履歴なし）

### Fixed
- （初回リリースのため修正履歴なし）

### Security
- news_collector において SSRF 対策・XML ハンドリング強化・レスポンスサイズ制限・gzip 解凍後の追加検査を導入。
- jquants_client の HTTP リトライ・401 リフレッシュ処理によりトークン漏洩や無限リトライの回避を考慮。

### Known issues / Limitations / Notes
- DuckDB のテーブル（prices_daily / raw_prices / raw_financials / raw_news / news_symbols 等）は事前にスキーマを作成しておく必要があります（schema モジュールで DDL を提供）。
- research モジュールは pandas 等を使わず実装しているため、大量データ処理の最適化やメモリ効率は今後の改善余地があります。
- news_collector の銘柄抽出は単純に 4 桁数字を探す実装のため、誤検出や企業識別の精度改善は今後の課題です。
- _is_private_host の DNS 解決に失敗した場合は「非プライベート」とみなす実装になっており、極端に保守的な環境では挙動に注意が必要です（解決失敗時はアクセスを許可）。
- jquants_client のモジュールレベルの ID トークンキャッシュはプロセス内で共有され、ページネーション間でトークンを再利用します。マルチプロセス環境ではプロセス毎のキャッシュとなります。
- calc_forward_returns は内部で LEAD を使い、指定日以降のデータが存在しないホライズンは None を返します。

### Migration notes
- 環境変数の必須設定:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルトの DuckDB ファイルパスは data/kabusys.duckdb。必要に応じて DUCKDB_PATH 環境変数で変更してください。
- 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト実行等で有用）。

---

今後の予定（未実装 / TODO の一例）
- Execution 層（発注・約定管理）テーブル・ロジックの実装完了。
- Processed / Feature 層の DDL 完全整備とマイグレーション機能。
- ニュースの NLP によるコード抽出精度向上（ルール拡張 / 辞書ベース / ML 利用）。
- 大規模データ処理のための最適化（batch/streaming、メモリ最適化）。
- 単体テスト・統合テストの整備と CI パイプライン構築。

※この CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のリリースノートとして配布する際は、実運用上の差分やコミット履歴に基づいて追記・修正してください。