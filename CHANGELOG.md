# CHANGELOG

すべての注目すべき変更点をここに記録します。本プロジェクトは Keep a Changelog の形式に準拠しています。  

注: 初期リリースはバージョン 0.1.0 です。

目次
- [Unreleased](#unreleased)
- [0.1.0 - 2026-03-29](#010-2026-03-29)

## [Unreleased]
（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-29

初期リリース。日本株自動売買システムのコアライブラリを提供します。主な機能・モジュール、設計上の注意点、外部依存や挙動の要点を以下にまとめます。

### Added
- パッケージ基盤
  - kabusys パッケージ初期版を追加。公開 API として `data`, `strategy`, `execution`, `monitoring` を __all__ に定義（実装ファイル群は段階的に追加予定）。
  - バージョン文字列: `__version__ = "0.1.0"`。

- 環境設定管理（kabusys.config）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは `.git` または `pyproject.toml` を基準に解決）。自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能。
  - .env パーサはシェルスタイル（export句、シングル/ダブルクォート、エスケープ、インラインコメント）に対応する堅牢な実装を提供。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / ログレベル / 実行環境（development/paper_trading/live）等を環境変数から取得するプロパティを用意。必須値未設定時は ValueError を送出。
  - OS 環境変数の保護（.env の上書き制御）を考慮した読み込みロジックを実装。

- データ処理（kabusys.data）
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - 差分取得・バックフィル・保存・品質チェックの設計を反映した ETLResult 型を実装（エラー・品質問題の集約、辞書化メソッドを含む）。
    - DuckDB を用いた最大日付取得やテーブル存在チェック等のユーティリティを追加。
  - ETLResult を公開インターフェースとして再エクスポート（kabusys.data.etl）。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間差分更新ジョブ（calendar_update_job）を追加。J-Quants クライアント経由で差分取得し、冪等的に保存する設計。
    - 営業日判定 / 翌営業日 / 前営業日 / 期間の営業日取得 / SQ判定等のユーティリティを提供。DB にデータがない場合は曜日ベースのフォールバックを行う。
    - 最大探索日数やバックフィル、健全性チェック（将来日付の異常検出）を実装。

- 研究・分析機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER/ROE）を DuckDB SQL を用いて計算する関数を実装。データ不足時の挙動（None を返す等）を明示。
    - 全関数は prices_daily / raw_financials のみ参照し、外部 API を呼ばない設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応・入力検証あり）。
    - IC（Information Coefficient, Spearman ランク相関）の計算（calc_ic）。データ不足時は None を返す。
    - ランク変換（rank）とファクター統計サマリー（factor_summary）を実装。外部ライブラリに依存しない純 Python 実装。

- AI / NLP 機能（kabusys.ai）
  - ニュースセンチメント（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとのニュースを LLM（gpt-4o-mini）へバッチ送信してセンチメントスコアを ai_scores テーブルへ書き込む処理（score_news）。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算するユーティリティ (calc_news_window)。
    - バッチサイズ、記事数・文字数制限、JSON Mode のレスポンス検証、リトライ (429/ネットワーク/5xx) と指数バックオフ、部分失敗時の DB 保護（対象コードのみ DELETE→INSERT）など堅牢性を考慮。
    - レスポンスパースとバリデーションに堅牢なロジックを実装（未知コードの無視、数値変換・有限値チェック、スコアクリッピング ±1.0）。
    - テスト容易性のため OpenAI 呼び出しポイントを個別関数化し、モック差し替え可能。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、ニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を計算し、market_regime テーブルへ冪等書き込みする関数（score_regime）を実装。
    - マクロキーワードで raw_news をフィルタし、LLM（gpt-4o-mini）で -1.0〜1.0 の JSON スコアを要求。API 失敗時にはフェイルセーフで macro_sentiment = 0.0 を使用。
    - LLM 呼び出しに対してリトライと指数バックオフを実装。DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等パターン、失敗時には ROLLBACK する。

### Changed
- （該当なし — 初期リリースのため変更履歴はありません）

### Fixed
- （該当なし — 初期リリースのため修正履歴はありません）

### Removed
- （該当なし）

### Security
- OpenAI API キーの扱い
  - OpenAI キーは関数引数で注入可能（api_key 引数）か環境変数 `OPENAI_API_KEY` を使用。未設定時は ValueError を送出して明確にエラー化。
- 環境変数の自動読み込みはデフォルトで有効だが、テスト用途等での無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供。
- .env ファイル読み込み時に既存 OS 環境変数を保護する仕組みを導入。

### Notable implementation / runtime behaviors
- DuckDB を主要なローカルデータストアとして想定（関数は duckdb.DuckDBPyConnection を受け取る）。
- 各種計算関数はルックアヘッドバイアスを避ける設計（内部で datetime.today()/date.today() を参照せず、明示的な target_date を受け取る）。
- API 呼び出しに関するポリシー
  - リトライ対象としないケース（クライアント・アプリケーションはログを確認し適切に対応）。
  - LLM レスポンスのパース失敗や API 永久失敗時はフェイルセーフ値（0.0 等）を使用し処理を続行する箇所あり。
- DB 書き込みは可能な限り冪等に設計（DELETE→INSERT、ON CONFLICT 相当、トランザクションでの COMMIT/ROLLBACK を使用）。
- DuckDB の executemany の実装制約への対応（空リスト渡し回避）を実装。

### Testing / Mocks
- OpenAI 呼び出しは内部関数化されており、ユニットテストでは `unittest.mock.patch` によって差し替え可能（kabusys.ai.news_nlp._call_openai_api / kabusys.ai.regime_detector._call_openai_api）。

---

今後のリリースでは以下のような点の充実を想定しています（計画例）:
- strategy / execution / monitoring の具体実装の追加・公開
- DB スキーマのマイグレーションツールや初期化ヘルパー
- より詳細な監視・アラート機能（Slack 通知連携の実装）
- パフォーマンス改善や大規模データ向けの最適化

問い合わせ・報告はリポジトリの issue をご利用ください。