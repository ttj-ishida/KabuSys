Keep a Changelog に準拠した CHANGELOG.md を以下に日本語で作成しました。プロジェクトのコード内容から推測して記載しています。必要なら日付や細部を調整してください。

----
Keep a Changelog
=================

すべての notable な変更はこのファイルに記録します。  
フォーマットは https://keepachangelog.com/ja/ に準拠します。

Unreleased
---------

- なし

0.1.0 - 2026-03-20
------------------

初回リリース（機能追加）。主要な機能と設計意図、既知の制限をまとめています。

Added
-----

- パッケージ基盤
  - kabusys パッケージの初期実装（__version__ = 0.1.0）。
  - public API: kabusys.data / kabusys.strategy / kabusys.execution / kabusys.monitoring をエクスポート。

- 設定管理
  - 環境変数・.env 読み込みのユーティリティを実装（kabusys.config）。
    - .env/.env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサは export プレフィックス、引用符付き値のエスケープ、インラインコメントルールなどをサポート。
    - .env の読み込み時に OS 環境変数を保護する仕組み（protected keys）を導入。
    - 必須環境変数取得時にエラーを出す _require 関数、KABUSYS_ENV/LOG_LEVEL の妥当性チェックを実装。
    - 主要設定プロパティ: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH 等。

- データ取得・保存（J-Quants）
  - J-Quants API クライアント実装（kabusys.data.jquants_client）
    - レート制限: 固定間隔スロットリングで 120 req/min を守る RateLimiter。
    - リトライ: 指数バックオフ（最大 3 回）、408/429/5xx を対象。429 の Retry-After を尊重。
    - 401 (Unauthorized) を検知した場合の自動トークンリフレッシュ（1 回のみ）と再試行。
    - ページネーション対応の fetch_* 系メソッド（株価・財務・カレンダー）。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は冪等（ON CONFLICT DO UPDATE / DO NOTHING）で fetched_at を UTC で記録。
    - 型変換ユーティリティ _to_float / _to_int を実装（破損データに対する耐性を強化）。

- ニュース収集
  - RSS ベースのニュース収集モジュール（kabusys.data.news_collector）。
    - デフォルトソース（Yahoo Finance 等）設定。
    - URL 正規化（トラッキングパラメータ削除、フラグメント除去、クエリソート）。
    - 記事ID は URL 正規化後の SHA-256（先頭 32 文字）を用いることで冪等性を確保。
    - defusedxml を用いた安全な XML パース、応答サイズ上限（MAX_RESPONSE_BYTES）や SSRF 対策などのセキュリティ配慮。
    - DB へバルク挿入（チャンク化）してパフォーマンスと SQL 長制限に配慮。

- 研究（research）
  - factor_research, feature_exploration 等の研究用モジュール実装（kabusys.research）。
    - calc_momentum / calc_volatility / calc_value: prices_daily / raw_financials テーブルから各種ファクターを計算。
      - モメンタム（1M/3M/6M）、MA200 乖離、ATR20、平均売買代金、出来高比率、PER/ROE など。
      - スキャン範囲バッファや営業日ベース（連続レコード数）での計算を考慮。
    - calc_forward_returns: 将来リターン（デフォルト: 1,5,21営業日）を高速に取得するクエリを提供。
    - calc_ic: Spearman（ランク相関）による IC 計算（同順位は平均ランクで処理）。有効データが 3 未満の場合 None を返す。
    - factor_summary / rank: 基本統計量の算出、ランク付けユーティリティ。
    - 研究モジュールは外部ライブラリ（pandas 等）に依存しない設計。

- 特徴量エンジニアリング
  - feature_engineering.build_features を実装。
    - research モジュールから取得した raw factors をマージし、ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 指定カラムを zscore_normalize（kabusys.data.stats）で正規化し ±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE + BULK INSERT）し原子性を保証。
    - 保存前に target_date 以前の最新価格を参照して休場日対応。

- シグナル生成（戦略）
  - signal_generator.generate_signals を実装。
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - final_score は重み付き合算（デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。
    - デフォルト BUY 閾値: 0.60。STOP-LOSS: -8%（_STOP_LOSS_RATE）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数 >= 3）。Bear 時は BUY を抑制。
    - 保有ポジションのエグジット判定（ストップロス、score 低下）を実装。
    - signals テーブルへ日付単位の置換を行い冪等性を確保。SELL を優先して BUY から除外、ランク再付与。

- DuckDB 連携
  - 各処理は DuckDB 接続を受け取り SQL と Python を組み合わせて処理する設計。テーブル設計を前提にしたクエリ群（prices_daily, raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals 等）を利用。

Changed
-------

- 初回リリースのため該当なし。

Fixed
-----

- 初回リリースのため該当なし。

Security
--------

- ニュース収集で defusedxml を使用し XML 関連の攻撃を防止。
- news_collector で受信サイズ制限、HTTP スキーム検査、トラッキングパラメータ除去、SSRF を意識した処理を実装。
- jquants_client はトークン自動リフレッシュ・リトライ制御を実装し、API 認証やネットワークエラーでの安全な再試行を導入。

Deprecated
----------

- 初回リリースのため該当なし。

Removed
-------

- 初回リリースのため該当なし。

Notes / Known limitations / TODO
--------------------------------

- signal_generator のエグジットロジックでは未実装の条件がコメントに記載されている:
  - トレーリングストップ（peak_price 情報が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
  - これらは positions テーブルに peak_price / entry_date 等の拡張が必要。
- research モジュールは外部解析ツール（pandas 等）を使わない設計だが、大量データ処理時の性能チューニングが今後の課題。
- news_collector の記事 ID は URL 正規化に依存するため、将来的に正規化ルール変更時は再整合が必要になる可能性あり。
- .env 自動読み込みはプロジェクトルート探索に依存するため、配布後の環境で想定通り機能しない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して明示的に設定を行うこと。

Contributing
------------

- バグ報告・機能要望は Issue を作成してください。大きな変更は Pull Request と設計説明を添えてください。

License
-------

- リポジトリの LICENSE を参照してください。

---- 

必要であれば次を追加できます:
- リリース日を任意の日付に更新
- 各関数（API）の細かいパラメータ例や戻り値のサンプルを CHANGELOG に含める変更履歴の追記
- さらに細かな既知のバグや改修予定（Issues へのリンク）