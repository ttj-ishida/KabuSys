# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従います。  

## [0.1.0] - 2026-03-20

初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化 (kabusys.__init__) を追加。バージョン "0.1.0" を設定し、主要サブパッケージをエクスポート（data, strategy, execution, monitoring）。
- 設定管理 (kabusys.config)
  - .env ファイルと環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途）。
    - プロジェクトルート探索は __file__ を基点に `.git` または `pyproject.toml` を探索して判定（CWD 非依存）。
  - .env の行パーサ実装（export プレフィックス、クォート文字のエスケープ、インラインコメントの扱いなどに対応）。
  - Settings クラスを提供し、主要設定をプロパティ経由で取得可能（J-Quants トークン、kabu API, Slack, DB パス、環境ロール、ログレベルなど）。
  - 環境変数のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。
- Data モジュール (kabusys.data)
  - J-Quants クライアント（kabusys.data.jquants_client）を追加。
    - 固定間隔の簡易レートリミッタ（120 req/min）を実装。
    - リトライ（指数バックオフ、最大 3 回）・HTTP ステータスハンドリング（408, 429, 5xx）実装。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ。
    - ページネーション対応の fetch_* 関数（daily quotes / financial statements / market calendar）を実装。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。挿入は冪等化（ON CONFLICT DO UPDATE）。
    - レスポンス変換ユーティリティ _to_float / _to_int を追加。
  - ニュース収集モジュール（kabusys.data.news_collector）を追加。
    - RSS フィードを取得して raw_news に保存する処理を実装。
    - 記事 ID は正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成して冪等性を担保。
    - defusedxml による安全な XML パース、受信サイズ制限（10 MB）、トラッキングパラメータ除去、HTTP スキーム制限などのセキュリティ対策を実装。
    - DB へはチャンク化してバルク挿入（INSERT RETURNING を想定）で保存。
- Research モジュール (kabusys.research)
  - ファクター計算群を追加（kabusys.research.factor_research）。
    - モメンタム（mom_1m, mom_3m, mom_6m, ma200_dev）を calc_momentum で計算。
    - ボラティリティ／流動性（atr_20, atr_pct, avg_turnover, volume_ratio）を calc_volatility で計算。
    - バリュー（per, roe）を calc_value で計算。raw_financials から最新財務データを取得して価格と組み合わせて計算。
    - 各計算は prices_daily / raw_financials を参照し、(date, code) キーの dict リストを返す設計。
  - 研究支援ユーティリティ（kabusys.research.feature_exploration）を追加。
    - 将来リターン計算 (calc_forward_returns): 1/5/21 営業日などの任意ホライズン計算、単一 SQL クエリで取得。
    - IC（Information Coefficient）計算 (calc_ic): Spearman の ρ（ランク相関）を実装。サンプル不足時は None を返す。
    - ランク関数 rank（同順位は平均ランク）。丸めで ties 判定の安定化を行う。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - research パッケージの __all__ を整備。
- Strategy モジュール (kabusys.strategy)
  - 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
    - research モジュールで計算された生ファクターを正規化・合成し、features テーブルへ保存する build_features を実装。
    - ユニバースフィルタ（最小株価 300 円、20 日平均売買代金 5 億円）を実装。
    - 正規化には zscore_normalize を使用し、対象カラムを ±3 でクリップ。
    - 日付単位での置換（DELETE → bulk INSERT）により冪等性・原子性を確保（トランザクション使用）。
  - シグナル生成 (kabusys.strategy.signal_generator)
    - features と ai_scores を統合して final_score を算出し、BUY / SELL シグナルを生成する generate_signals を実装。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news を計算。
    - スコア変換にシグモイド関数を使用。欠損コンポーネントは中立 0.5 で補完。
    - デフォルト重みと閾値を実装（デフォルト閾値: 0.60）。
    - ユーザ重みのバリデーション・補完と再スケール処理を実装（不正値スキップ）。
    - Bear レジーム検出（ai_scores の regime_score 平均が負かつ十分なサンプル数）を実装し、Bear 時は BUY を抑制。
    - SELL（エグジット）判定にストップロス（終値/avg_price - 1 <= -8%）とスコア低下（final_score < threshold）を実装。
    - signals テーブルへ日付単位で置換して書き込み（トランザクション＋bulk insert）を行い冪等化。
  - strategy パッケージのエクスポートを整備。

### 変更 (Changed)
- 設計方針・注意点をコードに明記（ルックアヘッドバイアス防止、発注層への依存排除、DuckDB を中心としたデータフローなど）。
- NewsCollector や J-Quants クライアントにセキュリティ上の注意（XML パーサの安全化、SSRF 防止、レスポンスサイズ制限）を反映。

### 修正 (Fixed)
- （初版のため該当なし: 実装時に見つかった典型的な行動は既にコード内で警告・例外処理や保護（protected keys、価格欠損時の SELL 判定スキップ等）として扱われています。）

### 既知の制限・未実装 (Known issues / Not implemented)
- signal_generator の SELL 条件で以下の機能は未実装（コメントに明記）。
  - トレーリングストップ（peak_price を使った判定）
  - 時間決済（保有 60 営業日超過）
  - これらの実装には positions テーブルに peak_price / entry_date の格納が必要。
- calc_value での PBR・配当利回りは未実装。
- news_collector の記事 → 銘柄紐付け（news_symbols への処理）はモジュール設計に含まれているが、詳細なマッピングロジックは個別実装が必要。
- fetch_* 関数は API 側の形式・フィールドに依存するため、実環境接続時に追加の互換対応が発生する可能性がある。

### セキュリティ (Security)
- news_collector は defusedxml を使用して XML 関連の脆弱性（XML Bomb 等）を防止。
- ニュースの URL 正規化でトラッキングパラメータを除去し、ID を安定化。
- J-Quants クライアントは 401 の自動リフレッシュ・429 の Retry-After を尊重するリトライ実装を備え、外部 API の利用での安定性と安全性を強化。

### マイグレーション / 運用メモ (Migration / Operational notes)
- 自動 env ロードを無効化してユニットテストを行うには、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のテーブルスキーマ（raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news 等）は本パッケージの関数が期待するカラム構成に合わせて事前に作成しておく必要があります（保存/取得部分の SQL を参照してください）。
- settings.jquants_refresh_token / settings.slack_bot_token / settings.slack_channel_id / settings.kabu_api_password は必須。未設定時は ValueError が発生します。
- generate_signals のデフォルト重みは合計 1.0 に正規化されます。カスタム重みを渡す際は非負で finite な数値を使用してください。

---

今後の予定（例）
- positions テーブルの拡張（peak_price, entry_date）によるトレーリングストップと時間決済の実装
- PBR / 配当利回りなどバリューファクターの追加
- ニュース → 銘柄関連付けアルゴリズムの強化（NLP 等の導入）
- 単体テスト・統合テストの追加と CI での自動化

（この CHANGELOG はコード内のドキュメントと実装から推測して作成しています。実際のリリースノート作成時は実行テスト結果やリリース日等を反映して更新してください。）