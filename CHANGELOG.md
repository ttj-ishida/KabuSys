CHANGELOG
=========

すべての注目すべき変更履歴はここに記載します。  
このプロジェクトは Keep a Changelog 準拠の形式を採用しています。意図的に過去のコミット履歴を再構築した初版のリリースノートです（コードベースのコメント・実装から推測して作成）。

[Unreleased]
------------

- （現時点の開発中の変更はここに記載します）

[0.1.0] - 2026-03-19
-------------------

Added
- パッケージ初期リリース。
  - kabusys パッケージのエントリポイント（src/kabusys/__init__.py）。
  - バージョン: 0.1.0。

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local を自動でロードする仕組み（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env ファイルパーサを実装（コメント、クォート、export 形式対応、インラインコメント処理）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスによる型付きプロパティ（J-Quants トークン、kabu API 設定、Slack トークン/チャンネル、DuckDB/SQLite パス、環境/ログレベル判定、is_live/is_paper/is_dev 等）。
  - 必須環境変数の取得時に未設定なら ValueError を送出する `_require`。

- データアクセス / 収集（src/kabusys/data/*）
  - J-Quants API クライアント（jquants_client.py）
    - ページネーション対応の fetch_* 関数（daily quotes / financial statements / market calendar）。
    - レート制限（120 req/min）を守る固定間隔スロットリング _RateLimiter を実装。
    - リトライ（指数バックオフ、最大3回）と 401 時の自動トークンリフレッシュ処理（1 回のみ）。
    - レスポンスの JSON デコードチェック、ネットワーク例外ハンドリング。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は冪等（ON CONFLICT DO UPDATE）で保存。
    - 型変換ユーティリティ `_to_float` / `_to_int`（堅牢な変換ルール）。
    - fetched_at を UTC タイムスタンプで記録し、look-ahead bias のトレースに配慮。

  - ニュース収集（news_collector.py）
    - RSS フィード取得→前処理→raw_news 保存の流れを実装。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリキーソート）。
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保。
    - defusedxml を用いた XML パースで XML Bomb 等の防御、受信最大バイト数制限でメモリ DoS を抑制、SSRF 対策（HTTP/HTTPS のみ許可等）、バルク INSERT のチャンク処理。

- リサーチモジュール（src/kabusys/research/*）
  - factor_research.py
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）、Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）、Value（per, roe）等の計算処理を DuckDB SQL で実装。
    - 営業日ベースのラグ/ウィンドウ計算、データ不足時の None 処理、スキャン範囲バッファ設計。
  - feature_exploration.py
    - 将来リターン calc_forward_returns（複数ホライズン対応、SQL でまとめて取得）。
    - IC（Spearman の ρ）計算 calc_ic と補助関数 rank。
    - factor_summary（count/mean/std/min/max/median）。
  - re-export（src/kabusys/research/__init__.py）で主要関数を公開。

- 戦略モジュール（src/kabusys/strategy/*）
  - feature_engineering.py
    - 研究で算出した生ファクターをマージ→ユニバースフィルタ（最低株価・平均売買代金）適用→Zスコア正規化→±3でクリップ→features テーブルへ日付単位で置換（トランザクションで原子性保証）。
    - ユニバースフィルタの閾値: 最低株価 300 円、20日平均売買代金 5 億円。
  - signal_generator.py
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完、重みの検証・正規化（デフォルト重みはコード内定義）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負でサンプル数閾値以上）。
    - BUY（閾値デフォルト 0.60）と SELL（ストップロス -8% / スコア低下）を生成し、signals テーブルへ日付単位で置換。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）やランク付けの実装。
  - strategy パッケージのエクスポート（build_features / generate_signals）。

- その他
  - デバッグ / ロギングメッセージが随所に実装され、警告や失敗時の詳細ログを残す設計。
  - 外部依存を最小化（標準ライブラリ中心、defusedxml のみ外部依存として明示的に使用）。

Changed
- 初版のため過去からの変更履歴は無し。

Fixed
- 初版のため既存不具合修正履歴は無し。

Security
- RSS パーサに defusedxml を使用して XML 攻撃を緩和。
- ニュース URL の正規化とスキーマ検査で SSRF を軽減。
- J-Quants クライアントは 401 時のトークン自動リフレッシュに注意深い制御（無限再帰を防止）を実装。

Notes / Known limitations（実装コメントより）
- signal_generator のエグジット条件では、以下が未実装（コメントで明示）:
  - トレーリングストップ（peak_price が positions テーブルに記録される必要あり）
  - 時間決済（60 営業日超過など）
- calc_value は PBR・配当利回りをまだ計算しない（コメントで未実装として記載）。
- positions テーブルの設計（peak_price / entry_date 等）が現状のコードでは必要になる箇所があるが、テーブル定義はこのコードベース内に含まれていない。
- ニュースのパース・保存は RSS の既知ソースのみを想定（DEFAULT_RSS_SOURCES にデフォルトを定義）。
- get_id_token は設定されていない refresh token に対して ValueError を送出するため、JQUANTS_REFRESH_TOKEN の設定が必須。
- DuckDB テーブルスキーマ（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar 等）は本 changelog 作成時点では別途用意される前提。

Migration / Usage Notes
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings で必須扱い。
- 自動 .env ロードはデフォルトで有効。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- デフォルトの DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- strategy.build_features / strategy.generate_signals は DuckDB 接続（duckdb.DuckDBPyConnection）と target_date を渡して実行。これらは日次で features / signals を置換する設計。

Acknowledgements
- 実装内の詳細なコメントや設計注釈に基づいてまとめました。将来のリリースでは未実装項目（トレーリングストップ、追加バリュー指標など）の実装やテーブル定義の含有が期待されます。