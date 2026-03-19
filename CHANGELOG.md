# Changelog

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog に準拠しています。  

## [Unreleased]

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システムのコアライブラリを提供します。主に DuckDB ベースのデータ処理、ファクター算出、シグナル生成、外部データ取得周りの機能を含みます。

### Added
- パッケージ基盤
  - パッケージ名 kabusys を追加。トップレベルで data / strategy / execution / monitoring を公開（src/kabusys/__init__.py）。
  - バージョン番号を 0.1.0 に設定。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサを実装（コメント/export/クォート/エスケープ/インラインコメント処理に対応）。
  - 必須設定取得時に未設定なら ValueError を投げる _require を提供。
  - 設定値検証: KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）のバリデーション。
  - デフォルト値: KABUSYS_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH など。

- データ取得クライアント: J-Quants (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
  - 固定間隔スロットリングによるレートリミット制御（120 req/min）。
  - リトライ機構（指数バックオフ、最大 3 回）と 408/429/5xx に対する再試行ロジック。
  - 401 受信時にはリフレッシュトークンを使ってトークンを自動更新し 1 回リトライ。
  - ページネーション対応の fetch_* 関数を提供: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
  - DuckDB への冪等保存ユーティリティ: save_daily_quotes / save_financial_statements / save_market_calendar（ON CONFLICT による上書き）。
  - レスポンスパース・型変換ユーティリティ：_to_float / _to_int を実装。
  - 取得時刻（fetched_at）を UTC ISO8601 で記録し、ルックアヘッドのトレーサビリティを確保。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集して raw_news に保存する骨組みを追加。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除、小文字化）を実装（_normalize_url）。
  - 記事 ID を URL 正規化後の SHA-256 ハッシュで生成する方針（冪等性）。
  - defusedxml を用いた安全な XML パース、HTTP(S) スキームのみ許可、受信サイズ上限（MAX_RESPONSE_BYTES）など、セキュリティ対策を実装。
  - バルク INSERT のチャンク処理、挿入されたレコード数取得を想定した設計。

- リサーチ / ファクター計算 (src/kabusys/research/*.py)
  - calc_momentum / calc_volatility / calc_value を実装（prices_daily / raw_financials を参照）。
  - ファクター計算は date, code をキーとする dict リストで返却する設計。
  - feature_exploration モジュールに以下を追加:
    - calc_forward_returns: 将来リターン（複数ホライズン）を一括取得するクエリ実装。
    - calc_ic: スピアマンランク相関（IC）計算。サンプル不足時は None を返す。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）。
    - rank: 同順位は平均ランクをとるランク化ユーティリティ（round(..., 12) による ties 対策）。
  - 外部ライブラリに依存せず標準ライブラリのみで実装する方針。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - research モジュールで計算した raw factor をマージ・フィルタ・正規化して features テーブルへ保存する build_features を実装。
  - ユニバースフィルタ: 最低株価（300 円）および 20 日平均売買代金 >= 5 億円。
  - Z スコア正規化は kabusys.data.stats.zscore_normalize を利用、±3でクリップ。
  - 日付単位で DELETE → INSERT（トランザクション）を行い、処理を冪等に実装。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合し final_score を計算、BUY/SELL シグナルを生成する generate_signals を実装。
  - ファクター重みのデフォルト設定（momentum/value/volatility/liquidity/news）と閾値デフォルト（0.60）。
  - スコア算出用ユーティリティ（_sigmoid, _avg_scores, 各コンポーネント計算）を実装。
  - Bear レジーム判定（ai_scores の regime_score 平均が負のとき、サンプル閾値あり）により BUY を抑制するロジック。
  - エグジット判定（stop_loss: -8% など）を _generate_sell_signals として実装。SELL 優先ポリシーを採用（SELL 対象は BUY から除外）。
  - signals テーブルへの日付単位の置換（トランザクション）で冪等性を保証。
  - ユーザ指定の weights の検証（既知キーのみ、数値・非負・有限値）と正規化を行う。

### Security
- news_collector で defusedxml を使用して XML Bomb 等を防止。
- RSS の URL 正規化とトラッキングパラメータ除去、HTTP/HTTPS スキーム限定、受信サイズ制限などを実装し SSRF やメモリ DoS のリスクを低減。
- J-Quants クライアントで 401 処理時の安全なトークンリフレッシュ制御（無限再帰を避ける allow_refresh フラグ）。

### Design / Implementation Notes
- DuckDB を中心としたデータフロー（prices_daily / raw_prices / raw_financials / features / ai_scores / signals / positions 等のテーブルを想定）。
- 主要な DB 書き込み操作はトランザクション + バルク挿入で原子性を確保。
- ルックアヘッドバイアス防止を重視: 各処理は target_date 時点のデータのみ参照する設計。
- 外部 API（発注 API / 本番口座）への直接アクセスは戦略・リサーチ層では行わない（分離設計）。
- 外部依存を最小化（pandas などを使わず、標準ライブラリ + duckdb で実装）。

### Removed
- 初版のため該当なし。

### Changed
- 初版のため該当なし。

### Fixed
- 初版のため該当なし。

---

参照:
- 各モジュールの docstring に設計意図と参照ドキュメント（StrategyModel.md, DataPlatform.md 等）を記載しています。実運用前に設定（.env）と DuckDB スキーマの準備、J-Quants / Slack 等の認証情報設定が必要です。