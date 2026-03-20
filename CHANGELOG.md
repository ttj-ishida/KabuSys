# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルは、現在のコードベースから実装内容を推測して作成した初期リリースの変更履歴です。

全般的な注意
- 本リリースはパッケージバージョン 0.1.0（src/kabusys/__init__.py の __version__）に対応します。
- 多くのデータ処理は DuckDB に対する読み書き（prices_daily / raw_prices / raw_financials / features / signals / ai_scores / positions / market_calendar など）を前提としています。
- 設計上、ルックアヘッドバイアス回避や冪等性・トランザクション原子性、レートリミット遵守、入力検証・堅牢化が重視されています。

Unreleased
- (なし)

[0.1.0] - 2026-03-20
Added
- パッケージ初期実装を追加
  - 基本パッケージ構成:
    - kabusys パッケージとサブモジュール（data, strategy, execution, monitoring）を公開。
- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートの検出は .git または pyproject.toml を基準に親ディレクトリを探索（CWD 非依存）。
    - 環境読み込みの順序: OS 環境 > .env.local（override）> .env（未設定時にセット）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パースロジックを強化:
    - コメント行、空行、export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - クォートなしの値でのインラインコメント検出（直前が空白/タブの場合のみ）。
  - 必須環境変数取得ヘルパー _require と Settings クラスを提供。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等のプロパティを定義。
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）。
    - データベースパスの取得（DuckDB / SQLite のデフォルトパス）。
- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティ _request を実装（JSON パース、エラーハンドリング、リトライ）。
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - 再試行ロジック: 指数バックオフ、最大 3 回、408/429/5xx を対象。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ（無限再帰回避）。
    - ページネーション対応（pagination_key を利用）。
    - ネットワークエラーや HTTP エラーでログと再試行を行う。
  - 認証ヘルパー get_id_token とモジュールレベルの ID トークンキャッシュを実装。
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - fetched_at を UTC ISO 時刻で記録し、ON CONFLICT を用いて更新を行う（重複防止）。
    - PK 欠損行のスキップとログ出力。
  - 型変換ユーティリティ _to_float / _to_int（安全な数値変換と入力検証）。
- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからのニュース収集基盤を実装。
    - デフォルト RSS ソースに Yahoo Finance を含む。
    - defusedxml を利用して XML の脆弱性（XML Bomb 等）に対処。
    - 受信最大バイト数制限（10MB）を設定してメモリ DoS を軽減。
    - URL 正規化機能（_normalize_url）を実装:
      - スキーム・ホストの小文字化、トラッキングパラメータ（utm_* 等）の除去、フラグメント除去、クエリパラメータのソート。
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）を使う想定で冪等性を確保。
    - HTTP/HTTPS 以外のスキームや SSRF を防ぐチェックを想定（設計メモ）。
    - DB へはバルク INSERT（チャンクサイズ制御）で保存し、ON CONFLICT DO NOTHING を想定して冪等性を保持。
- 研究用モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を計算。
    - calc_volatility: ATR20, atr_pct, 20日平均売買代金(avg_turnover), 出来高比(volume_ratio) を計算。
    - calc_value: raw_financials と当日の株価を用いて PER / ROE を計算（EPS が 0/欠損の場合は None）。
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみを参照し、ルックアヘッドバイアスを回避。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - calc_forward_returns: 与えられた horizon（デフォルト [1,5,21]）に対する将来リターン計算を実装（LEAD を活用）。
    - calc_ic: Spearman のランク相関（Information Coefficient）計算を実装（同順位は平均ランク）。
    - factor_summary: カラムごとの count/mean/std/min/max/median を算出。
    - rank: 同順位を平均ランクにするランク付け実装（丸め誤差対策あり）。
- 戦略モジュール（kabusys.strategy）
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）:
    - build_features(conn, target_date): research モジュールの calc_* を組み合わせて features を構築。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - 日付単位で削除→挿入することで冪等な upsert を実現（トランザクションで原子性確保）。
  - シグナル生成（kabusys.strategy.signal_generator）:
    - generate_signals(conn, target_date, threshold=0.60, weights=None):
      - features と ai_scores を統合して component スコア（momentum/value/volatility/liquidity/news）を計算。
      - 各コンポーネントはシグモイドや反転シグモイドで [0,1] に変換。欠損コンポーネントは中立 0.5 で補完。
      - デフォルト重みを持ち、ユーザー指定重みは検証してマージ・再スケール。
      - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）により BUY を抑制。
      - BUY は閾値を超えた銘柄（score >= threshold）を選定。SELL は保有ポジションに対するストップロス（-8%）やスコア低下で判定。
      - SELL 優先ポリシー: SELL 銘柄は BUY 候補から除外。signals テーブルへ日付単位の置換で書き込み（トランザクション）。
      - ログ出力で処理数を記録。
- ロギング・エラーハンドリング:
  - 各モジュールで適切な logger を利用し、警告・情報ログを出力（例: PK 欠損スキップ、ROLLBACK 失敗等の警告）。

Security
- RSS パースに defusedxml を使用して XML の脆弱性に対処。
- ニュース収集で受信サイズ上限（MAX_RESPONSE_BYTES）を設けることでメモリ DoS を軽減。
- ニュース URL 正規化でトラッキングパラメータを除去し、ID 生成により冪等性を担保。
- J-Quants クライアントでのトークン管理や HTTP エラーハンドリングにより、不正/期限切れトークンへの対応を実装。

Performance / Reliability
- J-Quants クライアントでの固定間隔スロットリングにより API レート制限遵守を保証。
- リトライ（指数バックオフ）と HTTP 429 の Retry-After 優先利用を実装。
- DuckDB への書き込みはバルク操作・ON CONFLICT を用いて効率化し、トランザクションで原子性を保証。
- ニュースのバルクINSERTはチャンク化して SQL パラメータ制限を回避。

Known limitations / TODO（コード中ドキュメントより）
- トレーリングストップや時間決済などのエグジット条件は未実装（positions テーブルに peak_price / entry_date が必要）。
- research 層での一部指標（PBR・配当利回り）は未実装。
- news_collector の詳細な SSRF 対応やネットワーク制限は設計に言及があるが、実装全体の確認が必要。
- execution / monitoring などのサブパッケージは存在するが、この差分からは実装詳細が読み取れない。

Acknowledgements
- 設計方針として「ルックアヘッドバイアスの回避」「冪等性」「トランザクション原子性」「セキュリティ対策」「レート制限遵守」が一貫して考慮されています。コード内のコメントや docstring が詳細な設計意図を示しています。

もしこの CHANGELOG を基にリリースノートを整形したい、あるいは各機能ごとにより詳細なリリースノート（例: API の仕様、設定例、使用例）を追加したい場合は、その旨を教えてください。