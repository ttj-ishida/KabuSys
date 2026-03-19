# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
リリース日付はこのコードベースから推測した初回公開日を記載しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買プラットフォームのコア機能群を実装しました。主な追加点は以下の通りです。

### Added
- 基本パッケージ構成
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring
  - バージョン定義: `__version__ = "0.1.0"`

- 環境設定 / 設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装
    - プロジェクトルート判定: .git または pyproject.toml を探索してプロジェクトルートを特定
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能（テスト向け）
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）
  - Settings クラスを提供し、以下の主要設定を取得
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL
    - SLACK_BOT_TOKEN、SLACK_CHANNEL_ID
    - DUCKDB_PATH、SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（検証付き）
    - is_live / is_paper / is_dev ユーティリティプロパティ

- Data 層
  - J-Quants API クライアント (`kabusys.data.jquants_client`)
    - 基本機能: 日足・財務データ・マーケットカレンダーの取得
    - レートリミッタ実装（120 req/min 固定間隔スロットリング）
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx 対応）
    - 401 レスポンス時のトークン自動リフレッシュ（1 回のみ）
    - ページネーション対応（pagination_key を利用）
    - DuckDB への保存関数（raw_prices / raw_financials / market_calendar）を実装
      - 冪等性: INSERT ... ON CONFLICT DO UPDATE を使用
    - 型変換ユーティリティ: `_to_float`, `_to_int`（空値・異常値に対する安全処理）

  - ニュース収集モジュール (`kabusys.data.news_collector`)
    - RSS フィード取得（デフォルトに Yahoo Finance のカテゴリ RSS を設定）
    - セキュリティ対策:
      - defusedxml を用いた XML パース（XML Bomb 等対策）
      - SSRF 対策: URL スキーム検証 (http/https のみ)、プライベート IP/ホストの検出と拒否、リダイレクト時検査（カスタム RedirectHandler）
      - レスポンス読み取りサイズ制限（MAX_RESPONSE_BYTES = 10MB、圧縮後も検査）
      - gzip 解凍の失敗・サイズ超過ハンドリング
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）と記事 ID 生成（SHA-256 先頭32文字）
    - テキスト前処理（URL 除去・空白正規化）
    - 銘柄コード抽出（4桁数字、known_codes でフィルタ、重複除去）
    - DB 保存処理:
      - `save_raw_news` はチャンク挿入＋INSERT ... RETURNING による新規挿入IDの取得、トランザクション管理（ロールバック）
      - `save_news_symbols` / `_save_news_symbols_bulk` による記事⇔銘柄の紐付け（チャンク・トランザクション・ON CONFLICT DO NOTHING）
    - 集約ジョブ `run_news_collection` を提供（各ソースを個別に処理し、失敗しても他ソース継続）

  - DuckDB スキーマ初期化 (`kabusys.data.schema`)
    - Raw / Processed / Feature / Execution 層を想定した DDL を定義
    - raw_prices, raw_financials, raw_news, raw_executions などのテーブル定義を含む（NOT NULL / CHECK / PRIMARY KEY 等の制約を定義）

- Research 層
  - 特徴量探索 (`kabusys.research.feature_exploration`)
    - 将来リターン計算: calc_forward_returns（複数ホライズン対応、1クエリで取得）
    - IC（スピアマンランク相関）計算: calc_ic（欠損/非有限値除外、最小サンプルチェック）
    - ファクター統計サマリー: factor_summary（count/mean/std/min/max/median）
    - ランク変換ユーティリティ: rank（同順位は平均ランク、丸めによる ties 対応）
    - 設計方針として DuckDB の prices_daily テーブルのみ参照、本番 API にはアクセスしない点を明示
  - ファクター計算 (`kabusys.research.factor_research`)
    - Momentum ファクター: calc_momentum（1M/3M/6M リターン、200日移動平均乖離率、データ不足時 None）
    - Volatility / Liquidity: calc_volatility（20日 ATR、ATR 比率、20日平均売買代金、出来高比）
    - Value ファクター: calc_value（raw_financials から最新財務を取得して PER / ROE 計算）
    - スキャンレンジやウィンドウ制御は営業日ベースの連続レコードを前提にし、パフォーマンスを考慮したカレンダーバッファを設定
  - research パッケージの __init__ で主要ユーティリティを再エクスポート（calc_momentum 等 + zscore_normalize 参照）

### Security
- J-Quants クライアント
  - レート制限とリトライにより API レート制限・一時障害に耐性を持たせる実装
  - 401 時のトークンリフレッシュは安全に一回のみ行う設計（無限再帰を回避）
- ニュース収集
  - SSRF 対策、プライベートアドレス拒否、スキーム制限、defusedxml による XML 攻撃対策、レスポンスサイズ制限など複数の防御を導入

### Reliability / Robustness
- DB 保存は冪等的に実行（ON CONFLICT ... DO UPDATE / DO NOTHING を利用）
- fetch_* 系はページネーションとトークンキャッシュをサポート
- ニュース保存はチャンク化・トランザクションで安全に処理
- .env パーサと自動ロードはプロジェクトルート探索に基づき、配布後も予期せぬ動作を避ける設計

### Documentation / Misc
- 各モジュールに docstring と設計方針を明確に記載（Research / DataPlatform / StrategyModel 参照）
- ロガーを各モジュールに導入し、重要な操作で情報・警告・例外ログを出力

## Unreleased / 今後の TODO（コードから推測）
- Strategy（発注ロジック）と Execution 層の実装（現状はパッケージ構成のみ）
- zscore_normalize の実装場所（kabusys.data.stats を参照）および関連ユーティリティの整備
- PBR・配当利回りなどのバリューファクター拡張
- 単体テスト・統合テストの整備（API/ネットワーク呼び出しをモックするテストヘルパーの追加）
- エラーハンドリングやメトリクスの強化、運用向けの詳細なログ/監視実装

---

この CHANGELOG はコードベース内の実装と docstring から推測して作成しています。実際の変更履歴と差異がある場合は、リリース時のコミットログやタグ情報に基づいて補正してください。