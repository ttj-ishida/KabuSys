# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従ってバージョニングしています。  

現在のバージョンはパッケージ定義 (src/kabusys/__init__.py) に基づき 0.1.0 です。

## [0.1.0] - 2026-03-19

初回リリース。以下の主要機能と実装方針を含みます。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化と公開 API を定義（data, strategy, execution, monitoring を __all__ に設定）。
  - バージョン: 0.1.0

- 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数からの設定読み込みを自動化（プロジェクトルート検出: .git または pyproject.toml）。
  - .env と .env.local の読み込み順序をサポート（OS 環境変数保護、.env.local は上書き可）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パースの堅牢化（コメント、export プレフィックス、シングル/ダブルクォート・エスケープ対応）。
  - 必須項目取得メソッド _require と Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - 環境・ログレベルのバリデーション（KABUSYS_ENV: development/paper_trading/live、LOG_LEVEL: DEBUG/INFO/...）。

- データ取得・保存 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアント実装:
    - 固定間隔レートリミッタ（120 req/min）で API 呼び出しを制御。
    - リトライ（指数バックオフ、最大3回）。408/429/5xx を再試行対象にし、429 の場合は Retry-After ヘッダを尊重。
    - 401 発生時は自動でリフレッシュトークンから id_token を更新して 1 回リトライ。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への保存関数（冪等性）:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE。
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE。
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE。
  - ユーティリティ: 安全な型変換関数 _to_float / _to_int。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードからニュース取得・正規化・保存：
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
    - 記事 ID を URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を確保。
    - defusedxml による XML パース（XML Bomb 対策）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）や URL スキーム検査などのセキュリティ対策。
    - バルク INSERT チャンク化による効率的な DB 保存。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリ RSS を追加。

- リサーチ（研究）モジュール (src/kabusys/research/)
  - ファクター計算 (factor_research.py):
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率の計算。
    - calc_volatility: 20日 ATR、相対 ATR (atr_pct)、20日平均売買代金、出来高比率の計算。
    - calc_value: PER/ROE の計算（raw_financials の最新財務データを用いる）。
    - DuckDB の prices_daily / raw_financials テーブルのみを参照する純粋な計算関数。
  - 特徴量探索 (feature_exploration.py):
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）での将来リターン計算。
    - calc_ic: Spearman ランク相関（Information Coefficient）計算。
    - factor_summary: 各ファクターの基本統計量（count/mean/std/min/max/median）。
    - rank: 同順位は平均ランクを採る安定したランク付け実装（丸め対策あり）。
  - research パッケージの公開 API を整備（calc_momentum 等と zscore_normalize の再公開）。

- 特徴量エンジニアリング（strategy） (src/kabusys/strategy/feature_engineering.py)
  - build_features 実装:
    - research モジュールから得た生ファクターをマージし、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - 指定列を Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）し ±3 でクリップ。
    - features テーブルへ日付単位で置換（BEGIN/DELETE/INSERT/COMMIT で原子性を確保）。
    - ルックアヘッドバイアス回避の設計（target_date 時点のデータのみを使用）。

- シグナル生成（strategy） (src/kabusys/strategy/signal_generator.py)
  - generate_signals 実装:
    - features と ai_scores を統合し、モメンタム/バリュー/ボラティリティ/流動性/ニュースのコンポーネントスコアを計算。
    - コンポーネントスコアはシグモイド変換・欠損は中立値(0.5)で補完。
    - デフォルト重みを定義し、ユーザ重みを検証・フォールバック・再スケール。
    - Bear レジーム判定（ai_scores の regime_score 平均が負でサンプル数閾値以上の場合）で BUY を抑制。
    - BUY は閾値(default 0.60)超え銘柄をランク付けして出力、SELL は保有ポジションに対するストップロス（-8%）・スコア低下で判定。
    - signals テーブルへ日付単位で置換（原子性を確保）。
    - SELL 優先ポリシー（SELL 対象は BUY から除外しランクを再付与）。

### 変更 (Changed)
- 初期設計方針に従い、各モジュールは発注 API / 実行層に直接依存しない構成に統一（研究・データ・戦略層の責務分離を明確化）。

### セキュリティ (Security)
- news_collector: defusedxml による XML 解析（XML BOM 等の攻撃対策）、URL スキーム検査、受信サイズ制限、トラッキングパラメータ除去で再現性/プライバシー配慮。
- jquants_client: トークン自動リフレッシュと慎重なエラーハンドリングにより秘密情報の取り扱いと API エラー対策を強化。

### ドキュメント/ログ (Docs / Logging)
- 各関数に docstring を追加して設計意図・引数・戻り値を明記。
- 主要処理点で logger による情報/警告/デバッグ出力を挿入（処理件数や欠損警告、ROLLBACK 失敗など）。

### 既知の未実装 / 制限 (Known issues / TODO)
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装（positions テーブルに peak_price / entry_date が必要）。
- execution パッケージは空のプレースホルダ（発注ロジックの実装は次フェーズ）。
- news_collector の記事→銘柄紐付け（news_symbols）の詳細実装は今後の拡張を想定。
- ai_scores の扱い: 未登録銘柄は中立扱い（0.5）とするため、AI モデルの品質に依存するシステム特性がある。
- DuckDB のスキーマ（tables: raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar, raw_news 等）は別途スキーマ定義/マイグレーションを提供する必要あり。

---

今後の予定 (Planned)
- execution 層の実装（Kabu ステーション API 経由の注文発行、注文管理、エラー回復）。
- monitoring / alerting 機能の追加（Slack 通知連携の整備）。
- 単体テスト・統合テストおよび CI 設定の整備。

（この CHANGELOG はソースコードのコメントおよび実装内容から推測して作成しています。実際のリリースノート作成時は差分ベースでの検証を推奨します。）