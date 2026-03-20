# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。Semantic Versioning に従います。

## [0.1.0] - 2026-03-20

初回公開（ベースライン実装）。本リリースでは日本株自動売買システム KabuSys のコアライブラリと研究・データ収集ユーティリティを実装しています。主な機能と設計方針は以下の通りです。

### 追加 (Added)
- パッケージ基礎
  - パッケージ初期化: kabusys.__init__ にバージョン情報と公開モジュール一覧を追加。(__version__ = "0.1.0")。

- 環境設定/ロード (kabusys.config)
  - .env/.env.local 自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml を基準に検出）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサを実装: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理、キー空チェック等。
  - .env 読み込み時の上書き制御（override）と OS 環境変数保護（protected keys）。
  - Settings クラスを実装し、J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、データベースパス（DuckDB/SQLite）、環境（development/paper_trading/live）およびログレベルをプロパティとして公開。無効値は ValueError を送出して早期検出を行う。

- データ収集/保存 (kabusys.data)
  - J-Quants API クライアントを実装（data.jquants_client）。
    - 固定間隔レートリミッタ（120 req/min）を実装。
    - HTTP リトライ（指数バックオフ、最大3回）および 401 時のトークン自動リフレッシュ処理。
    - ページネーション対応 fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB への冪等保存 helper（save_daily_quotes, save_financial_statements, save_market_calendar）を実装（ON CONFLICT を利用）。
    - 型安全な数値変換ユーティリティ（_to_float, _to_int）。
  - ニュース収集モジュール (data.news_collector) を追加。
    - RSS フィード収集、記事ID生成（URL 正規化後 SHA-256 ハッシュ）、テキスト前処理、raw_news への冪等保存のワークフローを実装。
    - defusedxml を使用した XML 関連の安全対策、受信サイズ制限（10 MB）、トラッキングパラメータ除去、HTTP スキーム検証、SQL バルク挿入のチャンク処理。

- リサーチ/ファクター計算 (kabusys.research)
  - ファクター計算モジュールを実装（research.factor_research）。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率の算出。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、平均売買代金、出来高比率の算出。
    - calc_value: PER、ROE（raw_financials から最新値を取得して計算）。
    - DuckDB 上の prices_daily / raw_financials のみを参照する設計で、本番資産や外部発注に依存しない。
  - 特徴量探索ユーティリティ（research.feature_exploration）。
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算（LEAD を利用した一括取得）。
    - calc_ic: スピアマンランク相関（Information Coefficient）計算（結合・欠損除外・最小サンプルチェックあり）。
    - factor_summary: 各ファクターの基本統計量（count/mean/std/min/max/median）。
    - rank: 同順位の平均ランク扱い（round による ties 対策）。
  - research パッケージの __init__ で主要関数をエクスポート。

- 戦略 (kabusys.strategy)
  - 特徴量エンジニアリング (strategy.feature_engineering)
    - research 側で計算された生ファクターをマージ・ユニバースフィルタ適用（最低株価 300 円、20日平均売買代金 5 億円）、Z スコア正規化、±3 でクリップし features テーブルへ日付単位で置換（トランザクションで原子性保証）。
    - ルックアヘッドバイアス防止のため target_date 時点のデータのみを利用する設計。
  - シグナル生成 (strategy.signal_generator)
    - features と ai_scores を統合して銘柄ごとのコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、重み付き合算で final_score を算出。
    - デフォルト重みと閾値を定義（デフォルト threshold=0.60）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負でかつサンプル数閾値以上で判定）により BUY を抑制。
    - BUY シグナル生成（rank付与）、SELL（エグジット）判定（ストップロス -8%、スコア低下）を実装。
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入で原子性保証）。
  - strategy パッケージの __init__ で build_features / generate_signals を公開。

- その他
  - 空の execution パッケージ（プレースホルダ）を追加（将来的な発注ロジックの分離を想定）。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### セキュリティ (Security)
- data.news_collector にて defusedxml を導入し XML パーシング攻撃（XML bomb 等）に対処。
- ニュース取得で受信最大サイズを制限（MAX_RESPONSE_BYTES=10MB）してメモリ DoS を軽減。
- URL 正規化でトラッキングパラメータ除去、スキームチェック等を実装し SSRF やトラッキング耐性を向上。
- J-Quants クライアントでトークン管理/自動更新とリトライ制御を実装し、誤ったトークン使用による情報漏洩やリクエスト失敗のリスクを低減。

### 既知の制限 / 未実装 (Known issues / TODO)
- signal_generator のエグジット条件でトレーリングストップや時間決済（保有60営業日超）に必要な position の peak_price / entry_date は未実装（positions テーブル要拡張）。
- feature_engineering / research の正規化はいまのところ zscore_normalize を呼び出す設計（外部依存なしだが計算ロジックの拡張余地あり）。
- news_collector の記事→銘柄紐付け(news_symbols)の実装詳細は将来的に追加予定。
- execution 層（オーダー送信ロジック）は別パッケージ化を予定しているが、本リリースでは実装されていない。

### 後方互換性 (Backwards compatibility)
- 本リリースは初回リリースのため互換性の過去版は存在しません。以後のリリースでは Breaking Changes を明記します。

---

注: 上記はソースコードの内容から推測して作成した CHANGELOG です。実際のリリースノートでは追加の利用例、API 契約、マイグレーション手順（DB スキーマ変更等）や変更の影響範囲を適宜追記してください。