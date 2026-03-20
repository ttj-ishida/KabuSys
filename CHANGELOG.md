CHANGELOG
=========
すべての変更は Keep a Changelog の形式に準拠して記載しています。

[Unreleased]
-------------
（なし）

[0.1.0] - 2026-03-20
--------------------
Added
- 初期リリース: KabuSys 日本株自動売買システムのコア機能を実装。
  - パッケージエントリポイント
    - src/kabusys/__init__.py にてバージョン "0.1.0" と公開モジュール (data, strategy, execution, monitoring) を定義。

- 設定・環境変数管理
  - src/kabusys/config.py
    - .env ファイルおよび OS 環境変数からの設定読み込み機能を実装。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）を導入し、カレントワーキングディレクトリに依存しない自動ロードを実現。
    - .env の行パーサーで export 構文、シングル/ダブルクォート、エスケープ、インラインコメントの扱いをサポート。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD のサポート。
    - 必須環境変数を取得する Settings クラスを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）。
    - DB パス（DUCKDB_PATH/SQLITE_PATH）のデフォルト値と KABUSYS_ENV / LOG_LEVEL のバリデーションを実装。

- データ取得・永続化（J-Quants クライアント）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装（株価日足、財務データ、マーケットカレンダー取得）。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx を再試行対象）、429 の場合は Retry-After 優先。
    - 401 発生時のトークン自動リフレッシュを1回行う仕組み（id_token キャッシュと get_id_token）。
    - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT による更新で重複排除。
    - レスポンスパース、安全な数値変換ユーティリティ（_to_float, _to_int）を実装。
    - fetched_at は UTC で記録（Look-ahead バイアス対策）。

- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィードから記事を取得して raw_news に保存するための基盤を実装。
    - URL 正規化（トラッキングパラメータ削除、クエリソート、フラグメント削除、小文字化）やテキスト正規化処理のユーティリティを実装。
    - defusedxml を用いた安全な XML パース、受信サイズ制限（MAX_RESPONSE_BYTES）などのセキュリティ対策。
    - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを設定。
    - 記事の冪等性を意図した ID 生成（ヘッダコメントでの設計方針として SHA-256 を使用する方針を明記）。

- 研究（Research）モジュール
  - src/kabusys/research/factor_research.py
    - モメンタム、ボラティリティ、バリュー等のファクター計算関数を実装:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日MAのデータ不足は None）
      - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（ATR にデータ不足チェック）
      - calc_value: per / roe（raw_financials の最新財務レコードから取得、EPS=0 は None）
    - DuckDB の prices_daily / raw_financials を前提にし、本番 API 等への依存を持たない設計。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（horizons のバリデーション、1クエリで複数ホライズン取得）。
    - スピアマンランク相関による IC 計算 calc_ic（同順位は平均ランク処理、最小サンプル数チェック）。
    - ランク変換ユーティリティ rank（同順位の平均ランク、丸めによる ties 検出対策）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median）。
  - research パッケージ __all__ を整理して外部公開。

- 特徴量エンジニアリング
  - src/kabusys/strategy/feature_engineering.py
    - research モジュールの生ファクターを統合し、ユニバースフィルタ（最低株価300円、20日平均売買代金 >= 5億円）を適用。
    - 正規化（zscore_normalize を利用）後に ±3 でクリップして外れ値を抑制。
    - DuckDB の features テーブルへ日付単位で置換（DELETE してから INSERT。トランザクションで原子性確保）。
    - ユニバース判定用に target_date 以前の最新価格を参照し、祝日・欠損に対応。

- シグナル生成
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成して signals テーブルへ書き込む。
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）の計算ロジックを実装（シグモイド変換、欠損は中立0.5で補完）。
    - 重み（_DEFAULT_WEIGHTS）と閾値（デフォルト 0.60）の取り扱い。ユーザー指定 weights の検証・フォールバック・再スケーリング。
    - Bear レジーム判定（ai_scores の regime_score の平均が負でサンプル数閾値以上の場合に BUY 抑制）。
    - SELL のエグジット判定を実装（ストップロス -8% と final_score の閾値割れ）。positions / prices_daily を参照。
    - signals テーブルへ日付単位の置換（トランザクションで原子性）。BUY と SELL の優先ルール（SELL 優先で BUY から除外）。

- パッケージ公開
  - src/kabusys/strategy/__init__.py で build_features / generate_signals を公開。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- defusedxml を利用した安全な RSS パース、受信サイズ制限、URL のスキーマ検証など SSRF/XML Bomb/DoS に対する予防的対策を設計ドキュメントと実装方針に反映。

Notes / Known issues / TODO
- エグジット条件の未実装部分（feature_engineering / signal_generator のドキュメントに記載）
  - トレーリングストップ（peak_price 必要）
  - 時間決済（保有 60 営業日超過）
- news_collector の記事 ID 生成や実際の RSS フェッチの一部実装は設計方針で記載されているが、モジュール末尾が切れているため（このバージョンでは）一部処理の最終実装・テストが必要。
- execution パッケージは現時点で初期化のみ（発注ロジックは別途実装予定）。
- DuckDB スキーマ（raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals 等）は本ライブラリの前提だが、スキーマ定義・マイグレーションツールは別途整備が必要。
- 単体テスト・統合テストは本リリースに含まれない（今後追加予定）。
- 設定取得で必須の環境変数が未設定の場合 ValueError を送出するため、導入時に .env の用意または環境変数設定が必要。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

References
- 各モジュール内の docstring に StrategyModel.md / DataPlatform.md 等の参照が記載されています。詳細設計・仕様はリポジトリ内の該当ドキュメントを参照してください。