# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-03-19

### Added
- パッケージ初期リリース。
  - パッケージ名: kabusys、バージョン: 0.1.0
  - パッケージ公開 API を __init__ で定義（data, strategy, execution, monitoring をエクスポート）。

- 環境設定読み込み機能（kabusys.config）
  - .env / .env.local ファイルまたは環境変数から設定を読み込む自動ローダ実装。
  - プロジェクトルート探索は __file__ を起点に .git または pyproject.toml を検出して決定（CWD に依存しない挙動）。
  - .env のパースは以下をサポート・考慮:
    - 空行・コメント行（先頭の #）の無視
    - export KEY=val 形式の対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしの行でのインラインコメント扱い（# の直前がスペース/タブでのみコメントと判定）
  - 読み込み順序: OS 環境 > .env.local（上書き）> .env（未設定のものを補う）
  - OS 環境変数の保護（読み込み時に protected set を使って上書きを防止）
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途）
  - 必須環境変数取得ヘルパ _require を提供（未設定時は ValueError を送出）

- 設定ラッパー Settings（kabusys.config.settings）
  - J-Quants / kabuAPI / Slack / DB パス等のプロパティを提供
  - env（KABUSYS_ENV）や log_level（LOG_LEVEL）の妥当性チェック（許容値の列挙）
  - is_live / is_paper / is_dev の便利プロパティ

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API 向けクライアントを実装
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（内部 RateLimiter）
  - リトライ / 指数バックオフ（最大 3 回、408/429/5xx を対象）および 429 の場合は Retry-After を考慮
  - 401 受信時に自動でリフレッシュトークンから id_token を再取得して 1 回リトライ（無限再帰防止）
  - ページネーション対応（pagination_key によるループ）を実装した fetch_* 関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（マーケットカレンダー）
  - DuckDB への保存ユーティリティ（冪等性を担保する ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes -> raw_prices テーブル
    - save_financial_statements -> raw_financials テーブル
    - save_market_calendar -> market_calendar テーブル
  - レコード変換ユーティリティ _to_float / _to_int（安全な型変換）

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を取得して raw_news に保存するフローを実装
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等の防御）
    - HTTP/HTTPS スキーム以外拒否、受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）
    - URL 正規化時にトラッキングパラメータ（utm_* 等）を除去、ソート、フラグメント除去
    - 記事 ID は正規化 URL の SHA-256 ハッシュ（先頭 32 文字）を採用して冪等性確保
  - バルク INSERT のチャンク処理、DB 保存は可能な限りトランザクションでまとめる設計
  - デフォルト RSS ソースに Yahoo Finance（business category）を追加

- 研究用ファクター計算 / 探索機能（kabusys.research）
  - factor_research:
    - calc_momentum（1M/3M/6M リターン、ma200 乖離）
    - calc_volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）
    - calc_value（最新財務データと株価から PER / ROE を計算）
    - 各関数は DuckDB の prices_daily / raw_financials を参照し、(date, code) キーの dict リストを返す設計
  - feature_exploration:
    - calc_forward_returns（指定ホライズン [1,5,21] をデフォルトにした将来リターン計算、ホライズン検証あり）
    - calc_ic（Spearman のランク相関（IC）計算、サンプル不足時は None）
    - factor_summary（count/mean/std/min/max/median を算出）
    - rank（同順位は平均ランク、丸め誤差対策に round(..., 12) を使用）
  - DuckDB SQL と Python を組み合わせた実装で外部依存を最小化

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date) を実装:
    - research の calc_momentum / calc_volatility / calc_value から生ファクターを取得
    - ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用
    - 指定カラムに対して zscore_normalize を適用（_NORM_COLS）
    - Z スコアを ±3 でクリップして外れ値の影響を抑制
    - features テーブルへ日付単位で削除→挿入する置換（トランザクションで原子性を保証）
    - 処理はルックアヘッドバイアスを避ける設計（target_date 時点のデータのみを使用）

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - シグモイド変換や平均化を用いたスコア計算（欠損コンポーネントは中立 0.5 で補完）
    - デフォルト重みを定義し、ユーザ提供 weights を検証・補完・再スケールして合計 1.0 に調整
    - Bear レジーム判定（ai_scores の regime_score 平均が負で、かつサンプル数が閾値以上の場合に BUY を抑制）
    - BUY シグナル閾値デフォルト 0.60、SELL（エグジット）条件の実装:
      - ストップロス: 終値/avg_price - 1 < -8%
      - スコア低下: final_score < threshold
      - （トレーリングストップや時間決済は未実装・要 positions に peak 等の追加情報）
    - SELL 優先ポリシー（SELL 対象は BUY から除外）、signals テーブルへ日付単位の置換で書き込み（原子性保証）
    - ログ出力により欠損データや異常値を警告

### Changed
- （初回リリースのため変更履歴はなし）

### Fixed
- （初回リリースのため修正履歴はなし）

### Security
- news_collector で defusedxml を利用して XML パースの脆弱性に対処
- RSS / URL 正規化・検証で SSRF・トラッキングパラメータ・大容量レスポンスなどの対策を実装

---

注:
- 各モジュール内にはロギング・警告出力が多数実装されており、運用時の異常検知に役立ちます（例: .env 読み込み失敗、PK 欠損によるスキップ、価格欠損による SELL 判定スキップ 等）。
- 実行環境（DB スキーマや外部トークン等）の準備が必要です。README/ドキュメントの .env.example を参照して環境変数を設定してください。