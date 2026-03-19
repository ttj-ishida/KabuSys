# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
このファイルにはパッケージ `kabusys` のコードベースから推測される変更・追加点を記載しています。

## [Unreleased]

### Added
- 開発中の日本株自動売買ライブラリ `kabusys` の初期情報を追加（`__version__ = "0.1.0"`）。
- パッケージエクスポートを定義（`kabusys.__all__ = ["data", "strategy", "execution", "monitoring"]`）。

- 環境設定管理モジュールを追加（`kabusys.config`）。
  - `.env` / `.env.local` の自動読み込み機能（プロジェクトルート検出：`.git` または `pyproject.toml`）。
  - `.env` パーサーの強化：`export KEY=val`、シングル/ダブルクォート内のエスケープ、インラインコメントの扱いなどに対応。
  - 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` フラグ。
  - `Settings` クラスによる型付き・検証付き設定アクセス（`JQUANTS_REFRESH_TOKEN` / `KABU_API_PASSWORD` / Slack・DBパス / 環境・ログレベル検証など）。
  - OS 環境変数保護（`.env.local` の上書きルールで保護セットを考慮）。

- データ取得・保存モジュール（`kabusys.data.jquants_client`）を追加。
  - J-Quants API クライアント：ページネーション対応、`fetch_daily_quotes` / `fetch_financial_statements` / `fetch_market_calendar`。
  - レート制限（固定間隔スロットリング）実装（120 req/min の制御）。
  - リトライロジック（指数バックオフ、最大試行回数、408/429/5xx の再試行、429 の `Retry-After` 優先）。
  - 401 レスポンス受信時のトークン自動リフレッシュ（1 回のみ）とキャッシュ化された ID トークンの共有。
  - DuckDB への冪等保存ユーティリティ（`save_daily_quotes` / `save_financial_statements` / `save_market_calendar`）：
    - PK 欠損行のスキップとログ警告。
    - `ON CONFLICT ... DO UPDATE` によるアップサート。
  - 文字列→数値変換ユーティリティ（厳密な int/float 変換処理）。

- ニュース収集モジュール（`kabusys.data.news_collector`）を追加（RSS ベース）。
  - RSS 取得→記事整形→DB 保存のフロー（`raw_news` 保存想定）。
  - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ削除、フラグメント削除、クエリソート）。
  - 記事 ID に正規化 URL の SHA-256 ハッシュ先頭等を用いることで冪等性を確保。
  - セキュリティ対策：`defusedxml` を用いた XML パース、受信サイズ上限（メモリDoS対策）、SSRF/不正スキームの検討（関連ユーティリティを含む）。
  - バルク挿入のチャンク化によるパフォーマンス対策。

- リサーチ用モジュール群（`kabusys.research`）。
  - ファクター計算（`kabusys.research.factor_research`）:
    - `calc_momentum`（1M/3M/6M リターン、MA200 乖離率）、`calc_volatility`（ATR20、相対 ATR、20日平均売買代金、出来高比率）、`calc_value`（PER/ROE の計算）。
    - DuckDB を使った窓関数中心の実装、データ不足時は None を返す堅牢な設計。
  - 特徴量探索機能（`kabusys.research.feature_exploration`）:
    - `calc_forward_returns`（複数ホライズンの将来リターンを一度のクエリで取得、horizons 検証あり）。
    - `calc_ic`（Spearman ランク相関に基づく IC 計算）、`rank`（同順位は平均ランクで処理）、`factor_summary`（count/mean/std/min/max/median を計算）。
  - 研究ユーティリティ `zscore_normalize` の再利用エクスポート。

- 戦略層（`kabusys.strategy`）。
  - 特徴量構築（`feature_engineering.build_features`）:
    - 研究モジュールの生ファクターを統合、ユニバースフィルタ（最低株価、20日平均売買代金）、Z スコア正規化＋±3 でのクリップ、日付単位の置換（削除→挿入）で冪等性を保証。
    - DuckDB トランザクション制御（BEGIN/COMMIT/ROLLBACK）とログ出力。
  - シグナル生成（`signal_generator.generate_signals`）:
    - features と ai_scores を組み合わせた最終スコア計算（コンポーネント：momentum/value/volatility/liquidity/news）。
    - デフォルト重みの合成とユーザー指定重みの検証・リスケール。
    - Sigmoid・欠損補完（中立 0.5）を用いたスコア計算。
    - Bear レジーム判定（AI の regime_score の平均が負で、十分なサンプル数がある場合）。
    - BUY（閾値ベース、Bear 時は抑制）/SELL（ストップロス、スコア低下）シグナル生成、SELL 優先で BUY から除外。
    - 日付単位の置換（`signals` テーブル）で冪等性を保証。

### Security
- XML パーシングに `defusedxml` を採用し、RSS フィード処理で XML の脆弱性に対処。
- RSS の URL 正規化でトラッキング削除・クエリソートを行い、ID 決定の安定性と冪等性を向上。
- ニュース取得時の受信サイズ上限（MAX_RESPONSE_BYTES）を導入してメモリ DoS を緩和。

### Known limitations / TODO
- シグナル生成の売り条件に関して、ドキュメント中で「未実装」とされている追加条件（トレーリングストップや時間決済）は現時点では未実装（コード内コメント参照）。
- `news_collector` の SSRF / IP フィルタなどの細部はユーティリティが存在するが、運用ルール次第で追加設定が必要。
- `execution` / `monitoring` パッケージはエクスポートされているが、今回のスナップショットでは内容が未提示（空の `__init__` 等）。

---

## [0.1.0] - 2026-03-19

### Added
- 初回公開リリースとして上記の機能群をパッケージ化。
  - 環境設定、自動 .env ロード、設定の検証機能。
  - J-Quants API クライアント（レート制御・リトライ・トークンリフレッシュ・ページネーション）。
  - DuckDB への安全なデータ保存ユーティリティ（アップサート）。
  - RSS ニュース収集の基礎実装（正規化・安全対策・冪等化）。
  - 研究用ファクター計算（モメンタム/ボラティリティ/バリュー）と解析ユーティリティ（将来リターン・IC・統計サマリー）。
  - 特徴量エンジニアリングとシグナル生成ロジック（スコアの統合・Bear 条件・BUY/SELL 判定・冪等な DB 書き込み）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

---

著作・貢献者情報やリリース手順は別途ドキュメントにて管理してください。必要であれば各モジュールごとのより詳細な変更履歴（関数単位の変更点や API 互換性注記）も作成します。