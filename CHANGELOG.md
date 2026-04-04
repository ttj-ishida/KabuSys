# Changelog

すべての重要な変更点は Keep a Changelog の形式で記載します。  
このファイルでは、パッケージの主要なリリース内容・仕様・設計上の振る舞いをコードベースから推測してまとめています。

フォーマット:
- Added: 新規追加された機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated / Removed / Security: 該当があれば記載

## [Unreleased]
（未リリースの変更はここに記載）

---

## [0.1.0] - 2026-04-04

初期公開リリース。日本株の自動売買・データ基盤・リサーチ用ユーティリティを含む初回機能セットを提供します。

### Added
- パッケージメタ情報
  - kabusys パッケージ初期バージョン（__version__ = 0.1.0）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ でエクスポート。

- 環境設定管理（kabusys.config）
  - .env/.env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env パース実装:
    - コメント行（#）・export KEY=val 形式対応。
    - シングル/ダブルクォート内のエスケープシーケンス処理やインラインコメント無視処理。
    - クォートなし値のインラインコメント判定（直前がスペース/タブの場合に # をコメントとして扱う）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラス:
    - J-Quants / kabuステーション / LINE / DB パス / 監視閾値などのプロパティを提供。
    - 必須環境変数未設定時は ValueError を発生（_require）。
    - 環境（development/paper_trading/live）やログレベルのバリデーション。

- AI 関連機能（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いて銘柄別にニュースを集約。
    - 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window。
    - 銘柄ごとの記事トリム（記事数・文字数上限）とバッチ（最大 20 銘柄）で OpenAI に送信。
    - JSON Mode を利用したレスポンスパース・バリデーション（results 配列・code と score の検証）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
    - スコアは ±1.0 にクリップ。部分失敗に対応するため ai_scores への書き込みは対象コードのみ DELETE→INSERT（冪等性確保）。
    - score_news(conn, target_date, api_key=None) により ai_scores へ書き込み、書き込み件数を返却。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して market_regime に日次で書き込み。
    - レジーム判定フローの実装（ma200_ratio 計算・ニュース抽出・OpenAI 呼び出し・合成・ラベル化）。
    - OpenAI 呼び出しは gpt-4o-mini、JSON 形式出力を想定。API エラー時は macro_sentiment = 0.0 として継続（フェイルセーフ）。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理。失敗時は ROLLBACK を試行。
    - score_regime(conn, target_date, api_key=None) を提供。

  - AI クライアント呼び出しはテスト容易性を考慮して _call_openai_api を抽象化（ユニットテストで差し替え可能）。

- データ基盤ユーティリティ（kabusys.data）
  - 市場カレンダー管理（calendar_management）
    - market_calendar を元に is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - market_calendar が未取得の場合は曜日ベース（土日を非営業日）でフォールバック。
    - カレンダー差分更新ジョブ calendar_update_job(conn, lookahead_days) を実装（J-Quants クライアント経由で取得・保存・バックフィル・健全性チェック）。
    - DB 登録を優先し、未登録日は曜日フォールバックで一貫した挙動を保証。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) による無限ループ回避。

  - ETL パイプライン（pipeline）
    - ETLResult データクラスを実装（取得件数・保存件数・品質チェック結果・エラー等を保持）。
    - 差分取得・バックフィル・品質チェック設計方針を実装に反映（jquants_client と quality モジュールを利用）。
    - kabusys.data.etl モジュールは ETLResult をエクスポート。

- リサーチ/ファクター分析（kabusys.research）
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials を参照）。
    - Momentum: 1M/3M/6M リターンおよび 200 日 MA 乖離。
    - Volatility/Liquidity: 20 日 ATR、相対 ATR、平均売買代金・出来高比率。
    - Value: PER／ROE（raw_financials の最新レコードを参照）。
    - DuckDB SQL とウィンドウ関数を活用した実装。データ不足時は None を返却。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。horizons の妥当性チェックあり。
    - calc_ic: スピアマンランク相関（IC）計算（ランクは平均ランク／同順位は平均ランク処理）。
    - rank: 値→ランク変換（round(..., 12) による ties の扱い）。
    - factor_summary: count/mean/std/min/max/median を算出するユーティリティ。
  - 研究用モジュール群を一括エクスポート（__all__ に calc_momentum 等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / 設計上の重要事項
- ルックアヘッドバイアス対策:
  - すべての処理で datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取る設計。
  - DB クエリでは target_date 未満／排他条件などを用いてルックアヘッドを防止。
- フェイルセーフ設計:
  - 外部 API（OpenAI / J-Quants）失敗時は例外をすべて上げるのではなく、可能な範囲でフォールバックやスキップを行い、処理を継続する実装が意図されている（ログ出力を伴う）。
- 冪等性:
  - DB への保存は DELETE → INSERT、または ON CONFLICT を想定した冪等書き込みを行う実装（ETL / calendar / ai スコア書き込み）。
- テスト容易性:
  - OpenAI API 呼び出しを内部関数で切り出しており、ユニットテスト時にモック差し替え可能。
- DuckDB 前提:
  - 多くの処理は DuckDB 接続（DuckDBPyConnection）を前提としている。executemany の空リスト制約（DuckDB 0.10 対応）等を考慮している。

### Known limitations / TODO（コードから推測）
- strategy, execution, monitoring パッケージの実体は公開 API に列挙されているが、この差分では詳細実装は含まれていない（将来的な拡張対象）。
- PBR・配当利回りなど一部バリューファクターは未実装（calc_value で注記あり）。
- OpenAI モデルや API 制限に関するレート管理は基本的リトライによる回復を試みるが、大規模運用時の追加設計（キューイング・バックプレッシャー等）が必要になる可能性あり。

---

参照:
- 本 CHANGELOG はソースコード（src/kabusys 以下）から機能・設計を推測して作成しています。実際の変更履歴はバージョン管理のコミットログやリリースノートを併せて確認してください。