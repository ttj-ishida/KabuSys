# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 準拠で記載しています。  
このファイルにはパッケージ kabusys のリリース・変更点の要約を日本語で記載しています。

なお、コードベースから推測して記載しています。実際のコミット履歴ではありません。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-19

### Added
- パッケージ初期リリース: kabusys 0.1.0
  - Python パッケージのエントリポイント `kabusys` を提供。
  - __version__ = "0.1.0" を定義。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）。
    - 自動読み込みを無効化する env 変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - 高度な .env パーサを実装（コメント・クォート・export 形式・エスケープ対応）。
  - 既存 OS 環境変数を保護するための protected パラメータを導入し、.env の上書きを制御。
  - Settings クラスを提供し、主要設定をプロパティ経由で読み取り・バリデーションする:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスを提供）
    - KABUSYS_ENV（valid: development, paper_trading, live）
    - LOG_LEVEL（valid: DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - ヘルパープロパティ: is_live / is_paper / is_dev

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - 固定間隔のレート制限 (120 req/min) を守る RateLimiter を導入。
    - リトライロジック（指数バックオフ、最大 3 回）を実装し、408/429/5xx を再試行。
    - 401 応答時にリフレッシュトークンを用いてトークンを自動更新し 1 回リトライする仕組みを実装。
    - ページネーション対応（pagination_key を利用）。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を提供。
  - DuckDB への保存ユーティリティを提供（冪等性を考慮）:
    - save_daily_quotes: raw_prices テーブルに ON CONFLICT DO UPDATE で保存。
    - save_financial_statements: raw_financials テーブルに ON CONFLICT DO UPDATE で保存。
    - save_market_calendar: market_calendar テーブルに ON CONFLICT DO UPDATE で保存。
  - 値変換ユーティリティ _to_float / _to_int を実装（型安全・不正値に寛容）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事収集して raw_news へ保存する仕組みを実装。
  - セキュリティ重視の実装:
    - defusedxml を使用して XML Bomb 等を防御。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を設定しメモリ DoS を緩和。
    - URL 正規化とトラッキングパラメータ除去（utm_* 等）。
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を担保。
    - HTTP/HTTPS スキーム以外の URL を拒否することにより SSRF を軽減する方針（コード中の設計コメント）。
  - バルク INSERT のチャンクサイズやトランザクションのまとめ挿入により DB オーバーヘッドを削減。

- 研究モジュール（kabusys.research）
  - factor_research:
    - モメンタム（mom_1m, mom_3m, mom_6m, ma200_dev）計算（calc_momentum）。
    - ボラティリティ / 流動性指標（atr_20, atr_pct, avg_turnover, volume_ratio）計算（calc_volatility）。
    - バリュー（per, roe）計算（calc_value）。raw_financials と prices_daily を組み合わせて算出。
    - DuckDB のウィンドウ関数・LAG/AVG を活用した実装。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）: LEAD を使用して複数ホライズンの将来リターンを一括取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関（同順位は平均ランク）を実装。サンプル不足時は None を返す。
    - factor_summary: 基本統計量（count, mean, std, min, max, median）を標準ライブラリのみで計算。
    - rank ユーティリティ: 同順位の平均ランク算出（round 精度により ties を扱う）。
  - research パッケージは外部ライブラリ（pandas等）に依存しない設計。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date) を実装:
    - research の calc_momentum / calc_volatility / calc_value を呼び出して生ファクターを取得。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 数値ファクターを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）し ±3 でクリップ。
    - features テーブルへ日付単位で置換（削除 → 挿入）して冪等性を担保（トランザクション）。
  - 設計方針に「ルックアヘッドバイアス防止」「execution 層に依存しない」を明記。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装:
    - features と ai_scores を統合してコンポーネントスコア（momentum, value, volatility, liquidity, news）を計算。
    - コンポーネントの欠損は中立値 0.5 で補完。
    - weight の入力検証と正規化（未知キー・非数値・負値は無視、総和が 1 になるよう再スケール）。
    - final_score に基づいて BUY シグナル（閾値以上）を生成。デフォルト閾値 0.60。
    - Bear レジーム判定（ai_scores の regime_score の平均が負 → BUY 抑制）。サンプル数閾値を設け誤判定を防止。
    - エグジット判定（_generate_sell_signals）:
      - ストップロス（終値/avg_price - 1 < -8%）優先。
      - final_score が閾値未満での売却。
      - 価格欠損時は SELL 判定をスキップして誤クローズを防止。
    - signals テーブルへ日付単位で置換（トランザクション）。

- パッケージ API 整理
  - kabusys.strategy から build_features と generate_signals を直接 import 可能に設定。
  - kabusys.research の主要関数群を __all__ に列挙。

### Changed
- 初回リリースのため特になし（新規実装）。

### Fixed
- 初回リリースのため特になし。

### Deprecated
- なし

### Removed
- なし

### Security
- RSS パーシングに defusedxml を採用し、XML に起因する攻撃ベクトルを低減。
- ニュース収集時の受信サイズ制限と URL 正規化で SSRF / DoS リスクを考慮。

### Notes / Known limitations / TODOs
- execution パッケージは存在するが実装ファイルが空（発注実装は別途必要）。
- signal_generator のエグジット戦略にはトレーリングストップや時間決済の記述があるが未実装（positions テーブルに peak_price / entry_date が必要）。
- news_collector 内の「銘柄コードとの紐付け（news_symbols）」の実装は設計ドキュメントにはあるが、コード中の関連処理は限定的。実運用では記事→銘柄マッピングロジックの実装が必要。
- J-Quants クライアントはネットワーク/API のエラー処理を行うが、本番での挙動（特に rate limit やトークン管理）は実運用での監視・チューニングを推奨。
- zscore_normalize 関数は kabusys.data.stats で提供される前提。stats モジュールの依存に注意。

---

作成者注: 上記は提供されたソースコードの解析に基づく初回リリース向け CHANGELOG です。より細かい変更履歴（コミット毎の差分）は実際の VCS の履歴に基づいて作成してください。