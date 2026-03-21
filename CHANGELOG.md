# Changelog

すべての注目すべき変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

注: この CHANGELOG はコードベースから推測して作成したものであり、実際のコミット履歴ではありません。

## [0.1.0] - 2026-03-21

### Added
- 全体
  - パッケージ初期リリース（kabusys v0.1.0）。
  - パッケージ公開 API: top-level で `data`, `strategy`, `execution`, `monitoring` をエクスポート（`execution` は空パッケージとして存在）。
  - バージョン情報: `__version__ = "0.1.0"`。

- 設定・環境変数 (`kabusys.config`)
  - .env ファイルと環境変数の自動ロード機能を実装（プロジェクトルートは `.git` または `pyproject.toml` を基準に探索）。
  - .env/.env.local の読み込み順序を実装（OS環境変数 > .env.local > .env）。`.env.local` は上書きモードで読み込まれる。
  - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テストなどで利用可能）。
  - `.env` パーサーの強化:
    - 空行・コメント行の無視、`export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - インラインコメント処理（クォート外での `#` 前の空白をコメントと判断）実装。
  - 環境変数保護機構: OS 環境変数を保護するための `protected` セットを導入し、上書きを制御。
  - `Settings` クラスを提供し、以下の設定プロパティを環境変数から取得:
    - J-Quants: `jquants_refresh_token`
    - kabuステーション API: `kabu_api_password`, `kabu_api_base_url`（デフォルト: http://localhost:18080/kabusapi）
    - Slack: `slack_bot_token`, `slack_channel_id`
    - DB パス: `duckdb_path`（デフォルト: data/kabusys.duckdb）、`sqlite_path`（デフォルト: data/monitoring.db）
    - システム: `env`（development/paper_trading/live のバリデーション）、`log_level`（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）、`is_live/is_paper/is_dev` ユーティリティプロパティ
  - 必須変数未設定時に明確なエラーメッセージを返す `_require` 実装。

- データ取得・永続化 (`kabusys.data.jquants_client`)
  - J-Quants API クライアントを実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング `_RateLimiter` を導入。
  - リトライ戦略: 指数バックオフ、最大 3 回、ネットワーク系エラーや 408/429/5xx を対象に再試行。
  - 401 Unauthorized 受信時にリフレッシュトークンで自動的に ID トークンを再取得して 1 回だけリトライする処理を実装（無限再帰防止フラグあり）。
  - ページネーション対応のフェッチ関数:
    - `fetch_daily_quotes`
    - `fetch_financial_statements`
    - `fetch_market_calendar`
  - DuckDB への冪等保存関数:
    - `save_daily_quotes`: `raw_prices` テーブルへ ON CONFLICT DO UPDATE による upsert を実装。
    - `save_financial_statements`: `raw_financials` へ upsert。
    - `save_market_calendar`: `market_calendar` へ upsert。
  - データ整形ユーティリティ `_to_float` / `_to_int` を提供し、型安全に変換。欠損や不正値は None に正規化。
  - 取得時刻（fetched_at）を UTC ISO8601 で保存し、Look-ahead バイアスのトレースを可能に。

- ニュース収集 (`kabusys.data.news_collector`)
  - RSS フィードからニュース記事を取得して `raw_news` に保存するためのモジュールを実装。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを設定。
  - セキュリティ・耐障害性対策:
    - defusedxml を使った XML パース（XML Bomb 等の攻撃防止）。
    - 受信最大バイト数（10 MB）によるメモリDoS 対策。
    - URL 正規化 (`_normalize_url`): スキーム/ホスト小文字化、トラッキングパラメータ除去（utm_*, fbclid, gclid 等）、フラグメント削除、クエリソート化。
    - 記事ID は正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を確保（トラッキングパラメータを除去してからハッシュ化）。
    - バルク INSERT のチャンク化（_INSERT_CHUNK_SIZE=1000）で SQL 長・パラメータ数を抑制。
    - DB 保存はトランザクション単位でまとめて実行し、INSERT RETURNING による実際の挿入数取得を想定。
  - テキスト前処理（URL除去・空白正規化）や銘柄コードとの紐付け処理の基盤を用意。

