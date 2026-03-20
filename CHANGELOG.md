# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

なお、本リリースはパッケージ版の初期公開を想定した内容（src/ 配下の実装に基づく推測）です。

## [Unreleased]
- 次のリリースに向けた変更点はここに記載します。

## [0.1.0] - 2026-03-20

Added
- 基本パッケージ構造を追加
  - パッケージ名: kabusys
  - __version__ = "0.1.0"
  - public API エクスポート: data, strategy, execution, monitoring

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装
    - プロジェクトルートの検出: .git または pyproject.toml を起点に上位ディレクトリを探索
    - 読み込み順序: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
  - .env パーサーの強化
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応
    - インラインコメントの扱いやクォート無しのコメント処理を細かく制御
  - .env 読み込みの保護機能
    - override フラグ、protected キーセットにより OS 環境変数の上書きを防止
  - Settings クラスを提供（settings インスタンス）
    - J-Quants / kabuステーション / Slack / データベースパス等のプロパティ
    - env や log_level の妥当性チェック（許容値の検証）
    - duckdb / sqlite のデフォルトパスを用意

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装
    - 固定間隔スロットリングでのレート制御（120 req/min）
    - 冪等性を考慮した保存（DuckDB への INSERT は ON CONFLICT DO UPDATE）
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes (日足 OHLCV)
      - fetch_financial_statements (財務諸表)
      - fetch_market_calendar (JPX カレンダー)
    - save_* 関数で DuckDB へ保存:
      - save_daily_quotes: raw_prices テーブルへ保存、PK 欠損行はスキップ・ログ出力
      - save_financial_statements: raw_financials テーブルへ保存
      - save_market_calendar: market_calendar テーブルへ保存
    - リトライと指数バックオフ
      - 対象: ネットワーク系エラーおよび 408/429/5xx
      - 最大リトライ回数: 3
      - 429 の場合は Retry-After ヘッダを優先
    - 401 Unauthorized 受信時は ID トークンを自動リフレッシュして1回だけ再試行（無限再帰防止）
    - モジュールレベルの ID トークンキャッシュを実装（ページネーション間で共有）
    - レスポンス JSON のデコード失敗時は明示的なエラーを送出
    - ユーティリティ: _to_float / _to_int（安全な型変換）

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集・保存機能（raw_news / news_symbols 想定）
  - セキュリティおよび耐障害性を考慮した実装
    - defusedxml による安全な XML パース（XML Bomb 等に対策）
    - 最大受信バイト数制限（MAX_RESPONSE_BYTES = 10MB）
    - URL 正規化: スキーム/ホストの小文字化、トラッキングパラメータ（utm_* 等）の削除、フラグメント削除、クエリパラメータのソート
    - 記事 ID を URL の正規化後ハッシュ（ドキュメント記述）で生成して冪等性を確保（ドキュメントに明記）
    - バルク INSERT のチャンク化による性能対策（_INSERT_CHUNK_SIZE）
    - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを追加

- リサーチ機能 (kabusys.research)
  - ファクター計算:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離率）
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（ATR/流動性指標）
    - calc_value: per / roe（raw_financials と prices_daily の組合せ）
  - 特徴量探索:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）で将来リターンを計算（LEAD を利用）
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算（有効サンプル数 3 未満なら None）
    - factor_summary: count/mean/std/min/max/median を計算
    - rank: 同順位は平均ランク扱い（浮動小数の丸めで ties の検出を安定化）
  - 実装方針: DuckDB 接続を受け取り、prices_daily / raw_financials を参照。外部依存を持たない純粋計算ロジック。

- 戦略モジュール (kabusys.strategy)
  - 特徴量作成 (feature_engineering.build_features)
    - research で算出した生ファクターをマージしてユニバースフィルタ適用（最低株価 300 円、20日平均売買代金 5 億円）
    - Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップ
    - features テーブルへ日付単位の置換（トランザクション + バルク挿入で原子性）
    - ルックアヘッドバイアス対策: target_date 時点のデータのみを使用
  - シグナル生成 (signal_generator.generate_signals)
    - features と ai_scores を統合して最終スコア final_score を計算
      - デフォルト重み: momentum=0.40, value=0.20, volatility=0.15, liquidity=0.15, news=0.10
      - デフォルト閾値 (BUY): 0.60
      - コンポーネントスコアの欠損は中立値 0.5 で補完
    - AI レジームスコア集計による Bear 検出（サンプル数閾値を設ける）
      - Bear レジーム時は BUY シグナルを抑制
    - BUY シグナル生成（スコア閾値超過、SELL 対象を優先して除外）
    - SELL シグナル生成（エグジット判定）
      - 実装済み: ストップロス（損益率 <= -8%）、final_score が閾値未満
      - 未実装（将来のTODO）: トレーリングストップ、時間決済（説明コメントに明記）
    - signals テーブルへ日付単位の置換（トランザクションで原子性）
    - weights の入力検証・正規化と合計の再スケール処理

Changed
- （初期リリースのため該当なし）主要な設計上の方針や各モジュールのインターフェースは docstring に明記

Fixed
- （初期リリースのため該当なし）実稼働中に判明したバグ修正は次版で記録予定

Security
- 外部入力（RSS XML / HTTP レスポンス / API）に対する安全対策を複数導入
  - defusedxml による XML パース
  - RSS ダウンロードサイズ制限
  - URL 正規化とトラッキングパラメータ除去
  - J-Quants クライアントでのエラーハンドリング強化（認証・リトライ制御）

Notes / Known limitations
- positions テーブルに peak_price / entry_date 等のメタデータがないため、トレーリングストップや保持期間決済は未実装（signal_generator 内に TODO コメントあり）
- news_collector の記事 ID 生成やニュース→銘柄の紐付けロジックは docstring に設計が述べられているが、実際のマッピングロジック（正規表現や辞書ベースのシンボル抽出など）は実装箇所の追加を想定
- DuckDB スキーマ（テーブル定義）は本 CHANGELOG に含まれていません。各関数は特定のテーブル列を参照するため、想定スキーマに合わせた DB 構築が必要です。
- 自動 .env ロードはプロジェクトルート検出に依存するため、配布先で .git や pyproject.toml が存在しない場合は自動読み込みをスキップします（明示的変数設定を推奨）。

Authors
- パッケージ実装者（コード内の docstring / ロガー記述に基づく設計責任者）

---

この CHANGELOG はコードベースの実装内容（docstring や関数仕様、定数、ログ記述）から推測して作成しています。実際のリリースノート作成時は差分コミットやリリース日、変更者等を正確に反映してください。