CHANGELOG
=========

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-03-21
--------------------

初期リリース。日本株自動売買システムのコアライブラリを追加しました。主な機能はデータ取得・保存、研究向けファクター計算、特徴量作成、シグナル生成、設定管理、ニュース収集などです。

Added
- パッケージ基本情報
  - src/kabusys/__init__.py にバージョン 0.1.0 と公開 API を追加。

- 環境変数・設定管理
  - src/kabusys/config.py
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）による .env 自動ロード機能を実装。
    - .env / .env.local の読み込み順序（OS 環境変数 > .env.local > .env）を実装。OS 環境変数は保護され、.env.local は上書き可能。
    - .env 行パーサ（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理）を実装。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスを提供し、必須環境変数取得（_require）と各種プロパティを定義：
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須。
      - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV（development/paper_trading/live）, LOG_LEVEL（DEBUG/INFO/...）の既定値とバリデーションを実装。
      - is_live / is_paper / is_dev のユーティリティプロパティを追加。

- データ取得・保存（J-Quants）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアント実装（ページネーション対応）。
    - 固定間隔レートリミッタ（120 req/min）を実装し API 呼び出しをスロットリング。
    - リトライロジック（最大 3 回、指数バックオフ、408/429/5xx をリトライ対象）と 401 発生時のトークン自動リフレッシュ（1 回のみ）を実装。
    - モジュールレベルの ID トークンキャッシュを導入しページネーション間で共有。
    - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar() を実装。
    - DuckDB 保存ユーティリティを実装（save_daily_quotes, save_financial_statements, save_market_calendar）。いずれも冪等（ON CONFLICT DO UPDATE）で保存し、fetched_at は UTC で記録。
    - 安全な型変換ユーティリティ _to_float(), _to_int() を提供。

- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィードからニュースを収集して raw_news に保存する処理（冪等性を意識）。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリキーソート）を実装。
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を担保。
    - defusedxml を使用した XML パース（XML Bomb 対策）、受信バイト数上限（MAX_RESPONSE_BYTES=10MB）、SSRF 対策等の安全対策を実装。
    - bulk insert のチャンク処理、INSERT RETURNING 相当で実際に挿入されたレコード数を得る設計。

- 研究用ファクター計算
  - src/kabusys/research/factor_research.py
    - calc_momentum(): mom_1m/mom_3m/mom_6m と ma200_dev を計算。200 日移動平均のデータ不足ハンドリング。
    - calc_volatility(): 20 日 ATR（atr_20）、atr_pct、20 日平均売買代金（avg_turnover）、volume_ratio を計算。true_range の NULL 伝播を適切に処理。
    - calc_value(): raw_financials と prices_daily を結合して PER と ROE を計算。最新の報告日ベースでの結合。
    - 各関数は DuckDB の SQL ウィンドウ関数を活用し、高速で一貫した出力を返す（date, code を含む dict のリスト）。

- 研究支援ツール
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns(): 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD による実装）。horizons の妥当性チェックあり。
    - calc_ic(): Spearman の ρ（ランク相関）を計算。欠損やサンプル不足（<3）に対する None 返却。
    - rank(): 平均ランクを返す（同順位は平均ランク、丸め処理で ties 検出の安定化）。
    - factor_summary(): count/mean/std/min/max/median を計算する統計サマリーユーティリティ。

- 特徴量生成（Feature Engineering）
  - src/kabusys/strategy/feature_engineering.py
    - research で計算した生ファクターを正規化・合成して features テーブルへ保存する build_features() を実装。
    - 処理フロー:
      1. calc_momentum / calc_volatility / calc_value の出力を取得
      2. ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用
      3. 指定カラム（mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）を z-score 正規化（外部ユーティリティ zscore_normalize を利用）、±3 でクリップ
      4. features テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性保証）
    - 冪等性を確保（target_date の既存レコードを削除してから挿入）。

- シグナル生成
  - src/kabusys/strategy/signal_generator.py
    - generate_signals() を実装し、features と ai_scores を統合して最終スコア（final_score）を算出、BUY / SELL シグナルを作成して signals テーブルへ保存。
    - コンポーネントスコア:
      - momentum (momentum_20/60, ma200_dev をシグモイド化して平均)
      - value (PER に基づく変換: per=20 -> 0.5, per->0 -> 1.0, per->∞ -> 0.0)
      - volatility (atr_pct の Z スコアを反転してシグモイド)
      - liquidity (volume_ratio のシグモイド)
      - news (ai_score をシグモイド、未登録は中立)
    - デフォルト重みと閾値:
      - 重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10
      - BUY 閾値: 0.60
    - Bear レジーム判定: ai_scores の regime_score 平均が負でサンプル数 >= 3 の場合は BUY を抑制（_is_bear_regime）。
    - SELL 条件（実装済）:
      1. ストップロス: 終値 / avg_price - 1 < -8%
      2. スコア低下: final_score が threshold 未満
      - 未実装: トレーリングストップ、時間決済（positions テーブルに peak_price / entry_date が必要）
    - 保有ポジションのエグジット判定時は価格が欠損する場合は判定をスキップするなど安全対策あり。
    - signals テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性保証）。
    - weights にはバリデーション・正規化（既知キーのみ、非数値は無視、合計が 1.0 でない場合は再スケール）を実装。

- パッケージ公開 API
  - src/kabusys/strategy/__init__.py および src/kabusys/research/__init__.py で主要関数をエクスポート。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Internal / Notes
- DuckDB の期待スキーマ（使用されるテーブル）
  - raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, signals, positions, raw_news などがコードで参照される。
- ロギングと警告:
  - 各モジュールは問題発生時に警告・情報ログを出力し、データ欠損時の安全な挙動（スキップ、デフォルト値補完）を採用。
- セキュリティ設計:
  - news_collector は defusedxml とネットワーク/URL の制限および受信サイズ上限を導入。
  - jquants_client はトークンの自動更新とリトライ制御で API 利用の堅牢性を高める。
- 未実装 / 今後の拡張候補:
  - signal_generator のトレーリングストップ・時間決済（positions に peak_price / entry_date が必要）。
  - 追加のファクター（PBR・配当利回り等）。
  - execution 層（src/kabusys/execution/ は現状空）と実際の注文処理の統合。
  - データ.stats の実装（zscore_normalize は参照されるが本差分では実装ファイルが省略されているため、既存の別ファイルで提供されている想定）。

Required environment variables (概要)
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- 任意/デフォルトあり:
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - KABUSYS_ENV (development, paper_trading, live; デフォルト: development)
  - LOG_LEVEL (DEBUG/INFO/...; デフォルト: INFO)
- 自動 .env ロードはプロジェクトルートの検出に依存し、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

ライセンス・互換性
- この変更履歴はコードベースの初期実装に基づいて推測したものです。使用にあたっては README / ドキュメントを参照の上、DB スキーマや実行環境のセットアップを行ってください。