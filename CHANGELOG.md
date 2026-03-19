# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

## [Unreleased]

---

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システムのコアライブラリを実装しました。以下はコードベースから推測される主要な追加機能・設計方針・既知の制約です。

### Added
- パッケージ基礎
  - kabusys パッケージ初期実装。バージョンは 0.1.0。
  - パブリック API エクスポート: build_features, generate_signals（kabusys.strategy）などを __all__ で公開。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml で探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パース機能: export プレフィックス対応、クォート内エスケープ、インラインコメントの扱いなど。
  - Settings クラス: 必須環境変数取得（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）、デフォルト値（KABU_API_BASE_URL, DB パス等）、値検証（KABUSYS_ENV, LOG_LEVEL）。
  - データベース既定パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。

- データ収集 / 保存 (kabusys.data)
  - J-Quants API クライアント (jquants_client)
    - RateLimiter による固定間隔スロットリング（120 req/min）。
    - 冪等な保存処理（DuckDB への INSERT ... ON CONFLICT DO UPDATE）。
    - リトライ戦略: 指数バックオフ、最大試行回数 3、408/429/5xx をリトライ対象。429 の場合は Retry-After ヘッダ考慮。
    - 401 Unauthorized 受信時は ID トークン自動リフレッシュ（1 回）して再試行。
    - ページネーション対応（pagination_key）。
    - 保存ユーティリティ: save_daily_quotes / save_financial_statements / save_market_calendar（各種 PK チェック、skipped ログ）。
    - データ変換ユーティリティ: _to_float, _to_int。
    - fetched_at を UTC ISO8601（Z）で記録し、look-ahead バイアスに対するトレーサビリティを提供。
  - ニュース収集モジュール (news_collector)
    - RSS フィード収集（デフォルトソース: Yahoo Finance ビジネスカテゴリ）。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）。
    - セキュリティ対策: defusedxml の利用、受信サイズ制限（10MB）、HTTP/HTTPS 以外拒否、IP/SSRF 対策想定（コメント・実装意図あり）。
    - 挿入はバルクで chunk（デフォルト 1000）に分割して実行。記事 ID は正規化 URL のハッシュで冪等性を確保する設計（仕様コメント）。
  
- 研究（Research）モジュール (kabusys.research)
  - factor_research: モメンタム / ボラティリティ / バリュー系ファクター計算機能
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200 日ウィンドウの存在チェック）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（true_range 計算の NULL 伝播制御）
    - calc_value: per, roe（raw_financials から target_date 以前の最新レコードを参照）
  - feature_exploration: 解析ユーティリティ
    - calc_forward_returns: 複数ホライズンの将来リターン取得（1,5,21 日がデフォルト）、SQL ロジックで効率的に取得
    - calc_ic: スピアマン順位相関（ランクの同位処理は平均ランク）
    - factor_summary: count/mean/std/min/max/median を計算
    - rank: 同順位を平均ランクで扱うランク付け（round(..., 12) による tie の安定化）
  - zscore_normalize は kabusys.data.stats（外部参照）から利用する設計（実装ファイルは今回提示分に含まれず参照のみ）。

- 戦略（Strategy）モジュール (kabusys.strategy)
  - feature_engineering.build_features
    - research のファクター（calc_momentum / calc_volatility / calc_value）をマージ、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 正規化（z スコア）を適用し ±3 でクリップ。features テーブルへ日付単位で置換（BEGIN/DELETE/INSERT/COMMIT）、冪等性を確保。
    - DuckDB の prices_daily / raw_financials を参照。
  - signal_generator.generate_signals
    - features と ai_scores を統合し最終スコア（final_score）を計算。
    - コンポーネントスコア: momentum, value, volatility, liquidity, news（AI スコア）。
    - 重みの検証と正規化（デフォルト重みは momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）。
    - デフォルト BUY 閾値 0.60、ストップロス -8%。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合。ただしサンプル数が閾値未満なら Bear としない）。
    - BUY は閾値超過かつ Bear でなければ生成。SELL はストップロス・スコア低下で生成。保有銘柄は positions テーブルを参照。
    - signals テーブルへ日付単位で置換（トランザクション処理）。
    - weights に不正値（未知キー、NaN/Inf、負値、bool 等）が含まれる場合は警告して無視し、合計が 1.0 でなければリスケールまたはデフォルトにフォールバック。

### Changed
- （初回リリースにつきなし）

### Fixed
- （初回リリースにつきなし）

### Security
- 外部データ取り込み箇所で複数の安全策を採用（defusedxml、受信サイズ制限、HTTP スキーム制限、token refresh の安全化など）。
- J-Quants クライアントは認証トークンをキャッシュし、トークン再発行時の無限再帰を防ぐ設計。

### Known limitations / 未実装
- signal_generator のエグジットルール
  - コメントで「未実装」と明記された条件あり:
    - トレーリングストップ（peak_price が positions に必要）
    - 時間決済（保有 60 営業日超過）
  - positions テーブルに peak_price / entry_date が存在しないと未実装条件は動作しない。
- news_collector の一部セキュリティ（SSRF/IP フィルタ等）は設計方針として記載されているが、提示ファイルでは細部実装が省略されている可能性あり。
- data.stats.zscore_normalize の実装ファイルは本差分に含まれていない（外部参照）。同関数に依存する機能はその実装が必要。
- DuckDB スキーマ依存
  - 多数のモジュールが特定のテーブル（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar, raw_news 等）を前提としているため、利用前にスキーマを整備する必要がある。

### Migration notes / 開発者向け注意
- 環境変数の未設定は Settings._require により ValueError を送出するため、初期セットアップ時に必須変数を .env 等で設定してください。
- .env 読み込みはプロジェクトルート探索に依存するため、パッケージ配布後に期待通りに動作させるにはプロジェクトルート要件（.git または pyproject.toml）に注意してください。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定。
- J-Quants API 利用時はレート制限・認証・リトライ動作に注意。大量データ収集時は RateLimiter の振る舞いが全体のスループットに影響します。
- signal_generator の weights に対する入力は厳密に検証されます。不正な値は無視されるため、カスタム重みを与える場合は数値と合計を確認してください。

---

（注）本 CHANGELOG は提示されたソースコードから推測して作成しています。実際のリリースノートや追加情報はプロジェクトの公式リリース記録を参照してください。