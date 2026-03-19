# Changelog

すべての変更は「Keep a Changelog」フォーマットに準拠しています。  
このプロジェクトはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-19

初回リリース。

### 追加（Added）
- パッケージ基礎
  - kabusys パッケージの初期公開。バージョンは 0.1.0。
  - __all__ に data, strategy, execution, monitoring を公開。

- 設定/環境変数管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする機能を実装。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env 行パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。
  - .env 読み込みで既存 OS 環境変数を保護する protected オプションを導入（.env.local を override=True で読み込みつつ OS 環境変数は上書きしない）。
  - 設定取得用 Settings クラスを提供。必須項目の検証（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）とデフォルト値（KABU_API_BASE_URL, LOG_LEVEL, KABUSYS_ENV, データベースパスなど）の取得ロジックを実装。
  - 環境（env）・ログレベルの妥当性チェック（許容値セット）を実装し、不正値で例外を送出。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - 固定間隔のレートリミッタ（120 req/min 相当）を導入。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx 対象）を実装。429 の場合は Retry-After ヘッダを優先。
  - 401 受信時にリフレッシュトークンから自動的に id_token を再取得して 1 回リトライする処理を実装。
  - ページネーション対応の fetch_* 関数を提供:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への冪等保存関数を実装:
    - save_daily_quotes -> raw_prices（ON CONFLICT DO UPDATE）
    - save_financial_statements -> raw_financials（ON CONFLICT DO UPDATE）
    - save_market_calendar -> market_calendar（ON CONFLICT DO UPDATE）
  - データ変換ユーティリティ（_to_float / _to_int）を提供。型安全性の考慮あり。
  - 取得時刻（fetched_at）を UTC ISO 形式で保存し、Look-ahead バイアスのトレースをサポート。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news に冪等保存するモジュールを追加。
  - 記事ID を URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を確保。
  - URL 正規化機能を実装（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
  - セキュリティ対策実装:
    - defusedxml による XML パース（XML Bomb 等の防御）。
    - 受信バイト数の上限（MAX_RESPONSE_BYTES=10MB）によるメモリ DoS 対策。
    - トラッキングパラメータ除去、HTTP(S) スキーム検証、SSRF 緩和の方針。
  - バルク挿入のチャンク化による性能対策（_INSERT_CHUNK_SIZE）。

- 研究（research）モジュール
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算。200 日移動平均のデータ不足判定を行う。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算。true_range の NULL 伝播制御を行う。
    - calc_value: target_date 以前の最新 raw_financials を用いて per, roe を計算。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズンの将来リターンを一度のクエリで取得。horizons の入力検証あり（1〜252 営業日）。
    - calc_ic: スピアマンのランク相関（IC）を実装（同順位は平均ランクで処理）。有効サンプルが 3 未満の場合は None を返す。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクとして扱うランク関数を実装（浮動小数点の丸めにより ties 検出漏れを防止）。

- 戦略（strategy）モジュール
  - feature_engineering.build_features:
    - research モジュールの calc_momentum / calc_volatility / calc_value を用いて生ファクターを取得・マージ。
    - ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を実装。
    - 指定カラムを z-score 正規化（kabusys.data.stats.zscore_normalize を使用）、±3 でクリップ。
    - 日付単位で features テーブルへ置換（BEGIN / DELETE / INSERT / COMMIT、ROLLBACK ハンドリング）。
    - 処理はルックアヘッドバイアス防止の観点から target_date 時点のデータのみを使用。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - デフォルト重み、閾値（デフォルト threshold=0.60）を実装。ユーザー指定 weights の検証・正規化機能を提供（未知キー・非数値・負値を無視、合計が 1 でない場合に再スケール）。
    - sigmoid、平均化ユーティリティを用いたスコア計算。欠損コンポーネントは中立値 0.5 で補完。
    - Bear レジーム判定（ai_scores の regime_score 平均が負なら Bear。ただしサンプル数閾値あり）。
    - BUY: threshold を超える銘柄に BUY シグナルを生成（Bear 時は抑制）。
    - SELL（エグジット判定）:
      - ストップロス（終値 / avg_price - 1 < -8%）
      - スコア低下（final_score < threshold）
      - positions / prices を参照して SELL 判定。価格欠損や avg_price 異常時のスキップとログ出力。
      - 未実装だが設計で想定されている条件（トレーリングストップ、時間決済）をコメントで明記。
    - signals テーブルへ日付単位の置換（トランザクションで原子性を保証）。BUY と SELL の優先ルール（SELL を優先し BUY から除外）を実装。

- DuckDB を中心としたデータパイプライン
  - 多くのモジュールで DuckDB 接続を受け取り、SQL と Python 組合せで処理を行う設計。
  - INSERT の冪等性、トランザクション管理、ログ出力を重視した実装。

### 変更（Changed）
- 初回リリースのため該当なし。

### 修正（Fixed）
- 初回リリースのため該当なし。

### 非推奨（Deprecated）
- 初回リリースのため該当なし。

### 削除（Removed）
- 初回リリースのため該当なし。

### セキュリティ（Security）
- news_collector で XML 関連の攻撃（XML Bomb 等）対策として defusedxml を使用。
- RSS 受信サイズに上限を設けることでメモリ DoS を緩和。
- J-Quants クライアントでリトライ時に Retry-After を尊重する等、外部 API 呼び出しの堅牢化を実施。

---

今後の注記（設計上の留意点）
- signal_generator のトレーリングストップや時間決済は positions テーブルに peak_price / entry_date 等の追加情報が必要であり、将来的に実装予定。
- research モジュールは外部依存（pandas 等）に依存しない設計だが、大規模データ処理や可視化は外部ツールとの連携を想定。