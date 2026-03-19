Keep a Changelog
=================

すべての変更はこのファイルに記載します。  
このプロジェクトは Keep a Changelog のガイドラインに従います。  

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-19
--------------------

Added
- パッケージ初版を公開。
  - パッケージ名: kabusys、バージョン: 0.1.0
  - パッケージルート: src/kabusys/__init__.py（__version__ とエクスポート定義）

- 環境設定・自動ロード機能（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動で読み込む仕組みを実装。
  - 環境変数自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env ファイルのパースはコメント・export プレフィックス・クォート・エスケープに対応。
  - 読み込みの優先順位: OS 環境変数 > .env.local > .env。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DBパス / システム設定（env, log_level）などをプロパティ経由で取得。
  - env / log_level の値検証とヘルプメッセージ（不正値時は ValueError）。

- Data 層（src/kabusys/data）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - 固定間隔レート制限（120 req/min）を実現する RateLimiter 実装。
    - リトライ（指数バックオフ）、最大試行回数、特定ステータス（408, 429, 5xx）での再試行ロジック。
    - 401 を検知した場合の自動トークンリフレッシュ（1 回のみ）と再試行。
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes（株価日足／ページネーション処理）
      - fetch_financial_statements（財務データ）
      - fetch_market_calendar（マーケットカレンダー）
    - DuckDB への冪等保存ユーティリティ:
      - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE
      - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE
      - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE
    - JSON のパース失敗やネットワークエラーに対するハンドリング、ログ出力。
    - 型変換ユーティリティ _to_float / _to_int（安全な変換、無効値は None）。
  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィード収集の基本実装（デフォルトに Yahoo Finance の RSS を設定）。
    - セキュリティ対策: defusedxml を用いた XML パース、安全な URL 正規化（トラッキングパラメータ除去、スキーム検証など）、受信サイズ上限（10MB）設定、SSR F等への配慮。
    - 記事 URL 正規化（クエリソート・utm_* 等の削除・フラグメント除去）とテキスト前処理のユーティリティ。
    - バルク INSERT のチャンク化（_INSERT_CHUNK_SIZE）とトランザクション最適化。
    - ドキュメントで ID 生成（正規化 URL の SHA-256 ハッシュ先頭を利用）による冪等性確保を想定。

- Research 層（src/kabusys/research）
  - ファクター計算・解析ユーティリティ群を実装。
  - factor_research.py:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA）計算
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（20日窓）
    - calc_value: per, roe を raw_financials と prices_daily から計算
    - SQL + DuckDB を用いた実装で、prices_daily/raw_financials のみ参照（外部 API に依存しない）
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）での将来リターンを一度のクエリで取得
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算（有効サンプル < 3 の場合は None）
    - factor_summary: count/mean/std/min/max/median を算出
    - rank: 平均ランク（同順位は平均ランクを割り当て、丸めで ties 検出を安定化）
  - research パッケージ __all__ を整備し、外部から利用しやすくした。

- Strategy 層（src/kabusys/strategy）
  - feature_engineering.build_features:
    - research 側で計算した raw ファクターをマージし、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位の置換（DELETE + INSERT をトランザクションで実行）により冪等性を確保。
    - 休場日や当日欠損に対応するため、target_date 以前の最新価格を参照してユニバース判定。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各銘柄の最終スコア（final_score）を算出。
    - コンポーネントスコア: momentum, value, volatility, liquidity, news（AI）
    - デフォルト重みと閾値（weights, threshold）を実装。外部から weights を受け取れるが、入力検証・フォールバック・再スケールを行う。
    - Bear レジーム検出（ai_scores の regime_score 平均が負の場合、かつサンプル数が閾値以上）により BUY を抑制。
    - SELL（エグジット）判定:
      - ストップロス（終値 / avg_price - 1 < -8%）
      - final_score が閾値未満
      - （未実装だが設計に明示）トレーリングストップ・時間決済は将来の拡張対象。
    - BUY / SELL シグナルを signals テーブルへ日付単位で置換して保存（トランザクション・バルク挿入）。
    - features が空の場合、BUY は生成せず SELL 判定のみ実施する仕様。
    - 欠損コンポーネントは中立値 0.5 で補完することで欠損銘柄の不当な降格を防止。

Changed
- （初版リリースのため該当なし）

Fixed
- （初版リリースのため該当なし）

Security
- news_collector で defusedxml を利用して XML Attack（XML Bomb 等）に対処。
- RSS URL の正規化でトラッキングパラメータを除去、HTTP スキーム検証等により SSRF リスクを低減。
- API クライアントでタイムアウト・再試行・リトライ制御を実装し、異常応答に対して堅牢化。

Known issues / Not implemented
- signal_generator のエグジット条件について、ドキュメントにあるトレーリングストップ（直近最高値から -10%）および時間決済（保有 60 営業日超過）は未実装。これらは positions テーブルに peak_price / entry_date 等が必要なため将来対応予定。
- calc_value は現時点で PER / ROE のみを算出。PBR や配当利回り等の指標は未実装。
- news_collector の一部（記事ID生成や銘柄との紐付け処理の詳細実装）は docstring 記載の設計指針に準拠する想定であり、実運用に向けた追加実装が必要。
- DuckDB テーブルスキーマ（テーブル名とカラム）を前提としているため、導入時にスキーマ準備が必要。

Notes / Implementation details
- 多くの DB 書き込み操作は日付単位の「DELETE → INSERT」をトランザクションで行い、処理の冪等性と原子性を保証する実装パターンを採用。
- ルックアヘッドバイアス防止を設計方針の中心に据え、target_date 時点のデータのみを用いることで再現性を担保。
- research モジュールは標準ライブラリのみで実装する方針（pandas 等の外部依存を避ける）。

--------------------------------
この CHANGELOG はコードベースの docstring・実装と設計コメントから推測して作成しています。実際のリリースノート作成時は用途に応じた詳細（コミットハッシュ、影響範囲、移行手順など）を追加してください。