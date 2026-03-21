CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に従って記載しています。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（なし）

[0.1.0] - 2026-03-21
-------------------

初期リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。以下はコードベースから推測してまとめた主要追加点・設計上の注意点です。

Added
- パッケージ骨格
  - kabusys パッケージの公開 API を定義（data, strategy, execution, monitoring）。
  - バージョン: 0.1.0（src/kabusys/__init__.py）。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルと OS 環境変数を組み合わせた自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env 行パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - protected キーを用いた上書き防止ロジック。
  - Settings クラスでアプリ設定をプロパティ提供（必須項目は例外を投げる）。
  - 必須環境変数（例）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - システム設定検証（KABUSYS_ENV, LOG_LEVEL のバリデーション）とヘルパー（is_live / is_paper / is_dev）。

- データ取得・保存（src/kabusys/data/）
  - J-Quants API クライアント（jquants_client.py）
    - レートリミッタ（120 req/min 固定間隔スロットリング）。
    - 再試行（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 の場合は Retry-After ヘッダを尊重。
    - 401 受信時にリフレッシュトークンから自動で id_token を再取得して 1 回再試行。
    - ページネーション対応（pagination_key）。
    - 取得時刻（fetched_at）を UTC で記録し、look-ahead バイアスのトレースを可能にする設計。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）は冪等（ON CONFLICT DO UPDATE）。
    - 型変換ユーティリティ（_to_float, _to_int）で不正データ耐性を向上。
  - ニュース収集モジュール（news_collector.py）
    - RSS 取得 → テキスト前処理 → raw_news への冪等保存（ON CONFLICT DO NOTHING）。
    - 記事IDは URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成する方針（重複防止）。
    - defusedxml を利用して XML 関連の攻撃を防止。
    - HTTP/HTTPS スキームのみ許可、受信サイズ上限（MAX_RESPONSE_BYTES=10MB）など DoS/SSRF 対策。
    - トラッキングパラメータ除去、クエリソートなど正規化ロジックを実装。
    - デフォルト RSS ソースに Yahoo Finance を設定。

- 研究用モジュール（src/kabusys/research/）
  - ファクター計算（factor_research.py）
    - Momentum（mom_1m / mom_3m / mom_6m / ma200_dev）、Volatility（atr_20 / atr_pct / avg_turnover / volume_ratio）、Value（per / roe）を DuckDB の prices_daily / raw_financials から計算。
    - ウィンドウ不足時の None 処理やスキャン範囲のバッファ設計。
  - 特徴量探索（feature_exploration.py）
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）。
    - IC（Spearman ランク相関）計算（rank ユーティリティ含む）。
    - ファクターの統計サマリー（count/mean/std/min/max/median）。
  - 研究向けユーティリティをパッケージ公開。

- 戦略層（src/kabusys/strategy/）
  - 特徴量エンジニアリング（feature_engineering.py）
    - research モジュールの生ファクターを取り込み、ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 指定カラムを Z スコア正規化（外部 zscore_normalize を使用）、±3 でクリップ。
    - DuckDB の features テーブルへ日付単位の置換（トランザクション + バルク挿入で原子性）。
    - 冪等性を意識した実装。
  - シグナル生成（signal_generator.py）
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを算出。
    - 重み付き合算による final_score（デフォルト重みはコード中定義）。
    - Bear レジーム判定（ai_scores の regime_score 平均 < 0 を Bear と判定、サンプル不足考慮）。
    - BUY（閾値デフォルト 0.60）・SELL（ストップロス -8%・スコア低下）シグナル生成。
    - SELL 優先ポリシー（BUY から SELL 対象を除外）と signals テーブルへの日付単位置換。
    - weights 引数のバリデーションと合計 1.0 への再スケール処理。
    - エグジットの未実装事項（コメントで明示）:
      - トレーリングストップ（positions に peak_price / entry_date が必要）
      - 時間決済（60 営業日超過）

- その他
  - DuckDB を用いた分析・実行用クエリが中心（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar, raw_news を想定）。
  - ロギングを随所に配置し、警告・情報を出力する設計。

Changed
- （新規プロジェクトのため該当なし）

Fixed
- （新規プロジェクトのため該当なし）

Security
- ニュース解析で defusedxml を使用して XML 攻撃を軽減。
- RSS URL 正規化、スキームチェック、受信サイズ上限、IP/SSRF を想定した対策が設計に盛り込まれている（news_collector）。
- 環境変数の保護（protected set）による OS 環境変数上書き防止。
- J-Quants クライアントでのトークン自動リフレッシュと再試行により認証失敗の安全なハンドリング。

Migration / 運用時の注意
- 必須環境変数を設定すること（Settings の _require で未設定時は ValueError）。
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルトの DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- 自動 .env 読み込みはプロジェクトルートを .git または pyproject.toml から検出するため、配布後に動かす場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用するか適切にファイルを配置してください。
- DuckDB に期待するテーブル:
  - raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar, raw_news
  - 各モジュールはこれらのスキーマに依存している（初期スキーマは実装ドキュメント／DDL を参照のこと）。
- signal_generator 内の未実装エグジット条件（トレーリングストップや時間決済）は将来の拡張ポイント。

既知の制限 / 今後の作業候補
- 一部アルゴリズムはコメントで未実装部分を明示（トレーリングストップ等）。
- 研究モジュールは外部ライブラリに依存せず純 Python + SQL で実装しているため、大規模データでのパフォーマンス微調整余地あり。
- news_collector の URL 検証・SSRF 保護は設計方針に沿っているが、運用環境に応じた追加検証（DNS/IP ブラックリスト等）を推奨。

署名
- 初期実装: 機能横断的なコア（設定、データ取得・保存、研究用ファクター計算、特徴量整備、シグナル生成、ニュース収集）

--- 

注: 上記は提供されたソースコードからの仕様・実装内容を推測してまとめた CHANGELOG です。実際のリリースノートとして使用する場合は、実際のコミット履歴やリリース日付、テスト結果に基づいて調整してください。