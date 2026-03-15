# Changelog

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog の形式に準拠します。

なお、この CHANGELOG は与えられたコードベースの内容から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回公開リリース

### Added
- パッケージ基盤
  - kabusys パッケージを追加。パッケージバージョンは 0.1.0。
  - パッケージの公開 API として data, strategy, execution, monitoring モジュールを明示的にエクスポート（src/kabusys/__init__.py）。

- 環境変数・設定管理（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートを検出するために .git または pyproject.toml を上位ディレクトリから探索する実装を追加（__file__ を起点に探索するため CWD に依存しない）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能（テスト用途等の配慮）。
    - 読み込み優先順位は OS 環境変数 > .env.local > .env。
    - OS 環境変数は protected として扱い、.env の上書きを防止。
  - .env のパース機能を実装（_parse_env_line）
    - コメント行（#）や空行を無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォートで囲まれた値の解析に対応し、バックスラッシュによるエスケープを解釈。
    - クォートなし値では、スペース/タブの直前にある '#' をコメント開始とみなすロジックを実装（一般的な .env の取り扱いに近づける挙動）。
    - 無効行（キーなし、等）はスキップ。
  - .env 読み込み時の例外を警告として処理（ファイル読み込み失敗時に warnings.warn）。
  - 設定取得用 Settings クラスを実装（settings インスタンスを公開）
    - J-Quants, kabuステーション API, Slack, DB パスなど主要設定をプロパティとして提供。
    - 必須設定は _require 関数により未設定時に ValueError を送出（利用者へ明示的に通知）。
    - デフォルト値を持つ設定（KABUS_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等）をサポート。
    - KABUSYS_ENV 値の検証（development, paper_trading, live のいずれかのみ許容）と補助プロパティ（is_live, is_paper, is_dev）を追加。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

- DuckDB スキーマと初期化（src/kabusys/data/schema.py）
  - 3 層（Raw / Processed / Feature）に加え Execution レイヤーを含むデータスキーマを定義。
    - Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions
    - Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature レイヤー: features, ai_scores
    - Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して適切な型・制約（PRIMARY KEY、CHECK、FOREIGN KEY）を定義：
    - 例: prices_daily の low <= high チェック、orders/trades といったテーブル間の外部キー制約等。
  - パフォーマンス向上のためのインデックス定義を追加（銘柄×日付スキャン、ステータス検索等の想定クエリパターンに対応）。
  - DB 初期化ユーティリティを提供
    - init_schema(db_path): 指定 DuckDB ファイルに対してスキーマとインデックスを作成。冪等（既存テーブルはスキップ）。
      - db_path がファイルの場合、親ディレクトリが存在しなければ自動作成。
      - ":memory:" を指定するとインメモリ DB を使用。
    - get_connection(db_path): 既存の DuckDB への接続を返す（スキーマ初期化は行わないため、初回は init_schema を推奨）。

### Documentation
- ソースコード内にモジュールの簡単な説明コメントや DataSchema.md 参照の記述を追加（スキーマ設計に関する外部ドキュメント参照が示されている）。

### Notes / Design decisions
- .env 自動ロードはプロジェクトルート検出に依存するため、パッケージ配布後でも適切に動作するように設計されている（作業ディレクトリに依存しない）。
- OS 環境変数の上書きを防ぐ protected 設計によりローカル .env による意図しない上書きを回避。
- スキーマは運用上の整合性を保つため多くのチェック制約を備え、実運用でのデータ品質を想定した設計になっている。

## 未対応（今後検討）
- マイグレーション機構（スキーマ変更履歴の管理）は未実装。スキーマ更新時は init_schema のみに依存しているため、将来的にマイグレーション戦略を追加することが望まれる。
- settings のユニットテストおよび .env パースロジックの細かいエッジケース検証（複雑なエスケープや改行を含む値等）。
- strategy、execution、monitoring モジュールの具体的な実装（現在はパッケージ構造のみ用意）。

---

追記: 本 CHANGELOG はコードベースから推測して作成したものであり、実際の変更履歴やリリースノートとは差異が生じる可能性があります。必要であれば、変更点の詳細（コミット単位や作者、チケット番号など）を含めて更新できます。