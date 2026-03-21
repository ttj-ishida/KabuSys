# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載します。  
このプロジェクトは現在バージョン 0.1.0 を初回リリースしています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-21
初回リリース。以下の主要コンポーネントを実装・追加しました。

### 追加（Added）
- パッケージ基本情報
  - パッケージ名: kabusys、バージョン 0.1.0 を追加。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ にてエクスポート。

- 設定／環境変数管理（kabusys.config）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env パーサーを実装。コメント行、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数は保護される（上書き防止）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、アプリケーションで利用する主要設定値（J-Quants トークン、kabu API パスワード／ベース URL、Slack トークン・チャンネル、DB パス、環境種別、ログレベル等）をプロパティ経由で取得。値検証（env 値の許容値チェック・必須値未設定時の例外）を実装。
  - is_live / is_paper / is_dev の便利プロパティを追加。

- Data 層（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - 固定間隔（スロットリング）ベースの RateLimiter を実装し、120 req/min のレート制限を遵守。
  - HTTP リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）を実装。429 の場合は Retry-After ヘッダを尊重。
  - 401 Unauthorized を検知するとリフレッシュトークンから id_token を自動更新して 1 回リトライ（無限再帰回避）。
  - ページネーション対応でデータを取得するユーティリティ（fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar）。
  - DuckDB への保存機能（save_daily_quotes、save_financial_statements、save_market_calendar）を実装。ON CONFLICT（UPSERT）による冪等性を確保。PK 欠損レコードはスキップし警告を出力。
  - データ整形ユーティリティ（数値変換の安全化: _to_float / _to_int）を実装。
  - データ取得時の fetched_at を UTC ISO8601 形式で保存し、Look-ahead バイアスの追跡を可能に。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集基盤を追加（デフォルトに Yahoo Finance のカテゴリ RSS を設定）。
  - URL 正規化（トラッキングパラメータ削除、スキーム/ホスト小文字化、フラグメント除去、クエリソート）を実装。
  - セキュリティ対策: defusedxml を利用した XML パース、防止策（XML bomb 等）、SSRF 対策、最大受信サイズ制限（MAX_RESPONSE_BYTES）を導入。
  - 記事ID 生成は URL 正規化後の SHA-256（短縮）を利用する方針（冪等性確保）。
  - DB へのバルク挿入はチャンク処理を行い、トランザクションのまとめによる性能最適化を想定。

- リサーチ（kabusys.research）
  - ファクター計算ユーティリティ群を実装しエクスポート:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率の計算（必要行数が満たない場合は None を返す）。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率等。
    - calc_value: raw_financials と prices_daily を組み合わせた PER / ROE の計算（最新の報告日を参照）。
  - feature_exploration モジュールを実装:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンランク相関（IC）計算。サンプル不足や等分散時の保護ロジックを実装。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算する統計要約。
    - rank: 同順位は平均ランクを返すランク付けユーティリティ（丸めによる ties 対策あり）。
  - DuckDB のみを参照する設計（外部 API / 本番発注にアクセスしない）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features 実装:
    - research の calc_* を用いて生ファクターを取得、ユニバースフィルタを適用（最低株価・平均売買代金基準）、指定カラムを Z スコア正規化、±3 でクリップ。
    - DuckDB の features テーブルへ日付単位で置換（BEGIN/DELETE/INSERT/COMMIT により原子的に更新）する冪等処理。
    - ユニバース定義: 最低株価 300 円、20 日平均売買代金 5 億円。
    - 正規化対象カラムの明示: mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals 実装:
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算して final_score を算出（デフォルト重みを提供、外部から重みを受け取り正規化）。
    - コンポーネントの欠損は中立 0.5 で補完し、不当な降格を防止。
    - スコア変換ユーティリティ: シグモイド変換、平均化、NaN/Inf 保護。
    - Bear レジーム判定機能（ai_scores の regime_score 集計により判定、サンプル数閾値あり）。Bear 時は BUY シグナルを抑制。
    - BUY シグナル生成は閾値（デフォルト 0.60）以上の銘柄に対して実行。SELL シグナルは保有ポジションを対象にストップロス（-8%）およびスコア低下を判定。
    - 保有ポジションの価格欠損時は SELL 判定をスキップする安全策を実装。
    - signals テーブルへ日付単位置換（原子性を保証）。
    - 未実装の機能（将来的実装予定）としてトレーリングストップや時間決済に関する注記あり（positions テーブルに peak_price / entry_date が必要）。

- API エクスポート（kabusys.strategy）
  - build_features と generate_signals をパッケージ外部へ公開する __all__ を追加。

### 変更（Changed）
- 初回リリースのため該当なし。

### 修正（Fixed）
- 初回リリースのため該当なし。

### 既知の制限・注意点（Notes）
- 一部のエグジット条件（トレーリングストップ、時間決済）は未実装で、将来的に positions テーブルの拡張を想定しています（signal_generator 内に注記あり）。
- news_collector の実装は URL 正規化等の設計を含みますが、外部フェッチの実行戦略（HTTP クライアントの細部・パーサーの完全な実装）は今後の拡張対象となる可能性があります。
- research / data / strategy 層はいずれも DuckDB を前提としており、本番での運用前にスキーマ整備（tables: raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar など）の確認が必要です。

<!--
追記:
- 今後のリリースでは監視（monitoring）・実行（execution）層の具体的な発注ロジック・Slack 通知などを追加予定。
-->
