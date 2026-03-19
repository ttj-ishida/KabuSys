# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

なお本リポジトリの初回公開リリースとして以下を記載します。

## [0.1.0] - 2026-03-19

### Added
- パッケージの初期リリースを追加。
  - パッケージ情報:
    - 名前: kabusys
    - バージョン: 0.1.0

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動ロード機能を実装（プロジェクトルートは .git / pyproject.toml を探索して特定）。
  - .env パースの堅牢化（export プレフィックス対応、クォート内のエスケープ処理、インラインコメント処理など）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスによる型付きプロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として検査。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証。
    - データベースパスの既定値（DUCKDB_PATH, SQLITE_PATH）。
    - ユーティリティプロパティ: is_live / is_paper / is_dev。

- データ取り込み・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装:
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - レート制限対応（固定間隔スロットリング、デフォルト 120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回。HTTP 408/429/5xx を再試行対象）。
    - 401 Unauthorized 受信時のトークン自動リフレッシュ（1 回だけ）とモジュールレベルの ID トークンキャッシュ。
    - JSON デコード・エラーの扱い、ネットワークエラーのログと再試行。
  - DuckDB への冪等保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）を実装:
    - INSERT ... ON CONFLICT ... DO UPDATE による更新（重複排除）。
    - fetched_at を UTC isoformat で記録（look-ahead bias 対策）。
    - 型安全な変換ユーティリティ (_to_float / _to_int)。
    - PK 欠損行のスキップとログ出力。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news に保存する基盤を実装:
    - デフォルト RSS ソース（Yahoo Finance のビジネスカテゴリ）。
    - 受信サイズ上限（10MB）や受信時の安全対策。
    - URL 正規化（トラッキングパラメータ削除、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。
    - defusedxml を用いた XML パースによる安全性確保。
    - 記事ID の生成方針（正規化 URL の SHA-256 ハッシュ先頭等）により冪等性を確保。
    - DB へのバルク INSERT 最適化やチャンク処理。

- 研究用モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research):
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日データ有無を考慮）。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（ATR の NULL 伝播制御を含む）。
    - calc_value: per, roe（raw_financials の最新レコードを参照）。
    - DuckDB の SQL ウィンドウ関数を活用した効率的な実装。
  - 特徴量探索 (kabusys.research.feature_exploration):
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて取得。
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算。
    - rank: 同順位は平均ランクを割り当てるランク変換（丸めで ties 判定の精度向上）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - 研究側モジュールは外部パッケージ（pandas 等）へ依存せず、prices_daily / raw_financials のみ参照する設計。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date):
    - research の calc_* 関数から生ファクターを取得し、ユニバースフィルタを適用。
    - 数値ファクターを Z スコア正規化（zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE + INSERT をトランザクション内で行い冪等化）。
    - ユニバースフィルタ: 最低株価 300 円、20日平均売買代金 5 億円。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントの補完: None は中立値 0.5 で補完。
    - デフォルト重み (Section 4.1 相当): momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10。合計が 1.0 でない場合は再スケール。
    - final_score に基づいて BUY シグナルを生成（デフォルト閾値 0.60）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合）では BUY を抑制。
    - SELL シグナル（エグジット）判定:
      - ストップロス: 終値/avg_price - 1 < -8%（優先）
      - スコア低下: final_score < threshold
    - positions / prices_daily / ai_scores を参照して signals テーブルへ日付単位置換で書き込み（冪等）。
    - SELL 優先ポリシー（SELL 対象は BUY リストから除外しランク再付与）。
    - ロギングによる透明性確保。

### Changed
- 初版のため該当なし。

### Fixed
- 初版のため該当なし。

### Deprecated
- 初版のため該当なし。

### Removed
- 初版のため該当なし。

### Security
- XML パースに defusedxml を使用して XML Bomb 等の攻撃に対処（news_collector）。
- ニュース取得時に URL のスキームチェックやトラッキングパラメータ除去を実施し、SSR F/追跡パラメータの扱いを制御。
- J-Quants クライアントはトークン自動リフレッシュとリトライ戦略を実装し、認証エラーやレート制限時の堅牢性を確保。

### Notes / Known limitations / TODO
- 一部のエグジット条件は未実装（コード内コメント）:
  - トレーリングストップ（peak_price が positions に必要）
  - 時間決済（60 営業日超過）などは positions テーブルの拡張を要する。
- research モジュールは外部 ML ライブラリに依存しない純 Python 実装であり、大規模データ処理は DuckDB のクエリ性能に依存する。
- settings は必須環境変数の欠落時に ValueError を投げるため、デプロイ時に .env を適切に設定すること（.env.example を参照）。

### 環境変数（主要）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- 任意 / デフォルトあり:
  - KABUSYS_ENV (development | paper_trading | live; default: development)
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL; default: INFO)
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - KABUSYS_DISABLE_AUTO_ENV_LOAD (1 で自動 .env ロードを無効化)

---

今後のリリースでは、実運用に向けた以下の改善を予定しています（順不同）:
- execution 層（kabusys.execution）の具現化と kabu ステーション連携の実装。
- モニタリング・アラート機能（Slack 通知等）の追加。
- テストカバレッジ拡充・CI パイプライン整備。
- パフォーマンス最適化（大規模データ向けのバッチ戦略／並列化等）。