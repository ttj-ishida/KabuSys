# Changelog

すべての注目すべき変更を記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-28

初回公開リリース。日本株自動売買システム KabuSys の基盤的機能をまとめて実装しました。主な追加点・設計方針は以下の通りです。

### Added
- パッケージ基盤
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"`。主要サブパッケージを `__all__` に公開（data, strategy, execution, monitoring）。
- 設定管理
  - 環境変数／.env の読み込みユーティリティ (`kabusys.config`) を実装。
    - .env/.env.local ファイル自動読み込み（プロジェクトルートは `.git` または `pyproject.toml` を基準に探索）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
    - `.env` のパースはコメント、クォート、エスケープ、`export KEY=val` 形式に対応。
    - `.env.local` は `.env` の上書きとして読み込まれる（OS 環境変数は保護）。
  - `Settings` クラスを追加。必要な設定プロパティを提供（J-Quants、kabu API、Slack、DB パス、環境種別、ログレベル等）。`KABUSYS_ENV` と `LOG_LEVEL` の値検証を実装。
- データプラットフォーム（DuckDB ベース）
  - ETL パイプライン基盤 (`kabusys.data.pipeline`) と結果クラス `ETLResult` を実装。
    - 差分取得・バックフィル・品質検査を想定した設計。
    - ETL 結果を辞書化する `to_dict()` を提供（品質問題はサマリ化して出力）。
  - カレンダー管理モジュール (`kabusys.data.calendar_management`)
    - JPX カレンダー管理ロジック（market_calendar テーブルの扱い、営業日判定、next/prev/get_trading_days、SQ 判定）。
    - カレンダー未取得時は曜日ベースのフォールバック（週末を休日扱い）。
    - 夜間更新ジョブ `calendar_update_job`：J-Quants から差分取得し冪等保存、バックフィル／健全性チェック実装。
- 研究（Research）モジュール
  - ファクター計算群 (`kabusys.research.factor_research`)
    - Momentum、Value、Volatility（ATR 等）、Liquidity 指標などを DuckDB SQL で計算する関数を実装（calc_momentum / calc_value / calc_volatility）。
    - 計算結果を (date, code) をキーとする辞書リストで返す設計。
  - 特徴量探索（`kabusys.research.feature_exploration`）
    - 将来リターン計算（calc_forward_returns）
    - IC（Information Coefficient）計算（calc_ic）
    - ファクター統計サマリ（factor_summary）
    - ランク変換ユーティリティ（rank） — 同順位は平均ランク扱い、丸めで ties の判定を安定化。
  - 研究用モジュール公開インターフェースをまとめた `kabusys.research.__init__`。
- AI（ニュース NLP / レジーム判定）
  - ニュースセンチメントスコアリング (`kabusys.ai.news_nlp`)
    - raw_news / news_symbols を集約して銘柄ごとにテキストを作成し、OpenAI（gpt-4o-mini）の JSON Mode でバッチ評価。
    - バッチ処理（1回最大 20 銘柄）、1 銘柄あたり記事数・文字数制限（トリム）を実装。
    - レスポンスの厳格バリデーション（JSON 抽出、results 配列、code/score 検証、スコアの有限性判定、±1.0 クリップ）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライ。非リトライエラーは該当チャンクスキップで継続。
    - スコア保存時は影響範囲を限定するため、取得済みコードのみを DELETE→INSERT で置換（DuckDB の executemany の挙動を考慮）。
    - テスト容易性のため API 呼び出し関数 `_call_openai_api` を patch 可能に設計。
  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321（Nikkei-linked ETF）の 200 日 MA 乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し `market_regime` テーブルへ冪等書き込み。
    - マクロニュース抽出はキーワードベース（デフォルトリストあり）。記事なしは LLM 呼び出しを行わず macro_sentiment = 0.0 を使用。
    - OpenAI 呼び出しはリトライロジックと JSON パースの耐性を持つ。API 失敗時はフォールバックして処理継続。
- ユーティリティと堅牢化
  - DuckDB を想定した SQL 実装で、空リストを executemany に渡さない等の互換性配慮を実装。
  - ルックアヘッドバイアス対策：各処理は内部で datetime.today()/date.today() に直接依存せず、target_date を明示的に受け取る設計。
  - DB 書き込みは冪等性（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK）を確保。例外発生時は ROLLBACK を試みるが失敗もログ出力して再送出。
  - ロギングと警告を充実させ、データ不足や API エラー時のフォールバック動作を明示。

### Changed
（初回リリースのため該当なし）

### Fixed
（初回リリースのため該当なし）

### Security
- 環境変数の自動読み込み時に OS 環境変数を上書きしない仕組みを導入（protected set）。`.env.local` は明示的に override を許容するが、既存の OS 環境変数は保護される。

### Notes / Design Decisions
- 外部 API（OpenAI / J-Quants / kabu API）はクライアント注入やエラーハンドリングを想定し、処理の継続性を重視（フェイルセーフ）。部分失敗で他データを毀損しない手順を採用。
- DuckDB のバージョン互換性を考慮した実装（executemany の空リスト回避等）。
- テスト容易性のため、API 呼び出し関数をモジュール内で分離（モック差し替え可能）している。

---

（今後のリリースではバグ修正・機能追加・API 互換対応等を個別に記載します）