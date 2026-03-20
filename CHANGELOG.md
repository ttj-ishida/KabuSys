# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-20

### Added
- 初期リリースとしてパッケージ `kabusys` を追加。
  - パッケージメタ情報: `src/kabusys/__init__.py`（version=0.1.0、公開 API: data, strategy, execution, monitoring）。
- 環境設定管理モジュールを追加（`kabusys.config`）:
  - .env ファイル / 環境変数を自動読み込み（優先順位: OS 環境変数 > .env.local > .env）。
  - プロジェクトルート検出: `.git` または `pyproject.toml` を基準に探索（CWD に依存しない実装）。
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
  - 強化された .env パーサー（引用符内のエスケープ処理、`export KEY=val` 形式対応、インラインコメントの取り扱い等）。
  - Settings クラスで必須環境変数の取得とバリデーション（J-Quants / kabu API / Slack / DB パス / env/log_level 等）。
  - `duckdb_path` / `sqlite_path` の Path 型ラッパー提供。
  - `KABUSYS_ENV` / `LOG_LEVEL` の許容値チェックと便利なプロパティ（is_live / is_paper / is_dev）。
- データ取得・永続化（`kabusys.data.jquants_client`）:
  - J-Quants API クライアントを実装。
  - レート制限 (120 req/min) 対応の固定間隔スロットリング（RateLimiter）。
  - 再試行（指数バックオフ）とステータスコード依存のリトライ方針 (408/429/5xx)。
  - 401 応答時のリフレッシュトークン自動再取得（1回）とモジュールレベルの ID トークンキャッシュ。
  - ページネーション対応のフェッチ関数: `fetch_daily_quotes`, `fetch_financial_statements`, `fetch_market_calendar`。
  - DuckDB へ保存するための冪等保存ユーティリティ: `save_daily_quotes`, `save_financial_statements`, `save_market_calendar`（ON CONFLICT DO UPDATE を使用、`fetched_at` を UTC で記録）。
  - 安全で堅牢な型変換ユーティリティ: `_to_float`, `_to_int`（空値・不正値を None に落とす実装）。
- ニュース収集モジュール（`kabusys.data.news_collector`）:
  - RSS フィード収集・前処理・DB への冪等保存のフローを実装。
  - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を確保。
  - defusedxml を用いた XML パースで XML Bomb 等への対策。
  - 受信サイズ上限（10MB）、トラッキングパラメータ除去、URL 正規化（スキーム/ホスト小文字化、フラグメント除去、クエリソート）を実装。
  - SSRF 緩和や不正スキーム拒否の方針を明記（HTTP/HTTPS のみを想定）。
  - バルク INSERT のチャンク処理とトランザクションまとめ保存、挿入数を正確に返す実装方針。
- リサーチ用モジュール（`kabusys.research`）:
  - ファクター計算 (`kabusys.research.factor_research`):
    - `calc_momentum`（mom_1m/mom_3m/mom_6m、ma200_dev）
    - `calc_volatility`（atr_20, atr_pct, avg_turnover, volume_ratio）
    - `calc_value`（per, roe）
    - DuckDB の prices_daily / raw_financials テーブルのみ参照する設計
  - 特徴量探索 (`kabusys.research.feature_exploration`):
    - `calc_forward_returns`（複数ホライズンでの将来リターン計算、1クエリ取得）
    - `calc_ic`（Spearman ランク相関 / IC 計算）
    - `factor_summary`（count/mean/std/min/max/median）
    - `rank`（同順位は平均ランクで処理、丸めによる ties 対応）
  - 研究向けユーティリティの公開（zscore_normalize は `kabusys.data.stats` を参照）。
- 戦略モジュール（`kabusys.strategy`）:
  - 特徴量エンジニアリング（`feature_engineering.build_features`）:
    - research 側の生ファクターを取得しユニバースフィルタ（最低株価・平均売買代金）適用、Z スコア正規化（指定カラム）、±3 でクリップ、features テーブルへ日付単位の置換（トランザクションで原子性確保）。
    - ルックアヘッドバイアス回避のため target_date 時点のデータのみを使用。
  - シグナル生成（`signal_generator.generate_signals`）:
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算、重み付き合算で final_score を算出。
    - 重みのバリデーションと合計が 1.0 でない場合のリスケールロジック。
    - Bear レジーム判定に基づく BUY 抑制。
    - BUY（閾値 0.60）/SELL（ストップロス -8% やスコア低下）シグナルの生成。
    - positions/price を参照したエグジット判定と signals テーブルへの日付単位置換（トランザクションで原子性確保）。
    - SELL を優先して BUY リストから除外し、ランク再付与。
- ロギング、例外処理、トランザクションの取り扱い（COMMIT/ROLLBACK）に関する詳細なログ出力を各所に追加。

### Fixed / Improved
- .env 読み込み時のファイル入出力エラーを警告で扱い処理継続するよう改善。
- API 呼び出しでの JSON デコード失敗やネットワークエラーに対する明確なエラーメッセージとリトライ戦略を導入。
- DuckDB へのバルク挿入で PK 欠損行をスキップする際に警告ログを出力するようにして、スキップ数の可視化を向上。
- SQL によるウィンドウ集計や LEAD/LAG を活用し、複数ホライズンを 1 クエリで取得する等パフォーマンスに配慮した実装を導入。

### Security
- RSS XML のパースに defusedxml を採用して XML ベース攻撃を緩和。
- ニュース収集においてトラッキングパラメータ除去、URL 正規化、受信サイズ制限を実装し、冗長な外部参照やメモリ DoS を防止する方針を導入。
- J-Quants クライアントでのトークン管理と 401 リフレッシュ挙動により、資格情報取り扱いの堅牢性を向上。

### Known limitations / Notes
- signal_generator 内の一部エグジット条件（トレーリングストップ、保有日数による時間決済）は positions テーブルに peak_price / entry_date 等の追加情報が必要で、現バージョンでは未実装（コメントで明記）。
- 一部の処理は `kabusys.data.stats.zscore_normalize` に依存する（本変更履歴に含まれるファイル一覧では未表示）。
- news_collector の URL/ネットワーク検証は設計に記載があるが、外部環境の制約により追加の検証・テストが必要な箇所がある可能性あり。
- execution パッケージは初期化ファイルのみ（実装は今後のリリース予定）。

### Breaking Changes
- なし（初期リリース）

---

（注）本 CHANGELOG は与えられたソースコードの内容とコメントから推測して作成したものであり、実際のリリースノートや履歴とは異なる可能性があります。必要であれば、リリース日や担当者、関連 issue/PR などのメタ情報を追加します。