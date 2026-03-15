# Changelog

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

注意: 以下の履歴は提供されたコードベースの内容から推測して作成したものであり、コミット履歴や実際のリリースノートと必ずしも一致しない場合があります。

## [Unreleased]

（現時点で未リリースの作業や計画中の項目をここに記載してください）

## [0.1.0] - 2026-03-15

初回リリース（推定）。日本株自動売買システム "KabuSys" のコア骨格を実装。

### 追加 (Added)
- パッケージ初期化
  - パッケージ名: kabusys
  - パッケージ公開API: data, strategy, execution, monitoring を __all__ として公開
  - バージョン: 0.1.0 を src/kabusys/__init__.py に定義

- 環境設定モジュール (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装
  - 自動読み込み機能:
    - プロジェクトルートを .git または pyproject.toml を起点に探索して特定
    - OS環境変数 > .env.local > .env の優先順位で自動ロード
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
  - .env パーサ実装 (`_parse_env_line`)：
    - 空行・コメント行（先頭の #）のスキップ
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応
    - クォートなしの値で `#` がインラインコメントとして扱われる条件の実装（直前が空白/タブのとき）
  - .env 読み込みユーティリティ (`_load_env_file`)：
    - override フラグ、protected キー（OS 環境変数保護）に対応
    - ファイル読み込み失敗時は警告を出力
  - 必須環境変数取得 `_require()` を実装し、未設定時は ValueError を送出
  - 設定プロパティ:
    - J-Quants、kabuステーション、Slack、DBパス（DuckDB/SQLite）、システム設定（KABUSYS_ENV、LOG_LEVEL）
    - env 値および log_level の検証（許容値チェック）
    - is_live / is_paper / is_dev の補助プロパティ

- データスキーマ (src/kabusys/data/schema.py)
  - DuckDB を用いたスキーマ初期化ユーティリティを実装:
    - init_schema(db_path) : 必要に応じて親ディレクトリを作成し、すべてのテーブルとインデックスを作成して接続を返す（冪等）
    - get_connection(db_path) : 既存 DB への接続を返す（スキーマ初期化は行わない）
  - 3層（Raw / Processed / Feature）+ Execution 層に基づくテーブル定義を追加:
    - Raw Layer:
      - raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer:
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer:
      - features, ai_scores
    - Execution Layer:
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して適切な型、NOT NULL 制約、チェック制約（価格 >= 0、サイズ > 0、列挙値の CHECK など）を定義
  - 外部キー制約（news_symbols -> news_articles、orders -> signal_queue、trades -> orders）を定義
  - 頻出クエリを想定したインデックスを複数追加（銘柄×日付、ステータス検索、order_id 等）

- パッケージ構成（プレースホルダ）
  - src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/monitoring/__init__.py を配置（各サブパッケージの骨格）

### 変更 (Changed)
- 初回リリースのため該当なし（ベース実装の追加が中心）

### 修正 (Fixed)
- 初回リリースのため該当なし

### セキュリティ (Security)
- 初回リリースのため該当なし

### 備考 (Notes)
- .env のパース実装は実用的だが、完全な dotenv 仕様（例えば行継続や複雑なエスケープ）を網羅しているわけではない点に注意してください。
- strategy / execution / monitoring サブパッケージは現在はプレースホルダのため、具体的なロジックは今後実装が必要です。
- DuckDB のスキーマは詳細な制約・外部キー・インデックスを含むため、将来のスキーマ拡張時は互換性に注意してください（カラムの追加や変更は既存データに影響を及ぼす可能性があります）。

---

参照:
- パッケージバージョン: 0.1.0（src/kabusys/__init__.py）