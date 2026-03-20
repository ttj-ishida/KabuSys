# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-03-20

初回リリース — 日本株自動売買システムのコア機能を実装しました。主な追加点・挙動は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0", __all__ 設定）。

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git / pyproject.toml を探索）。
  - 高度な .env パーサーを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、行末コメント処理）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - env/ログレベルの検証、および各種必須設定取得用の Settings クラスを実装（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - デフォルトの DB パス (duckdb/sqlite) の設定と Path への展開。

- データ取得・保存 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアント実装:
    - 固定間隔スロットリングに基づく RateLimiter（120 req/min を想定）。
    - 再試行（指数バックオフ、最大 3 回）と HTTP ステータス別のハンドリング（408/429/5xx のリトライ、429 の Retry-After 利用）。
    - 401 の場合は ID トークンを自動リフレッシュして一回リトライ。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar）。
    - DuckDB へ冪等に保存する save_* 関数（save_daily_quotes、save_financial_statements、save_market_calendar）。ON CONFLICT による upsert を使用。
    - 入力値変換ユーティリティ (_to_float, _to_int) を実装し、型安全な変換ルールを適用。
    - fetched_at を UTC ISO 形式で記録し、look-ahead bias のトレーサビリティを確保。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィード収集の基礎実装:
    - デフォルトソースに Yahoo Finance のカテゴリ RSS を設定。
    - 受信サイズ制限（10 MB）、defusedxml を使用した安全な XML パース。
    - URL 正規化（スキーム/ホストの小文字化、トラッキングパラメータ除去、フラグメント削除、クエリキーソート）。
    - 記事 ID は正規化 URL の SHA-256 の先頭を利用して冪等性を確保。
    - SQL のバルク挿入チャンク化、トランザクションでの保存、ON CONFLICT DO NOTHING による重複排除。
    - SSRF対策や制限（HTTP/HTTPS のみ許可、受信サイズ制限等）を考慮した実装指針。

- リサーチ用ファクター計算 (src/kabusys/research/factor_research.py)
  - モメンタム計算 (calc_momentum): 1M/3M/6M リターン、200 日移動平均乖離率 (ma200_dev)。
  - ボラティリティ/流動性計算 (calc_volatility): 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金、出来高比率。
  - バリュー計算 (calc_value): raw_financials から最新財務を参照し PER / ROE を算出（EPS が 0/欠損 の場合は None）。
  - 全関数とも DuckDB の prices_daily / raw_financials を参照し、date/code をキーとする dict リストを返す。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features(conn, target_date):
    - research モジュールで計算した生ファクターを取得し結合。
    - ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ。
    - features テーブルへ日付単位で削除→挿入の置換（トランザクションで原子性保証）。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を統合し、コンポーネントスコア（momentum, value, volatility, liquidity, news）を計算。
    - シグモイド変換・欠損補完（None を中立 0.5）を行い、重み付き合算で final_score を算出。デフォルト重みはドキュメント準拠。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合）。Bear 時は BUY シグナルを抑制。
    - BUY: threshold 以上の銘柄（Bear 時は抑制）。SELL: ストップロス (-8% 未満) と final_score の低下時。
    - positions / prices を参照し、SELL 判定は価格欠損時のスキップや features にない保有銘柄は score=0 とするなど安全策あり。
    - signals テーブルへ日付単位で置換（トランザクションで原子性保証）し、SELL を優先して BUY から除外。

- 研究用ユーティリティ (src/kabusys/research/feature_exploration.py)
  - 将来リターン計算 (calc_forward_returns): 指定ホライズン (デフォルト [1,5,21]) に対するリターンを一括 SQL で取得。
  - IC 計算 (calc_ic): ファクター値と将来リターンの Spearman ランク相関を算出（有効サンプル < 3 は None）。
  - ランク関数 (rank) と統計サマリー (factor_summary) を実装（外部ライブラリ不使用）。

- public API export
  - strategy、research パッケージで主要関数を __all__ により公開（build_features, generate_signals, calc_momentum 等）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- RSS パーサーで defusedxml を使用して XML 拡張攻撃を防止。
- ニュース収集で受信バイト数上限、HTTP/HTTPS スキーム制限、URL 正規化により SSRF/トラッキング対策を導入。
- J-Quants クライアントはトークンの自動リフレッシュと慎重な再試行戦略を採用。

### 既知の制限 / TODO
- execution パッケージは現状空のスケルトン（発注層の統合は未実装）。
- signal_generator のエグジット条件でトレーリングストップや時間決済は未実装（positions テーブルに peak_price / entry_date 情報が必要）。
- news_collector の実際の RSS パース・DB の紐付け処理（news_symbols など）はファイルの途中で定義が切れているため、追加実装が必要。
- 一部のユーティリティ（zscore_normalize 等）は別モジュール（kabusys.data.stats）に依存しており、その実装が前提となる。
- pandas 等の外部データ処理ライブラリを使用しない設計のため、大規模データに対する最適化（メモリ/パフォーマンス）は今後の改善対象。

### マイグレーション/運用メモ
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - その他: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/...）
- .env 自動読み込みはプロジェクトルート検出に依存。パッケージ配布後に環境が異なる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化し、明示的に環境を構成してください。
- DuckDB/SQLite のデフォルトファイルパスは settings で確認できます（DUCKDB_PATH, SQLITE_PATH 環境変数で上書き可能）。
- J-Quants API のレート制限やリトライ挙動に注意。ローカルテストで高速に多数のリクエストを投げないようにしてください。

---

今後のリリースでは execution 層の統合、news_collector の完全実装、追加の戦略/指標、性能改善・テスト拡充を予定しています。