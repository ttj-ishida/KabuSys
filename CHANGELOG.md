# Changelog

すべての変更は「Keep a Changelog」フォーマットに従って記載しています。  
このファイルはコードベースからの実装内容をもとに作成された推測ベースの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-20

### Added
- 初回リリース（パッケージバージョン: 0.1.0）。
- パッケージ基盤
  - パッケージ初期化: `kabusys.__init__`（モジュールエクスポートとバージョン管理）。
- 設定管理 (`kabusys.config`)
  - .env ファイルまたは OS 環境変数から設定を自動読み込みする仕組みを追加。
  - プロジェクトルート検出 (`.git` または `pyproject.toml`) に基づく .env 自動ロード（`KABUSYS_DISABLE_AUTO_ENV_LOAD` による無効化可）。
  - .env パーサ実装: `export KEY=val` 形式、クォート文字列のエスケープ、コメント処理などをサポート。
  - 設定アクセス用クラス `Settings` を追加。J-Quants/Slack/DB/システム関連の設定プロパティ（必須チェック・値検証含む）。
  - 環境値検証: `KABUSYS_ENV`（development/paper_trading/live）や `LOG_LEVEL` の妥当性チェックを実装。
- データ取得/保存（J-Quants） (`kabusys.data.jquants_client`)
  - J-Quants API クライアントを実装。ページネーション対応の fetch 関数:
    - `fetch_daily_quotes`
    - `fetch_financial_statements`
    - `fetch_market_calendar`
  - レート制限対応: 固定間隔スロットリング（120 req/min）を実装する `_RateLimiter`。
  - リトライ/指数バックオフ: ネットワーク障害・一部ステータス(408,429,5xx)で最大 3 回の再試行。429 時は `Retry-After` を優先。
  - 401 応答時のトークン自動リフレッシュを実装（1回のリトライ許可）。ID トークン取得関数 `get_id_token` を提供。
  - DuckDB への冪等保存関数を実装:
    - `save_daily_quotes` → `raw_prices`（ON CONFLICT DO UPDATE）
    - `save_financial_statements` → `raw_financials`
    - `save_market_calendar` → `market_calendar`
  - データ変換ユーティリティ `_to_float`, `_to_int` を追加（堅牢な型変換処理）。
  - 取得時の fetched_at を UTC ISO8601 で記録し、Look-ahead バイアスのトレースを可能に。
- ニュース収集 (`kabusys.data.news_collector`)
  - RSS フィードからの記事収集処理を実装。既定のソースに Yahoo Finance を含む。
  - セキュリティ対策: defusedxml を利用した XML パース、受信サイズ上限 (10 MB)、HTTP/HTTPS のみ許可、IP/SSRF 対策を考慮した実装方針（実装の一部はコード上に明記）。
  - URL 正規化（トラッキングパラメータ除去・ソート・フラグメント削除・スキーム/ホスト小文字化）と記事 ID の SHA-256 ベース生成（先頭 32 文字）で冪等性を確保。
  - raw_news へのバルク挿入はチャンク化して実行、INSERT RETURNING を想定した設計。
- リサーチ（研究用）機能 (`kabusys.research`)
  - ファクター計算群（`kabusys.research.factor_research`）:
    - `calc_momentum`（1M/3M/6M リターン、MA200 乖離）
    - `calc_volatility`（20日 ATR、相対 ATR、20日平均売買代金、出来高比）
    - `calc_value`（PER, ROE；raw_financials と prices_daily を組み合わせ）
  - ファクター探索（`kabusys.research.feature_exploration`）:
    - `calc_forward_returns`（任意ホライズンの将来リターン計算、デフォルト [1,5,21]）
    - `calc_ic`（ファクターと将来リターンの Spearman IC 計算）
    - `factor_summary`（基本統計量: count/mean/std/min/max/median）
    - `rank`（同順位は平均ランクで処理）
  - いずれも DuckDB 接続を受け取り、prices_daily/raw_financials のみ参照する設計。
  - 外部大容量ライブラリに依存しない実装（標準ライブラリ + duckdb）。
- 戦略（strategy）機能 (`kabusys.strategy`)
  - 特徴量エンジニアリング（`feature_engineering.build_features`）:
    - research 側で計算した生ファクターをマージ、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5億円）を適用。
    - 指定列を Z スコア正規化（`kabusys.data.stats.zscore_normalize` を利用）し ±3 でクリップ。
    - features テーブルへの日付単位 UPSERT（トランザクションで原子性保証）。
    - ルックアヘッドバイアス回避を考慮した target_date ベースの処理。
  - シグナル生成（`signal_generator.generate_signals`）:
    - features と ai_scores を統合して複数コンポーネントのスコア（momentum/value/volatility/liquidity/news）を計算。
    - 各コンポーネントはシグモイド変換や逆数変換などで 0..1 に正規化。欠損値は中立 0.5 で補完。
    - デフォルト重みは StrategyModel.md の仕様に準拠（momentum 0.40 等）。ユーザ入力の重みは検証・補完・再スケール。
    - Bear レジーム判定で BUY シグナルを抑制（AI の regime_score 平均が負の場合、サンプル数条件あり）。
    - BUY シグナル閾値はデフォルト 0.60。SELL シグナルはストップロス（-8%）やスコア低下で判定。
    - signals テーブルへの日付単位置換（トランザクション + バルク挿入）。
- DB/トランザクション周り
  - features / signals など日付単位の置換（DELETE → INSERT）を行い、BEGIN/COMMIT/ROLLBACK による原子性とエラーハンドリングを実装。
  - 例外発生時の ROLLBACK 失敗を WARN ログで通知するガード処理を追加。

### Changed
- n/a（初回リリースのため、過去リリースからの変更は無し）

### Fixed
- n/a（初回リリースのため）

### Security
- ニュースパーサで defusedxml を使用し XML 関連の攻撃を軽減。
- RSS URL 処理でトラッキングパラメータを除去し、記事 ID の一意化と冪等性を確保。
- J-Quants クライアントはトークンの自動リフレッシュと再試行制御を実装し、不正な認証状態での暴走を防止。
- .env 読み込み処理はファイル読み込みエラーを警告により安全に扱う（例外伝播を避ける）。

### Notes / Known limitations
- signal_generator の一部エグジット条件（トレーリングストップや時間決済）は未実装。positions テーブルに peak_price / entry_date が必要になる設計で、将来的な拡張箇所として明記。
- news_collector の一部（IP アドレス検査や SSRF 対策の完全実装）は設計上の記述があるが、外部環境依存のため運用での追加チェックが推奨される。
- research モジュールは DuckDB の prices_daily/raw_financials を前提とするため、データ準備（raw_prices → prices_daily 等）フローは別途必要。
- 一部の処理は外部サービス（J-Quants API）や DB スキーマに依存するため、運用前にスキーマ定義と環境変数の整備が必要。
- news_collector は defusedxml という外部パッケージに依存する（デフォルト RSS 処理で使用）。

---

メンテナンスや将来的なリリースでは、テストカバレッジ、API 呼び出しのモック化、外部依存の明示的な要件ファイル化（requirements）を追加していくことを推奨します。