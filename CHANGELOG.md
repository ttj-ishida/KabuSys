# CHANGELOG

すべての注目すべき変更を記載します。本ドキュメントは Keep a Changelog の形式に準拠します。

現在のリリース履歴:

- [Unreleased]
- [0.1.0] - 2026-03-19

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-19
初回公開リリース。日本株の自動売買・リサーチプラットフォームの基礎機能を実装しました。主な追加点・設計方針・注意点は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - パッケージのバージョン定義と公開 API を追加（kabusys.__init__）。
  - モジュールのトップレベル __all__ に data / strategy / execution / monitoring を登録。

- 設定管理
  - 環境変数読み込み・管理モジュールを実装（kabusys.config.Settings）。
    - プロジェクトルート（.git または pyproject.toml）を起点に .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env の行パースは export プレフィックス、クォート、エスケープ、インラインコメント等に対応。
    - OS 環境変数を保護する protected オプション（.env.local は既存 OS 環境変数を上書きしない）を実装。
    - 必須環境変数未設定時に分かりやすいエラーメッセージを送出する _require を提供。
    - 環境（development / paper_trading / live）やログレベルの検証プロパティ、DB パス取得などのプロパティを提供。

- データ層（J-Quants クライアント）
  - J-Quants API クライアントを実装（kabusys.data.jquants_client）。
    - レートリミット制御（120 req/min）の固定間隔スロットリングを実装（内部 _RateLimiter）。
    - リトライ（指数バックオフ、最大 3 回）とステータスコード指定（408/429/5xx）への対応。
    - 401 Unauthorized 受信時のトークン自動リフレッシュを実装（1 回のみ試行）。モジュールレベルで ID トークンをキャッシュ。
    - ページネーション対応の fetch_* 系 API を提供：
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（四半期財務データ）
      - fetch_market_calendar（JPX カレンダー）
    - DuckDB への保存関数（冪等）を提供：
      - save_daily_quotes（raw_prices）
      - save_financial_statements（raw_financials）
      - save_market_calendar（market_calendar）
    - 取得時刻（fetched_at）を UTC ISO フォーマットで記録することで「いつデータが既知になったか」を追跡可能に。

  - データ変換ユーティリティを追加（_to_float / _to_int）。
    - _to_int は "1.0" 等を float 経由で変換し、小数部が 0 以外なら None を返す等、入力の曖昧さに配慮。

- ニュース収集
  - RSS ベースのニュース取得モジュール（kabusys.data.news_collector）を実装。
    - defusedxml を用いた安全な XML パース、HTTP レスポンスサイズ制限（MAX_RESPONSE_BYTES）などによりセキュリティ・可用性に配慮。
    - URL 正規化（スキーム/ホスト小文字化・トラッキングパラメータ除去・フラグメント削除・クエリキーソート）を実装。
    - 記事 ID を URL 正規化後の SHA-256（先頭32文字）で生成して冪等性を確保。
    - raw_news へのバルク保存ポリシー（チャンク化、トランザクション等）を採用。

- リサーチ（ファクター計算・探索）
  - ファクター計算モジュールを追加（kabusys.research.factor_research）:
    - calc_momentum（1M/3M/6M リターン、MA200乖離）
    - calc_volatility（20日 ATR, atr_pct, avg_turnover, volume_ratio）
    - calc_value（PER, ROE を raw_financials と prices_daily から計算）
    - DuckDB を用いた SQL+ウィンドウ関数での実装。営業日の欠損・データ不足時の None 戻しを採用。
  - 特徴量探索モジュールを追加（kabusys.research.feature_exploration）:
    - calc_forward_returns（指定ホライズンの将来リターン：デフォルト [1,5,21]）
    - calc_ic（Spearman のランク相関による IC 計算）
    - factor_summary（count/mean/std/min/max/median を算出）
    - rank（同順位は平均ランクとして扱うランク付けユーティリティ）
  - 研究 API は外部依存（pandas 等）を持たず、prices_daily のみ参照する設計。

- 戦略（特徴量エンジニアリング・シグナル生成）
  - 特徴量作成（kabusys.strategy.feature_engineering.build_features）を実装。
    - research の生ファクターをマージしユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を通し、指定カラムを Z スコア正規化（±3 クリップ）して features テーブルへ日付単位で置換（冪等）。
    - 休場日や当日欠損に対応するため target_date 以前の最新価格参照を使用。
  - シグナル生成（kabusys.strategy.signal_generator.generate_signals）を実装。
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news コンポーネントで final_score を計算（デフォルト重みを定義）。
    - final_score の閾値（デフォルト 0.60）超過で BUY、エグジット条件（ストップロス -8% / スコア低下）で SELL を生成。
    - Bear レジーム判定（ai_scores の regime_score の平均が負の場合）では BUY を抑制。
    - positions / prices_daily を参照して SELL 条件を判定。features が空の場合は BUY を生成せず SELL 判定のみ行う挙動。
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）し、SELL 優先で BUY からSELL銘柄を除外してランクを再付与。

- 共通
  - DuckDB をデータストアとして前提にした SQL/トランザクション設計。
  - ルックアヘッドバイアスを防ぐ設計方針（target_date 時点のデータのみを使用、fetched_at による取得時刻記録等）を明示。

### 変更 (Changed)
- なし（初回リリースのため既存機能の変更履歴はなし）。

### 修正 (Fixed)
- DB トランザクション中の例外発生時に ROLLBACK 失敗をロギングする安全処理を追加（feature_engineering / signal_generator の例外ハンドリング）。
- save_* 系の関数で PK 欠損レコードをスキップして警告を出すようにして、部分的な不整合で処理が止まらないようにした。

### 破壊的変更 (Breaking Changes)
- 該当なし（初回公開）。

### セキュリティ (Security)
- news_collector で defusedxml を使用して XML 攻撃を低減。
- RSS の取得時に受信サイズ上限（MAX_RESPONSE_BYTES）を導入してメモリ DoS を軽減。
- J-Quants クライアントで認証トークン管理を改善（自動リフレッシュ時のループ防止設計）。

### 注意事項 / 制限 (Notes)
- 多くの機能は DuckDB 内の所定テーブル（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar, raw_news 等）を前提とします。スキーマは実装に応じて準備してください。
- 一部仕様（例: トレーリングストップ、時間決済など）は positions テーブルに追加データ（peak_price / entry_date 等）が必要なため未実装として明記されています。
- J-Quants API の利用にはリフレッシュトークン等の環境変数設定が必須です（Settings が未設定の場合は ValueError を送出します）。
- 本リリースでは execution 層（発注インターフェース）の実装は含まれていません（パッケージ構成上のプレースホルダは存在）。

---

上記はソースコード内の実装・ドキュメンテーションコメントから推測して作成した変更履歴です。必要であれば、各機能の利用方法・期待される DB スキーマやサンプルワークフローを別途まとめます。どのセクションを詳しく展開しましょうか？