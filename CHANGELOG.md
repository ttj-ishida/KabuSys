# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
このプロジェクトはまだ初期リリース段階です。

フォーマット: [バージョン] - YYYY-MM-DD

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-20

初回公開リリース。以下の主要機能および実装方針を含みます。

### 追加 (Added)
- 全体
  - パッケージ kabusys を初期実装。
  - __version__ を "0.1.0" に設定し、主要サブモジュールを __all__ に公開 (data, strategy, execution, monitoring)。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート自動検出: .git または pyproject.toml を起点として .env/.env.local をプロジェクト配下から自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサ実装: export 形式対応、クォート文字列のバックスラッシュエスケープ対応、行内コメント処理などの堅牢なパース。
  - 環境値検証: KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の有効値チェック。必須キー取得時のエラー報告 (_require)。

- データ取得・保存 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装（認証トークン取得、ページネーション対応の fetch 関数群）。
  - RateLimiter による固定間隔スロットリング（120 req/min）実装。
  - 再試行（指数バックオフ、最大3回）と 401 時の自動トークンリフレッシュ処理を実装。
  - DuckDB への冪等保存関数を実装:
    - save_daily_quotes: raw_prices への保存（ON CONFLICT DO UPDATE）
    - save_financial_statements: raw_financials への保存（ON CONFLICT DO UPDATE）
    - save_market_calendar: market_calendar への保存（ON CONFLICT DO UPDATE）
  - データ変換ユーティリティ (_to_float / _to_int) を提供し、入力の堅牢化を実現。
  - 取得時刻（fetched_at）を UTC ISO8601 で記録し、Look-ahead バイアス追跡をサポート。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードから記事収集して raw_news に保存する機能を実装。
  - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント除去）と記事ID生成（SHA-256 の先頭32文字）による冪等性確保。
  - セキュリティ対策:
    - defusedxml を使用して XML Bomb 等を防止。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）を導入してメモリDoSを緩和。
    - SSRF や不正 URL を避けるための入力検証方針（実装の考慮点を明記）。
  - バルク INSERT のチャンク処理を導入して DB オーバーヘッドを抑制。
  - デフォルト RSS ソースに Yahoo Finance のビジネス RSS を設定。

- リサーチ系（研究用） (src/kabusys/research/*)
  - ファクター計算モジュールを実装（prices_daily / raw_financials 使用）:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率
    - calc_value: per, roe（直近の財務データを参照）
  - 特徴量探索・統計モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）に対する将来リターンの一括取得
    - calc_ic: スピアマンランク相関（Information Coefficient）の計算
    - factor_summary: 各ファクターの count/mean/std/min/max/median を計算
    - rank: 同順位は平均ランクとするランク付けユーティリティ
  - 研究モジュールは外部ライブラリ（pandas 等）に依存せず、DuckDB と標準ライブラリだけで実装。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features(conn, target_date) を実装:
    - research モジュールの calc_momentum / calc_volatility / calc_value を利用して生ファクターを取得。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 指定カラムの Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップして外れ値の影響を抑制。
    - 日付単位で features テーブルに置換（DELETE + バルク INSERT）して冪等性を保証。
    - DuckDB トランザクションを使用して原子性を確保。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装:
    - features / ai_scores / positions を参照して各銘柄のコンポーネントスコア（momentum, value, volatility, liquidity, news）を算出。
    - コンポーネントはシグモイド変換や逆数変換などで [0,1] スコアに正規化し、欠損は中立 0.5 で補完。
    - デフォルト重みを実装（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。ユーザー指定 weights はバリデーション・補完・再スケールされる。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）により BUY シグナルを抑制。
    - BUY シグナルは threshold 超過銘柄に対して付与。SELL シグナルはエグジット判定（ストップロス -8% / スコア低下）により生成。
    - SELL 優先ポリシーにより SELL 対象は BUY から除外し、signals テーブルへ日付単位で置換して保存（トランザクションで原子性を保障）。
    - ログ・警告を豊富に出力し、欠損データや不正な入力に対して堅牢に動作。

### 変更 (Changed)
- n/a （初回リリースのため既存コードの変更点はなし）

### 修正 (Fixed)
- n/a （初回リリース）

### 非推奨 (Deprecated)
- n/a

### 削除 (Removed)
- n/a

### セキュリティ (Security)
- news_collector で defusedxml を利用、受信バイト数制限および URL 正規化による SSRF/トラッキング緩和を実装。
- J-Quants クライアントでトークン管理・自動リフレッシュを実装し、認証ロジックを安全に扱う。

### 注意事項 / 実装上の制約・未実装項目
- 売却条件に関して、トレーリングストップ（ピーク価格ベース）や時間決済（保有 60 営業日超）などは positions テーブルに peak_price / entry_date 等の追加データが必要であり、現行実装では未実装として注記されています。
- calc_forward_returns の horizons は営業日ベースの連続レコード数として扱われ、SQL の取得範囲はカレンダー日で十分なバッファを取る実装になっています。
- feature_engineering では per カラム（逆数変換する対象）は正規化対象から除外しています（value 側で別処理）。
- 一部の関数はデータ欠損時に None を返す設計（データ不足の銘柄は無理に評価しない方針）。

---

今後のリリースでは以下を予定しています（例）:
- execution 層（kabu API 連携）および monitoring 周りの実装強化
- テストカバレッジの拡充、CI/CD の導入
- パフォーマンス最適化（大規模データ処理時のメモリ／I/O 改善）

お問い合わせやバグ報告はリポジトリの Issue をご利用ください。