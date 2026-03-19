KEEP A CHANGELOG
すべての重要な変更を記録します。  
このファイルは「Keep a Changelog」仕様に準拠しています。

[Unreleased]

[0.1.0] - 2026-03-19
Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージのトップレベル __init__ により主要サブパッケージを公開: data, strategy, execution, monitoring。

- 環境設定/読み込み機能（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - プロジェクトルート検出: __file__ を基準に .git または pyproject.toml を探索して自動で .env/.env.local を読み込む実装を追加。CWD に依存しないためパッケージ配布後も動作。
  - .env パーサを強化:
    - export プレフィックス対応、
    - シングル/ダブルクォートのエスケープ処理、
    - インラインコメント扱いの判定（クォート有無での扱い差）などに対応。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。自動読み込みを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須設定の取得用 _require と Settings のプロパティ群を提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - 環境（KABUSYS_ENV）・ログレベル（LOG_LEVEL）のバリデーション、パス設定（DUCKDB_PATH/SQLITE_PATH）の Path 返却を実装。

- データ収集クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制限保護（固定間隔スロットリング、デフォルト 120 req/min）を実装する RateLimiter。
  - リトライロジック（指数バックオフ、最大 3 回）を実装。HTTP 408/429/5xx を再試行対象に含める。429 の場合は Retry-After を優先。
  - 401 (Unauthorized) 受信時にリフレッシュトークンから ID トークンを自動更新して 1 回リトライする仕組みを実装。モジュールレベルで ID トークンをキャッシュしページネーション間で共有。
  - ページネーション対応の fetch_* 関数群を実装:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（マーケットカレンダー）
  - DuckDB への保存関数を実装（冪等性を確保する ON CONFLICT DO UPDATE を利用）:
    - save_daily_quotes → raw_prices（fetched_at を UTC ISO8601 で記録）
    - save_financial_statements → raw_financials
    - save_market_calendar → market_calendar
  - 入力変換ユーティリティ: _to_float / _to_int を厳密に実装し、型エラーや不正な値に安全に対応。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news に冪等保存する実装。
  - 安全対策:
    - defusedxml を使用して XML BOM 等の攻撃対策。
    - 受信最大バイト数（10 MB）に制限してメモリ DoS を防止。
    - URL 正規化・トラッキングパラメータ除去（utm_* 等）を実装。正規化後の URL を基に SHA-256 の先頭 32 文字を記事 ID として生成し冪等性を保証。
    - HTTP/HTTPS 以外のスキームを拒否する方針（SSRF 対策）。
  - バルク INSERT のチャンク化（デフォルト 1000 件）やトランザクションでの一括保存、実際に挿入されたレコード数の正確な取得を設計。

- 研究用モジュール（kabusys.research）
  - ファクター計算・探索用ユーティリティを追加。
  - calc_momentum / calc_volatility / calc_value を実装（kabusys.research.factor_research）。
    - Momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200 日移動平均乖離）を DuckDB のウィンドウ関数で実装。
    - Volatility: 20 日 ATR（true_range の NULL 伝播制御）、atr_pct、avg_turnover、volume_ratio を計算。
    - Value: raw_financials から最新財務を取得して PER/ROE を計算（EPS = 0/欠損時は None）。
    - 各関数は prices_daily / raw_financials のみ参照し、外部 API にはアクセスしない設計。
  - feature_exploration を追加:
    - calc_forward_returns（指定ホライズンに対する将来リターン、複数ホライズン対応・入力検証あり）
    - calc_ic（Spearman の ρ をランクベースで計算、ties を平均ランクで処理）
    - factor_summary（count/mean/std/min/max/median を標準ライブラリのみで計算）
    - rank ユーティリティ（同順位は平均ランク、round(..., 12) による ties 対策）
  - 研究モジュールは pandas 等の外部依存を使わず標準ライブラリ + duckdb で実装。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research で計算した raw factor を正規化・合成して features テーブルへ保存する build_features を追加。
  - 処理フローを実装:
    1. calc_momentum / calc_volatility / calc_value から raw factor を取得
    2. ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用
    3. 数値ファクターを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップ
    4. features テーブルへ日付単位で置換（DELETE->INSERT をトランザクションで行い原子性を保証）
  - 欠損や価格取得失敗等のエッジケースに配慮し、ログ出力を行う設計。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して最終スコア final_score を計算し BUY/SELL シグナルを生成する generate_signals を追加。
  - 実装のポイント:
    - コンポーネントスコア（momentum, value, volatility, liquidity, news）を計算。Z スコアはシグモイド変換で [0,1] にマップ。
    - value（PER）は 1/(1 + per/20) で正規化。
    - volatility は反転シグモイド（低ボラ = 高スコア）。
    - AI news スコアは存在しない場合中立（0.5）で補完。
    - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10。weights 引数は検証・フィルタリングし合計が 1 になるよう再スケール。
    - BUY 閾値のデフォルトは 0.60。Bear レジーム（ai_scores の regime_score 平均が負かつサンプル >= 3）では BUY を抑制。
    - エグジット（SELL）判定:
      - ストップロス: 終値/avg_price - 1 < -8% が最優先
      - final_score が threshold 未満 → score_drop
      - 価格欠損時は SELL 判定をスキップ（誤クローズ回避）しログを出力
    - SELL 優先ポリシー: SELL 対象は BUY から除外し、残りの BUY を再ランク付け。
    - signals テーブルへ日付単位で置換（トランザクション + バルク挿入）し冪等を保証。
    - ログ出力（INFO/DEBUG/警告）を充実させて運用時のトレーサビリティを確保。

Changed
- （このバージョンは初期リリースのため「Changed」は該当なし）

Fixed
- （初期リリース）

Removed
- （初期リリース）

Security
- defusedxml の採用や受信サイズ制限、URL スキーム検証、.env ファイル読み込み時の警告等、外部攻撃（XML BOM / SSRF / 大容量レスポンス）に対する予防策を導入。

その他 / 設計注記
- DuckDB を中心とした設計: 多くの計算は SQL ウィンドウ関数で実装し、Python 側は結合・後処理に集中。これにより大量データ処理の効率を確保。
- ルックアヘッドバイアス防止: 全ての集計・シグナル生成は target_date 時点の利用可能データのみを参照する方針で実装。
- 外部 API への直接発注ロジック（execution 層）や本番口座連携は strategy 層から切り離しており、シグナル生成は DB 内の signals テーブルへの出力に限定。
- research モジュールは本番データや発注 API にアクセスしないことを明確に設計。

開発者向け補足（使用例）
- 設定読み込み:
  from kabusys.config import settings
  token = settings.jquants_refresh_token
- ファクター構築:
  from kabusys.strategy import build_features
  build_features(conn, target_date)
- シグナル生成:
  from kabusys.strategy import generate_signals
  generate_signals(conn, target_date)

既知の制限・未実装の機能
- signal_generator のトレーリングストップ・時間決済は positions テーブルに peak_price / entry_date 等が必要なため未実装（注釈あり）。
- news_collector の記事→銘柄紐付け（news_symbols）の具体的な実装は設計書に基づくが、本リリースでは汎用的な収集/正規化/保存基盤を提供。

---- 
注: 日付はこのアーカイブのスナップショット日（2026-03-19）を使用しました。リリース履歴に合わせて日付を調整してください。