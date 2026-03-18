# CHANGELOG

すべての注目すべき変更をここに記録します。本ファイルは Keep a Changelog のスタイルに準拠します。

現在のリリース履歴は、このコードベースから推測して作成した初版リリースノートです。

## [Unreleased]

- 今後の変更点やマイナー修正・改善はここに追記してください。

## [0.1.0] - 2026-03-18

初期リリース（初期実装）。日本株自動売買プラットフォーム "KabuSys" のコア機能群を実装しました。以下の主要機能・設計方針を含みます。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージ初期化（`__version__ = "0.1.0"`）。
  - サブパッケージプレースホルダ: data, strategy, execution, monitoring。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数からの設定読み込みを自動化。
  - プロジェクトルート検出ロジック（`.git` または `pyproject.toml` を基準）により、CWDに依存しない自動ロードを実装。
  - .env パーサを実装:
    - export KEY=val 形式に対応
    - シングル/ダブルクォートとバックスラッシュエスケープ処理対応
    - インラインコメント処理（スペース直前の # をコメントとみなす等）
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`
  - Settings クラスを提供し、必須設定を取得するプロパティを定義:
    - J-Quants / kabuステーション / Slack / データベースパス等
  - 設定値検証:
    - KABUSYS_ENV（development / paper_trading / live）
    - LOG_LEVEL（DEBUG, INFO, WARNING, ERROR, CRITICAL）

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API ベース機能:
    - 日足（OHLCV）、財務（四半期 BS/PL）、JPX カレンダーの取得関数を実装（ページネーション対応）。
    - ID トークン取得（リフレッシュ）実装（POST `/token/auth_refresh`）。
  - 信頼性・運用機能:
    - 固定間隔のレートリミッター（デフォルト 120 req/min、スロットリングで間隔制御）。
    - 再試行（指数バックオフ）ロジック（最大 3 回、HTTP 408/429 と 5xx を対象）。
    - 401 受信時のトークン自動リフレッシュ（1 回のみ）と再試行対応。
    - レスポンス JSON デコード失敗時の明示的エラー。
  - データ保存機能（DuckDB 連携）:
    - save_daily_quotes / save_financial_statements / save_market_calendar を提供。
    - 挿入は冪等（ON CONFLICT DO UPDATE）で重複を排除。
    - fetched_at を UTC ISO 形式で記録し、データ取得時刻を残す（Look-ahead Bias 対策）。
    - PK 欠損行のスキップとログ出力。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからのニュース収集と DuckDB への保存ワークフローを実装。
  - セキュリティ・堅牢性対策:
    - defusedxml を利用した XML パース（XML Bomb 等への対策）。
    - SSRF 対策: リダイレクト時にスキーム検証とプライベートアドレス判定を行うカスタム RedirectHandler を導入。
    - URL スキーム制限（http/https のみ）。
    - レスポンス受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズ検証（Gzip bomb 対策）。
  - データ前処理と正規化:
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）。
    - 記事IDは正規化 URL の SHA-256 ハッシュ先頭32文字で生成（冪等性確保）。
    - テキスト前処理（URL除去、空白正規化）。
    - pubDate パース（RFC2822 互換）し UTC naive datetime に変換。パース失敗時は現在時刻で代替。
  - DB 保存の効率化:
    - raw_news へのチャンク単位（デフォルト 1000 件）バルク INSERT、INSERT ... RETURNING を使って実際に挿入された ID を返す。
    - news_symbols の一括保存用内部関数（重複除去、チャンク挿入、トランザクション管理）。
  - 銘柄抽出:
    - 本文/タイトルから4桁の銘柄コード候補を抽出し、既知コードセットに基づき絞り込み。重複は除去。

- スキーマ定義（kabusys.data.schema）
  - DuckDB 用 DDL を提供し、層別（Raw / Processed / Feature / Execution）テーブルを定義:
    - raw_prices, raw_financials, raw_news, raw_executions 等（Raw）
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等（Processed）
    - features, ai_scores（Feature）
    - signals, signal_queue, orders, trades, positions, portfolio_performance（Execution）
  - カラム制約（型チェック、NOT NULL、CHECK 制約、外部キー）を豊富に設定。
  - 頻出クエリのためのインデックスを作成。
  - init_schema(db_path) による初期化関数と get_connection() を提供。
  - db_path の親ディレクトリ自動作成（ファイル DB の場合）。":memory:" 対応。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新を前提とした ETL の枠組みを実装（差分取得、保存、品質チェック呼び出し）。
  - ETLResult dataclass を導入し、取得/保存件数、品質問題、エラー一覧などを集約。
  - 差分ヘルパー: テーブルの最終日取得関数（raw_prices, raw_financials, market_calendar）。
  - 市場カレンダー補助: 非営業日の場合に直近営業日に調整する _adjust_to_trading_day 実装。
  - run_prices_etl 実装（差分の自動計算、backfill デフォルト 3 日、初回ロードは 2017-01-01 を下限）。
  - 品質チェックは失敗を即停止しない設計（収集継続し、呼び出し元に判断を委ねる）。

### 変更 (Changed)
- （初期リリースのため該当なし）コードベース設計段階でのドキュメント的なコメント・設計方針を多数付与。
  - 各モジュールに設計原則や安全性・データ品質に関する注記を追加。

### 修正 (Fixed)
- （初期リリースのため該当なし）実装における既知の小さな取り扱い改善（.env パースのコメント/クォート処理など）を含む。

### セキュリティ (Security)
- RSS パーサで defusedxml を使用し、外部からの悪意ある XML 攻撃を低減。
- HTTP リダイレクトでの SSRF 対策:
  - リダイレクト先のスキーム検証（http/https のみ許可）。
  - リダイレクト先ホストのプライベートアドレス判定（DNS解決した全 A/AAAA をチェック）。プライベート/ループバック/リンクローカル/マルチキャストは拒否。
- URL 正規化でトラッキングパラメータ（utm_*, fbclid, gclid 等）を除去。
- 外部アクセス系でタイムアウトや最大受信バイト数を設定して DoS を緩和。

### パフォーマンス (Performance)
- J-Quants API 呼び出しでレート制御（固定間隔）を行い API レート制限を遵守。
- ニュース保存はチャンク挿入と単一トランザクションでのコミットを行いオーバーヘッドを削減。
- news_symbols の重複除去とチャンク化により大量挿入時の効率化を図る。

### 既知の制限 / 注意点 (Known issues / Notes)
- ETL の品質チェック実装（kabusys.data.quality）は参照されているが、この差分では品質チェックの具体的実装詳細が含まれていない（将来的な追加を想定）。
- pipeline の一部関数定義が途中で切れている箇所がある（この CHANGELOG は現コードベースからの推測に基づく）。
- NewsCollector の DNS 解決失敗時は安全側（非プライベート）として扱う実装方針で、特定環境での挙動に注意が必要。

---

注: 本 CHANGELOG は提供されたソースコードの内容から推測して作成した初期の変更履歴です。実際のリリース日や運用メモ、ユーザー向けの変更点説明はプロジェクト方針に応じて追記・調整してください。