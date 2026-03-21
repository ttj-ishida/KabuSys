# CHANGELOG

すべての変更は Keep a Changelog の方針に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-21
初回公開リリース — 日本株自動売買システム "KabuSys" の基盤機能を実装。

### 追加 (Added)
- パッケージ基本情報
  - パッケージ名/説明: KabuSys - 日本株自動売買システム
  - バージョン: 0.1.0（src/kabusys/__init__.py）

- 環境設定・自動 .env ロード機能（src/kabusys/config.py）
  - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサを実装: export KEY=val、クォート文字列、行内コメント（#）の扱いを考慮した安全なパース処理をサポート。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（DEBUG/INFO/... の検証）
    - is_live / is_paper / is_dev のユーティリティ

- データ取得クライアント: J-Quants API（src/kabusys/data/jquants_client.py）
  - 固定間隔スロットリングによるレート制御（120 req/min）。
  - リトライ（指数バックオフ）実装（最大 3 回、408/429/5xx を対象）、429 の Retry-After サポート。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）実装。
  - ページネーション対応の取得関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB へ冪等保存する関数:
    - save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT / DO UPDATE を使用）
  - データ変換ユーティリティ _to_float / _to_int を提供。
  - 各リクエスト処理で取得時刻（UTC）を記録し、look-ahead bias 対策を考慮。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード収集と前処理の実装（デフォルトソース: Yahoo Finance のカテゴリ RSS）。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、クエリソート、フラグメント除去）。
  - 記事ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を確保。
  - defusedxml を利用した XML パースによる安全対策。
  - SSRF 対策（HTTP/HTTPS スキームの制限、IP/サイズ等の入力チェックを想定）。
  - 受信バイト数上限（MAX_RESPONSE_BYTES）やバルク INSERT チャンク処理を実装。

- 研究（Research）モジュール（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離）を計算。
    - calc_volatility: 20 日 ATR、atr_pct、20 日平均売買代金、volume_ratio を計算。
    - calc_value: target_date 以前の最新財務データ（raw_financials）と株価から PER / ROE を計算。
    - 各関数は prices_daily / raw_financials テーブルのみを参照し、(date, code) 単位の dict リストを返す設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターン計算。
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算。
    - factor_summary: 各カラムの基本統計量（count/mean/std/min/max/median）。
    - rank: 同順位は平均ランクにするランク関数（丸め処理で ties に対処）。
  - zscore_normalize を data.stats から利用する（research パッケージの再エクスポートあり）。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features(conn, target_date): research モジュールの生ファクターを統合し、ユニバースフィルタ（価格 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
  - 指数: Z スコア正規化（指定カラムのみ）、±3 でクリップ。
  - features テーブルへの日付単位の置換（BEGIN / DELETE / INSERT / COMMIT）により冪等性と原子性を保証。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features / ai_scores / positions を参照し、モメンタム・バリュー・ボラティリティ・流動性・ニュースを重み付きで統合した final_score を算出。
    - デフォルト重み、スコアの補完ロジック（欠損コンポーネントは中立 0.5 を使用）、weights の検証・再スケール機能。
    - Bear レジーム判定（ai_scores の regime_score の平均が負で、サンプル数閾値を満たす場合 BUY を抑制）。
    - BUY: threshold（デフォルト 0.60）を超える銘柄に BUY シグナルを生成（Bear 時は抑制）。
    - SELL: positions と最新価格に基づくエグジット判定を実装（ストップロス -8%、final_score < threshold）。
    - signals テーブルへ日付単位の置換で保存（冪等性）。

- パッケージエクスポート
  - strategy パッケージから build_features / generate_signals を公開（src/kabusys/strategy/__init__.py）。
  - research パッケージから主要ユーティリティを再エクスポート（src/kabusys/research/__init__.py）。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### 削除 (Removed)
- （初版のため該当なし）

### 非推奨 (Deprecated)
- （初版のため該当なし）

### セキュリティ (Security)
- news_collector で defusedxml を利用して XML 攻撃を軽減。
- RSS URL の正規化とトラッキング除去、受信サイズ制限、HTTP スキーム/ドメイン検証などにより SSRF / DoS リスクを軽減。
- J-Quants クライアントでのトークンリフレッシュは allow_refresh フラグにより無限再帰を防止。

### 既知の制限・注意事項 (Known issues / Notes)
- 実行（execution）レイヤーは空のパッケージとして用意されていますが、実際の発注ロジック（kabu API への注文送信等）は本リリースでは実装されていません（src/kabusys/execution/__init__.py が空）。
- signal_generator のトレーリングストップや時間決済（保有 60 営業日超過）は、positions テーブルに peak_price / entry_date 等の情報が必要なため未実装としてコメントに記載されています。
- research モジュールは外部ライブラリ（pandas 等）に依存せず標準ライブラリと DuckDB を前提に実装されています。大規模データ処理や最適化は今後の改善余地があります。
- news_collector の SSRF/IP 判定・ネットワーク堅牢性は実装方針に沿って考慮されていますが、実運用時は追加のネットワーク制限（プロキシ / ACL）を推奨します。

---

もしリリースノートの粒度をさらに細かく（関数単位の変更履歴や SQL クエリの差分など）記載したい場合は、どのレベルで詳細化するかを指定してください。