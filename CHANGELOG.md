# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」仕様に準拠します。  

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-20
初回リリース。以下の主要機能および実装方針を含みます。

### Added
- パッケージ基盤
  - kubusys パッケージの初期公開（src/kabusys/__init__.py）。
  - バージョン情報: 0.1.0。

- 環境変数・設定管理
  - settings から各種必須設定を取得する Settings クラスを実装（src/kabusys/config.py）。
  - .env / .env.local の自動ロード機能（プロジェクトルート検出: .git / pyproject.toml に基づく）。
  - .env パーサの実装（export 形式対応、クォート／エスケープ／インラインコメント処理）。
  - 環境変数の自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須キー未設定時の _require による明確なエラーメッセージ。
  - env / log_level の入力検証（限定値チェック）および is_live/is_paper/is_dev 帯域プロパティ。

- データ取得・保存（J-Quants）
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
    - 固定間隔レートリミッタ（120 req/min）を実装。
    - 再試行ロジック（指数バックオフ、最大3回）と 408/429/5xx の再試行ハンドリング。
    - 401 受信時のトークン自動リフレッシュ（1 回のみ）を実装。
    - ページネーション対応の fetch_* 系関数:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務データ）
      - fetch_market_calendar（マーケットカレンダー）
    - DuckDB へ冪等保存する save_* 系関数:
      - save_daily_quotes → raw_prices テーブルへの ON CONFLICT DO UPDATE
      - save_financial_statements → raw_financials テーブルへの ON CONFLICT DO UPDATE
      - save_market_calendar → market_calendar テーブルへの ON CONFLICT DO UPDATE
    - データの型変換ユーティリティ _to_float / _to_int を実装し安全に変換。

- ニュース収集
  - RSS から記事を取得・正規化して raw_news に保存するニュースコレクタを実装（src/kabusys/data/news_collector.py）。
    - URL 正規化（トラッキングパラメータ除去、キーでソート、フラグメント削除）。
    - 記事ID を正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成して冪等性を確保。
    - defusedxml を使った XML パースと受信サイズ制限（MAX_RESPONSE_BYTES）。
    - SSRF / 不正スキーム対策・チャンク化によるバルク INSERT の最適化。

- リサーチ用モジュール
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - calc_volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）
    - calc_value（PER/ROE、raw_financials と prices_daily の結合）
    - 各関数は DuckDB の prices_daily / raw_financials を参照し、(date, code) ベースで結果を返す。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns（指定ホライズンの将来リターン計算、デフォルト [1,5,21]）
    - calc_ic（Spearman ランク相関での IC 計算）
    - factor_summary（count/mean/std/min/max/median の統計サマリー）
    - rank（同順位は平均ランクのランク関数）
  - zscore_normalize 用ユーティリティを research パッケージで再公開（src/kabusys/research/__init__.py）。

- 戦略実装（feature engineering / signal generation）
  - 特徴量作成（src/kabusys/strategy/feature_engineering.py）
    - research モジュールからの生ファクター取得（calc_momentum, calc_volatility, calc_value）。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）。
    - 正規化（z-score）対象カラムの指定と ±3 でのクリップ。
    - features テーブルへの日付単位 UPSERT（トランザクションで原子性保証）。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合して各銘柄の final_score を計算。
    - コンポーネント: momentum, value, volatility, liquidity, news（デフォルト重みを実装）。
    - 重みのバリデーション・合計が 1.0 でない場合の再スケーリング。
    - Sigmoid 変換や欠損補完（None は中立値 0.5）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負 → BUY 抑制）。
    - BUY（閾値デフォルト 0.60）・SELL（ストップロス -8% など）シグナル生成。
    - positions / prices を参照したエグジット判定と signals テーブルへの日付単位置換（原子性保証）。

### Changed
- ドキュメント・設計方針をソースコード内 docstring として詳細に追加。
  - ルックアヘッドバイアス回避、冪等性、外部依存の切り分けなどの設計指針を明記。
- SQL 実行は DuckDB を前提に最適化（ウィンドウ関数／LEAD/LAG の活用）。

### Fixed / Hardening
- .env パーサの堅牢化（クォート内のエスケープ処理、コメント処理、export プレフィックス対応）。
- J-Quants クライアント:
  - JSON デコード失敗時に詳細を含めて失敗させる実装。
  - 429 (Retry-After) ヘッダ優先の再試行待機を実装。
- ニュース収集:
  - defusedxml を利用して XML 関連攻撃を緩和。
  - 受信サイズ制限と URL 正規化により SSRF / トラッキング除去を考慮。
- DuckDB への保存で PK 欠損行をスキップし警告を出力（データ整合性を保護）。

### Known issues / Limitations
- signal_generator のエグジット条件で未実装のポリシー:
  - トレーリングストップ（peak_price が positions に必要）
  - 時間決済（保有 60 営業日超過）  
  — コード内に未実装コメントあり。
- NewsCollector の RSS フィードはデフォルトで Yahoo Finance のビジネスカテゴリのみを登録。追加ソースは利用者側で拡張が必要。
- get_id_token は settings.jquants_refresh_token に依存しているため、環境変数の設定が必須。
- 一部の数値変換は保守的（ex. _to_int は小数部が非ゼロの場合 None を返す）ため、入力データに依存したスキップが発生する可能性あり。

### Migration notes
- .env 自動読み込みの挙動:
  - パッケージ導入後、実行環境で .env / .env.local がある場合は自動的に読み込まれます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- settings による必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須。不足時は ValueError が発生します。

---

作成した CHANGELOG はコードベースから推測した初期リリースのまとめです。必要であれば、各項目をより細かいコミット単位や日付で追記できます。