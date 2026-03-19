# Changelog

すべての重要な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システム「KabuSys」の基本機能を実装しました。以下はコードベースから推測される主な追加点・設計方針・既知の制約です。

### Added
- パッケージのエントリポイントとバージョン
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を定義。
  - __all__ に data, strategy, execution, monitoring を公開。

- 環境設定管理
  - src/kabusys/config.py
    - .env/.env.local 自動読み込み（OS 環境変数優先、.env.local は上書き可）。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）。
    - シンプルな .env パーサを実装（export 形式、クォートとエスケープ、インラインコメント処理に対応）。
    - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / 環境・ログレベル等のプロパティを取得。
    - 環境変数検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。

- データ収集・保存（J-Quants クライアント）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装。ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - レート制限を守る固定間隔スロットリング（120 req/min）を実装する RateLimiter。
    - リトライ戦略（指数バックオフ、最大3回、408/429/5xx を対象）。429 の Retry-After ヘッダ尊重。
    - 401 時の自動トークン再取得（get_id_token）とモジュール内トークンキャッシュを実装。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を提供し、ON CONFLICT を用いた冪等保存をサポート。
    - データ型変換ユーティリティ（_to_float, _to_int）を用意し不正データを寛容に扱う。

- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィードから記事を収集・正規化して raw_news に保存する処理を実装。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリキーソート）。
    - defusedxml を用いた XML インジェクション対策、受信サイズ上限（10MB）、SSRF 対策（HTTP/HTTPS スキームのみ想定）などの安全対策を採用。
    - 記事ID を URL 正規化後の SHA-256（先頭 32 文字）で生成する運用を想定。
    - バルク挿入時のチャンク処理を導入（SQL 長やパラメータ数対策）。

- 研究・因子計算
  - src/kabusys/research/factor_research.py
    - Momentum, Volatility, Value（PER/ROE など）ファクター計算を実装:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA の欠損処理あり）。
      - calc_volatility: 20 日 ATR（atr_20/atr_pct）、avg_turnover、volume_ratio（欠損時の扱いを明確化）。
      - calc_value: prices_daily と raw_financials を結合して PER/ROE を計算。
    - DuckDB（prices_daily / raw_financials）を前提とした SQL ベースの実装。営業日数に対する窓幅やスキャン範囲に考慮（カレンダー日バッファ）。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（複数ホライズン、単一クエリ実行、ホライズン検証）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンのρ をランク平均扱いで計算、サンプル不足時は None）。
    - ランク変換 util rank（同順位は平均ランク、浮動小数丸め処理あり）。
    - factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等の外部依存を用いない実装方針。

  - src/kabusys/research/__init__.py で主要関数を公開（calc_momentum, calc_volatility, calc_value, zscore_normalize 等）。

- 特徴量エンジニアリング
  - src/kabusys/strategy/feature_engineering.py
    - research で計算した生ファクターをマージしユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定された正規化対象カラムを zscore_normalize（kabusys.data.stats から）で正規化し ±3 でクリップ。
    - features テーブルへの日付単位の置換（トランザクション + バルク挿入で原子性を保証）。
    - ルックアヘッドバイアス対策として target_date 時点までのデータのみ参照。

- シグナル生成（戦略）
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合して最終スコア final_score を計算し BUY/SELL シグナルを生成。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI スコアをシグモイド変換で扱う）。
    - 重みの受け取りと検証（未知キー除外、非数/負値スキップ）、合計が 1.0 でない場合の再スケール処理を実装。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合。ただしサンプル数が閾値未満なら Bear としない）。
    - BUY: threshold（デフォルト 0.60）超えの銘柄を上位から採用。Bear レジーム時は BUY を抑制。
    - SELL: 保有ポジションに対するエグジット判定を実装（ストップロス -8%、final_score が閾値未満）。保有銘柄の価格欠損時は判定をスキップして誤クローズを防止。
    - signals テーブルへの日付単位置換（トランザクションで原子性確保）。
    - 未実装のエグジット条件をコード内コメントで明示（トレーリングストップ、時間決済などは将来対応予定）。

- モジュール API エクスポート
  - src/kabusys/strategy/__init__.py で build_features, generate_signals を公開。
  - src/kabusys/research/__init__.py で主要な研究 API を公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- news_collector で defusedxml を使用して XML 関連攻撃に対応。
- RSS 受信サイズ上限、URL 正規化、トラッキングパラメータ除去、HTTP/HTTPS のみ許可など SSRF/DoS 対策を実装。
- J-Quants クライアントは HTTP エラーやネットワーク例外に対してリトライとバックオフを実装し、429 の Retry-After を尊重。

### Notes / Known limitations / TODO
- signal_generator 内の一部エグジット条件（トレーリングストップ、時間決済）は未実装。これらは positions テーブルに peak_price / entry_date 等の追加列が必要と明記。
- execution モジュールは空のパッケージとして存在（発注ロジックは別層で実装する想定）。
- monitoring モジュールは __all__ に含まれるが、この差分では実装コードが見当たらない（別途実装予定か既に別ファイルに存在する可能性）。
- news_collector の記事 ID は SHA-256(先頭32文字) を用いることが想定されているが、重複判定/マッピング処理の詳細は実運用で確認が必要。
- settings の必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）が未設定の場合は ValueError を送出するため、デプロイ前に .env の準備が必要。

### Public API（主な関数）
- kabusys.config.settings（Settings インスタンス）
- kabusys.data.jquants_client:
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- kabusys.data.news_collector: URL 正規化などのユーティリティ（news 収集フロー）
- kabusys.research:
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize
- kabusys.strategy:
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=..., weights=...)

---

今後のリリースでは、execution 層（発注実装）、monitoring（監視・アラート）、未実装のエグジットルールの追加、より詳細なテスト、ドキュメントの拡充を予定してください。