# Changelog

すべての注目すべき変更点はここに記載します。  
このファイルは Keep a Changelog の形式に従っています。  

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主にデータ取得・格納、ファクター計算、特徴量作成、シグナル生成、研究用ユーティリティ、設定管理、ニュース収集の各モジュールを含みます。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報と公開 API を定義（kabusys.__init__）。
  - バージョン: 0.1.0。

- 設定管理（kabusys.config）
  - .env ファイル／環境変数から設定をロードする自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - .env パーサーを実装（export 形式、シングル/ダブルクォート、エスケープ、行末コメントの処理をサポート）。
  - .env の読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
  - Settings クラスを提供し、必須環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）やパス（DUCKDB_PATH, SQLITE_PATH）、env/log_level の検証ロジックを実装。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレートリミット制御（120 req/min）。
    - リトライ（指数バックオフ、最大3回）と HTTP ステータスに基づく再試行制御（408/429/5xx）。
    - 401 受信時は自動でリフレッシュトークンから id token を再取得して 1 回リトライ。
    - ページネーション対応で全ページを取得。
    - 取得時刻（fetched_at）を UTC で記録し、look-ahead バイアスのトレースを可能に。
  - データ保存関数:
    - save_daily_quotes: raw_prices テーブルへ冪等保存（ON CONFLICT DO UPDATE）。
    - save_financial_statements: raw_financials テーブルへ冪等保存。
    - save_market_calendar: market_calendar テーブルへ冪等保存。
  - ユーティリティ: 型変換関数 _to_float / _to_int（空値・不正値は None）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集と raw_news への保存ロジック。
  - セキュリティ対策:
    - defusedxml を使用して XML 攻撃を軽減。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ削除、フラグメント除去、キー順ソート）。
    - HTTP/HTTPS 以外のスキーム拒否や受信最大バイト数制限（10MB）によるメモリDoS対策。
    - 記事IDは正規化 URL の SHA-256（先頭32文字）を利用して冪等性を確保。
  - 保存時はバルク挿入のチャンク化（_INSERT_CHUNK_SIZE）やトランザクションまとめで効率化。

- 研究用モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）の算出。
    - calc_volatility: 20日 ATR、atr_pct、avg_turnover、volume_ratio の計算。
    - calc_value: per、roe（raw_financials の最新財務データを用いる）。
    - 各関数は DuckDB の prices_daily / raw_financials を参照し、データ不足時は None を返す設計。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - calc_forward_returns: 指定ホライズンの将来リターン（デフォルト [1,5,21]）を計算（営業日ベース）。
    - calc_ic: ファクターと将来リターンの Spearman（ランク相関）IC を計算。サンプル不足時は None を返す。
    - factor_summary: count/mean/std/min/max/median の統計サマリを算出。
    - rank: 同順位は平均ランクにするランク付け実装（丸めで ties の検出漏れを防止）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features 実装:
    - research モジュールの生ファクターを取得し、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats::zscore_normalize を使用）、±3 でクリップして外れ値影響を抑制。
    - features テーブルへ日付単位の置換（DELETE→INSERT をトランザクションで実行）により冪等性と原子性を確保。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals 実装:
    - features と ai_scores を統合し、モメンタム/バリュー/ボラティリティ/流動性/ニュース の各コンポーネントスコアを算出。
    - コンポーネントの合成は重み付き和（デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。
    - final_score を閾値（デフォルト 0.60）で評価して BUY シグナルを生成。Bear レジーム（AI の regime_score 平均が負）を検出した場合は BUY を抑制。
    - エグジット判定（SELL）:
      - ストップロス: 終値 / avg_price - 1 < -8%（優先）。
      - スコア低下: final_score が閾値未満。
      - SELL は BUY より優先し、signals テーブルへ日付単位の置換で書き込む（冪等）。
    - weights 引数は検証・補完・正規化を行い、無効値は警告して無視。合計が 1.0 でなければ再スケール。

- strategy パッケージ公開 API
  - build_features, generate_signals を公開。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- news_collector で defusedxml の採用、受信サイズ制限、URL 正規化およびスキームチェックにより外部入力による攻撃ベクタを低減。
- jquants_client は認証トークンの自動リフレッシュとリトライ制御を実装し、不正なトークン状態に対して安全に復帰するよう設計。

---

メモ:
- 本リリースは主にデータパイプラインと戦略計算基盤の整備を目的としています。発注・execution 層や実運用の監視（monitoring）・実取引対応は別モジュール／今後のリリースで補完される想定です。