CHANGELOG
=========

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」の形式に準拠します。

フォーマット:
- すべての変更はバージョン別に記載します。
- 初回リリースは 0.1.0 として記録しています。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-03-20
--------------------

Added
- パッケージ初版を追加（kabusys v0.1.0）。
  - パッケージ宣言: src/kabusys/__init__.py に __version__ = "0.1.0" を定義。
  - エクスポート: data, strategy, execution, monitoring モジュールを公開。

- 設定 / 環境変数管理
  - src/kabusys/config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env 行のパースは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
    - Settings クラスを提供し、J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス（DuckDB/SQLite）、
      KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL の検証付き取得をサポート。
    - 必須環境変数未設定時は ValueError を送出する _require を実装。

- Data 層: J-Quants クライアント / ニュース収集 / 保存ユーティリティ
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装。
    - 固定間隔によるレート制限（120 req/min）を RateLimiter で実装。
    - リトライ（指数バックオフ、最大 3 回）と 401 時のトークン自動リフレッシュ（1回）に対応。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を提供。
    - DuckDB への保存用ユーティリティ save_daily_quotes / save_financial_statements / save_market_calendar を実装。
      - ON CONFLICT DO UPDATE による冪等保存を採用。
      - PK 欠損行のスキップや挿入件数のログを出力。
    - JSON デコードエラー、HTTP/ネットワークの取り扱い、レスポンスヘッダの Retry-After を考慮。

  - src/kabusys/data/news_collector.py
    - RSS フィードからニュースを収集するモジュールを実装（デフォルト: Yahoo Finance ビジネス RSS）。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングクエリ除去、フラグメント除去、クエリソート）を実装。
    - XML パースに defusedxml を利用して XML Bomb 等に対する安全化。
    - 受信サイズ上限（10 MB）や SSRF 対策（HTTP/HTTPS のみ）などの安全策を導入。
    - バルク挿入のチャンク化や ON CONFLICT DO NOTHING による冪等性を想定。

  - 共通ユーティリティ
    - 型変換ユーティリティ _to_float / _to_int（厳密な int 変換ルール）を実装。

- Research 層（因子計算 / 探索）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20 日 ATR、相対 ATR）、流動性（20 日平均売買代金、出来高比率）、
      バリュー（PER, ROE）を DuckDB 上の prices_daily / raw_financials を参照して計算する関数を提供:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - 各関数は不足データ時に None を返す設計で、結果は (date, code) をキーとした dict のリストを返す。
    - SQL ウィンドウ関数を活用し、カレンダー日と営業日の乖離を吸収するスキャン幅を採用。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns(conn, target_date, horizons) を実装（複数ホライズン対応）。
    - スピアマンランク相関（IC）を計算する calc_ic(factor_records, forward_records, factor_col, return_col) を実装。
    - ランク変換ユーティリティ rank(values) とファクター統計要約 factor_summary(records, columns) を実装。
    - 標準ライブラリのみでの実装を目標とし、pandas 等に依存しない設計。

  - re-export: src/kabusys/research/__init__.py で主要関数を公開。

- Strategy 層（特徴量エンジニアリング / シグナル生成）
  - src/kabusys/strategy/feature_engineering.py
    - 研究モジュールの生ファクターを取り込み、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 選別後の数値ファクターを Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）、±3 でクリップ。
    - features テーブルへ日付単位で置換（BEGIN/DELETE/INSERT/COMMIT でトランザクション及び原子性を確保）。
    - build_features(conn, target_date) を提供（処理は冪等）。

  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換、欠損コンポーネントは中立値 0.5 補完、重みを合成して final_score を算出。
    - デフォルト重みと閾値（threshold=0.60）を採用。weights 引数で上書き可能（入力検証・リスケーリングあり）。
    - Bear レジーム検知（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）で BUY を抑制。
    - エグジット条件（ストップロス -8%、スコア低下）で SELL シグナルを生成（positions テーブル参照）。
    - BUY / SELL を signals テーブルへ日付単位で置換する generate_signals(conn, target_date, threshold, weights) を提供。
    - SELL が BUY を優先して除外するポリシーを実装（SELL 優先）。

- パッケージ公開 API
  - src/kabusys/strategy/__init__.py で build_features / generate_signals を公開。
  - src/kabusys/research/__init__.py で主要な research 関数を公開。

Security
- defusedxml を利用した RSS パース、安全な URL 正規化、受信サイズ制限、SSRF を意識したスキーム検査等の対策を実装。
- J-Quants クライアントはトークン管理やリトライ制御を組み込み、誤った再帰呼び出しを防止するため allow_refresh フラグを導入。

Notes / Design decisions
- DuckDB を主に用いてオンメモリではなく永続 DB（prices_daily, raw_prices, raw_financials, features, ai_scores, signals, positions, market_calendar 等）を想定。
- データ取得・保存は冪等性を重視（ON CONFLICT DO UPDATE / DO NOTHING）。
- ルックアヘッドバイアス防止を強く意識し、各処理は target_date 時点の利用可能データのみを参照する設計。
- 外部依存を最小限にし、研究コードは標準ライブラリでの実装を目指す（pandas 等には依存しない）。
- エラー時のログとトランザクションロールバックを考慮（ROLLBACK 失敗時は警告ログ）。

Known limitations / TODOs
- strategy の一部条件（トレーリングストップ、保有 60 営業日超の時間決済）は positions テーブルに peak_price / entry_date 等の追加が必要として未実装。
- news_collector の記事→銘柄紐付け（news_symbols）は実装想定だが、本バージョンでの詳細実装は要確認。
- execution（発注）層は空のパッケージディレクトリが用意されているが、取引実行APIとの接続実装は含まれていない。
- data 層の外部 API（J-Quants）呼び出しに対する統合テストやモックが必要。
- zscore_normalize の実装は kabusys.data.stats 側に依存。該当モジュールの仕様に注意。

Upgrade / Migration notes
- 初回リリースのため特別な移行手順はありません。DuckDB スキーマ定義や既存データがある環境ではテーブル名・カラム名を確認してください。
- .env の自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Contributors
- 本リポジトリのコードから推測して実装を行ったチームに感謝します（詳細な著者情報はリポジトリのコミット履歴を参照してください）。

お問い合わせ
- バグ報告、改善案、移行サポート等はリポジトリの Issue/Ticket システムにてお願いします。