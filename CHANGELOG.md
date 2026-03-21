Keep a Changelog
=================

すべての変更はこのファイルに記録します。  
遵守ルール: https://keepachangelog.com/ja/1.0.0/

[Unreleased]: https://example.com/compare/v0.1.0...HEAD

v0.1.0 - 2026-03-21
-------------------

初回公開リリース。日本株自動売買システム「KabuSys」のコアライブラリを提供します。
主にデータ取得・保存、ファクター計算、特徴量作成、シグナル生成、環境設定ユーティリティを実装しています。

Added
-----

- 基本パッケージ構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定 / config
  - .env ファイル（プロジェクトルートの .git または pyproject.toml を起点に検索）を自動読み込みする仕組みを実装。
  - .env と .env.local の読み込み順（OS 環境 > .env.local > .env）と上書き保護のサポート。
  - .env パーサー: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
  - Settings クラスで以下の設定をプロパティとして提供:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（validation: development/paper_trading/live）
    - LOG_LEVEL（validation: DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - Settings による env 判定ユーティリティ: is_live / is_paper / is_dev。

- データ取得・保存（data）
  - jquants_client:
    - J-Quants API クライアントを実装（トークン取得・自動リフレッシュ、ページネーション対応）。
    - レート制限対応（固定間隔スロットリング: 120 req/min）。
    - リトライロジック（指数バックオフ、最大3回、HTTP 408/429/5xx 対象）。
    - 401 受信時にはトークンを自動リフレッシュして1回リトライ。
    - ページネーション対応で fetch_* 系関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）を実装。
    - DuckDB へ保存するユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）を実装（冪等、ON CONFLICT DO UPDATE）。
    - 型変換ユーティリティ: _to_float / _to_int（堅牢な変換と不正値スキップ）。
  - news_collector:
    - RSS から記事収集して raw_news テーブルへ冪等保存するモジュールを実装。
    - URL 正規化（トラッキングパラメータ削除・ソート・フラグメント除去）、SHA-256 による記事 ID 生成（先頭32文字）を採用し冪等性を保証。
    - defusedxml による安全な XML パース（XML Bomb 等への対策）。
    - SSRF や大容量応答対策（受信最大バイト数制限）を考慮。
    - raw_news / news_symbols への保存をトランザクションでまとめて行う設計（INSERT チャンク化）。

- 研究用モジュール（research）
  - factor_research:
    - モメンタム（mom_1m / mom_3m / mom_6m / ma200_dev）計算（prices_daily を利用）。
    - ボラティリティ・流動性（atr_20 / atr_pct / avg_turnover / volume_ratio）計算。
    - バリュー（per / roe）計算（raw_financials の最新レコードを組み合わせる）。
    - SQL ベースの計算でデータ不足時は None を返す設計。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）：複数ホライズンを一括で取得、営業日→カレンダー日バッファを考慮。
    - スピアマン IC（calc_ic）計算（ランク付け、同順位は平均ランクで処理）。
    - 基本統計量サマリ（factor_summary）と rank ユーティリティ。
  - research/__init__.py で主要関数を公開。

- 戦略モジュール（strategy）
  - feature_engineering.build_features:
    - research 側で計算した生ファクターを統合し、ユニバースフィルタ（最低株価・平均売買代金）を適用。
    - 指定カラムを Z スコア正規化（外部 zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへの日付単位の置換（トランザクション + バルク挿入で原子性と冪等性を保証）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して銘柄ごとにコンポーネントスコア（momentum / value / volatility / liquidity / news）を算出。
    - デフォルト重みを採用しつつユーザ指定 weights を許容（検証・再スケールを実施）。
    - final_score による BUY（閾値デフォルト 0.60）と SELL ロジックを実装。
    - Bear レジーム（ai_scores の regime_score 平均が負）検知で BUY を抑制。
    - SELL 判定条件としてストップロス（-8%）とスコア低下を実装（positions / prices_daily を参照）。
    - signals テーブルへの日付単位置換（トランザクションで原子性を確保）。
    - 未登録コンポーネントは中立値 0.5 で補完する挙動により欠損銘柄の不当な降格を回避。

- パブリック API エクスポート
  - strategy.__init__ で build_features / generate_signals を公開。
  - research/__init__ で主要研究用関数を公開。

Security
--------

- news_collector で defusedxml を採用し XML 関連攻撃を防止。
- RSS URL の正規化でトラッキングパラメータを除去、SSRF に対してスキーム制限の実装方針あり。
- J-Quants クライアントはトークン管理と最小待機間隔で API レート制限を順守する設計。

Notes / Known limitations
-------------------------

- signal_generator の SELL ロジックでは、トレーリングストップや保有日数による時間決済は未実装。これらを実装するには positions テーブルに peak_price / entry_date 等の追加フィールドが必要。
- data.stats.zscore_normalize が外部参照されているが、ここでは実装ファイルは含まれていません（別モジュールとして提供予定）。
- news_collector はデフォルトで Yahoo Finance の RSS を参照する設定になっています。運用時はソースの追加・管理が必要です。
- DuckDB 接続（duckdb.DuckDBPyConnection）前提で設計されているため、利用環境に duckdb が必要です。
- 非同期処理や並列フェッチは未導入。大量データ取得時は時間がかかる可能性あり。

Usage highlights
----------------

- 環境変数の準備が必要（例）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
  - （任意）DUCKDB_PATH / SQLITE_PATH / KABUSYS_ENV / LOG_LEVEL
- 主要関数:
  - build_features(conn, target_date) で features テーブルを作成／更新。
  - generate_signals(conn, target_date, threshold?, weights?) で signals を作成／更新。
  - jquants_client.fetch_* / save_* を組み合わせて raw データを取得・永続化。

Unreleased
----------

- 次期予定（例）:
  - positions テーブル拡張 (peak_price, entry_date) とトレーリングストップ・時間決済の実装。
  - 並列フェッチ・非同期化によるデータ取得速度改善。
  - zscore_normalize の公開実装とチューニング。
  - execution 層（発注実装）と監視（monitoring）モジュールの実装強化。
  - 単体テスト・統合テストの追加（現在はテスト用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を用意）。

Acknowledgements
----------------

- 本リリースはコードベース（各モジュールの docstring と実装）から機能を推測してまとめています。実際の運用での詳細設定や DB スキーマは README / ドキュメントを参照してください。