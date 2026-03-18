# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/

## [Unreleased]

### Added
- パッケージ初期化とバージョン定義
  - src/kabusys/__init__.py によるパッケージエントリポイントと __version__ = "0.1.0" の追加。
- 環境変数・設定管理
  - src/kabusys/config.py を追加。
  - .env ファイル（.env, .env.local）および環境変数からの自動ロード機能を実装（プロジェクトルートの探索は .git / pyproject.toml を使用）。
  - export 形式の行、クォートやエスケープ、コメント付き行などを考慮した .env パーサー実装。
  - 設定の必須チェック（_require）と各種プロパティ（J-Quants トークン、kabu API 設定、Slack、DB パス、実行環境・ログレベル判定）を提供。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py を追加。
  - 日足（fetch_daily_quotes）、財務諸表（fetch_financial_statements）、取引カレンダー（fetch_market_calendar）を取得する API 呼び出しを実装（ページネーション対応）。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
  - 再試行（指数バックオフ、最大 3 回）、ステータスコード（408, 429, >=500）に対するリトライ対応を実装。
  - 401 Unauthorized 到達時の自動トークンリフレッシュを 1 回まで行いリトライを実施。
  - get_id_token によりリフレッシュトークンから id_token を取得する実装。
  - DuckDB へ冪等に保存する save_* 関数群（save_daily_quotes, save_financial_statements, save_market_calendar）を実装し、ON CONFLICT ... DO UPDATE による重複排除を実施。
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead bias を抑制。
  - 型変換ユーティリティ（_to_float, _to_int）を実装し不正値耐性を持たせた保存処理。
- ニュース収集（RSS）
  - src/kabusys/data/news_collector.py を追加。
  - RSS フィード取得（fetch_rss）、XML パース（defusedxml を使用）および記事前処理機能を実装。
  - 記事IDは URL 正規化後の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を担保。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）を実装。
  - SSRF 対策を複合的に導入:
    - URL スキーム検証（http/https のみ許可）
    - ホストのプライベート/ループバック/リンクローカル判定（IP 直接判定と DNS 解決による判定）
    - リダイレクト時にスキーム・ホストを検査するカスタムリダイレクトハンドラ（_SSRFBlockRedirectHandler）
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES）と gzip 解凍後の検査によるメモリ DoS 対策
  - DB 保存はトランザクションでまとめ、チャンク単位のバルク挿入（INSERT ... RETURNING）で実際に挿入された ID を返す（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - テキスト前処理（URL 除去・空白正規化）と本文＋タイトルからの銘柄コード抽出（4桁数字、既知コードフィルタリング）を実装。
  - デフォルト RSS ソースとして Yahoo Finance のカテゴリフィードを設定。
- DuckDB スキーマ管理
  - src/kabusys/data/schema.py を追加。
  - Raw/Processed/Feature/Execution 層に分けたテーブル定義を実装（raw_prices, raw_financials, raw_news, market_calendar, prices_daily, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など多数）。
  - 各テーブルに適切な型チェック・制約（CHECK、PRIMARY KEY、FOREIGN KEY）を追加。
  - 頻出クエリに備えたインデックス定義を追加。
  - init_schema(db_path) により DB ファイルの親ディレクトリ自動作成とテーブル初期化を行う。
  - get_connection() で既存 DB への接続を提供。
- ETL パイプライン基盤
  - src/kabusys/data/pipeline.py を追加。
  - 差分更新のためのヘルパー群（最終取得日の取得、営業日調整、バックフィル日数適用など）を実装。
  - run_prices_etl 等の個別 ETL ジョブの骨組みを実装（差分取得→保存のフローを想定）。
  - ETL 結果を表すデータクラス ETLResult を追加し、品質チェック結果やエラーを集約して返却できる設計。
  - デフォルトバックフィル日数、カレンダー先読み等の運用パラメータを定義。
  - 品質チェック（quality モジュール）との連携を想定するインターフェースを準備（実際の quality 実装は外部想定）。
- パッケージ構造
  - data, strategy, execution, monitoring の各サブパッケージ用 __init__.py を配置（将来的な拡張ポイント）。

### Changed
- （初期リリース）設計原則と実装で以下を重視:
  - API レート制限遵守、再試行ロジック、トークン自動リフレッシュ。
  - データ取得日時の記録（fetched_at）による監査性・Look-ahead 防止。
  - DB 保存の冪等性（ON CONFLICT）とトランザクション管理。

### Security
- RSS/XML 周りでの安全対策を実装:
  - defusedxml を用いた XML パースで XML Bomb 等の攻撃を軽減。
  - SSRF 防止（スキーム検証、プライベート IP 検出、リダイレクト時検査）。
  - レスポンス受信上限（MAX_RESPONSE_BYTES）によるメモリ DoS 対策。

### Performance
- API 呼び出しに対する固定間隔レートリミッタを実装（_RateLimiter）。
- ニュース保存・銘柄紐付けはチャンク単位のバルク INSERT を用い挿入回数を削減。
- DuckDB の接続/トランザクションを活用して I/O オーバーヘッドを低減。

### Internal / Refactor
- 多数のユーティリティ関数（URL 正規化、パース、型変換、テーブル存在確認など）を実装し再利用性を向上。
- ロギングを各モジュールに埋め込み、処理状況・警告を出力する設計。

---

## [0.1.0] - 2026-03-18

初期公開リリース（パッケージ基盤）

### Added
- 上記 Unreleased に記載した全機能をこのバージョンに含む:
  - 設定管理、J-Quants クライアント、ニュースコレクタ、DuckDB スキーマ、ETL パイプライン骨格、セキュリティ対策、ユーティリティ群。
- ドキュメント的な docstring を各モジュールに整備（関数の目的、引数、戻り値、例外の説明）。

### Known issues / TODO
- strategy, execution, monitoring パッケージはプレースホルダ（空の __init__）であり、実際の戦略・発注ロジックは未実装。
- quality モジュールへの依存はインターフェースを想定しているが、実運用向けの品質チェック実装・ルール整備が必要。
- 一部関数（ETL の個別ジョブ等）は追加のユニットテストとエッジケース検証が必要。
- 外部 API（J-Quants）や RSS ソースの変化に対する互換性テストが今後必要。
- 運用時のシークレット保護（.env の扱い、ロギングの秘匿）は運用ガイドラインを整備することを推奨。

---

メジャー/マイナー/パッチの運用方針やリリース頻度については別途リリースポリシーを策定してください。必要であれば、各機能ごとの変更点をより詳細に分割して記載します。