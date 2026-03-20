# Changelog

すべての注目すべき変更点を記載します。フォーマットは "Keep a Changelog" に準拠しています。

履歴はセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-20

初回リリース。

### 追加 (Added)
- パッケージの初期公開
  - パッケージ名: kabusys、バージョン: 0.1.0
  - パッケージトップに __version__ を追加。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの自動ロード機能を実装。
    - プロジェクトルート判定: カレントワーキングディレクトリに依存せず、__file__ を基点に `.git` または `pyproject.toml` を探索してプロジェクトルートを特定。
    - 読み込み優先順位: OS 環境 > .env.local > .env。
    - 自動ロード無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能（テスト用途）。
  - .env パーサを実装（引用符付き値、エスケープ、export プレフィックス、行内コメント処理に対応）。
  - 上書きポリシー:
    - override=False のときは未設定のキーのみセット。
    - override=True のときは OS 環境変数（読み込み時に収集された protected set）を上書きしない保護機構を実装。
  - 必須環境変数取得ヘルパー `_require()` を実装（未設定時は ValueError を送出）。
  - Settings クラスを実装し、アプリ設定をプロパティ経由で公開:
    - J-Quants / kabuステーション / Slack / DB パス（duckdb/sqlite） / env/ログレベルの取り扱い。
    - KABUSYS_ENV 値検証（development, paper_trading, live のみ）。
    - LOG_LEVEL 値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 基本機能:
    - レート制限 (120 req/min) を守る固定間隔スロットリング実装（_RateLimiter）。
    - 冪等なデータ保存用ユーティリティ（DuckDB への INSERT ... ON CONFLICT DO UPDATE を利用）。
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes: 日足データ取得（ページネーション対応）。
      - fetch_financial_statements: 財務データ取得（ページネーション対応）。
      - fetch_market_calendar: マーケットカレンダー取得。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx 等に対応）。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）を実装。
    - id_token のモジュールレベルキャッシュを実装し、ページネーション等で共有。
  - 保存関数:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装し、PK 欠損行のスキップや挿入件数ログを実装。
    - 日時は UTC の fetched_at を記録。
  - HTTP ユーティリティ: JSON デコードエラーの扱い、Retry-After ヘッダ優先処理等を実装。
  - 型変換ユーティリティ: _to_float / _to_int。

- ニュース収集 (kabusys.data.news_collector)
  - RSS から記事を収集して raw_news へ保存するための基礎を実装。
  - セキュリティと堅牢性:
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - レスポンス最大読み込みバイト数制限（MAX_RESPONSE_BYTES = 10 MB）。
    - URL 正規化とトラッキングパラメータ除去（utm_* 等）、クエリソート、フラグメント除去。
    - 記事 ID は正規化後のハッシュ（仕様での冪等性確保）を想定。
  - バルク挿入用チャンク処理を用意（_INSERT_CHUNK_SIZE）。

- リサーチ: ファクター計算 / 探索 (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金、出来高比率を計算。
    - calc_value: 直近財務情報（raw_financials の最新レコード）と当日株価から PER / ROE を計算。
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみ参照。結果は (date, code) をキーとする辞書リストで返却。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の入力検証あり。
    - calc_ic: スピアマンランク相関（IC）を計算。サンプル不足（<3）や分散ゼロの場合は None を返す。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
    - rank: 同順位は平均ランクに変換するランク関数（丸めで ties の扱い安定化）。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date) を実装:
    - research の calc_momentum / calc_volatility / calc_value を利用して生ファクターを取得。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 指定カラム（mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）に対する Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE + INSERT をトランザクションで行い冪等性を保証）。
    - 価格欠損・非数値の扱いに注意。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装:
    - features / ai_scores / positions テーブルを参照して最終スコア（final_score）を計算。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI）。
      - 各コンポーネントの計算法を実装（シグモイド変換や PER の逆スケール等）。
      - AI スコアが未登録の場合は中立 0.5 で補完。
    - 重みの受け取りと検証:
      - 未知キー・非数値・NaN/Inf・負値を無視し、既知キーで補完。
      - 合計が 1.0 でない場合にリスケール、合計 0 の場合はデフォルトにフォールバック。
    - Bear レジーム判定（AI の regime_score の平均が負の場合を Bear、ただしサンプル数閾値を満たすことが条件）。
      - Bear 時は BUY シグナルを抑制。
    - BUY: threshold（デフォルト 0.60）を超える銘柄に対して BUY シグナルを生成。
    - SELL（エグジット判定）:
      - 実装済: ストップロス（終値/avg_price -1 < -8%）および final_score が閾値未満の場合。
      - 未実装（保留）: トレーリングストップ、時間決済（説明あり）。
    - SELL 優先ポリシー: SELL 対象は BUY から除外し、BUY のランクを再付与。
    - signals テーブルへ日付単位の置換（トランザクションで冪等性を保証）。
    - ログ出力・警告を適切に追加。

- パッケージ公開用のモジュール構成
  - kabusys.strategy, kabusys.research で便利関数を __all__ にて公開。

### 変更 (Changed)
- （初回リリースにつき該当なし）

### 修正 (Fixed)
- （初回リリースにつき該当なし）

### 削除 (Removed)
- （初回リリースにつき該当なし）

### 非推奨 (Deprecated)
- （初回リリースにつき該当なし）

### セキュリティ (Security)
- RSS パースに defusedxml を使用し、XML ベースの攻撃耐性を向上。
- ニュース収集で受信バイト数を制限し、メモリ DoS を軽減する設計。
- J-Quants クライアントはトークンの自動リフレッシュを限定的に行い、無限再帰を防止する安全対策を実装。

---

注:
- 本 CHANGELOG はコードベースからの推測に基づいて作成しています。実際の挙動や追加ドキュメント（StrategyModel.md / DataPlatform.md 等）と併せてご確認ください。