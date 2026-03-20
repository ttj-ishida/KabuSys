# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。日付は本リリース作成日です。

全般注記:
- この CHANGELOG はリポジトリ内のソースコード（docstring/実装）から推測して作成したものです。実際の運用上の振る舞いはテスト・実行環境での確認を推奨します。

## [Unreleased]
- 今後のリリース計画・未実装機能の記載
  - strategy のエグジット条件に記載されている「トレーリングストップ」「時間決済」はドキュメントに記載があるが未実装。
  - execution パッケージはプレースホルダ（空の __init__）のまま。発注レイヤーの実装が必要。
  - news_collector の記事→銘柄紐付け（news_symbols）などの運用処理や追加の RSS ソース設定は今後拡充予定。

---

## [0.1.0] - 2026-03-20
初回リリース

### 追加 (Added)
- パッケージ基盤
  - パッケージのバージョンを定義（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開 API のエクスポート定義（strategy, execution, data, monitoring 配下を想定）。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local 自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。
  - .env ファイルの堅牢なパース実装を追加（コメント、export プレフィックス、シングル／ダブルクォート、エスケープ処理に対応）。
  - 環境変数の取得ヘルパー Settings クラスを実装。主要設定項目をプロパティとして提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL のバリデーション
    - is_live / is_paper / is_dev の便宜プロパティ

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアント実装:
    - 固定間隔の RateLimiter（120 req/min）でレート制御。
    - 冪等的な API 呼び出しラッパー（ページネーション対応）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 受信時にリフレッシュトークンで id_token を自動更新して 1 回リトライ。
    - 取得時刻（fetched_at）を UTC ISO8601 で記録し、look-ahead バイアスのトレースに対応。
  - データ保存関数（DuckDB 用）を追加:
    - save_daily_quotes: raw_prices への冪等的保存（ON CONFLICT DO UPDATE）。
    - save_financial_statements: raw_financials への冪等的保存（ON CONFLICT DO UPDATE）。
    - save_market_calendar: market_calendar への冪等的保存（ON CONFLICT DO UPDATE）。
  - HTTP ユーティリティおよび型変換ユーティリティ (_to_float/_to_int) を実装。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからの記事収集と raw_news への保存ロジック（設計仕様を実装）。
  - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ削除、フラグメント削除、クエリキーソート）。
  - セキュリティ対策: defusedxml を用いた XML パース、HTTP スキーム検証、受信サイズ上限（MAX_RESPONSE_BYTES）など。
  - 記事ID は正規化 URL の SHA-256（先頭 32 文字）等で冪等性を担保する方針。
  - バルク INSERT チャンク処理と INSERT RETURNING を念頭に置いた実装設計。

- 研究用ユーティリティ (kabusys.research)
  - ファクター計算モジュール (factor_research):
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率 (ma200_dev) の計算。
    - calc_volatility: 20日 ATR、相対 ATR (atr_pct)、20日平均売買代金 (avg_turnover)、volume_ratio の計算。
    - calc_value: PER / ROE を raw_financials と prices_daily から計算（最新財務レコードを参照）。
  - 特徴量探索モジュール (feature_exploration):
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効サンプル >= 3 が必要）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 同順位を平均ランクで扱うランク化ユーティリティ（丸めによる ties 対応）。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features を実装:
    - research モジュールの calc_momentum / calc_volatility / calc_value を用いて生ファクターを取得。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 にクリップ。
    - features テーブルへの日付単位の置換（DELETE + bulk INSERT をトランザクションで実行）で冪等性と原子性を確保。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals を実装:
    - features / ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - デフォルトウェイトとユーザー指定ウェイトのマージ・再スケール処理（不正値は無視）。
    - final_score に基づく BUY シグナル生成（デフォルト閾値 0.60）。Bear レジーム検知時は BUY を抑制。
    - 保有ポジションのエグジット判定（stop_loss: -8% 目安、score_drop）による SELL シグナル生成。
    - SELL 優先で BUY を除外し、signals テーブルへ日付単位の置換で保存（トランザクション化）。

- パッケージ __init__・export
  - strategy.__init__ で build_features / generate_signals をエクスポート。
  - research.__init__ で主要ユーティリティ・関数をエクスポート。

### 変更 (Changed)
- （初回リリースのため過去の変更はなし）

### 修正 (Fixed)
- （初回リリースのため過去の修正はなし）

### セキュリティ (Security)
- news_collector で defusedxml を使用し XML 関連攻撃（XML Bomb 等）を緩和。
- RSS 取得時の受信バイト上限を設定しメモリ DoS を軽減。
- URL 正規化とトラッキングパラメータ除去により一貫した ID 生成と冪等性を向上。

### 既知の未実装・制約 (Known issues / Limitations)
- strategy の一部エグジット条件（トレーリングストップ、時間決済）は未実装。positions テーブルに peak_price / entry_date 等の追跡カラムが必要。
- execution レイヤ（実際の発注ロジック）は現状未定義であり、本実装はシグナル生成までを想定している（発注は別実装を期待）。
- news_collector の SSRF 判定や詳細なホワイトリスト検査は設計上の言及はあるが、実装の詳細は要確認。
- DuckDB スキーマ（テーブル定義）はこのコードからは直接提供されないため、本実装を利用するには適切なスキーマ作成が必要。

---

開発者向けメモ:
- Settings は環境変数未設定時に ValueError を投げる必須プロパティがあるため、CI / 実行環境での .env 設定に注意してください。
- J-Quants クライアントはネットワーク・HTTP エラーに対してリトライとトークン自動更新を備えますが、実稼働では API レートやレスポンス挙動に応じた監視を推奨します。