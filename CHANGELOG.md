# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載します。  
このプロジェクトの最初の公開リリースを想定した変更点を、ソースコードから推測してまとめています。

全般的な方針
- DuckDB をローカルデータレイクとして利用し、prices_daily / raw_prices / raw_financials / features / ai_scores / positions / signals / market_calendar / raw_news 等のテーブルを想定した処理を実装。
- ルックアヘッドバイアス回避、冪等性（idempotency）、トランザクションによる原子性、入力データの欠損に対する堅牢性を設計目標に含める。
- 外部 API 呼び出しはレート制限・リトライ・トークンリフレッシュ等の堅牢な実装を行う。
- research 層は本番発注や外部サービスにアクセスしないことを明確に保持。

Unreleased
- （現時点なし）

0.1.0 - 2026-03-20
- Added
  - パッケージ初期化
    - kabusys パッケージを追加。__version__ = "0.1.0"、公開 API として data, strategy, execution, monitoring を __all__ に定義。
  - 環境設定管理（kabusys.config）
    - .env / .env.local の自動ロード機構を実装（プロジェクトルートは .git または pyproject.toml で探索）。
    - 自動ロード無効化用環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
    - .env のパースは export KEY=val 形式、クォート文字列（エスケープ対応）、インラインコメントの扱いをサポート。
    - .env.local は .env を上書きする形で適用、OS 環境変数は保護（protected）し上書きされない。
    - Settings クラスを実装し、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等の必須設定をプロパティとして提供。duckdb/sqlite のデフォルトパスや環境（development/paper_trading/live）/ログレベル検証を含む。
  - データ取得・保存（kabusys.data.jquants_client）
    - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制限制御（120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）、429 の Retry-After 優先扱い。
    - 401 受信時はリフレッシュトークンで id_token を自動更新して1回だけリトライ。
    - ページネーション対応の fetch_* 系関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB へ冪等保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT により更新処理を行い、PK 欠損行のスキップとログ出力を行う。
    - データ保存時に fetched_at を UTC ISO8601 で記録。
  - ニュース収集（kabusys.data.news_collector）
    - RSS フィードの収集と raw_news への冪等保存を実装する基盤を追加。
    - URL 正規化（トラッキングパラメータ除去、フラグメント削除、キーソート、小文字化）を実装。
    - defusedxml による XML パースで XML Bomb 等の攻撃対策を実装。
    - SSRF/不正スキーム対策や受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策を設計。
    - バルク INSERT のチャンク化（_INSERT_CHUNK_SIZE = 1000）を導入し、INSERT RETURNING 想定で挿入件数を正確に返す方針を採用。
  - 研究（research）モジュール
    - factor_research: モメンタム（calc_momentum）、ボラティリティ & 流動性（calc_volatility）、バリュー（calc_value）を実装。
      - Momentum: mom_1m / mom_3m / mom_6m、200日移動平均乖離率（ma200_dev）を算出。必要なウィンドウ件数が足りない場合は None を返す。
      - Volatility: 20日 ATR、相対 ATR (atr_pct)、20日平均売買代金(avg_turnover)、出来高比(volume_ratio) を算出。
      - Value: raw_financials から最終財務データを取得し PER / ROE を算出（EPS が 0/欠損のとき PER は None）。
      - クエリのスキャン範囲はパフォーマンス考慮でカレンダーバッファを置いている。
    - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリ（factor_summary）、ランク関数（rank）を実装。
      - calc_forward_returns はホライズン検証（1〜252営業日）を行い、同一クエリで複数ホライズンを取得。
      - calc_ic は Spearman の順位相関（ties は平均ランク）を実装し、有効レコード < 3 の場合は None を返す。
      - rank は round(v, 12) により浮動小数の丸め誤差を扱い、同順位は平均ランクを付与。
      - factor_summary は count/mean/std/min/max/median を返す（None 値は除外）。
    - research パッケージの公開 API を整理（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
  - 戦略（strategy）
    - feature_engineering.build_features を実装（研究側ファクターを正規化・合成して features テーブルへ UPSERT）。
      - ユニバースフィルタ（最低株価 _MIN_PRICE=300 円、20日平均売買代金 _MIN_TURNOVER=5e8 円）を適用。
      - 正規化は zscore_normalize を利用、Z スコアを ±3 でクリップ。
      - 日付単位での置換（DELETE + INSERT をトランザクション内で実行）により冪等性を保証。
    - signal_generator.generate_signals を実装（features と ai_scores を統合して BUY/SELL を生成して signals テーブルへ保存）。
      - コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、重み付き合算で final_score を算出（デフォルト重みを設定）。
      - デフォルト閾値 _DEFAULT_THRESHOLD = 0.60、ストップロス率 _STOP_LOSS_RATE = -0.08（-8%）。
      - AI レジームスコアの平均が負でサンプル数 >= _BEAR_MIN_SAMPLES（=3）の場合は Bear レジームとして BUY を抑制。
      - 欠損コンポーネントは中立 0.5 で補完し、不当な降格を防止。
      - BUY と SELL はトランザクション内で日付単位の置換を行い冪等性を保証。SELL 優先（SELL 対象は BUY から除外しランクを再付与）。
      - 不正な weights 値は無視し、合計が 1.0 でない場合は正規化して扱う。
  - ユーティリティ
    - データ型変換ユーティリティ（_jquants_client._to_float, _to_int）を実装。空文字や不正値は None に変換し、int 変換では小数部が非ゼロの値を排除。
    - RateLimiter クラスで固定間隔スロットリングを実装。
    - ニュース関連で NewsArticle 型定義を追加。

- Changed
  - （新規リリースのため該当なし）

- Fixed
  - （初回リリースのため該当なし）

- Removed
  - （初回リリースのため該当なし）

- Security
  - news_collector で defusedxml を使用して XML パースを行い、XML エンティティ攻撃を防止。
  - URL 正規化とトラッキングパラメータ除去、および受信サイズ制限を実装してメモリ DoS / トラッキング情報漏洩を軽減。
  - J-Quants クライアントはトークン管理と HTTP エラー処理（429 の Retry-After 優先）を実装し、誤ったリトライや無限再帰を防止する設計。

注記 / 既知の制限
- signal_generator のエグジット条件のうち「トレーリングストップ」や「時間決済（保有 60 営業日超過）」は未実装であり、positions テーブルに peak_price / entry_date 等の情報が必要となる。
- research モジュールは pandas 等の外部依存を持たない実装であり、パフォーマンス上の要件によっては将来的に最適化や外部ライブラリ採用が検討される可能性がある。
- .env ファイル自動ロードはプロジェクトルートの検出に依存するため、パッケージ配布後や別配置では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動設定を行うことを推奨。

必須環境変数（設定ガイド）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用（必須）
- KABUSYS_ENV: 環境識別（development / paper_trading / live）、デフォルトは development
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）、デフォルト INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化する場合に 1 を設定

開発者向けメモ
- DuckDB の接続オブジェクトを関数引数に渡す設計にしており、テスト時はインメモリや専用テスト DB での接続差し替えが容易。
- ほとんどの DB 書き込みはトランザクション（BEGIN / COMMIT / ROLLBACK）で囲んでおり、例外時には ROLLBACK を試行するロジックがある。
- ロギングは各モジュールで logger = logging.getLogger(__name__) を使用しており、アプリケーション側でハンドラ・レベルを設定可能。

Contributors
- この CHANGELOG はソースコードから自動推測して作成しています。実際のコミット履歴に基づく変更ログが必要な場合は git の履歴から詳細を抽出してください。