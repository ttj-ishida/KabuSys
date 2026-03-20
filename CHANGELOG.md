# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに準拠します。  

※ 日付はコードベースから推測できる最初のリリースとして記載しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-20
初回リリース。日本株自動売買システムの基礎機能を実装。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化を追加。バージョン情報 (__version__ = "0.1.0") と公開 API モジュールを定義（data, strategy, execution, monitoring）。
- 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env, .env.local の優先順位ロジック、OS 環境変数を保護する protected セット、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - 行パーサは export プレフィックス、クォート（シンプルなエスケープ考慮）、インラインコメント処理に対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境 / ログレベル等のプロパティで型安全にアクセス可能。
  - 必須環境変数未設定時は明確な例外メッセージを返す `_require` 実装。
  - 環境値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。
- データ取得・保存 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。機能:
    - ID トークン取得（リフレッシュトークン→idToken）。
    - ページネーション対応で日足 / 財務データ / マーケットカレンダーを取得する fetch_* 関数。
    - API レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を実装。
    - リトライ（指数バックオフ、最大3回）、408/429/5xx のリトライ判定、429 の Retry-After 優先処理を実装。
    - 401 受信時はトークンを自動リフレッシュして 1 回リトライする仕組みを実装（再帰防止フラグ対応）。
    - 取得データの DuckDB への保存用関数 save_daily_quotes / save_financial_statements / save_market_calendar を実装。ON CONFLICT DO UPDATE による冪等保存。
    - 取得時刻 (fetched_at) を UTC ISO8601 形式で記録し Look-ahead バイアスの追跡を可能に。
    - 型変換ユーティリティ `_to_float`, `_to_int` を実装（堅牢な変換ルール）。
- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news に冪等保存する機能（記事IDは正規化後の SHA-256 ハッシュの先頭を利用）を実装方針として実装。
  - URL 正規化機能を実装（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
  - 受信サイズ制限（MAX_RESPONSE_BYTES）やバルク挿入チャンク化などの実装方針を導入。
  - セキュリティ対策：defusedxml の利用想定、HTTP スキーム制限、SSRF/メモリDoS対策方針を記載。
- リサーチ用ファクター計算 (src/kabusys/research/factor_research.py)
  - モメンタム、ボラティリティ（ATR・出来高関連）、バリュー（PER/ROE）等のファクター計算関数を実装（prices_daily / raw_financials を参照）。
  - 各関数は date, code をキーとする dict リストを返す設計で、データ不足時は None を返却する堅牢性を持つ。
  - 計算窓・スキャン範囲は週末/祝日を考慮したカレンダーバッファがある実装（営業日換算のウィンドウ）。
- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - research モジュールの生ファクターを取得し、ユニバースフィルタ（最低株価・平均売買代金）を適用、Zスコア正規化（kabusys.data.stats の zscore_normalize を利用）・±3でクリップして features テーブルへ日付単位で置換（トランザクションによる原子性）する build_features を実装。
  - ルックアヘッドバイアス防止のため target_date 時点のデータのみ参照する方針を明記。
- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントから final_score を計算、閾値超過で BUY シグナル、保有ポジションに対するエグジット条件（ストップロス・スコア低下）で SELL シグナルを生成する generate_signals を実装。
  - 重み (weights) のフォールバック・検証・正規化ロジックを実装（既定重み _DEFAULT_WEIGHTS を採用、合計を 1.0 に再スケール）。
  - Zスコア→[0,1] 変換にはシグモイドを使用。欠損コンポーネントは中立値 0.5 で補完。
  - Bear レジーム判定（AI レジームスコアの平均が負かつサンプル数閾値以上）を導入し、Bear 時には BUY シグナルを抑制する方針を採用。
  - SELL 判定は保有ポジションの最新価格取得や価格欠損時のスキップ、保有銘柄が features に存在しない場合の扱い（score=0.0）などの堅牢化を実装。
  - signals テーブルへの日付単位置換（トランザクション＋バルク挿入）で冪等性を確保。
- 研究支援ユーティリティ (src/kabusys/research/feature_exploration.py)
  - 将来リターン計算（calc_forward_returns）、IC（Spearman ランク相関）計算（calc_ic）、ファクター統計サマリー（factor_summary）、ランク付けユーティリティ（rank）を実装。
  - pandas 等の外部依存を用いず標準ライブラリのみで実装する方針。
- パッケージエクスポート (src/kabusys/research/__init__.py, src/kabusys/strategy/__init__.py)
  - 主要関数をパッケージレベルで公開（calc_momentum 等、build_features/generate_signals）。
- DuckDB を中心としたデータフロー
  - ほとんどのモジュールで DuckDB 接続を受け取り、prices_daily / raw_financials / features / ai_scores / positions 等のテーブルを参照・更新する設計。

### 変更 (Changed)
- 初回リリースのため該当なし

### 修正 (Fixed)
- 初回リリースのため該当なし

### セキュリティ (Security)
- news_collector で defusedxml を利用予定とするなど、XML パーサ攻撃対策を導入方針に明記。
- RSS URL 正規化やスキームチェック、受信制限による SSRF / メモリ DoS の緩和方針を採用。
- J-Quants クライアントでの認証トークン管理と自動リフレッシュ、レート制限および再試行ロジックにより外部 API 利用に伴う失敗耐性を強化。

### 互換性 / 注意点 (Compatiblity / Notes)
- DuckDB のスキーマ（テーブル名・カラム名）に依存するため、運用環境では想定スキーマが事前に作成されている必要があります（features, ai_scores, positions, prices_daily, raw_prices, raw_financials, market_calendar, signals など）。
- generate_signals / build_features は target_date 時点のデータのみを参照する設計のため、データの fetched_at や prices の欠損があると出力が変化します。
- news_collector の一部実装（完全な RSS 取得/パースや SSRF 検査の具体的ロジック）は設計方針が示されており、運用時に追加の実装/レビューが推奨されます。
- execution / monitoring パッケージは公開されているが現時点で実装が最小限（空の __init__ 等）なため、実行・監視周りの実装は今後追加予定。

---

開発・運用に関する詳しい設計方針は各モジュールの docstring / コメントを参照してください。README やドキュメントに追記する変更点があれば別途反映してください。