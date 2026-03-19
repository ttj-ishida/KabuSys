# CHANGELOG

すべての日付はコミット時点の目安です。セマンティックバージョニングを採用します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システムのコアモジュール群を実装しました。

### 追加
- パッケージ基盤
  - パッケージ初期化を追加（kabusys.__init__）。バージョンは `0.1.0`。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に設定。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートは `.git` または `pyproject.toml` を基準に自動検出（CWD 非依存）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env 行パーサを実装（export 形式、クォート、エスケープ、インラインコメント対応）。
  - Settings クラスを提供（プロパティ経由で設定値取得）。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID）。
    - DB デフォルトパス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。
    - 環境モード検証（development / paper_trading / live）、ログレベル検証。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - レート制限（120 req/min）の固定間隔スロットリング実装。
    - リトライロジック（指数バックオフ、最大 3 回）および 429 の Retry-After 利用。
    - 401 受信時の自動トークンリフレッシュ（1 回）対応。
    - ページネーション対応の fetch 関数:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務データ）
      - fetch_market_calendar（取引カレンダー）
    - DuckDB への冪等保存関数:
      - save_daily_quotes -> raw_prices（ON CONFLICT DO UPDATE）
      - save_financial_statements -> raw_financials（ON CONFLICT DO UPDATE）
      - save_market_calendar -> market_calendar（ON CONFLICT DO UPDATE）
    - 取得時刻（fetched_at）を UTC ISO8601 で記録し look-ahead bias のトレースを可能に。
    - 入力パースユーティリティ（_to_float / _to_int）。

- ニュース収集（kabusys.data.news_collector）
  - RSS からの記事収集の基盤を実装（RSS ソースのデフォルト、XML パース、URL 正規化等）。
    - defusedxml を用いた安全な XML パース。
    - 受信サイズ上限（10 MB）や SSRF 対策の考慮。
    - 記事ID を URL の正規化 + SHA-256 ハッシュで生成して冪等性を確保。
    - raw_news へのバルク保存設計（INSERT RETURNING を想定、チャンク処理）。
    - URL 正規化機能（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化など）。

- リサーチ（kabusys.research）
  - 研究向けユーティリティとファクター計算を実装・公開。
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率。
    - calc_value: PER / ROE（raw_financials と prices_daily を組合せ）。
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）の将来リターン計算（1 クエリで取得）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算。
    - factor_summary: 各ファクター列の基本統計量（count, mean, std, min, max, median）。
    - rank: 同順位を平均ランクで扱うランク付けユーティリティ（丸めで ties 検出を安定化）。
  - 研究モジュールは DuckDB の prices_daily / raw_financials のみ参照し、本番 API 等にはアクセスしない設計。

- 戦略（kabusys.strategy）
  - feature_engineering.build_features:
    - research 側の生ファクターを統合し正規化して features テーブルへ UPSERT（日付単位で置換）。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）。
    - Z スコア正規化（対象カラム指定）、±3 でクリップ、欠損処理。
    - トランザクション + バルク挿入で原子性を保証。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して final_score を計算し、BUY / SELL シグナルを生成して signals テーブルへ書き込む（日付単位置換）。
    - コンポーネントスコア:
      - momentum（momentum_20, momentum_60, ma200_dev のシグモイド平均）
      - value（PER ベースの逆スケール）
      - volatility（atr_pct の Z スコア反転 → シグモイド）
      - liquidity（volume_ratio のシグモイド）
      - news（AI スコアのシグモイド、未登録時は中立）
    - 欠損コンポーネントは中立（0.5）で補完。
    - 重み（デフォルト値）を受け取り検証・正規化（負値・NaN 等は無視、合計が 1 に再スケール）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合は BUY を抑制）。
    - SELL ルール:
      - ストップロス（終値/avg_price - 1 <= -8%）
      - final_score が閾値を下回る（threshold デフォルト 0.60）
    - エグジット判定は保有（positions）テーブルの最新レコード基づく。価格欠損時は判定をスキップ。

### 仕様メモ / 設計上の注意
- DB スキーマ（tables）やカラム名（prices_daily, raw_prices, raw_financials, features, ai_scores, signals, positions, market_calendar 等）は各モジュールの SQL に依存します。運用前にスキーマ整備が必要です。
- settings の必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- 自動 .env ロードはプロジェクトルート検出に失敗した場合はスキップされます（テスト・配布時の安全策）。
- jquants_client のレート制御は固定間隔スロットリングです。厳密な同時並列呼び出しがある場合は別途調整が必要です。
- news_collector は RSS の解析や URL 正規化でセキュリティ対策（defusedxml、受信サイズ制限、SSRF 対策）を想定していますが、外部ソースの多様性に伴う追加対応（文字コードやエンコーディング等）が必要になる場合があります。

### 既知の未実装 / 将来の拡張予定
- signal_generator 内の一部エグジット条件は未実装（トレーリングストップ、時間決済）。positions テーブルに peak_price / entry_date 等が必要。
- news_collector のさらなるフィード追加、記事→銘柄紐付けロジックの強化（現状は基本処理）。
- より厳密なレート制御（トークンバケット等）や非同期実行対応の検討。
- 単体テスト・統合テストのカバレッジ拡充。

### 依存関係（実装で使用）
- duckdb
- defusedxml
- 標準ライブラリ（urllib, json, datetime, logging, math, hashlib 等）

---

この CHANGELOG はコードベースから推測して作成しています。実際のコミット履歴やリリースノートに合わせて適宜調整してください。