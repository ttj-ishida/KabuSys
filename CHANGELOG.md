# Keep a Changelog — CHANGELOG.md (日本語)

すべての変更は「慣例的変更ログ（Keep a Changelog）」に従って記載しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [Unreleased]
（現時点のリリースは v0.1.0 のため未リリースの変更はありません）

## [0.1.0] - 2026-03-19
最初の公開リリース。システムのコア機能（設定管理、データ取得/保存、研究用ファクター計算、特徴量生成、シグナル生成、ニュース収集）を実装。

### Added
- パッケージ基礎
  - 初期バージョンのパッケージを追加（kabusys v0.1.0）。
  - パブリック API: kabusys.strategy.build_features, kabusys.strategy.generate_signals などをエクスポート。

- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動ロードする仕組みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートの自動検出（.git または pyproject.toml を探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - .env 行パーサを実装（export 形式・シングル/ダブルクォート・エスケープ・インラインコメント処理対応）。
  - Settings クラスを追加し、必須値の取得（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID など）とバリデーション（KABUSYS_ENV, LOG_LEVEL）を提供。
  - DB パス（DUCKDB_PATH, SQLITE_PATH）の Path 返却、is_live / is_paper / is_dev のブールプロパティを提供。

- データ取得 / 保存（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。
    - レートリミット制御（120 req/min 固定間隔スロットリング）。
    - リトライ（指数バックオフ、最大 3 回、HTTP 408/429/5xx を対象）。
    - 401 受信時のトークン自動リフレッシュ（1 回のみ）を実装。
    - ページネーション対応（pagination_key）。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
  - DuckDB への冪等保存ユーティリティを実装（save_daily_quotes, save_financial_statements, save_market_calendar）。
    - INSERT ... ON CONFLICT DO UPDATE を用いた重複排除。
    - レコードの型変換ユーティリティ（_to_float, _to_int）。
    - fetched_at に UTC タイムスタンプを記録して look-ahead bias のトレースを可能に。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード収集モジュールを実装。
    - RSS パースに defusedxml を使用して XML 攻撃を緩和。
    - 受信サイズ上限（MAX_RESPONSE_BYTES）やホワイトリスト化された URL スキーマにより SSRF / DoS を低減。
    - URL 正規化（トラッキングパラメータ削除、クエリソート、フラグメント削除、スキーム/ホスト小文字化）。
    - 記事 ID は URL 正規化後の SHA-256（短縮）を使用して冪等性を担保。
    - raw_news へのバルク挿入、チャンク処理（_INSERT_CHUNK_SIZE）により効率化。
    - デフォルト RSS ソースに Yahoo Finance の経済カテゴリを追加。

- 研究用モジュール（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev を計算（MA200 のデータ不足時は None）。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算（ATR にデータ不足チェック）。
    - calc_value: target_date 以前の最新財務データと価格を組み合わせて PER / ROE を計算。
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみを参照。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）での将来リターンを計算（LEAD ウィンドウを使用）。
    - calc_ic: スピアマン順位相関（Information Coefficient）を実装（ランクの扱いは同位順位を平均ランクで処理）。
    - rank, factor_summary ユーティリティを実装（統計サマリー: count/mean/std/min/max/median）。
    - すべて標準ライブラリと DuckDB で実装（pandas 等に依存しない）。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features を実装。
    - research モジュールの生ファクターを取得してマージ、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 指定列を Z スコア正規化（kabusys.data.stats.zscore_normalize）し ±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE + bulk INSERT をトランザクションで実施）して冪等性を確保。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals を実装。
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントはシグモイド変換や反転処理を用いる（例: volatility は反転して低ボラ＝高スコア）。
    - 欠損コンポーネントは中立 0.5 で補完。
    - ウェイトの入力検証と正規化（デフォルト重みを用意、合計が 1 でない場合はスケール）。
    - Bear レジーム検知（ai_scores の regime_score 平均が負の場合）で BUY シグナル抑制。
    - SELL の判定ロジック実装（ストップロス -8%、final_score が閾値未満）。
    - BUY/SELL を signals テーブルへ日付単位で置換（トランザクションで原子性を保証）。
    - SELL を優先して BUY から除外するポリシーを採用。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- ニュースパーサで defusedxml を採用、RSS の XML 攻撃を緩和。
- news_collector にて受信バイト数制限・URL 正規化・スキーマ検査・IP/SSRF への配慮（コード中に注釈あり）。
- J-Quants クライアントでトークン管理とリトライ戦略を実装し、401・429・5xx などに備える。

### Notes / Limitations / TODO
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等の追加情報が必要なため未実装（ソースに明記）。
- 一部の集計は DuckDB 上のウィンドウ関数に依存するため、テーブルスキーマ（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals など）の存在が前提。
- news_collector では記事と銘柄の紐付け処理（news_symbols）についての完成度は本版では要確認。
- 外部依存を最小化する設計（pandas 等を用いない）を採用しているため、必要に応じて研究ワークフローでのデータフレーム処理を運用側で補完することを想定。

---

（注）本 CHANGELOG は与えられたコードベースの実装内容とドキュメンテーション文字列から推測して作成しています。実際のリリースノートや運用上の注意点はプロジェクト実際の変更履歴・バージョン管理のコミットログに基づいて更新してください。