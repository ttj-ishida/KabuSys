Keep a Changelog v1.0.0
すべての重要な変更をこのファイルに記載します。フォーマットは Keep a Changelog に準拠します。
リリース日はコードベースから推測した初版リリース日（このドキュメント生成日）を記載しています。

[Unreleased]
- （なし）

[0.1.0] - 2026-03-19
Added
- パッケージ骨組みを追加
  - パッケージメタ情報: kabusys.__version__ = 0.1.0、公開 API を __all__ で定義。
- 環境設定管理
  - kabusys.config.Settings を追加。環境変数から設定値を取得するプロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）。
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出ロジック: .git または pyproject.toml を基準）。
  - .env パーサを実装。export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - KABUSYS_ENV（development/paper_trading/live）・LOG_LEVEL の値検証、および is_live / is_paper / is_dev の便捷プロパティを提供。
  - デフォルトの DB パス（DUCKDB_PATH / SQLITE_PATH）を定義。
- Data レイヤー（DuckDB 操作・外部データ取得）
  - J-Quants クライアント（kabusys.data.jquants_client）を追加
    - API 呼び出しラッパー _request：ページネーション対応、JSON デコードエラー検出、リトライ（指数バックオフ）、429 の Retry-After 尊重、401 の自動トークンリフレッシュを実装。
    - 固定間隔の RateLimiter（120 req/min）を実装。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar：ページネーション対応の取得関数を実装。
    - save_daily_quotes / save_financial_statements / save_market_calendar：DuckDB への冪等保存（ON CONFLICT DO UPDATE）を実装。PK 欠損行のスキップとログ出力を行う。
    - 型変換ユーティリティ _to_float / _to_int を実装（頑健な空値・文字列処理）。
  - ニュース収集モジュール（kabusys.data.news_collector）を追加
    - RSS フィード取得(fetch_rss)、XML パース（defusedxml 使用）、記事前処理(preprocess_text) を実装。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）と記事 ID 生成（SHA-256 先頭32文字）を実装し冪等性を担保。
    - SSRF 対策（スキーム検証、プライベート IP 検出、リダイレクト検査）を実装。リダイレクト時の事前検証ハンドラを追加。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES＝10MB）・gzip 解凍の取り扱い・Gzip bomb 対策を実装。
    - raw_news へのバルク挿入(save_raw_news)をトランザクション単位で行い、INSERT ... RETURNING を使って新規挿入IDを正確に返却。チャンク分割で SQL 長制限に対応。
    - 抽出した記事と銘柄コードの紐付け(save_news_symbols / _save_news_symbols_bulk)を実装（重複除去、チャンク挿入、トランザクション管理）。
    - テキストから4桁銘柄コードを抽出する extract_stock_codes を実装（既知コードフィルタ付き）。
    - run_news_collection で複数ソースを順次収集し、失敗したソースはスキップして続行する堅牢なジョブを提供。
- Research レイヤー（特徴量・統計）
  - kabusys.research パッケージを追加（高水準 API を __all__ で公開）
  - feature_exploration モジュールを実装
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト 1,5,21 営業日）の将来リターンを DuckDB の prices_daily テーブルから一括取得する SQL 実装。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。欠損値/非有限値を除外し、有効レコードが 3 未満なら None を返却。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と各種統計量(count/mean/std/min/max/median) を純粋 Python で実装（pandas 非依存）。
  - factor_research モジュールを実装
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離）を DuckDB の window 関数で効率的に計算。データ不足時は None を返却。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算（true_range 計算で NULL 伝播を考慮）。
    - calc_value: raw_financials から target_date 以前の最新財務を取得し PER・ROE を算出。prices_daily と結合して返却。
  - 設計方針: DuckDB 接続のみ参照、外部 API 呼び出しなし、結果は (date, code) 単位の dict リストを返す（戦略に安全）。
- スキーマ定義
  - kabusys.data.schema に DuckDB のテーブル定義（raw_layers 等）の DDL を追加（raw_prices, raw_financials, raw_news, raw_executions 等の定義を含む）。初期化用の DDL 準備。

Security
- ニュース収集でのセキュリティ強化
  - defusedxml を使用して XML 関連攻撃（XXE など）を防止。
  - SSRF 防止（スキーム検証、プライベートアドレス判定、リダイレクト先チェック）を実装。
  - レスポンスサイズ制限と gzip 解凍後のサイズ検査でメモリ DoS を軽減。
- J-Quants クライアント
  - 401 時のトークン自動リフレッシュを実装（無限再帰を防ぐ制御あり）。
  - リトライ対象ステータスや Retry-After の尊重実装で API 呼び出し安全性を向上。

Performance
- API 呼び出しで固定間隔のレートリミッタを導入（120 req/min に準拠）。
- DuckDB へのバルク挿入でチャンク処理と単一トランザクションを採用しオーバーヘッドを削減。
- 特徴量計算や将来リターン計算は SQL の window 関数と一括取得を活用して効率化（スキャン範囲はホライズンバッファで限定）。

Fixed / Edge-case handling
- .env パーサでクォート内のバックスラッシュエスケープやインラインコメントの扱いを正しく処理するよう実装。
- 数値変換ユーティリティで不正な小数文字列を安全に扱い、誤った切り捨てを回避。
- raw_* 保存関数で PK 欠損行をスキップしログ出力することで不整合データ挿入を回避。
- RSS の pubDate パース失敗時に警告を出し、NULL を許容しない設計のため現在時刻で代替。

Notes / Limitations
- 現バージョンでは PBR や配当利回りなど一部バリューファクタは未実装（calc_value に注記あり）。
- research モジュールは pandas 等に依存せず標準ライブラリと DuckDB のみで実装しているため、大量データの高度な集計や可視化は別途ツールが必要。
- raw DDL の一部（raw_executions など）はファイル末尾で切れているため、今後のリリースで続き／補完が必要。

Copyright / License
- 本 CHANGELOG は提供されたコード内容から推測して作成しました。実際のリリースノートはプロジェクトの変更履歴／コミットログに基づいて更新してください。