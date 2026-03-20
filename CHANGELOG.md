# Changelog

すべての変更は Keep a Changelog の形式に従います。  
リリースはセマンティックバージョニングに従います。  

なお、以下は提示されたコードベースの内容から推測してまとめた初期リリースの変更履歴です。

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-03-20
初回リリース — 日本株自動売買システム「KabuSys」の基盤機能を実装。

### 追加
- 基本パッケージ構成
  - パッケージエントリポイント: kabusys パッケージ（version 0.1.0）。__all__ に data/strategy/execution/monitoring を公開。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準に探索）。
  - .env / .env.local の読み込み順や override 挙動を実装し、OS 環境変数を protected として上書きから保護。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
  - .env の行パーサを実装（コメント、export プレフィックス、クォートとエスケープ、インラインコメントの扱いなどを考慮）。
  - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス / システム設定（env, log_level 等）を環境変数から取得・検証。

- データ収集・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装：
    - 固定間隔スロットリングによるレート制御（120 req/min）。
    - リトライ（指数バックオフ、最大3回）、HTTP 408/429/5xx のリトライ、429 の Retry-After 優先。
    - 401 受信時の ID トークン自動リフレッシュ（1 回のみ）とモジュールレベルのトークンキャッシュを実装。
    - ページネーション対応（pagination_key を用いた逐次取得）。
    - 取得データに fetched_at（UTC ISO8601）を付与して「いつデータを知り得たか」を記録。
  - DuckDB への保存ユーティリティを実装（冪等性: ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes, save_financial_statements, save_market_calendar を提供。
    - 入力整形と型変換ユーティリティ（_to_float/_to_int）を実装。
    - PK 欠損行のスキップとログ警告を出力。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news に保存する基盤を実装。
  - セキュリティ対策:
    - defusedxml を使った XML パース（XML Bomb 等の防御）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を緩和。
    - URL 正規化とトラッキングパラメータ削除（utm_* 等）、SHA-256 ベースの一意ID生成による冪等性。
    - HTTP/HTTPS スキーム以外の URL を拒否する旨の設計（SSRF 緩和方針）。
  - バルク INSERT のチャンク化（_INSERT_CHUNK_SIZE）や DB トランザクションの集約でパフォーマンスを改善。

- リサーチ機能 (kabusys.research)
  - ファクター計算モジュール（factor_research）:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev を DuckDB の window 関数で計算。
    - calc_volatility: ATR（atr_20 / atr_pct）、avg_turnover、volume_ratio を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を算出。
    - 各関数は prices_daily / raw_financials のみ参照し、外部 API に依存しない設計。
  - 特徴量探索 (feature_exploration):
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて取得するクエリを実装。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。サンプル不足時の None 返却。
    - factor_summary: カラムごとの基本統計量（count/mean/std/min/max/median）を計算。
    - rank: 同順位は平均ランクで扱うランク関数を実装（丸め誤差対策に round を適用）。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features を実装:
    - research の calc_momentum/calc_volatility/calc_value を利用して生因子を取得。
    - ユニバースフィルタ（最低株価 _MIN_PRICE=300 円、20日平均売買代金 _MIN_TURNOVER=5e8 円）を適用。
    - 正規化: zscore_normalize を使用し指定カラムを Z スコア正規化、±3 でクリップ。
    - DuckDB の features テーブルへ日付単位の置換（DELETE + INSERT within トランザクション）で冪等性を保証。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals を実装:
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算。
    - コンポーネントはシグモイド変換や反転（volatility）などで [0,1] に変換。
    - 欠損コンポーネントは中立値 0.5 で補完。
    - final_score を重み付き合算（デフォルトウェイトを定義）し BUY 閾値（デフォルト 0.60）で判定。
    - Bear レジーム判定（ai_scores の regime_score の平均が負で一定サンプル数以上で Bear と判定）により BUY を抑制。
    - エグジット判定（売りシグナル）を実装（ストップロス -8% / final_score の閾値割れ）。トレーリングストップ等は未実装として注記。
    - signals テーブルへ日付単位の置換（DELETE + INSERT トランザクション）で冪等化。
    - weight 引数のバリデーション・正規化（未知キー・非数値・負値の無視、合計を 1.0 に正規化）を実装。

### 改善 / パフォーマンス
- DuckDB 側でのウィンドウ関数・集約クエリを多用し、大量データ処理のパフォーマンスを考慮した実装。
- API クライアント側で固定間隔スロットリングを実装し、レート制限を守ることで API からのスローを平準化。
- news_collector や保存処理でバルク挿入・チャンク化・単一トランザクション集約を用いて DB オーバーヘッドを低減。

### 修正 / ロバスト性
- .env パーサでのクォート内エスケープ対応やインラインコメントの扱いなど、実運用での .env の多様な記法に対応。
- API 異常系（HTTPError/URLError/OSError）に対して多段リトライ・バックオフ処理を実装。429 の Retry-After を尊重。
- JSON デコード失敗時の明示的なエラー報告（生レスポンスの先頭を含めて例外を発生）。
- DuckDB への保存処理で PK 欠損行をスキップし、スキップ件数をログに記録。

### セキュリティ
- RSS パースに defusedxml を利用して XML 攻撃に対処。
- ニュース収集で受信サイズを制限し、トラッキングパラメータ除去・URL 正規化で一意化と冪等性を担保。
- 環境読み込み時に OS 環境変数を protected として上書き防止。

### 未実装 / 既知の制限
- strategy のエグジット条件に関して、トレーリングストップや時間決済（保有日数基準）は未実装（positions テーブルに peak_price / entry_date 等が必要）。
- 一部の設計やドキュメント（StrategyModel.md, DataPlatform.md 等）を参照する実装注記があるが、これらのドキュメント自体は本リリースに含まれていない前提。
- execution（発注）層や monitoring 層はパッケージに名前空間は用意されているが、提示コード内では実装詳細が含まれていない。

### 既知のリスク / 注意点
- get_id_token は settings.jquants_refresh_token を必須とする。環境変数が未設定の場合は ValueError を発生。
- 自動 .env 読み込みはプロジェクトルート検出が失敗する（配布後等）とスキップされる点に注意。
- 一部の関数は DuckDB のテーブルスキーマ（columns, PK）に依存しているため、運用前にスキーマの整合性を確認すること。

---

今後の予定（例）
- execution（発注）層の実装（kabu ステーション API 経由の注文送信・状態管理）
- monitoring（稼働監視・アラート送信）モジュールの実装（Slack 連携等）
- トレーリングストップ・保有期間ルールなどエグジット条件の実装拡張
- テストカバレッジ強化、CI ワークフロー整備

（以上）