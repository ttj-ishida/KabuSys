# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティック バージョニングを使用します。詳細は各リリースノートを参照してください。

## [0.1.0] - 2026-03-19

初回公開リリース。日本株の自動売買システム「KabuSys」のコア機能群を実装しました。主な追加点・設計方針は以下のとおりです。

### 追加
- パッケージ基盤
  - パッケージメタ情報を提供（kabusys.__init__。バージョン: 0.1.0、公開 API: data, strategy, execution, monitoring）。
- 設定管理
  - 環境変数／.env の自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - .env の柔軟なパース処理（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、コメント処理の細かな扱い）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須設定取得時の検証関数と Settings クラス（J-Quants / kabu API / Slack / DB パス / 環境名・ログレベル検証、is_live/is_paper/is_dev プロパティ）。
- データ取得 / 永続化
  - J-Quants API クライアント（data/jquants_client）
    - レートリミット（120 req/min）に合わせた固定間隔スロットリング（RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 受信時の ID トークン自動リフレッシュ（1 回）とモジュールレベルのトークンキャッシュ。
    - ページネーション対応でデータを段階的に取得。
    - DuckDB への保存関数（raw_prices / raw_financials / market_calendar）における冪等保存（ON CONFLICT DO UPDATE）を実装。
    - 型安全な変換ユーティリティ（_to_float, _to_int）。
  - ニュース収集（data/news_collector）
    - RSS フィード取得 → テキスト前処理 → raw_news への冪等保存ワークフロー。
    - 記事 ID を URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を担保。
    - トラッキングパラメータ除去／クエリソート／フラグメント削除などの URL 正規化処理。
    - defusedxml を使った XML パースによる安全対策、受信サイズ上限、SSRF・メモリ DoS を考慮した設計。
- リサーチ機能（research）
  - factor_research モジュール
    - Momentum（1M/3M/6M リターン、200 日移動平均乖離）、Volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER, ROE）を DuckDB の prices_daily/raw_financials から計算。
    - 営業日ベースのラグ処理・ウィンドウ集計を SQL で実装。
  - feature_exploration モジュール
    - 将来リターン calc_forward_returns（複数ホライズンの一括取得、入力検証）。
    - IC（Spearman の ρ）計算 calc_ic（ランク化・同順位の平均ランク処理）。
    - factor_summary（count/mean/std/min/max/median）および rank ユーティリティ。
  - これらは外部ライブラリ（pandas 等）に依存せず、DuckDB と標準ライブラリのみで実装。
- 特徴量エンジニアリング（strategy/feature_engineering）
  - 研究環境で計算した生ファクターを統合・正規化して features テーブルへ日次置換（冪等）。
  - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を実装。
  - zscore 正規化（kabusys.data.stats に依存）、±3 でクリップして外れ値影響を抑制。
  - トランザクション＋バルク挿入による原子性（DELETE してから INSERT）。
- シグナル生成（strategy/signal_generator）
  - features と ai_scores を統合して final_score を計算し、signals テーブルへ日次置換（冪等）。
  - コンポーネントスコア: momentum/value/volatility/liquidity/news を計算（シグモイド変換や PER の逆スコア化など）。
  - デフォルト重みと閾値（デフォルト threshold=0.60）を実装。外部から weights を渡して上書き可能（入力検証・再スケーリングあり）。
  - Bear レジーム（AI レジームスコア平均が負）判定および Bear 時の BUY 抑制ロジック。
  - SELL（エグジット）判定実装（ストップロス -8% / final_score 閾値未満）。価格欠損時の SELL 判定スキップ・警告出力。
  - SELL 優先ポリシー（SELL 銘柄は BUY リストから除外しランクを再付与）。
  - トランザクション＋バルク挿入により signals の日次置換を原子化、ロールバック失敗時はログ出力。
- 公開 API
  - strategy パッケージから build_features, generate_signals をエクスポート。
  - research パッケージから主要ユーティリティをエクスポート（calc_momentum/calc_volatility/calc_value/zscore_normalize/calc_forward_returns/calc_ic/factor_summary/rank）。

### 変更（設計上の注意）
- DuckDB を主要なストレージとして想定し、SQL と Python の組合せで主要計算を行う設計としました（外部 DB 依存を排除）。
- ルックアヘッドバイアス防止のため、すべての処理は target_date 時点のデータのみを参照する方針で実装。
- research モジュールは本番口座や発注 API へアクセスしない設計。
- .env 読み込みは OS 環境変数（既存キー）をデフォルトで保護し、.env.local は上書きとして読み込む優先度を持ちます。

### 既知の未実装 / 今後の TODO
- signal_generator のエグジット条件でドキュメントに記載の「トレーリングストップ（peak_price 必要）」「時間決済（保有 60 営業日超）」は positions テーブルの追加フィールドが必要なため未実装としてコメントで明示。
- news_collector の記事→銘柄紐付け（news_symbols への連携）については処理の完成度向上・追加テストが想定される。

### 修正点 / 安全対策
- HTTP クライアント処理における 401 ケースの自動処理、リトライ・バックオフ、429 の Retry-After 優先適用を実装し、実運用での堅牢性を確保。
- ニュース XML のパースに defusedxml を使用して XML BOM 等の攻撃を軽減。
- .env パーサは引用符・エスケープ・コメント処理を丁寧に扱い、テストや配布後の実行環境差異に耐性を持たせた。

---

今後のリリースでは、運用監視・実際の注文実行（kabu ステーション連携）、より高度なポジション管理（トレーリングストップ等）、追加の QA テストとドキュメント整備を予定しています。