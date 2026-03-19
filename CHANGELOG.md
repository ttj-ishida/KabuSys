CHANGELOG
=========
全ての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
バージョニングはセマンティックバージョニングに従います。

[Unreleased]
-------------
- 予定/検討中の改善点（コード内 docstring から推測）
  - execution 層（発注実行ロジック）の実装完了（現状はパッケージにプレースホルダのみ）
  - monitoring モジュールの実装（__init__ の __all__ に含まれるが未提供）
  - ポジション管理の拡張:
    - positions テーブルに peak_price / entry_date を保存してトレーリングストップや時間決済を実装
  - Value ファクターの拡張: PBR・配当利回りの追加
  - シグナル生成の改善:
    - トレーリングストップ、時間決済の条件実装
    - AI スコアの取り扱い改善・追加メタデータ
  - 単体テスト、統合テスト、CI の整備
  - パフォーマンス改善（大規模データ向けのクエリ最適化、bulk/バッチ処理の調整）
  - ドキュメント、使用例、CLI / サービス化（scheduler/worker）の追加

0.1.0 - 2026-03-19
------------------
Added
  - 基本パッケージ構成を追加
    - パッケージ名: kabusys、__version__ = "0.1.0"
    - パッケージ公開 API: data, strategy, execution, monitoring（execution は空の初期化子、monitoring は参照のみ）
  - 環境設定管理モジュール（kabusys.config）
    - .env/.env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml から探索）
    - export KEY=val 形式やコメント/クォートを考慮した .env パース実装
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
    - Settings クラスによる型付きアクセス（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等）
    - env 値検証（KABUSYS_ENV の許容値検査、LOG_LEVEL 検査）
  - データ取得／永続化（kabusys.data）
    - J-Quants API クライアント（kabusys.data.jquants_client）
      - レート制限制御（固定間隔スロットリング、120 req/min を想定）
      - リトライ（指数バックオフ、最大 3 回、408/429/5xx を対象）
      - 401 受信時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルのトークンキャッシュ
      - ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
      - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）。ON CONFLICT を用いた upsert 実装
      - 入力変換ユーティリティ（_to_float / _to_int）
    - ニュース収集モジュール（kabusys.data.news_collector）
      - RSS フィード取得と前処理、記事 ID を正規化 URL の SHA-256（先頭32文字）で生成（冪等性）
      - defusedxml を使用した安全な XML パース（XML Bomb 対策）
      - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）、トラッキングパラメータ除去、URL 正規化、SSRF 対策等のセキュリティ考慮
      - バルク INSERT チャンク処理、INSERT RETURNING を想定した実装方針
  - リサーチ／ファクター計算（kabusys.research）
    - ファクター計算モジュール（kabusys.research.factor_research）
      - Momentum（mom_1m / mom_3m / mom_6m / ma200_dev）、Volatility（atr_20 / atr_pct / avg_turnover / volume_ratio）、Value（per / roe）を DuckDB の prices_daily / raw_financials を参照して計算
      - 欠損・データ不足時の None 処理を明示
    - 特徴量探索モジュール（kabusys.research.feature_exploration）
      - 将来リターン計算（calc_forward_returns）、IC（Spearman の ρ）計算(calc_ic)、ファクター統計サマリー(factor_summary)、ランク付け関数(rank)
      - pandas 等の外部依存を避け、標準ライブラリと DuckDB で実装
    - モジュールの再エクスポート（__all__）で主要関数を公開
  - 戦略（kabusys.strategy）
    - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
      - research 側で計算した raw factors を取得しユニバースフィルタ（最低株価300円、20日平均売買代金5億円）を適用
      - 指定カラムの Z スコア正規化（zscore_normalize を使用）、±3 でクリップ、features テーブルへの日付単位の置換（冪等）
    - シグナル生成（kabusys.strategy.signal_generator）
      - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出
      - final_score を重み付き合算（デフォルト重みを定義）し BUY/SELL シグナル生成
      - Bear レジーム判定（ai_scores の regime_score 平均が負の場合、サンプル数閾値あり）
      - エグジット判定（ストップロス -8%、final_score が閾値未満）
      - signals テーブルへの日付単位の置換（トランザクション＋バルク挿入）
    - 公開 API: build_features, generate_signals
  - 決済/実行（プレースホルダ）
    - src/kabusys/execution/__init__.py を追加（現時点では内容無し、将来の発注ロジック用）
  - 一貫したログ出力（各モジュールで logger を使用）

Changed
  - （初版のため該当なし）

Fixed
  - （初版のため該当なし）

Security
  - ニュースパーシングで defusedxml を使用して XML 脅威を軽減
  - ニュース収集で受信バイト数制限、トラッキングパラメータ除去、スキーム制約等で SSRF/DoS を考慮
  - J-Quants クライアントで認証トークンの安全なリフレッシュとキャッシュを実装

Known issues / Limitations
  - ポジション管理に peak_price / entry_date が存在しないため、トレーリングストップや時間決済は未実装
  - Value ファクターで PBR / 配当利回りは未実装
  - monitoring モジュールが未実装だが __all__ には含まれている点に注意
  - ニュース収集の DB 保存部分（raw_news / news_symbols への実際の INSERT ロジックの詳細）は docstring に記載された設計に従うものの、環境依存のため運用時に確認が必要
  - DuckDB スキーマ（tables: raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar 等）は本 CHANGELOG に含まれていません。導入時にスキーマ定義を用意する必要があります

作者ノート
  - ルックアヘッドバイアス回避、冪等性、トランザクション原子性、外部 API の安全な呼び出しといった設計原則がコード全体で一貫して採用されています。
  - この CHANGELOG は提供されたソースコードのドキュメント文字列・実装から推測して作成しています。実際のリリースノート作成時は運用での差分・変更履歴に基づいて更新してください。

--- 
（このファイルは Keep a Changelog の形式に従っています。必要に応じて日付／カテゴリを調整してください。）