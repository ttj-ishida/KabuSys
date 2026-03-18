# Changelog

すべての注目すべき変更はこのファイルに記録します。本ファイルは Keep a Changelog の形式に準拠しています。

最新リリース: [0.1.0] - 2026-03-18

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-18
初回公開リリース。日本株自動売買システム "KabuSys" の基礎機能を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期構成（src/kabusys/__init__.py）。
  - モジュール群のエクスポート定義: data, strategy, execution, monitoring。

- 環境設定 (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により、CWD に依存しない自動ロードを実現。
  - .env / .env.local の読み込み順と上書きルール（OS 環境変数保護）をサポート。
  - 行単位の高度な .env パーサ（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理、インラインコメント取り扱い）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト用途向け）。
  - Settings クラスを提供し、J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス等のプロパティを定義。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）および便宜的な is_live/is_paper/is_dev プロパティ。

- データ取得・保存（J-Quants クライアント）(kabusys.data.jquants_client)
  - J-Quants API クライアントを実装（認証、ページネーション対応のデータ取得関数）。
  - API レート制御（_RateLimiter）: 120 req/min を満たす固定間隔スロットリング。
  - 再試行ロジック: 指数バックオフ、最大リトライ回数、特定ステータス(408/429/>=500)でのリトライ。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ共有。
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar の実装（ページネーション対応）。
  - DuckDB への冪等保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT による更新）。
  - 型変換ユーティリティ (_to_float / _to_int) を実装し、堅牢なパースを実現。
  - fetched_at を UTC ISO フォーマットで記録し、Look-ahead Bias の追跡を可能に。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード取得 & パース機能を実装（デフォルトに Yahoo Finance のカテゴリ RSS を登録）。
  - defusedxml を用いた安全な XML パース（XML Bomb 等の防御）。
  - SSRF 対策:
    - HTTP リダイレクト時にスキームとホスト検証を行うカスタムリダイレクトハンドラを実装。
    - ホストがプライベート/ループバック/リンクローカル/マルチキャストの場合は拒否。
    - URL スキームは http/https のみ許可。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズチェック（Gzip bomb 対策）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）と記事 ID（正規化 URL の SHA-256 先頭32文字）生成による冪等化。
  - テキスト前処理（URL 除去、空白正規化）。
  - raw_news テーブルへのチャンク INSERT（ON CONFLICT DO NOTHING、INSERT ... RETURNING による挿入ID取得）。トランザクションでまとめて実行。
  - 銘柄コード抽出ロジック（4桁の数字パターンにより既知銘柄だけ抽出）と news_symbols への紐付け機能（重複排除、チャンク保存）。
  - run_news_collection により複数 RSS ソースの統合収集ジョブを提供。各ソースは独立したエラーハンドリングで継続性を確保。

- 研究（Research）モジュール (kabusys.research)
  - feature_exploration: 将来リターン計算(calc_forward_returns)、IC（calc_ic）、ファクターの統計サマリー(factor_summary)、ランク変換(rank)を実装。
    - calc_forward_returns: DuckDB の prices_daily テーブルを参照し、複数ホライズン（デフォルト: 1,5,21）を一度のクエリで計算。
    - calc_ic: スピアマンのランク相関を自前実装（同順位は平均ランク、NaN/None 排除、3 サンプル未満は None）。
    - factor_summary: count/mean/std/min/max/median を計算（None 値除外）。
  - factor_research: ファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - Momentum: mom_1m/mom_3m/mom_6m、200日移動平均乖離率（MA200）を計算。データ不足時は None。
    - Volatility / Liquidity: 20日 ATR（true range の平均）、ATR 比率、20日平均売買代金、出来高比などを計算。true_range の NULL 伝播を考慮。
    - Value: raw_financials テーブルから最新の財務データを結合して PER / ROE を計算（EPS が無効な場合は None）。DuckDB の ROW_NUMBER を用いた最新レコード抽出。
  - research パッケージの __init__.py で主要ユーティリティをエクスポート（zscore_normalize を含む）。

- スキーマ定義 (kabusys.data.schema)
  - DuckDB 用 DDL 定義を実装（Raw Layer のテーブル定義を含む: raw_prices, raw_financials, raw_news, raw_executions 等のスキーマ）。
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）設計に準拠した初期スキーマ実装。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### セキュリティ (Security)
- ニュース収集での SSRF 緩和と XML 安全化（defusedxml）の導入。
- RSS フィードでの受信サイズ上限と Gzip 解凍後の再チェックを実装し、DoS 攻撃耐性を向上。

### 注意事項 / 既知の制約 (Notes / Known limitations)
- strategy/ execution / monitoring パッケージは存在するが、発注ロジックや実行管理の具体実装は含まれていません（骨格のみ）。
- research の一部関数は外部ライブラリ（pandas など）に依存せず標準ライブラリと DuckDB の SQL によって実装されています。大規模データ処理の最適化は今後の課題です。
- J-Quants クライアントは urllib を使用した実装で、環境によってはより高機能な HTTP クライアントに差し替える余地があります。
- DuckDB DDL は Raw Layer を中心に定義されており、Processed / Feature 層の具体テーブルは拡張が必要です。
- 日付・ホライズンは「営業日（連続レコード数）」を前提とした実装箇所があるため、価格データの欠損やカレンダーずれに対する取り扱いに注意してください。

---

（付記）この CHANGELOG はソースコードの実装内容から推定して作成しています。実際のリリースノート作成時は追加の文言や運用上の注意、後続の変更履歴へのリンクを適宜追加してください。