# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買プラットフォーム "KabuSys" のコアライブラリを導入。

### Added
- 基本パッケージおよびバージョン情報
  - パッケージエントリポイント: `kabusys.__version__ = "0.1.0"`、公開モジュール: `["data", "strategy", "execution", "monitoring"]`。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数の自動ロード機能（プロジェクトルート: `.git` または `pyproject.toml` を探索）。
  - 自動ロードを無効化するための環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パーサーの実装：`export KEY=val`、シングル/ダブルクォートとバックスラッシュエスケープ、行内コメントの扱いに対応。
  - 上書き制御: `.env` / `.env.local` の優先度処理、既存 OS 環境変数の保護（protected set）。
  - Settings クラス: J-Quants / kabuステーション / Slack / DB パス / 実行環境（KABUSYS_ENV）/LOG_LEVEL のプロパティを提供。未設定必須変数は `ValueError` を送出。
  - デフォルト値: `KABUS_API_BASE_URL`、`DUCKDB_PATH`（data/kabusys.duckdb）、`SQLITE_PATH`（data/monitoring.db）等。

- AI モジュール (`kabusys.ai`)
  - ニュース NLP スコアリング (`news_nlp.score_news`)
    - 指定タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）で raw_news を集計、銘柄ごとに OpenAI (gpt-4o-mini, JSON Mode) にバッチ送信してセンチメントを算出。
    - チャンク処理（最大 20 銘柄/回）、トークン肥大化対策（記事数・文字数トリム）、応答バリデーション、スコアクリップ（±1.0）。
    - リトライ戦略（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）。API 失敗時は該当チャンクをスキップ（フェイルセーフ）。
    - 書き込み: ai_scores テーブルへ置換（DELETE → INSERT、部分失敗時に既存スコアを保護）。
    - テスト容易性: `_call_openai_api` を patch 可能に設計。

  - 市場レジーム判定 (`regime_detector.score_regime`)
    - ETF 1321 の 200 日移動平均乖離 (重み 70%) とマクロニュースの LLM センチメント (重み 30%) を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロニュースは `news_nlp.calc_news_window` に従い抽出。OpenAI 呼び出しは独自実装でモジュール結合を低減。
    - ロバストな API リトライとフォールバック（API失敗時 macro_sentiment=0.0）。
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT、例外時は ROLLBACK）。

- データプラットフォーム (`kabusys.data`)
  - カレンダー管理 (`calendar_management`)
    - JPX カレンダーの夜間差分更新ジョブ（J-Quants から差分取得・保存）。
    - 営業日判定、前後営業日取得、期間内営業日一覧取得、SQ日判定等のユーティリティを実装。
    - DB にカレンダーがない場合は曜日ベースのフォールバックを採用。
    - 安全策: 最大探索範囲 `_MAX_SEARCH_DAYS`、バックフィル `_BACKFILL_DAYS`、整合性チェック `_SANITY_MAX_FUTURE_DAYS`。

  - ETL パイプライン (`pipeline.ETLResult` を `data.etl` で再エクスポート)
    - ETL 実行結果を表す dataclass `ETLResult` を導入（取得/保存件数・品質チェック・エラー一覧等を保持）。
    - 差分取得、保存（jquants_client の idempotent save_* を想定）、品質チェックの設計方針を実装。

- リサーチ/ファクター解析 (`kabusys.research`)
  - ファクター計算 (`factor_research`)
    - Momentum（1M/3M/6M リターン・200日 MA 乖離）、Volatility（20日 ATR、相対 ATR）、Value（PER, ROE）等を DuckDB の SQL と Python で算出。結果は (date, code) をキーとした dict のリストで返却。
    - 欠損やデータ不足時の None ハンドリングを実装。
  - 特徴量探索 (`feature_exploration`)
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（スピアマンランク相関）、ファクターの統計サマリー、ランク変換ユーティリティ等を実装。
    - pandas 等の外部ライブラリに依存しない実装。
  - 研究ユーティリティの公開: `zscore_normalize`（data.stats から）および上記関数を __all__ で再公開。

### Changed
- 設計上の安全性・品質方針の明確化
  - すべての時間判定処理で datetime.today()/date.today() を直接参照せず、外部から target_date を受け取ることでルックアヘッドバイアスを排除。
  - DuckDB の互換性（executemany に空リストを渡さない等）を考慮した実装を採用。
  - OpenAI レスポンス解析では JSON mode の不確実性に対応（前後余計テキストから最外の {} を抽出して復元する等）。
  - API 呼び出しと DB 書き込みは冪等性とトランザクション安全性（BEGIN/COMMIT/ROLLBACK）を優先。

### Fixed / Robustness improvements
- .env 読み込み時の I/O エラーハンドリングと警告出力を追加（ファイルオープン失敗時に warnings.warn）。
- .env パーサーの強化:
  - export プレフィックス対応、クォート内バックスラッシュエスケープ処理、行内コメントの扱いの改善。
  - 空行・コメント行を無視。
- OpenAI 呼び出しでのリトライ振る舞いを詳細化（429/接続/タイムアウト/5xx の場合は指数バックオフ、その他は非リトライ）。
- DB 書き込み失敗時に ROLLBACK に失敗した場合の警告ログを追加（ROLLBACK 失敗を swallow せずログ化）。
- API キー未設定時の早期検出（`score_news` / `score_regime` がキー未設定の場合に `ValueError` を送出）。

### Security
- API キー等の機密情報は Settings 経由で環境変数から取得する設計。必須トークンが未設定の場合は明示的に例外を発生させることで誤動作を防止。

### Breaking Changes
- 初回リリースのため破壊的変更はなし。

---

注記:
- 実装は DuckDB を前提とした SQL / Python ハイブリッドで設計されています。実行には適切なスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等）が必要です。
- OpenAI を利用する箇所は gpt-4o-mini と JSON Mode を想定しており、API のバージョンやレスポンス形式の変化に伴う調整が将来必要になる可能性があります。