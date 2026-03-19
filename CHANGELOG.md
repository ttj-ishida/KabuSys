Keep a Changelog
=================
すべての重要な変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。

[0.1.0] - 2026-03-19
-------------------

初回公開 (初版) — コア機能の実装をまとめたリリース。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージを導入。バージョンは 0.1.0、top-level の __all__ に data, strategy, execution, monitoring を公開。
- 設定管理
  - 環境変数 / .env 読み込みユーティリティを実装（src/kabusys/config.py）。
    - プロジェクトルート自動検出（.git または pyproject.toml を起点）。
    - .env と .env.local の自動ロード（OS 環境変数優先、.env.local は上書き）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env パースは export 句、クォート、インラインコメント、エスケープに対応。
    - Settings クラスを提供（必須設定の取得、値検証、パス（duckdb/sqlite）変換、環境・ログレベルの検証）。
    - 必須環境変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。
- データ取得（J-Quants）
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
    - 固定間隔のレートリミッタ（120 req/min）実装。
    - リトライ（指数バックオフ、最大 3 回）と 401 時の自動トークンリフレッシュ対応。
    - ページネーション対応の fetch_* 関数（株価、財務、カレンダー）。
    - DuckDB への保存関数（raw_prices/raw_financials/market_calendar）を実装し、ON CONFLICT DO UPDATE により冪等性を確保。
    - 型変換ユーティリティ（_to_float / _to_int）を提供。
- ニュース収集
  - RSS からのニュース収集モジュール（src/kabusys/data/news_collector.py）。
    - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除）と記事 ID の SHA-256 ハッシュ化。
    - defusedxml を使用した安全な XML パース。
    - 受信サイズ制限（最大 10MB）、SSRF 対策、チャンク化バルク INSERT。
    - デフォルト RSS ソース（Yahoo Finance のビジネスカテゴリ）を設定。
- リサーチ（研究用）モジュール
  - ファクター計算および探索ツール群を実装（src/kabusys/research/ 以下）。
    - calc_momentum / calc_volatility / calc_value: prices_daily / raw_financials を参照して主要ファクターを計算。
      - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（20日 ATR、相対 ATR）、バリュー（PER/ROE）等。
    - calc_forward_returns: 将来リターン (1,5,21 デフォルト) を計算。
    - calc_ic: スピアマンのランク相関（IC）を計算。
    - factor_summary / rank: ファクターの統計サマリ・ランク計算ユーティリティ。
    - 研究モジュールは外部ライブラリ依存を抑え、DuckDB のみ参照。
- 特徴量エンジニアリング
  - build_features を実装（src/kabusys/strategy/feature_engineering.py）。
    - research モジュールの生ファクターを取り込み、株価・流動性によるユニバースフィルタを適用。
    - 指定列の Z スコア正規化（zscore_normalize を利用）と ±3 のクリップ。
    - features テーブルへ日付単位で置換（DELETE→INSERT をトランザクションで実行し冪等性を確保）。
    - ユニバース基準: 最低株価 300 円、20 日平均売買代金 5 億円。
- シグナル生成
  - generate_signals を実装（src/kabusys/strategy/signal_generator.py）。
    - features と ai_scores を統合して各銘柄の最終スコア（final_score）を計算。
    - コンポーネント: momentum / value / volatility / liquidity / news（AI）を合成（デフォルト重みあり）。
    - 重みの検証・スケーリング、欠損コンポーネントは中立値 0.5 で補完。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合）により BUY シグナルを抑制。
    - エグジット判定（ストップロス -8%、スコア低下）による SELL シグナル生成（positions テーブル参照）。
    - signals テーブルへ日付単位で置換（トランザクションで原子性を保証）。
- API の設計方針と安全性の配慮
  - 研究・戦略ロジックは発注 API（execution 層）へ依存しないよう分離。
  - ルックアヘッドバイアス対策（target_date 時点のみを利用、fetched_at に UTC タイムスタンプ記録）。
  - DB 操作はトランザクション + バルク挿入で原子性と効率を確保。
  - XML パーサーに defusedxml を使用し XML Bomb 等に対処。
  - HTTP レスポンスサイズ制限や SSRF 判定等で外部入力を制限。

### 変更 (Changed)
- （初回リリースのためなし）

### 修正 (Fixed)
- （初回リリースのためなし）

### 既知の制限 / TODO
- エグジット条件に関する未実装機能（src/kabusys/strategy/signal_generator.py の注記）:
  - トレーリングストップ（直近最高値から -10%）は未実装。positions テーブルに peak_price / entry_date が必要。
  - 時間決済（保有 60 営業日超過）も未実装。
- execution パッケージは現在空のプレースホルダ（発注実装は別途）。
- 一部の入力検査は実運用で追加が望ましい（外部 API レスポンスの想定外フィールド等）。
- news_collector の RSS ソースはデフォルトが少数のため、運用時には追加リストの管理が必要。

### セキュリティ注記
- news_collector で defusedxml を使用、受信サイズ上限、トラッキングパラメータ除去、SSRF 対策を実装済み。
- J-Quants クライアントはトークン管理・自動リフレッシュを実装。API のレート制限を守るため固定間隔スロットリングを採用。

参考
- 本リリースは設計文書（StrategyModel.md, DataPlatform.md 等）に基づいた機能群の初期実装を含みます。実運用に際しては環境変数の設定（.env）・DuckDB スキーマ整備・Slack 通知や execution 層の実装が必要です。