- 研究・因子計算 (`kabusys.research`)
  - ファクター計算モジュールを実装（prices_daily / raw_financials を参照）。
  - factor_research: ファクター群を計算する関数を提供:
    - `calc_momentum`: mom_1m, mom_3m, mom_6m, ma200_dev を計算（200日移動平均のデータ不足チェック含む）。
    - `calc_volatility`: atr_20, atr_pct, avg_turnover, volume_ratio を計算（ATR の NULL 伝播制御あり）。
    - `calc_value`: per, roe を計算（raw_financials の最新レコードを target_date 以前から取得）。
  - feature_exploration: 研究用途の分析ユーティリティを実装:
    - `calc_forward_returns`: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。horizons の入力バリデーションあり。
    - `calc_ic`: スピアマンのランク相関（Information Coefficient）を計算（有効レコード数が 3 未満の場合は None）。
    - `rank`: 同順位は平均ランクとするランク付け（浮動小数丸めで ties を安定化）。
    - `factor_summary`: count/mean/std/min/max/median を計算する統計サマリー。
  - 研究向け API を top-level でエクスポート（`calc_momentum`, `calc_volatility`, `calc_value`, `zscore_normalize`, `calc_forward_returns`, `calc_ic`, `factor_summary`, `rank`）。

- 戦略 (`kabusys.strategy`)
  - 特徴量エンジニアリング (`feature_engineering.build_features`):
    - 研究環境で算出した生ファクターをマージし、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - 数値ファクターを Z スコア正規化し ±3 でクリップ。
    - features テーブルへ日付単位で DELETE → INSERT（トランザクションによる原子置換）して冪等性を保証。
    - ユニバースフィルタの閾値: 最低株価 300 円、最低平均売買代金 5 億円。
  - シグナル生成 (`signal_generator.generate_signals`):
    - features と ai_scores を統合し、コンポーネントスコア（momentum / value / volatility / liquidity / news）を計算。
    - 最終スコア final_score を重み付き合算で計算（デフォルト重みを実装）。
    - AI レジームスコアの集計により Bear レジームを判定し、Bear 時は BUY シグナルを抑制。
    - BUY シグナル閾値（デフォルト 0.60）を超えた銘柄に BUY を生成。SELL はストップロス（-8%）やスコア低下で判定。
    - weights の入力は検証され、既定値でフォールバック・合計が 1.0 になるよう再スケール。
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入で原子性）。
    - SELL 優先ポリシー: SELL 対象は BUY から除外し、BUY のランクを再付与。
    - ロギングにより生成結果を出力（BUY/SELL カウント等）。
  - `build_features` と `generate_signals` をパッケージ公開関数としてエクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- ニュース収集: defusedxml 利用、レスポンスサイズ制限、URL 正規化で SSRF/トラッキングによる問題を軽減。
- J-Quants クライアント: トークン自動リフレッシュ時の無限再帰防止、HTTP リトライポリシーで一部の一時エラー耐性を強化。

### Notes / Known limitations
- signal_generator の一部エグジット条件は未実装。ドキュメント内に以下の未実装項目が明記されています:
  - トレーリングストップ（直近最高値から -10%）
  - 時間決済（保有 60 営業日超過）
  これらは positions テーブルに peak_price / entry_date 等の情報が必要。
- `execution` パッケージは存在するが実装（発注ロジックなど）はこのスナップショットには含まれていない。
- News collector の一部（IP アドレス/SSRF チェックや記事→銘柄マッピングなど）は準備された設計を含むが、外部サービス連携や完全なマッピングロジックは環境に依存するため追加実装が必要。
- DB スキーマ（tables: raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals, raw_news など）は本 CHANGELOG では明示されていませんが、各関数はそれらの存在を前提としています。

もしリリースノートに追加したい技術的詳細、日付の修正、あるいは既知のバグや将来のロードマップ情報があれば教えてください。必要に応じて CHANGELOG を更新します。