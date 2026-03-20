CHANGELOG
=========

すべての重要な変更点をこのファイルに記載します。  
このプロジェクトは Keep a Changelog の形式に従います。  

v0.1.0 - 2026-03-20
-------------------

Added
- 初回公開リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを実装。
- パッケージ初期化
  - src/kabusys/__init__.py にバージョン情報と公開モジュール一覧を定義。
- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動ロード機能を実装。読み込み順は OS 環境変数 > .env.local > .env。
  - プロジェクトルート検出：.git または pyproject.toml を基準に探索（CWD に依存しない）。
  - .env パーサー強化：export 形式対応、シングル/ダブルクォート内でのバックスラッシュエスケープ処理、インラインコメント処理など。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
  - 必須設定取得用 _require() と Settings クラスを提供。主な必須環境変数:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - DB パスや実行環境（KABUSYS_ENV）、ログレベル（LOG_LEVEL）等のプロパティと検証を実装。
- Data 層 - J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API からのデータ取得（株価日足 / 財務 / マーケットカレンダー）を実装。
  - 固定間隔スロットリングによるレート制限管理（120 req/min）。
  - リトライロジック（指数バックオフ、最大3回）。408/429/5xx を再試行対象に設定。429 の場合は Retry-After を優先。
  - 401 受信時は ID トークン自動リフレッシュして 1 回リトライ（無限再帰回避のため allow_refresh 制御）。
  - ページネーション対応とモジュールレベルのトークンキャッシュ。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT による冪等性を確保。
  - データ変換ユーティリティ（_to_float/_to_int）を追加し、型安全に変換。
  - 取得時の fetched_at を UTC ISO8601 で記録（Look-ahead バイアス回避のためデータ取得時刻をトレース）。
- Data 層 - ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事取得・整形のためのモジュール骨格を実装。
  - URL 正規化ロジックの一部実装（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。
  - セキュリティ方針: defusedxml を採用して XML 攻撃対策、受信サイズ上限（10MB）によるメモリDoS緩和、SSRF 対策方針を明記。
  - 記事 ID を正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を意図。
  - デフォルト RSS ソースに Yahoo Finance のビジネス RSS を追加。
- Research 層
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（mom_1m/mom_3m/mom_6m、ma200_dev）、Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）、Value（per, roe）を DuckDB の prices_daily / raw_financials を参照して計算。
    - 営業日ベースのウィンドウ処理やデータ不足時の None 戻しなど、実務的な扱いを想定。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（複数ホライズンをサポート、デフォルト [1,5,21]）。
    - IC（Spearman の ρ）計算、ランク付けユーティリティ、ファクター統計サマリーを実装（外部依存なし）。
  - 研究用ユーティリティのエクスポートをパッケージ化（research.__init__）。
- Strategy 層
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - research 側で算出した生ファクターをマージ・ユニバースフィルタ（最低株価・平均売買代金）で絞り込み、Zスコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップした上で features テーブルへ日付単位で UPSERT（トランザクションによる原子性）する build_features を実装。
    - ユニバース基準値: 最低株価 300 円、20 日平均売買代金 5 億円。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、重み付け合算で final_score を計算。
    - デフォルト重み・閾値を実装（デフォルト閾値 = 0.60）。weights 引数で上書き可能だが、妥当性検証と合計が 1.0 になるようリスケールを実施。
    - Bear レジーム判定（ai_scores の regime_score 平均が負でサンプル数 >= 3 の場合）で BUY を抑制。
    - エグジット（SELL）ロジックを実装（ストップロス -8%、スコア低下）。一部の条件（トレーリングストップ、時間決済）は未実装で注記あり。
    - BUY/SELL を signals テーブルへ日付単位で置換して書き込む（トランザクション + バルク挿入）。
- その他
  - strategy パッケージの簡易エクスポート（build_features, generate_signals）。
  - config/戦略/研究/データの各モジュールでロギングを適切に追加。

Changed
- 初版のため該当なし（新規実装）。

Fixed
- 初版のため該当なし。

Notes / 補足（開発者向け）
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（get_id_token に利用）
  - KABU_API_PASSWORD: kabuステーション API のパスワード
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知
- DuckDB 側に期待するテーブル（本実装はこれらの存在を前提に動作）
  - raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news, など
  - 各関数・モジュールの docstring に想定カラムや PK が明記されています。マイグレーションやテーブル定義は別途スキーマ定義を参照してください。
- 冪等性・トランザクション
  - データ保存系は原則 ON CONFLICT や日付単位の DELETE→INSERT を組み合わせ、トランザクションで原子性を確保しています。
- セキュリティ・運用上の配慮
  - news_collector は XML パーサーに defusedxml を使用し、受信サイズ制限や URL 正規化で SSRF/DoS に備える設計方針を採用。
  - J-Quants クライアントはレート制限とリトライ・トークンリフレッシュを組み合わせ、堅牢な API 呼び出しを行います。
- 未実装 / 今後の機能
  - strategy のエグジット条件のうちトレーリングストップや時間決済は positions テーブル側に peak_price / entry_date 等の情報が必要であり、将来実装予定。
  - news_collector の RSS 取得・XML 解析・DB 保存の詳細処理（チャンク挿入・記事ID生成の最終化）は継続開発対象。

ライセンス、貢献方法、スキーマ定義などは別ファイル（README / CONTRIBUTING / schema.sql 等）で管理してください。