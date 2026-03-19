# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
このファイルは、ソースコードから推測される機能追加・仕様・既知の制約をもとに作成しています。

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-03-19
初回公開リリース。

### 追加 (Added)
- 基本パッケージ構成
  - パッケージエントリポイント: kabusys.__init__ (バージョン: 0.1.0)。
  - エクスポート: data, strategy, execution, monitoring モジュールを公開。

- 環境設定管理 (kabusys.config)
  - Settings クラスを提供し、主要な設定値を環境変数から取得。
  - 必須環境変数の検査（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
  - 環境値の検証（KABUSYS_ENV の許容値: development / paper_trading / live、LOG_LEVEL の検証）。
  - .env 自動読み込み機能:
    - プロジェクトルート（.git または pyproject.toml を基準）から .env と .env.local を自動読み込み。
    - 読み込み順: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサ実装:
    - export 形式対応、シングル/ダブルクォート処理、インラインコメント処理。
    - ファイル読み込み失敗時は警告を出力して継続。

- データ取得・保存機能 (kabusys.data.jquants_client)
  - J-Quants API クライアント:
    - 固定間隔スロットリングによるレート制御（デフォルト 120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回。HTTP 408/429 および 5xx をリトライ対象）。
    - 401 Unauthorized を検知すると自動でトークンをリフレッシュして再試行（1回のみ）。
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes: 日足（OHLCV）取得。
      - fetch_financial_statements: 四半期財務データ取得。
      - fetch_market_calendar: JPX カレンダー取得。
    - DuckDB への冪等保存関数:
      - save_daily_quotes: raw_prices テーブルに ON CONFLICT DO UPDATE で保存。
      - save_financial_statements: raw_financials テーブルに ON CONFLICT DO UPDATE で保存。
      - save_market_calendar: market_calendar テーブルに ON CONFLICT DO UPDATE で保存。
    - データ変換ユーティリティ: _to_float / _to_int（型安全に変換、失敗は None）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからの記事収集機能（デフォルト: Yahoo Finance のビジネス RSS を用意）。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等の防御）。
    - URL 正規化（トラッキングパラメータの除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。
    - 受信サイズ上限（10 MB）や SSRF を考慮した URL 検証の設計が示唆されている。
  - 記事 ID は URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性確保。
  - raw_news / news_symbols などのテーブルへバルク挿入を行う設計（チャンクサイズ制御）。

- リサーチ・ファクター計算 (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算（True Range 計算の NULL 考慮あり）。
    - calc_value: per, roe を raw_financials と prices_daily を組み合わせて算出。
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみ参照し、結果は (date, code) をキーとした dict のリストで返す。
  - feature_exploration モジュール:
    - calc_forward_returns: 将来リターン（デフォルト horizons=[1,5,21]）を計算（LEAD を用いた実装）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算（必要最小サンプル 3 を要求）。
    - factor_summary / rank: 基本統計量やランク付けユーティリティを提供。
  - research パッケージは zscore_normalize を外部（kabusys.data.stats）から利用できるよう再エクスポート。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date):
    - research モジュールのファクターを取得し、ユニバースフィルタを適用（最低株価 300 円、20日平均売買代金 5億円）。
    - 数値ファクターを Z スコア正規化し ±3 でクリップ。
    - 結果を features テーブルへ日付単位で置換（BEGIN/COMMIT を用いたトランザクション + bulk insert で原子性保証）。
    - 冪等設計: 既存 target_date の行を削除してから挿入。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - Z スコアをシグモイド変換し、欠損コンポーネントは中立値 0.5 で補完。
    - デフォルト重みは StrategyModel.md に準拠（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。ユーザ渡しの weights は検証・正規化される（非数値や負値は無視、合計が 1 に再スケール）。
    - Bear レジーム検知: ai_scores の regime_score 平均が負でサンプル数が閾値以上なら BUY シグナルを抑制。
    - SELL シグナル（エグジット）判定を実装（ストップロス -8% / final_score が閾値未満）。保有ポジションの価格欠損時には SELL 判定をスキップ。
    - signals テーブルへ日付単位で置換（トランザクションで原子性保証）。
    - 生成数をログ出力して返却。

### 変更 (Changed)
- 該当なし（初回リリース）。

### 修正 (Fixed)
- 該当なし（初回リリース）。

### セキュリティ (Security)
- news_collector は defusedxml を使用し XML 攻撃に対処する設計。
- ニュース収集時の URL 正規化・トラッキング除去や受信上限設定などで DoS/SSRF リスク低減を意図。
- J-Quants クライアントはトークンリフレッシュとエラーハンドリングを持ち、失敗時は明示的に例外を返す。

### 既知の制限 / 未実装の機能 (Known issues / TODO)
- signal_generator の一部エグジット条件は未実装（コード注記あり）:
  - トレーリングストップ（直近最高値からの −10%）
  - 時間決済（保有 60 営業日超過）
  - これらは positions テーブルに peak_price / entry_date が必要になる想定。
- news_collector の一部低レベルの SSRF 判定・IP ブロック等の実装詳細はソースコードのコメントにとどまる（追加実装の余地あり）。
- DuckDB のスキーマ（raw_prices / raw_financials / market_calendar / features / ai_scores / positions / signals / raw_news 等）は本 CHANGELOG に含まれないため、実行前にスキーマ定義・マイグレーションが必要。
- 一部関数は外部（kabusys.data.stats の zscore_normalize）に依存するため、依存モジュールの提供が前提。

### 注意事項 (Notes)
- 環境変数の自動ロードはプロジェクトルートの検出に依存する（.git / pyproject.toml）。配布環境での挙動に注意。自動ロードが不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- J-Quants API のレート制限・リトライポリシーはデフォルト設定を持つが、プロダクション要件に応じて min_interval 等の調整を検討してください。
- generate_signals の weights に不正値を渡した場合は警告が出てデフォルトにフォールバックされるため、重み設定は事前に検証することを推奨します。

---

CHANGELOG はコード内の設計コメント・実装から推測して作成しています。実際のリリースノートとして使用する場合は、テスト状況や実運用での挙動確認結果を反映して更新してください。