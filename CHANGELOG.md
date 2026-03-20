# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。  
現在のパッケージバージョン: 0.1.0

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-20

初回リリース。本リポジトリの主要機能・モジュールを実装しました。主な追加点・設計方針は以下の通りです。

### Added
- パッケージ基盤
  - パッケージメタ情報（kabusys.__version__ = "0.1.0"）を導入。
  - public API を __all__ で整理（data, strategy, execution, monitoring）。

- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード:
    - プロジェクトルート判定は .git または pyproject.toml に基づく（CWD非依存）。
    - ロード順: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
    - 既存 OS 環境変数は保護（protected）して上書きを制御。
  - .env パーサは export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理に対応。
  - 必須環境変数取得のための _require と、env/log_level の値検証を実装。
  - 設定項目例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、DUCKDB_PATH、SQLITE_PATH、KABUSYS_ENV、LOG_LEVEL。

- データ取得 / 保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装:
    - レート制限（120 req/min）を固定間隔スロットリングで遵守する RateLimiter。
    - リトライ（指数バックオフ、最大3回）と 408/429/5xx のリトライ判定。
    - 401 受信時は自動でリフレッシュトークンから ID トークンを取得して 1 回リトライ（トークンキャッシュを共有）。
    - ページネーション対応（pagination_key を利用）。
    - JSON デコード失敗などのエラー判定・詳細メッセージ。
  - データ保存関数（DuckDB 用）を提供:
    - save_daily_quotes / save_financial_statements / save_market_calendar：いずれも冪等（ON CONFLICT DO UPDATE / DO NOTHING）で保存。
    - fetched_at は UTC ISO8601 で記録。
    - 型変換ユーティリティ（_to_float / _to_int）を実装し不正データを安全に扱う。
    - PK 欠損レコードはスキップし、スキップ数をログ出力。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集モジュールを実装（既定ソース: Yahoo Finance のビジネスRSS）。
  - セキュリティと堅牢性:
    - defusedxml を利用して XML 攻撃を防止。
    - 受信サイズ上限（10 MB）を設けメモリ DoS を軽減。
    - URL 正規化（tracked パラメータ除去、クエリソート、フラグメント除去）、SSRF を意識したスキーム制限（HTTP/HTTPS）。
    - 記事ID は URL 正規化後の SHA-256（先頭32文字）を採用し冪等性を保証。
  - DB 保存はチャンク処理、単一トランザクションでパフォーマンスと整合性を確保。

- リサーチ（kabusys.research）
  - 研究用ユーティリティ群を実装（外部依存なし、標準ライブラリ + DuckDB）。
  - feature_exploration:
    - calc_forward_returns: 指定日から将来リターンを計算（デフォルト horizons=[1,5,21]）。
    - calc_ic: スピアマンのランク相関（IC）を計算。サンプル不足（<3）は None を返す。
    - factor_summary: count/mean/std/min/max/median の統計サマリー。
    - rank: 同順位は平均ランクで処理（float 丸めで ties 検出安定化）。
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility: atr_20、atr_pct、avg_turnover、volume_ratio を計算（true_range の NULL 伝播に注意）。
    - calc_value: latest 財務データと当日の株価を組合せて per / roe を算出（EPS=0/NULL の場合は per=None）。
  - 設計方針として prices_daily / raw_financials のみ参照し、本番発注等へ影響しないことを保証。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features を追加:
    - research モジュールの生ファクターを結合、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5億円）を適用。
    - Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップして外れ値を抑制。
    - features テーブルへ日付単位で置換（DELETE + bulk INSERT をトランザクションで実行し原子性を保証）。
    - 設計上、target_date 時点のデータのみを利用しルックアヘッドバイアスを防止。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals を追加:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - コンポーネントはシグモイド変換／平均化し、欠損コンポーネントは中立 0.5 で補完。
    - デフォルト重みと閾値: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10、BUY 閾値 0.60。
    - ユーザ提供の weights を検証・正規化（未知キーや負値・非数は無視、合計が 1.0 になるよう再スケール）。
    - Bear レジーム検知（ai_scores の regime_score 平均が負の場合）では BUY を抑制。
    - SELL 生成（保有ポジションのストップロス -8%、final_score が閾値未満等）を実装。
    - signals テーブルへ日付単位の置換（DELETE + INSERT をトランザクションで実行）。
    - positions / prices_daily から価格を取得できない場合の安全対策（ログ出力し判定をスキップ）。

- DB 操作の原子性・冪等性
  - features / signals / raw_* / market_calendar 等の挿入はトランザクション + ON CONFLICT / DELETE-then-INSERT のパターンで原子性・冪等性を確保。

### Security
- ニュース収集で defusedxml を利用して XML の脆弱性を軽減。
- RSS URL の正規化・トラッキング除去・スキームチェックにより SSRF / 準備攻撃対策を実施。
- J-Quants クライアントでトークンの自動リフレッシュとキャッシュ、タイムアウト、リトライ制御を実装し誤動作・過負荷を抑制。

### Known limitations / TODOs
- signal_generator の未実装項目（コメントに記載）:
  - トレーリングストップ（peak_price が positions テーブルに必要）。
  - 時間決済（保有 60 営業日超過の自動決済）。
- calc_value は PBR / 配当利回りを未実装。
- execution 層（発注 API 連携）はパッケージ内にスケルトンのみであり、実稼働用の実装は別途。
- news_collector の詳細な URL ホワイトリストやネットワーク制限は追加検討の余地あり。
- 一部の検証（大規模データ下のパフォーマンス、極端な欠損データケース等）は実運用での確認が必要。

### Minor
- 各モジュールでログ出力（logger）を適切に導入し、運用時の可観測性を確保。

---

参考: 本 CHANGELOG はソースコード内の docstring / コメント・実装から推測して作成しています。実際のリリースノート作成時はプロジェクト方針・リリース履歴に基づいて適宜調整してください。