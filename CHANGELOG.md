# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
リリースはセマンティックバージョニングに従います。

<!-- NOTE: 自動生成ドキュメントのため日付はパッケージバージョンに合わせて付与しています。 -->

## [Unreleased]

## [0.1.0] - 2026-03-19
初回公開リリース。

### Added
- パッケージ初期構成
  - kabusys パッケージを追加。トップレベルで data / strategy / execution / monitoring を公開。

- 環境設定・自動 .env ロード（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env のパースは export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメント等に対応。
  - settings オブジェクトを提供し、J-Quants / kabuAPI / Slack / DB パス等の設定値をプロパティで取得。
  - 必須環境変数未設定時は明示的に ValueError を送出（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - 環境名（KABUSYS_ENV）やログレベル（LOG_LEVEL）の検証を実装。

- データ取得・永続化: J-Quants クライアント（kabusys.data.jquants_client）
  - API レート制御（120 req/min）を行う固定間隔レートリミッタを実装。
  - 再試行ロジック（指数バックオフ、最大3回）と 408/429/5xx 再試行ポリシーを実装。
  - 401 受信時はリフレッシュトークンを用いた ID トークン自動更新を一度行い再試行。
  - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を提供。
  - DuckDB への冪等保存関数を提供（save_daily_quotes / save_financial_statements / save_market_calendar）。ON CONFLICT を用いて重複を更新。
  - レスポンスの数値変換ユーティリティ（_to_float / _to_int）を提供。
  - 取得時刻（fetched_at）を UTC ISO8601 で記録し、Look-ahead バイアスの管理を容易にする設計。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード取得・記事正規化処理を実装。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化、フラグメント除去）。
  - 記事IDは正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を保証。
  - defusedxml を使用して XML 関連の脆弱性（XML Bomb 等）を回避。
  - HTTP/HTTPS スキーム限定、受信サイズ上限（10 MB）などの安全策を実装。
  - raw_news / news_symbols への一括挿入のためのチャンク処理を実装。

- ファクター計算（kabusys.research.factor_research）
  - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）、Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）、Value（per, roe）を DuckDB の prices_daily / raw_financials を用いて計算する関数を実装（calc_momentum / calc_volatility / calc_value）。
  - 過去データ不足時の None 返却やウィンドウ行数チェック等の安全処理を実装。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research モジュールの生ファクターを取得しユニバースフィルタ（最低株価・最低平均売買代金）を適用後、選定カラムを Z スコア正規化（kabusys.data.stats の zscore_normalize を使用）・±3 でクリップして features テーブルへ UPSERT（トランザクションで日付単位の置換）する build_features を実装。
  - ルックアヘッドバイアス防止のため target_date 時点のデータのみを利用する設計。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum, value, volatility, liquidity, news）を計算し、重み付け合算による final_score を算出する generate_signals を実装。
  - デフォルト重み・閾値を定義し、ユーザー指定 weights は検証・フォールバック・リスケールされる。
  - Bear レジーム判定（ai_scores の regime_score 平均が負の場合）により BUY シグナルを抑制するロジックを実装。
  - エグジット（SELL）判定としてストップロス（-8%）・スコア低下を実装。positions / prices_daily を参照して SELL を決定。
  - signals テーブルへ日付単位で置換挿入（トランザクションで原子性を保証）。
  - 欠損コンポーネントは中立値（0.5）で補完して不当な降格を防止。

- 研究用ユーティリティ（kabusys.research.feature_exploration）
  - 将来リターン計算（calc_forward_returns）：指定ホライズン（デフォルト [1,5,21]）に対するリターンを一括取得。
  - IC（Information Coefficient）計算（calc_ic）：factor と将来リターンのスピアマンランク相関を計算する関数を実装。
  - factor_summary：ファクターの基本統計量（count/mean/std/min/max/median）を計算。
  - rank：同順位は平均ランクを使うランク付けを実装。浮動小数の丸めで ties 検出漏れを抑制。

### Changed
- ドキュメント・設計ノートを多数のモジュールに追加（モジュール毎に設計方針・処理フロー・制約を明記）。これにより実装意図の追跡と検証が容易に。

### Known limitations / TODO
- execution パッケージは __init__.py のみで具体的な発注ロジックは未実装。生成した signals を実際の発注に繋げる層は今後実装予定。
- signal_generator 内の SELL 条件で説明しているトレーリングストップや時間決済（保有 60 営業日超過）は未実装（positions テーブルに peak_price / entry_date が必要）。
- news_collector は defusedxml に依存するため、実行環境に該当ライブラリが必要。
- research モジュールは外部データフレームライブラリに依存しない実装だが、大規模データでの性能評価・最適化は今後の課題。
- J-Quants リクエストの再試行ポリシーは限定的（最大3回）。運用環境に応じた監視やバックオフ調整が推奨される。

### Security
- news_collector で defusedxml を利用して XML の攻撃を緩和。
- RSS / URL 処理でスキームチェック（HTTP/HTTPS）や受信サイズ制限等の SSRF / DoS 対策を導入。
- .env 読み込み時に OS 環境変数を保護する仕組み（.env.local の上書き制御含む）を実装。

---

注: この CHANGELOG は提供されたソースコードから実装内容・設計意図を推測して作成したものです。実際のリリースノートとして使用する場合は、変更履歴・日付・責任者などをプロジェクトの実際の運用記録に合わせて調整してください。