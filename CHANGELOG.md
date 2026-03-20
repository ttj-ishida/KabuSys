# Changelog

すべての変更は Keep a Changelog の形式に従います。セマンティックバージョニングを使用します。

## [Unreleased]
（なし）

## [0.1.0] - 初回リリース
最初の安定リリース。日本株自動売買システムのコア機能群を実装しました。主にデータ取得・保存、因子計算（research）、特徴量生成（strategy）、シグナル生成、環境設定ユーティリティを含みます。

### Added
- パッケージ基礎
  - パッケージ情報とバージョンを追加（kabusys.__version__ = "0.1.0"）。
  - 公開 API を整理（kabusys.__all__ に data/strategy/execution/monitoring）。

- 環境設定 / ロード (.env)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を検出）から自動ロードする仕組みを実装（kabusys.config）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パースの堅牢化：
    - コメント・空行を無視、`export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - インラインコメント処理（クォート有無で挙動を分離）。
    - 無効行のスキップ。
  - OS 環境変数を保護する protected オプション（.env.local は override=True による上書きが可能）。
  - Settings クラスを提供し、必須環境変数取得（_require）・既定値・値検証を実装：
    - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等を必須として取得。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証。
    - データベースパス（DUCKDB_PATH / SQLITE_PATH）の Path 変換ユーティリティ。
    - is_live / is_paper / is_dev ヘルパー。

- データ取得・保存（J-Quants）
  - J-Quants API クライアントを実装（kabusys.data.jquants_client）：
    - 固定間隔スロットリングによるレート制御（120 req/min）。
    - リトライ（指数バックオフ、最大3回）と HTTP ステータスに基づく挙動（408/429/5xx の再試行、429 の Retry-After 優先）。
    - 401 発生時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）：
      - 冪等性のため ON CONFLICT（アップサート）を使用。
      - PK 欠損行のスキップと警告ログ。
      - fetched_at を UTC で記録（Look-ahead バイアス対策トレーサビリティ）。
    - 入力データの安全な型変換ユーティリティ (_to_float / _to_int)。

- ニュース収集
  - RSS ベースのニュース収集モジュール（kabusys.data.news_collector）を追加：
    - デフォルト RSS ソース（Yahoo Finance のビジネスカテゴリ）を準備。
    - 記事 ID を URL 正規化後の SHA-256（先頭 32 文字）で生成し冪等性を確保。
    - URL 正規化でトラッキングパラメータ（utm_* 等）を除去、クエリをソート、フラグメント除去。
    - defusedxml を使った XML パースで XML Bomb 等への対策。
    - HTTP 応答サイズ上限（MAX_RESPONSE_BYTES = 10MB）設定でメモリDoS軽減。
    - SSRF を避けるための URL スキームチェックやホスト扱いの保守（実装方針に基づく）。
    - DB へバルク挿入（チャンク処理）と ON CONFLICT DO NOTHING による冪等保存。

- 研究（Research）モジュール
  - ファクター計算群を実装（kabusys.research.factor_research）：
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日MAの乖離）を DuckDB のウィンドウ関数で計算。データ不足時に None を返す。
    - calc_volatility: 20日 ATR, atr_pct（ATR/close）, avg_turnover（20日平均売買代金）, volume_ratio（当日/20日平均）を計算。true_range の NULL 伝播制御。
    - calc_value: raw_financials から最新財務を取得して PER（price / EPS）・ROE を計算。財務データの最新レコード抽出に ROW_NUMBER を使用。
  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）：
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来終値リターンを一括取得。ホライズン検証（正の整数 ≤ 252）。
    - calc_ic: ファクターと将来リターンの Spearman（ランク）相関を実装（有効レコードが 3 未満は None）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
    - rank: 同順位は平均ランクを採るランク関数（浮動小数の丸めで ties 対応）。
  - research パッケージの __all__ を整備（calc_momentum 等をエクスポート）。
  - 研究コードは標準ライブラリのみ依存の設計（pandas 等に依存しない）。

- 戦略（Strategy）
  - 特徴量生成（kabusys.strategy.feature_engineering）を実装：
    - 外部 research の calc_momentum / calc_volatility / calc_value を呼び出して生ファクターを取得。
    - ユニバースフィルタ（最低株価 _MIN_PRICE=300 円、20 日平均売買代金 _MIN_TURNOVER=5e8）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）し ±3 でクリップ（外れ値抑制）。
    - features テーブルへ日付単位で置換（DELETE + bulk INSERT、トランザクションで原子性保証）して冪等化。
    - 価格取得は target_date 以前の最新価格を参照して休場日や当日欠損に対応。
  - シグナル生成（kabusys.strategy.signal_generator）を実装：
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を計算。
    - コンポーネントはシグモイド変換・平均化で正規化。欠損コンポーネントは中立値 0.5 で補完。
    - final_score を重み付き合算（デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。ユーザ指定の weights は検証・補正（既知キーのみ、負値や非数は無視、合計で再スケール）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数が閾値を満たす場合 buy を抑制）。
    - BUY 閾値デフォルト _DEFAULT_THRESHOLD = 0.60。
    - エグジット（SELL）判定を実装（stop_loss -8% を最優先。final_score < threshold による売却など）。保有銘柄の価格欠損時は SELL 判定をスキップして誤クローズを防止。
    - SELL 優先ポリシー: SELL 対象は BUY から除外し、BUY のランクを再付与。
    - signals テーブルへ日付単位の置換（トランザクションで原子性保証）して冪等化。
    - ロギングによる状況通知（WARN/INFO/DEBUG）。

### Changed
- 設計上の方針や実装注意点を明確化（ルックアヘッドバイアス回避、発注層への依存を持たない、DuckDB のみ参照等）。
- DB 操作は可能な限りトランザクションとバルク挿入でまとめ、原子性と性能を考慮。

### Fixed / Robustness
- データ欠損や異常値に対する堅牢化：
  - 価格や統計値が None / 非有限（NaN/Inf）の場合は適切にスキップまたは None を返す。
  - save_* 系の関数で PK 欠損行をスキップし警告を出力。
  - _to_int で "1.0" のような文字列を float 経由で int に変換し、小数部がある場合は None を返すことで想定外の切り捨てを防止。
  - トークン取得・HTTP リクエストでの再試行とログ出力を整備。

### Security / Safety
- defusedxml を使用した XML パースで RSS の安全処理を実装。
- ニュース収集における受信サイズ制限や URL 正規化によるトラッキング除去、SSRF 対策方針を盛り込む。
- J-Quants クライアントにおける認証トークンの安全なリフレッシュとキャッシュ。

---

必要であれば、各モジュールの詳細な変更点や使用例、マイグレーション手順（既存 DB スキーマ等）を追記します。どの部分を詳しく書き起こしましょうか？