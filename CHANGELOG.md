# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従い、日本語で記載します。

リリース日付はコードベースから推測して付与しています。

## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買・データ基盤の基礎機能を実装。

### 追加 (Added)
- パッケージ全体
  - 初期パッケージ kabusys を追加。サブモジュール群（data, strategy, execution, monitoring）をエクスポート。
  - バージョン情報を `__version__ = "0.1.0"` で管理。

- 環境設定 / ロード
  - `kabusys.config`:
    - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。
    - `.env` / `.env.local` の読み込み順序（OS 環境 > .env.local > .env）と上書きポリシーを実装。OS 環境変数は protected として保持。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途を想定）。
    - .env 行パーサを実装（`export KEY=val`、シングル/ダブルクォート、エスケープ、インラインコメントルール対応）。
    - Settings クラスを実装し、必要な設定値（J-Quants / kabuステーション / Slack / DB パス 等）をプロパティ経由で取得。値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL の許容値）を実装。

- データ取得・保存（J-Quants）
  - `kabusys.data.jquants_client`:
    - J-Quants API クライアントを実装。日足・財務・マーケットカレンダー等の取得関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を提供。ページネーション対応。
    - 固定間隔スロットリング `_RateLimiter` によるレート制限（120 req/min）を実装。
    - 再試行ロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx を対象）と 401 受信時のトークン自動リフレッシュを実装。トークンはモジュールレベルでキャッシュしてページネーション間で共有。
    - API レスポンスの JSON デコードエラーやネットワークエラーに対するエラーハンドリングを実装。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。冪等性のため ON CONFLICT DO UPDATE を使用。
    - データ型変換ユーティリティ `_to_float`, `_to_int` を実装し、空値や不正値を安全に None に変換。

- ニュース収集
  - `kabusys.data.news_collector`:
    - RSS フィード収集の骨格を実装（デフォルトソースに Yahoo Finance のカテゴリ RSS を含む）。
    - 記事の前処理と正規化（URL 正規化、トラッキングパラメータ除去、空白正規化）を実装。
    - セキュリティ対策を考慮（defusedxml を利用した XML パース、受信サイズ上限、SSRF 対策方針の記載）。
    - 記事ID を URL 正規化後の SHA-256（先頭 32 文字）で生成し、冪等に保存する方針を採用。
    - DB へのバルク挿入を想定したチャンク処理などの実装方針を含む。

- 研究用ファクター計算
  - `kabusys.research.factor_research`:
    - Momentum / Volatility / Value 系ファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - prices_daily / raw_financials テーブルを参照して、各ファクター（mom_1m/mom_3m/mom_6m, ma200_dev, atr_20, atr_pct, avg_turnover, volume_ratio, per, roe 等）を計算。
    - 移動平均・ATR 等で必要なウィンドウサイズやスキャン範囲の定義を実装し、データ不足時の None 返却を明確化。

  - `kabusys.research.feature_exploration`:
    - 将来リターン計算（calc_forward_returns）を実装。複数ホライズン（デフォルト [1,5,21]）に対応。
    - IC（Information Coefficient）計算（calc_ic）・ランキング関数（rank）・統計サマリー（factor_summary）を実装。外部ライブラリ依存はなく標準ライブラリのみで完結。

  - `kabusys.research.__init__` で主要関数を再エクスポート。

- 特徴量エンジニアリング
  - `kabusys.strategy.feature_engineering`:
    - 研究環境の生ファクターを統合・正規化して features テーブルへ保存する `build_features` を実装。
    - ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5 億円）を実装。
    - 正規化は z スコア（kabusys.data.stats の zscore_normalize を利用）で ±3 クリップ。
    - DuckDB に対して日付単位で削除→挿入するトランザクション（冪等）を実施。

- シグナル生成（戦略）
  - `kabusys.strategy.signal_generator`:
    - features と ai_scores を統合して最終スコア（final_score）を計算し、BUY / SELL シグナルを生成する `generate_signals` を実装。
    - スコア計算にシグモイド変換、コンポーネント（momentum/value/volatility/liquidity/news）ごとの計算関数を実装。
    - デフォルト重みと閾値（デフォルト threshold=0.60、weights は正規化して合計 1 に調整）を実装。無効な重みは無視しログ警告。
    - Bear レジーム検知（ai_scores の regime_score 平均が負でかつサンプル数閾値以上）により BUY シグナルを抑制する挙動を実装。
    - 保有ポジションに対するエグジット判定（ストップロス -8%／スコア低下）を実装（_generate_sell_signals）。価格欠損時の判定スキップや features にない保有銘柄の扱い（score=0 と見なす）も明記。
    - signals テーブルへの日付単位の置換（トランザクション＋バルク挿入で冪等）を実装。

- モジュール初期化
  - `kabusys.strategy.__init__` で build_features / generate_signals をエクスポート。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- news_collector で defusedxml を利用した XML パースを採用、受信サイズ制限（10MB）や URL 正規化により SSRF / XML Bomb / メモリ DoS に対する防御を考慮。
- .env 読み込みは OS 環境変数を保護する仕組み（protected set）を実装し、誤った上書きを防止。

### 既知の制限・未実装（Notes / TODO）
- signal_generator のエグジット条件に記載されている「トレーリングストップ（直近最高値から -10%）」や「時間決済（保有 60 営業日超過）」は未実装。positions テーブルに peak_price / entry_date が必要。
- news_collector の RSS パーサ本体や SSRF の厳密実装（例: IP アドレスチェック等）の実装詳細は骨格中心で記載されており、運用前の追加実装・検証が必要。
- 一部ロジックは research と data 層の連携を前提としており、DuckDB スキーマ（tables: raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar など）の事前定義が必要。
- get_id_token は settings.jquants_refresh_token に依存して動作するため、実運用では .env 等でのトークン設定が必要。
- エラーハンドリングやログは実装されているが、運用上の詳細な監視・メトリクス報告は別途実装を想定。

---

今後の予定（参考）
- execution 層（kabu API 連携）および monitoring（監視・アラート）モジュールの実装。
- news_collector の完全実装・単体テストの追加。
- DuckDB スキーマ定義・マイグレーション仕組みの追加。
- テストカバレッジ拡充と CI/CD の導入。

（以上）