# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
慣例としてセマンティックバージョニングを採用しています。

現在のバージョン: 0.1.0

## [0.1.0] - 2026-03-18

初回公開リリース。日本株自動売買システム KabuSys の最初の主要機能セットを実装しました。以下はコードベースから推測される追加機能・設計方針・注意点の要約です。

### 追加 (Added)
- パッケージ基礎
  - パッケージ初期化情報を追加（kabusys.__version__ = "0.1.0"）。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ に設定。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動ロードする仕組みを実装。
  - プロジェクトルートの検出は __file__ を基点に .git または pyproject.toml を探索（CWD に依存しない）。
  - .env のパースを厳密に実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ文字等に対応）。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、必須設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を取得・検証。
  - 環境種別（development, paper_trading, live）およびログレベルのバリデーションを実装。
  - データベースパス（DuckDB/SQLite）のデフォルト値を提供。

- データ取得・保存 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
  - レート制限（120 req/min）の固定間隔スロットリング実装（RateLimiter）。
  - 再試行（指数バックオフ）ロジックを実装（最大3回、HTTP 408/429/5xx 等を対象）。
  - 401 Unauthorized 受信時はリフレッシュトークンから id_token を自動再取得して1回だけ再試行。
  - ページネーション対応（pagination_key）、ページ間でのトークンキャッシュ共有。
  - 取得データに対して fetched_at を UTC で記録し、Look-ahead バイアス対策を強化。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等性確保。
  - 安全なパースユーティリティ: _to_float, _to_int（"1.0" のような文字列処理や不正値の扱いに注意）。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィード収集パイプラインを実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection 等）。
  - セキュリティ / 安全対策:
    - defusedxml を用いた XML パース（XML Bomb 等への対策）。
    - SSRF 対策: リダイレクト先のスキーム検査、プライベートアドレス検出（_is_private_host）およびカスタム RedirectHandler による事前検証。
    - URL スキームの検証（http/https のみ許可）。
    - レスポンスの最大バイト数制限（MAX_RESPONSE_BYTES）と gzip 解凍後の再チェック。
  - コンテンツ前処理（URL 除去、空白正規化）と URL 正規化（トラッキングパラメータ除去、クエリソート）。
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
  - 銘柄コード抽出ユーティリティ（4桁の数字）と既知銘柄セットによるフィルタリング。
  - DB への挿入はチャンク化してトランザクション内で実行、INSERT ... RETURNING により実際に挿入された件数を返す。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution の層構造を想定したスキーマ定義を追加。
  - raw_prices, raw_financials, raw_news, raw_executions 等の DDL を提供（NOT NULL / CHECK / PRIMARY KEY 等の制約を含む）。

- 研究（Research）用ユーティリティ (src/kabusys/research/)
  - 特徴量探索モジュール (feature_exploration.py)
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、SQL で一括取得）。
    - IC（Information Coefficient）計算 calc_ic（Spearman の ρ：ランク化と ties の平均ランク処理を実装）。
    - 基本統計量 factor_summary（count/mean/std/min/max/median）。
    - rank 関数（同順位は平均ランク、丸め処理により浮動小数誤差を考慮）。
    - 標準ライブラリのみで実装（pandas 等に依存しない）。
  - ファクター計算モジュール (factor_research.py)
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA のデータ不足判定含む）。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（true range 計算・NULL 伝播に注意）。
    - calc_value: per, roe（raw_financials と prices_daily の組合せで最新財務データを使用）。
    - DuckDB をデータソースとした SQL + Python のハイブリッド実装。
  - research パッケージの __all__ に主要関数を公開。

### 変更 (Changed)
- （初回リリースのため、既存機能からの変更はありません）

### 修正 (Fixed)
- （初回リリースのため、バグ修正履歴はありません）

### セキュリティ (Security)
- NewsCollector:
  - defusedxml による XML パース、安全なリダイレクト検査、プライベートアドレス拒否、レスポンスサイズ制限など、外部入力処理における複数の防御策を実装。
- J-Quants クライアント:
  - レート制御・リトライ・トークンリフレッシュにより API 利用時の安定性と安全性を高める。

### 注意点 / 既知の制約 (Notes)
- research モジュールは本番口座や発注 API にはアクセスせず、DuckDB 内の prices_daily/raw_financials テーブルのみを参照する設計です（Look-ahead Bias に配慮）。
- NewsCollector の記事 ID は正規化 URL に基づくハッシュを用いるため、URL の正規化ロジックが変わると同一記事の扱いが変わる可能性があります。
- _to_int の実装は "1.0" のような文字列を float 経由で整数化するが、小数部が存在する場合は None を返し意図しない切り捨てを防ぐ挙動です。
- .env 自動読み込みはプロジェクトルートが見つからない場合はスキップされ、KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で明示的に無効化可能です。
- research 系関数は外部依存（pandas 等）を使わず標準ライブラリのみで実装されており、パフォーマンスや機能要件によっては将来的に最適化や外部ライブラリ導入を検討する余地があります。

---

今後のリリースでは以下のような項目が想定されます（例）:
- Strategy / Execution 層の具体的な発注ロジック・ポジション管理の実装
- モニタリング (Slack 通知など) の統合
- テストカバレッジと CI ワークフローの整備
- パフォーマンス最適化（DuckDB クエリのチューニング、並列収集等）

要望や補足の情報があればお知らせください。CHANGELOG の日付や細部表現は調整可能です。