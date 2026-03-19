# Changelog

すべての注目すべき変更点をここに記録します。  
このファイルは Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に準拠しています。

## [0.1.0] - 2026-03-19

初回リリース。日本株の自動売買システム "KabuSys" の基礎機能を実装しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__init__）。バージョンは 0.1.0。公開 API: data, strategy, execution, monitoring を想定。
- 環境設定
  - 環境変数 / .env 読み込みユーティリティを実装（kabusys.config）。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
    - .env パースは export 形式・クォート・エスケープ・インラインコメントに対応。
    - 必須変数を取得する _require() と Settings クラスを提供（J-Quants / kabu / Slack / DB パス等のプロパティ）。
    - KABUSYS_ENV・LOG_LEVEL の検証を実装（許容値チェック）。
- データ取得・保存（J-Quants）
  - J-Quants API クライアントを実装（kabusys.data.jquants_client）。
    - レート制限（120 req/min）を固定間隔スロットリングで実装（RateLimiter）。
    - リトライ（指数バックオフ）・HTTP 429 の Retry-After 対応・408/429/5xx のリトライ対象化。
    - 401 時は自動でリフレッシュトークンから ID トークンを取得し 1 回リトライする仕組みを実装（トークンキャッシュ含む）。
    - ページネーションに対応した fetch_* 関数（株価、財務、マーケットカレンダー）。
    - DuckDB へ冪等保存する save_* 関数（raw_prices / raw_financials / market_calendar）。ON CONFLICT を用いた更新ロジック。
    - データ型安全変換ユーティリティ（_to_float/_to_int）を実装。
- ニュース収集
  - RSS ベースのニュース収集モジュールを実装（kabusys.data.news_collector）。
    - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント除去）を実装。
    - 受信上限（最大バイト数）や XML の安全解析（defusedxml）などセキュリティ考慮。
    - 記事 ID は URL 正規化後の SHA-256（先頭 32 文字）で冪等性を確保する設計。
    - bulk insert のチャンク処理や PK 欠損行スキップの仕様を実装。
- リサーチ（研究用）モジュール
  - ファクター算出モジュール（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、MA200 乖離）
    - Volatility（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率）
    - Value（PER、ROE を raw_financials と prices_daily から算出）
    - DuckDB に対する SQL ベースの実装（ウィンドウ関数と行数チェックでデータ不足を扱う）
  - 特徴量探索モジュール（kabusys.research.feature_exploration）
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21] 日）
    - IC（スピアマンのランク相関）計算
    - ファクター統計サマリー（count/mean/std/min/max/median）
    - 小数丸めを考慮したランク付けユーティリティ
  - research パッケージの公開 API を整理（calc_momentum 等と zscore_normalize の再公開）
- 特徴量エンジニアリング（strategy）
  - features テーブル向けの正規化・合成処理を実装（kabusys.strategy.feature_engineering）。
    - research の生ファクターを取得し、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 数値ファクターを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）し ±3 でクリップ。
    - 日付単位の置換（DELETE → INSERT）で冪等に features を更新。
- シグナル生成（strategy）
  - features と ai_scores を統合して最終スコアを算出し signals テーブルへ出力するモジュールを実装（kabusys.strategy.signal_generator）。
    - momentum/value/volatility/liquidity/news の各コンポーネント計算と重み付けによる final_score（デフォルト重みを実装）。
    - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完する設計。
    - Bear レジーム（AI の regime_score の平均が負）検知により BUY を抑制する機能。
    - BUY（閾値: 0.60）と SELL（ストップロス -8% / スコア低下）を生成し、signals テーブルへ日付単位置換で保存。
    - positions テーブルと prices_daily を参照してエグジット判定を行う。
- トランザクションと冪等性
  - features / signals への書き込みはトランザクション（BEGIN/COMMIT）で日付単位の置換を行い、途中失敗時はROLLBACK を試行する実装。
- ロギング
  - 各主要処理にログ出力（info/warning/debug）を追加。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### 既知の制限・未実装 (Known limitations / Unimplemented)
- signal_generator の SELL 条件のうち「トレーリングストップ（peak_price に依存）」や「時間決済（保有 60 営業日超過）」は未実装。positions テーブルに peak_price / entry_date を追加すれば実装可能。
- kabusys.data.stats モジュールの実体はソース中で参照されているが（zscore_normalize）、この変更履歴で提供されるコードスニペットに実装は含まれていない。実行環境では該当ユーティリティが必要。
- news_collector は RSS の取得と正規化ロジックを備えるが、外部 RSS ソース追加やシンボル紐付け（news_symbols）の運用ルールは別途実装・設定が必要。
- DuckDB スキーマ（tables 定義）は本リリースに含まれていないため、実行前に適切なスキーマ定義が必要。

### セキュリティ (Security)
- news_collector で defusedxml を利用し XML 攻撃に対処。
- J-Quants クライアントはトークンリフレッシュと HTTP エラーに対する堅牢なハンドリングを実装。
- .env 読み込みは .env.local による上書きや OS 環境変数保護を考慮。

---

今後の予定（例）
- positions スキーマ拡張（peak_price / entry_date）とトレーリングストップ実装
- AI スコア取得パイプラインと news ↔ 銘柄マッピング精度向上
- 単体テスト・統合テストの強化および CI/CD パイプライン構築

（注）本 CHANGELOG は提供されたソースコードの内容から推測して記載しています。実際の変更履歴やリリースノートとして用いる場合は、コミット履歴やリリース管理システムの情報と照合してください。