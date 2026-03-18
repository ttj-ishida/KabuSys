# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に準拠しています。  

全てのリリースは逆日時順で並べます。

## [0.1.0] - 2026-03-18

初回公開リリース。

### 追加
- 基本パッケージ構成
  - パッケージ名: kabusys、バージョン 0.1.0。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機構を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサの堅牢化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - コメントの扱い（クォート外かつ直前が空白の場合に # をコメントとみなす等）
  - 環境変数取得用 Settings クラスを提供（各種必須設定をプロパティ経由で取得）。
    - J-Quants / kabu API / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベルの取得とバリデーションを実装。
    - is_live / is_paper / is_dev の便利プロパティを追加。

- データ取得・保存（kabusys.data）
  - J-Quants API クライアント（data.jquants_client）
    - 固定間隔スロットリングによるレート制御（120 req/min を想定）。
    - 冪等性を考慮した保存ロジック（DuckDB へ ON CONFLICT DO UPDATE を使用）。
    - リトライロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx を対象）。
    - 401 応答時は自動でリフレッシュトークンから ID トークンを取得して 1 回リトライ。
    - ページネーション対応の fetch_* 関数（daily_quotes, statements, trading_calendar）。
    - 受信データを適切に変換するユーティリティ関数 (_to_float / _to_int) と保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）。
    - fetched_at を UTC で記録し、Look-ahead Bias のトレースを可能に。

  - ニュース収集（data.news_collector）
    - RSS フィードからの記事収集と DuckDB への保存機能。
    - 安全性対策:
      - defusedxml を用いた XML パース（XML Bomb 等への対策）。
      - SSRF 対策（リダイレクト先のスキームとプライベートIP検査、初回ホスト検証）。
      - URL スキーム検証（http/https のみ許可）。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後のサイズ再チェック。
    - URL 正規化機能（トラッキングパラメータ除去、ソート、フラグメント削除）、正規化 URL からの記事ID生成（SHA-256 の先頭32文字）。
    - テキスト前処理（URL除去、空白正規化）、pubDate の安全なパースロジック。
    - DB 挿入時にトランザクションを用い、INSERT ... RETURNING により新規挿入IDを正確に返す実装（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
    - 記事中から有効銘柄コード（4桁）を抽出するユーティリティ（extract_stock_codes）。
    - 複数ソースを巡回して収集する統合ジョブ run_news_collection を実装。

- DuckDB スキーマ定義（data.schema）
  - DataSchema に基づくテーブル定義（Raw / Processed / Feature / Execution 層のスキーマ定義を開始）。
  - raw_prices, raw_financials, raw_news, raw_executions の DDL を実装（制約・型チェック含む）。

- リサーチ（kabusys.research）
  - feature_exploration:
    - calc_forward_returns: 指定日の終値から複数ホライズン（デフォルト 1,5,21 営業日）先の将来リターンを DuckDB を用いて一括計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。データ不足時は None を返す。
    - rank: 同順位は平均ランクを割り当てるランク化関数（浮動小数丸めで ties を安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
    - 標準ライブラリのみでの実装（pandas 等に依存しない）。
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を DuckDB を用いて計算（不足データは None）。
    - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（EPS が 0 または欠損の場合は None）。
    - 各関数は prices_daily / raw_financials のみ参照し、本番発注APIへのアクセスは行わない旨を設計で明示。

- パッケージエクスポート
  - kabusys.research の __init__ で主要ユーティリティ（calc_momentum / calc_volatility / calc_value / zscore_normalize / calc_forward_returns / calc_ic / factor_summary / rank）を公開。

### セキュリティ
- RSS 収集での SSRF 対策を実装（リダイレクトブロックハンドラ、プライベートアドレス検査）。
- XML パースに defusedxml を採用。
- URL 正規化によりトラッキングパラメータを排除し、記事IDの一意性と冪等性を向上。

### 変更（設計上の注記）
- DuckDB 系関数は全て DuckDB 接続を受け取り、DB テーブル（prices_daily, raw_financials, raw_prices, raw_news 等）へアクセスする設計。
- 研究モジュールは外部 API や発注系コンポーネントに依存しない「リードオンリー」実装。

### 既知の制限 / 注意点
- research モジュールは pandas 等の外部依存を避けており、大規模データに対しては DuckDB の SQL 側での最適化が必要となる場合がある。
- _to_int は "1.9" のように小数部が 0 以外の文字列に対しては None を返す（意図的な切り捨て回避）。
- calc_ic / その他統計関数は有効なレコード数が少ない場合に None を返す設計（安全側）。
- raw_executions の DDL はファイル中で続きがある（将来的な Execution 層実装に依存）。

### 修正
- （初版のため過去のバグ修正履歴はありません）

### 廃止 / 削除
- （初版のためなし）

---

今後のリリースでは以下のトピックを予定しています（計画）:
- 実行 / 発注系（kabuapi 連携）モジュールの実装とテストカバレッジの追加
- DuckDB スキーマの完全版（Processed / Feature / Execution 層の追加）
- モジュール間の統合テスト、CI ワークフローの整備
- ドキュメント（使用例、環境構築手順）の拡充

もし CHANGLEOG に追加してほしい項目（注目すべき設計判断や既知の問題など）があれば教えてください。