# Changelog

すべての変更は Keep a Changelog のフォーマットに従っています。  
現在のバージョン: 0.1.0（初期リリース）

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-19
初回公開リリース。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を設定。
  - 公開 API エントリポイントを定義（kabusys.data / kabusys.strategy / kabusys.execution / kabusys.monitoring を __all__ に登録）。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - 自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行う。
    - OS 環境変数＞.env.local＞.env の優先順位で読み込む。既存 OS 環境変数は保護される。
    - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理など）。
  - 設定取得ラッパー Settings を実装し、J-Quants のトークン、kabu API パスワード、Slack トークン/チャンネル、DB パス（DuckDB / SQLite）、稼働モード（development/paper_trading/live）やログレベルなどをプロパティで提供。
  - env 値のバリデーション（有効な env 値、LOG_LEVEL 値の検査）を実装。

- データ収集 / 保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - 固定間隔スロットリング（120 req/min）によるレート制御。
    - ネットワーク・HTTP 5xx / 408/429 等に対する指数バックオフリトライ（最大 3 回）。
    - 401 レスポンス時はリフレッシュトークンから自動的に ID トークンを再取得して 1 回再試行（無限再帰防止ロジックあり）。
    - ページネーション対応（pagination_key を利用して完全取得）。
    - 取得日時（fetched_at）を UTC で記録して look-ahead bias のトレースを容易に。
  - DuckDB への保存ユーティリティを実装（冪等性を ON CONFLICT DO UPDATE / DO NOTHING で確保）:
    - save_daily_quotes: raw_prices テーブルへ保存（PK 欠損行をスキップ）。
    - save_financial_statements: raw_financials テーブルへ保存（PK 欠損行をスキップ）。
    - save_market_calendar: market_calendar テーブルへ保存（取引日/半日/SQ フラグを型安全に格納）。
  - 型変換ユーティリティ（_to_float / _to_int）を実装。float 文字列→int の扱いや不正値時の None 戻しを定義。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を取得して raw_news に保存する基盤を実装。
    - デフォルト RSS ソース（Yahoo Finance Business 等）を定義。
    - 受信サイズ上限（MAX_RESPONSE_BYTES=10MB）によるメモリ DoS 対策。
    - 記事 ID を URL 正規化後の SHA-256（先頭 32 文字）で生成し冪等性を確保。
    - URL 正規化機能: スキーム/ホストの小文字化、トラッキングパラメータ（utm_*, fbclid, gclid 等）の除去、クエリキーソート、フラグメント削除。
    - defusedxml を利用した XML パースで XML Bomb 等の攻撃を緩和。
    - DB 挿入はバルク（チャンク化）かつトランザクションで実行し、INSERT RETURNING 相当の挙動で挿入数を正確に把握する方針。

- リサーチ（kabusys.research）
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR・相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。true_range の NULL 伝播を明示的に制御。
    - calc_value: raw_financials から最新の財務データを取得し PER / ROE を計算（EPS=0/欠損時は None）。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定 horizon（デフォルト [1,5,21]）の将来リターンを計算（営業日ベース）。
    - calc_ic: factor と将来リターンの Spearman ランク相関（IC）を算出（ties の扱い、最小サンプル検証）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクにするランク変換ユーティリティ。
  - これらは DuckDB（prices_daily / raw_financials）に対して SQL を実行する形で実装され、外部ライブラリ（pandas 等）に依存しない設計。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date): research 側で計算した生ファクターをマージ、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用、指定カラムを Z スコア正規化して ±3 でクリップし、features テーブルへ日付単位で置換（トランザクション＋バルク挿入で原子性を保証）。
  - 正規化対象カラムやクリップ値などは定数化。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントは欠損時に中立値 0.5 で補完し、不当な降格を防止。
    - 最終スコア final_score を重み付き合算で算出（デフォルト重みを持ち、ユーザ指定 weights は検証・正規化して適用）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつ十分なサンプル数）により BUY シグナルを抑制。
    - BUY 生成はしきい値超を採用。SELL はポジションテーブルを参照してストップロス（-8%）やスコア低下を判定。
    - 保持ポジションの価格欠損時は SELL 判定をスキップ（誤クローズ防止のため）。
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入で原子性）。
    - ロールバック失敗時にロギングして再送出する耐障害性を備える。

### Changed
- （該当なし：初回リリース）

### Fixed
- （該当なし：初回リリース）

### Security
- defusedxml を利用した RSS パースにより XML 脅威を軽減。
- ニュース URL の正規化とトラッキングパラメータ除去機能を実装し、ID 生成と冪等性を向上。
- .env ロード処理は OS 環境変数を保護する仕組みを導入（.env による上書きを制御）。

### Known limitations / Notes
- 一部のエグジット条件は未実装（コメントに記載）:
  - トレーリングストップ（peak_price / entry_date が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）など
- execution パッケージは現行コードベースでは空（発注層は分離を意図）。
- ニュース収集の SSRF 防止や IP ホワイトリスト等の詳細な検証ロジックは今後強化の余地あり（関連インポートはあるが実装の続きが想定される）。
- DuckDB をデータ層に利用する設計。SQLite（monitoring 用）や DuckDB のスキーマ準備が別途必要。
- research モジュールは外部ライブラリ非依存を維持するため、データフレーム系操作はすべて標準ライブラリ / SQL で実装。

---

作者・メンテナ情報やバグ報告、機能要求はリポジトリの Issue を利用してください。