# CHANGELOG

すべての注目すべき変更をこのファイルで管理します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-03-20

初期リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。以下はソースコードから推測される主要な追加点・設計方針・注意点の要約です。

### 追加 (Added)
- パッケージ構成
  - kabusys パッケージの基本骨格を追加。公開 API: data, strategy, execution, monitoring（execution は空のパッケージとして存在）。
  - バージョン: 0.1.0

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする仕組みを実装（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサーはコメント行、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントなどのケースに対応。
  - 環境変数上書きルール（OS 環境変数保護機能）を導入。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境（development/paper_trading/live） / ログレベル等の取得・検証を行う。
  - 必須環境変数を取得する _require() を実装（未設定時に ValueError を送出）。

- データ取得クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装（価格・財務・市場カレンダーの取得）。
  - レート制限対応（120 req/min、固定間隔スロットリング実装）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 の場合は Retry-After を優先。
  - 401 エラー時のトークン自動リフレッシュ（1 回）とモジュールレベルの ID トークンキャッシュを実装。
  - ページネーション対応（pagination_key を使用）。
  - DuckDB への保存ユーティリティ（raw_prices, raw_financials, market_calendar）を実装。ON CONFLICT を用いた冪等保存を行う。
  - 入力変換ユーティリティ _to_float / _to_int を提供（堅牢な型処理）。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィード取得〜正規化〜raw_news への冪等保存フローを実装（URL 正規化・トラッキングパラメータ除去・記事ID の SHA-256 ハッシュ化等）。
  - defusedxml を使った安全な XML パース、受信サイズ上限、SSRF 対策（HTTP/HTTPS のみ等）などセキュリティ指向の実装。
  - バルク挿入時のチャンク処理、挿入結果の精密カウントを想定。

- 研究モジュール (src/kabusys/research/*.py)
  - factor_research: Momentum / Volatility / Value / Liquidity 等のファクター計算を実装。
    - モメンタム（1M/3M/6M、MA200 乖離）、ATR（20 日）、20 日平均売買代金、出来高比率、PER / ROE などを計算。
    - DuckDB のウィンドウ関数を利用した効率的な集計（スキャン範囲バッファあり）。
  - feature_exploration: 将来リターン（horizons: デフォルト [1,5,21]）計算、IC（Spearman の ρ）、統計サマリー、rank ユーティリティを実装。
    - calc_forward_returns は単一クエリで複数ホライズンを取得。
    - calc_ic はランク相関（同順位は平均ランク）を扱い、サンプル数が不足する場合は None を返す。
  - research パッケージの __all__ に主要関数をエクスポート。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - research モジュールから得た生ファクターをマージ/フィルタ/正規化して features テーブルに UPSERT（日付単位の置換）する build_features を実装。
  - ユニバースフィルタ: 最低株価（300 円）・20 日平均売買代金（5 億円）を適用。
  - 正規化: zscore_normalize 呼び出し後 ±3 でクリッピング。
  - トランザクション + バルク挿入で日付単位の原子置換を保証。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合し最終スコア final_score を算出、BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換する generate_signals を実装。
  - スコア計算:
    - momentum/value/volatility/liquidity/news を重み付き合算（デフォルト重みを実装）。合計が 1.0 でない場合はリスケール。
    - コンポーネント欠損は中立値 0.5 で補完。
    - Z スコアをシグモイド関数で [0,1] に変換。
  - Bear レジーム判定: ai_scores の regime_score 平均が負で、かつサンプル数が閾値以上なら BUY シグナルを抑制。
  - エグジット条件（売りシグナル）: ストップロス（-8%）および final_score の閾値割れを実装。positions / prices_daily を参照。
  - signals テーブルへのトランザクション置換を実施（COMMIT/ROLLBACK の安全処理を含む）。

### 変更 (Changed)
- 設計方針（全体）
  - ルックアヘッドバイアス対策として、各計算は target_date 時点までのデータのみを参照する方針を徹底。
  - 発注 API（execution 層）への直接依存を避け、strategy 層は signals テーブルへ出力するのみの実装。

### 修正 (Fixed)
- 入力データの欠損・非数値への堅牢性を強化
  - 各種計算で None / NaN / Inf / 非数値を排除・無視する処理を追加。
  - price 欠損時に SELL 判定をスキップするなど誤動作防止のログ出力を追加。

- DuckDB 書き込みの冪等性
  - raw_* / market_calendar などの保存関数で ON CONFLICT を利用し、重複や再実行に対して安全に動作するようにした。

### セキュリティ (Security)
- news_collector で defusedxml を使用し XML 関連攻撃を緩和。
- URL 正規化時にトラッキングパラメータを除去、HTTP/HTTPS のみ許可するなど SSRF やトラッキング対策を取り入れた。
- .env 自動読み込みで OS 環境変数を保護（protected set）し、予期せぬ上書きを防止。

### 注意事項 / マイグレーション
- 必要な環境変数（少なくとも以下は必須）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - .env.example を参照して .env を用意してください。未設定の場合 Settings.* プロパティで ValueError が発生します。
- デフォルト DB パス
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - 必要に応じて環境変数で変更可能。
- DB スキーマ（想定テーブル）
  - raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, signals, positions, raw_news, news_symbols 等が参照 / 更新される前提です。運用前に想定スキーマを準備してください。
- generate_signals / build_features は target_date ごとに既存レコードを削除して再挿入するため、同一日付での再実行は基本的に安全（冪等）。ただしトランザクションが失敗した場合のロールバック動作に注意してください。
- jquants_client の rate limiter / retry はデフォルト設定を使用。大量取得時はレートやリトライ挙動に注意。

### 既知の制限 / 未実装 (Known Issues / TODO)
- signal_generator の一部のエグジット条件（トレーリングストップや時間決済）は未実装（positions テーブルに peak_price / entry_date が必要）。
- NewsCollector の詳細な記事—銘柄紐付け（news_symbols への保存処理）は設計コメントとして存在するが、実装の完全版が必要な場合は追実装が必要。
- execution 層（発注ロジック）はこのリリースでは未実装。signals テーブルをトリガーとして外部の執行モジュールを連携する想定。

---

今後のバージョンでは、execution（発注）層の実装、監視（monitoring）機能の拡充、ニュース → 銘柄マッチングの強化、バックテスト/パラメータ最適化ツールの追加などを予定しています。必要な点や補足したい点があれば教えてください。