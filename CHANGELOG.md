# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買システムのコアライブラリを実装しました。主要な機能・設計方針・モジュール別の追加点は以下の通りです。

### 追加 (Added)

- パッケージ基礎
  - パッケージ初期化: kabusys/__init__.py にてバージョン設定および公開モジュール定義（data, strategy, execution, monitoring）。
- 環境設定管理 (`kabusys.config`)
  - .env / .env.local 自動ロード機構を実装。プロジェクトルートは `.git` または `pyproject.toml` を基準に探索するため CWD に依存しない。
  - 自動ロードを無効化するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
  - `.env` パーサーの強化:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープのサポート。
    - コメント（#）処理の改善（クォート外で直前が空白/タブの時のみコメント扱い）。
  - 環境変数取得ユーティリティ `Settings` を追加。必須キーのチェック、デフォルト値、型変換（Path）を提供。
  - 設定値バリデーション:
    - `KABUSYS_ENV` は `development|paper_trading|live` のみ許可。
    - `LOG_LEVEL` は `DEBUG|INFO|WARNING|ERROR|CRITICAL` のみ許可。
- データ取得 / 永続化 (`kabusys.data.jquants_client`)
  - J-Quants API クライアント実装（ページネーション対応）。
  - レート制限（120 req/min）制御のための固定間隔スロットリング `_RateLimiter` を導入。
  - リトライロジック（指数バックオフ、最大 3 回）。HTTP 408/429/5xx をリトライ対象とする。
  - 401 受信時のトークン自動リフレッシュ（1 回のみ）とモジュールレベルのトークンキャッシュ。
  - JSON パース失敗時の明確な例外メッセージ。
  - fetch_* 系関数: 日足、財務、マーケットカレンダーの取得を実装。
  - save_* 系関数: DuckDB への冪等保存（ON CONFLICT DO UPDATE）を実装。
  - 型変換ユーティリティ `_to_float`, `_to_int` を用意し入力の頑健化（空文字や不正値は None）。
  - 取得時刻（fetched_at）は UTC ISO8601 で記録し、Look-ahead バイアスの追跡を可能に。
- ニュース収集 (`kabusys.data.news_collector`)
  - RSS からニュース記事を収集して raw_news に保存する実装（デフォルトソースに Yahoo）。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等の防止）。
    - URL 正規化・トラッキングパラメータ除去（utm_*, fbclid 等）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を設定してメモリ DoS を軽減。
    - HTTP/HTTPS 以外のスキーム排除等の SSRF 対策（設計方針に準拠）。
  - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）を用いて冪等性を担保。
  - バルク INSERT のチャンク処理を導入して SQL/パラメータ長の上限に対応。
- リサーチモジュール (`kabusys.research`)
  - ファクター計算（factor_research）を実装:
    - Momentum（mom_1m / mom_3m / mom_6m / ma200_dev）
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
    - Value（per, roe） — raw_financials の最新財務情報と組み合わせて計算
    - 各関数は DuckDB の SQL を用いて実装し prices_daily / raw_financials テーブルのみを参照
  - 特徴量探索 (feature_exploration) を実装:
    - 将来リターン計算 `calc_forward_returns`（ホライズン: デフォルト [1,5,21]）
    - IC（Spearman ランク相関）計算 `calc_ic`（欠損ハンドリング、最小サンプル数チェック）
    - 基本統計量サマリー `factor_summary`
    - ランク変換ユーティリティ `rank`（同順位は平均ランク、丸め処理で ties 検出の安定化）
- 特徴量エンジニアリング (`kabusys.strategy.feature_engineering`)
  - 研究環境の生ファクターを正規化・合成して `features` テーブルに保存する `build_features` を実装。
  - 流れ:
    - research の calc_* を呼び出して元ファクターを取得
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用
    - 指定カラムを Z スコア正規化（data.stats.zscore_normalize を利用）、±3 でクリップ
    - 日付単位の置換（DELETE + INSERT）で冪等に保存（トランザクションで原子性保証）
  - 欠損・外れ値に配慮した実装
- シグナル生成 (`kabusys.strategy.signal_generator`)
  - `generate_signals` を実装。`features` と `ai_scores` を統合して最終スコア（final_score）を算出し、BUY/SELL シグナルを生成。
  - 実装の特徴:
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算（シグモイド変換等）
    - デフォルト重みを定義し、ユーザ渡しの weights を検証・正規化して合計が 1.0 にリスケール
    - AI スコア（ai_scores）の regime_score を集計して Bear レジーム判定（サンプル数の下限あり）
    - Bear レジーム時は BUY シグナルを抑制
    - 保有ポジションに対する SELL 条件（ストップロス -8% / final_score の閾値割れ）
    - SELL 優先ポリシー（SELL 対象は BUY リストから除外、ランク再付与）
    - 日付単位の置換で `signals` テーブルへ冪等に保存（トランザクションで原子性）
- 汎用改善・堅牢性
  - 各所で欠損データや不整合をスキップ・警告し（PK 欠損でのスキップ警告等）、運用時の堅牢性を高めた。
  - DB 操作でのトランザクションと例外時のロールバック（失敗ログ）による原子性保証。

### 変更 (Changed)

- （初回リリースのため該当なし）

### 修正 (Fixed)

- ファイル I/O / ネットワーク / DB 系での細かいエラー条件に対して警告出力やスキップ処理を追加（例: .env 読み込み失敗時の警告、raw_* 保存での PK 欠損スキップなど）。
- SQL 実行中のロールバック失敗時に logger.warning を出すようにしてデバッグ性を向上。

### 非互換性 (Breaking Changes)

- なし（初回リリース）。ただし内部の DB スキーマ（テーブル名 / カラム名）に依存するため、運用時は既存 DB スキーマとの整合性に注意してください。

### セキュリティ (Security)

- news_collector で defusedxml を使用して XML 攻撃を軽減。
- RSS パース / URL 正規化時にトラッキングパラメータ除去やスキームチェックを行い SSRF 等のリスクを低減。
- 外部 API 呼び出しに対してタイムアウト、リトライ、レート制限を実装。

---

今後の予定（例）
- execution 層の実装（kabu ステーションとの注文実行ロジック）
- モニタリング・アラート機構の実装（Slack 通知等）
- 分析パイプラインのテストカバレッジ拡充

（必要に応じてこの CHANGELOG を更新してください。）