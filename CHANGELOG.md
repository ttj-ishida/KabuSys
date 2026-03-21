# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

- リリース管理方針: ここではリポジトリ現時点の最初の公開バージョン 0.1.0 の変更点を記載します。

## [Unreleased]
（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-21

### 追加 (Added)
- パッケージの初期公開: kabusys - 日本株自動売買システム（__version__ = 0.1.0）。
- 環境設定管理モジュール (kabusys.config)
  - .env および .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする仕組みを実装。
  - 行パーサー実装: export プレフィックス、クォート文字列、インラインコメント、エスケープシーケンスに対応。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須設定取得ヘルパー _require() を提供。
  - settings オブジェクトを公開し、J-Quants / kabu / Slack / DB / 環境種別・ログレベルなどの設定プロパティを追加（既定値とバリデーション含む）。
- データ取得・保存モジュール (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装（株価日足・財務データ・マーケットカレンダー取得）。
  - レート制限対応: 固定間隔スロットリング（120 req/min）を実装する RateLimiter を導入。
  - リトライロジック: 指数バックオフ、最大3回リトライ（408/429/5xx 対象）、429 の場合は Retry-After を優先。
  - 401 時の自動トークンリフレッシュ（1回のみ）とモジュール内トークンキャッシュを実装。
  - ページネーション対応で全件取得を行う fetch_* 関数群を実装。
  - DuckDB への冪等保存関数を実装（save_daily_quotes / save_financial_statements / save_market_calendar）: ON CONFLICT DO UPDATE / DO NOTHING を利用。
  - 型安全な変換ユーティリティ (_to_float / _to_int) を実装。
- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS から記事を収集し raw_news に保存する基盤を実装（デフォルト RSS ソースを含む）。
  - セキュリティと堅牢性: defusedxml を用いた XML パース、受信サイズ上限（MAX_RESPONSE_BYTES）、URL 正規化（トラッキングパラメータ除去・フラグメント除去・キーソート）、記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を保証。
  - バルク INSERT のチャンク処理を考慮した設計。
- リサーチ（研究）モジュール (kabusys.research)
  - ファクター計算モジュール（factor_research）を実装:
    - Momentum（mom_1m / mom_3m / mom_6m / ma200_dev）
    - Volatility（atr_20 / atr_pct / avg_turnover / volume_ratio）
    - Value（per / roe。raw_financials の最新レコードを参照）
    - DuckDB の SQL とウィンドウ関数を組み合わせた実装で、営業日欠損や部分ウィンドウに配慮。
  - 特徴量探索モジュール（feature_exploration）を実装:
    - calc_forward_returns（複数ホライズンの将来リターンを一括で取得）
    - calc_ic（スピアマンのランク相関による IC 計算、サンプル数チェック）
    - factor_summary（count/mean/std/min/max/median の統計サマリー）
    - rank（平均ランクを用いる同順位処理）
  - zscore_normalize を公開（kabusys.data.stats 経由で利用想定）。
- 戦略モジュール (kabusys.strategy)
  - 特徴量エンジニアリング（feature_engineering.build_features）
    - research モジュールの生ファクターを統合し、ユニバースフィルタ（最低株価・平均売買代金）を適用。
    - 指定カラムを Z スコア正規化し ±3 でクリップ。
    - DuckDB のトランザクション + 日付単位の置換（DELETE + bulk INSERT）で冪等に features テーブルを更新。
  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。重み（デフォルト値は StrategyModel に基づく）を受け取り合成。
    - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完、ユーザー提供 weights は検証・正規化して合計を 1.0 に再スケール。
    - Bear レジーム判定（ai_scores の regime_score の平均が負で且つ十分なサンプル数）により BUY シグナルを抑制。
    - エグジット判定（ストップロス -8%、スコア低下）を実装し SELL シグナルを生成。
    - signals テーブルもトランザクションで日付単位置換（冪等）。
- 共通実装
  - DuckDB 接続を用いる SQL ベースの処理で、トランザクション・ロールバック処理（例外時のROLLBACK の扱い、ロールバック失敗の警告ログ）を各所で実装。
  - ロギング（logger）を各モジュールに追加し、警告・情報出力を適切に行う設計。
  - 型ヒント（PEP 484）を広く導入し、可読性と静的解析を支援。

### 変更 (Changed)
- 設定（settings）のデフォルト値:
  - kabu_api_base_url のデフォルトを "http://localhost:18080/kabusapi" に設定。
  - duckdb/sqlite のデフォルトパスを data/ 配下に設定（duckdb: data/kabusys.duckdb, sqlite: data/monitoring.db）。
- 環境変数バリデーション:
  - KABUSYS_ENV の許容値を {"development", "paper_trading", "live"} に制限し、不正値で ValueError を送出。
  - LOG_LEVEL の許容値を標準的なログレベルに制限し、不正値で ValueError を送出。

### 修正 (Fixed)
- DB 書き込みの冪等性とトランザクション原子性を担保するため、features / signals / raw_* / market_calendar 書き込みにおいて削除→挿入の原子処理を実装し、例外発生時に適切にロールバックするように対処。
- API リクエストで JSON デコード失敗時にわかりやすいエラーメッセージを返すよう改善。

### セキュリティ (Security)
- XML パーシングに defusedxml を利用して XML Bomb 等の攻撃を緩和（news_collector）。
- RSS ニュース取得時に受信最大バイト数を設定してメモリ DoS を防止。
- URL 正規化でトラッキングパラメータを除去、フラグメント削除を行い記事 ID の重複検出の信頼性を向上。
- J-Quants クライアントでのトークン管理・自動リフレッシュを導入し、認証エラー時の安全なリカバリを実装。

### 既知の制限・未実装 (Known issues / TODO)
- signal_generator のエグジット条件の一部（トレーリングストップ、時間決済）は positions テーブルの追加情報（peak_price / entry_date 等）を要するため未実装。
- news_collector 内での SSRF 回避（IPブロックチェック等）・SSL 証明書の精査はコード内で準備はあるが、外部ネットワーク制約に合わせた追加検討が必要。
- research モジュールは pandas 等への依存を避け標準ライブラリ + DuckDB SQL で実装しているため、大規模データに対する性能チューニングは今後の課題。

### マイグレーション / 使用上の注意 (Migration / Notes for Users)
- 環境変数（必須）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須。未設定時は settings のプロパティアクセスで ValueError が発生します。
- 自動 .env 読み込みはデフォルトで有効。テスト等で無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のテーブル定義（raw_prices / raw_financials / prices_daily / features / ai_scores / positions / signals / market_calendar 等）は本 Changelog に含まれません。初回利用時は提供されるスキーマ定義を作成してください。
- generate_signals の weights 引数は未認識キー、非数値、NaN/Inf、負値を無視し、残りをデフォルト値とマージして合計を 1.0 に正規化します。外部から重みを与える際は正規化を意識してください。

---

参照:
- パッケージ公開バージョン: 0.1.0（今回の初期リリース）
- 日付はリポジトリスナップショット日時に基づく（2026-03-21）。