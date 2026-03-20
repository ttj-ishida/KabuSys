CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

[0.1.0] - 2026-03-20
--------------------

Added
- 初回リリース。日本株自動売買システム "KabuSys" の基本モジュール群を追加。
  - パッケージエントリポイント
    - kabusys.__init__ にてバージョン "0.1.0" と公開 API を定義。
  - 設定 / 環境変数管理 (kabusys.config)
    - .env / .env.local の自動読み込み（プロジェクトルートを .git / pyproject.toml から探索）。
    - export KEY=val 形式、引用符付き値、インラインコメント等に対応する堅牢な .env パーサ実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
    - Settings クラスを提供: J-Quants / kabu API / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベル 等のプロパティを取得・検証。
  - データ収集・保存 (kabusys.data)
    - J-Quants クライアント (jquants_client)
      - 固定間隔レートリミッタ（120 req/min）実装。
      - リトライ（指数バックオフ、最大 3 回）、HTTP 429/408/5xx に対する再試行ロジック。
      - 401 時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ。
      - ページネーション対応 fetch_* 関数（daily_quotes / financial_statements / market_calendar）。
      - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装（ON CONFLICT DO UPDATE）。
      - 入力変換ユーティリティ（_to_float / _to_int）。
      - データの取得時刻（fetched_at）を UTC で記録し、Look-ahead バイアスのトレーサビリティを確保。
    - ニュース収集モジュール (news_collector)
      - RSS フィード取得・パース、記事正規化、raw_news への冪等保存（INSERT RETURNING 想定）を実装。
      - 記事 ID を URL 正規化後の SHA-256（先頭 32 文字）で生成して重複防止。
      - defusedxml による XML 攻撃防御、受信サイズ上限（10MB）、SSRF 防止のためスキームチェック等の堅牢化を実施。
      - トラッキングパラメータの削除、クエリソートなどの URL 正規化機能を実装。
  - 研究（research）モジュール
    - factor_research: prices_daily / raw_financials を基にモメンタム / ボラティリティ / バリュー系ファクターを計算する関数を実装。
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日移動平均乖離）を算出。
      - calc_volatility: 20 日 ATR（atr_20 / atr_pct）・平均売買代金・出来高比率を算出。
      - calc_value: target_date 以前の最新財務データと株価を組合わせて PER / ROE を算出。
    - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク化ユーティリティ（rank）を実装。外部依存を使わず標準ライブラリのみで実装。
    - research.__init__ で主要ユーティリティを再エクスポート。
  - 戦略（strategy）モジュール
    - feature_engineering.build_features
      - research 側で算出した生ファクターをマージ・ユニバースフィルタ（最低株価・20 日平均売買代金）適用・Z スコア正規化（指定カラム、±3 でクリップ）して features テーブルへ日付単位で置換（トランザクションで原子性確保）。
      - ルックアヘッドバイアス回避のため target_date 時点のデータのみ参照。
    - signal_generator.generate_signals
      - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、重み付きで final_score を算出。
      - 重みの入力検証・補完・正規化（合計が 1.0 になるよう再スケール）。無効なキー/値は無視。
      - Bear レジーム判定（ai_scores の regime_score の平均が負の場合、サンプル数閾値あり）により BUY シグナルを抑制。
      - BUY シグナル閾値（デフォルト 0.60）を超えた銘柄を BUY、保有ポジションに対してストップロス（-8%）やスコア低下で SELL を生成。
      - SELL 優先ポリシー（SELL 対象は BUY から除外）と signals テーブルへの日付単位置換をトランザクションで実施。
  - その他
    - strategy パッケージのエクスポート（build_features / generate_signals）。
    - execution パッケージのプレースホルダ（今後の実装を想定）。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Deprecated
- 該当なし。

Removed
- 該当なし。

Security
- news_collector で defusedxml を使用し XML 関連の脆弱性を軽減。
- news_collector 内で受信サイズ制限・URL 正規化・トラッキング除去・スキームチェック等を実装し、SSRF やメモリ DoS 等への対策を講じている。
- J-Quants クライアントはトークンの自動リフレッシュを実装しつつ無限再帰を防止する設計（allow_refresh フラグ）。

Notes / Known limitations
- execution パッケージは未実装のプレースホルダ。
- 一部仕様（例: トレーリングストップ、時間決済）は signal_generator の _generate_sell_signals 内コメントにある通り未実装で、positions テーブルに追加情報（peak_price / entry_date 等）が必要。
- DuckDB 側のスキーマ（テーブル定義）は本リリースに含まれていないため、実行前に必要テーブルを作成する必要あり。
- 一部処理（特に外部 API 呼び出し）はネットワークや外部サービスの挙動に依存するため、実運用前に統合テストを推奨。

作者
- KabuSys 開発チーム

-------------