# Changelog

このファイルは Keep a Changelog の仕様に従って管理されています。
配布バージョン: 0.1.0

すべての変更は主にコードベースから推測して記載しています。

## [0.1.0] - 2026-04-03

初期リリース。主要なサブモジュールと機能を追加。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージ公開 API: data, strategy, execution, monitoring（__all__）。
- 設定管理 (.env / 環境変数)
  - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml で検出）。
  - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサーの強化:
    - export プレフィックス対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - インラインコメントの扱い（クォート有無での判定ルール）。
  - .env 読み込みで OS 環境変数を保護する protected キーセットの概念（.env.local は既存 OS 環境変数を上書きしない）。
  - Settings クラスを提供（settings インスタンス）:
    - J-Quants / kabuステーション / LINE / DB / 監視 / システム関連のプロパティを環境変数から取得。
    - path の Path 型変換（duckdb/sqlite/pid/killflag 等）。
    - ブール・数値変換や既定値の設定。
    - 環境値検証: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL の検証。
    - 必須値未設定時は明示的な ValueError を送出（_require）。

- AI モジュール
  - kabusys.ai.news_nlp
    - raw_news / news_symbols から銘柄別に記事を集約し、OpenAI (gpt-4o-mini) によりセンチメントを算出して ai_scores テーブルへ書き込む処理を実装。
    - 時間ウィンドウ計算（JST 前日 15:00 〜 当日 08:30 を UTC に変換）。
    - 1銘柄あたり記事数・文字数上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）によるトリム。
    - チャンク単位（最大 _BATCH_SIZE=20）での API 呼び出し。
    - JSON Mode での厳密なレスポンス期待とレスポンス復元ロジック（前後余計テキストから最外の {} を抽出してパース）。
    - レスポンス検証（results 配列、code と score の存在と型検証、score を ±1.0 にクリップ）。
    - リトライ/バックオフ戦略（429/ネットワーク断/タイムアウト/5xx に対して指数バックオフ、最大試行回数）。
    - 部分失敗時の DB 保護（DELETE→INSERT をコード絞り込みで実行し、他コードの既存スコアを保持）。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api を patch 可能）。
  - kabusys.ai.regime_detector
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - マクロ記事フィルタリング（複数の日本/米国マクロキーワード）と LLM によるマクロセンチメント評価（gpt-4o-mini、JSON 出力）。
    - ma200_ratio 計算は target_date 未満のデータのみを使用（ルックアヘッド防止）。
    - API 失敗やパース失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - 冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT、エラー時は ROLLBACK を試行）。
    - API キー注入（api_key 引数または環境変数 OPENAI_API_KEY）。
    - リトライ/バックオフ処理と 5xx 判定の扱い。

- 研究（Research）モジュール
  - kabusys.research.factor_research
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均出来高/売買代金）、バリュー（PER/ROE）等のファクター計算関数を実装。
    - DuckDB を用いた SQL ベースの実装（prices_daily / raw_financials 参照）。
    - データ不足時の None 扱い、結果は辞書リストで返却（date, code を含む）。
  - kabusys.research.feature_exploration
    - 将来リターン計算（calc_forward_returns）：指定ホライズン（デフォルト [1,5,21]）のリターンを一括取得。
    - IC（Information Coefficient）計算（calc_ic）：スピアマンのランク相関による評価、レコード不足時は None。
    - rank ユーティリティ（同順位は平均ランク、float の丸め対策あり）。
    - factor_summary（基本統計量：count/mean/std/min/max/median）を標準ライブラリのみで実装。
    - いずれも外部依存（pandas 等）なしで実装。

- データ（Data）モジュール
  - kabusys.data.calendar_management
    - market_calendar を基にした営業日判定と補助関数を提供：
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB の calendar データがない場合は曜日（土日）ベースでフォールバック。
    - next/prev_trading_day の探索上限（_MAX_SEARCH_DAYS）を設定して無限ループ回避。
    - 夜間バッチ calendar_update_job を追加（J-Quants API から差分取得し save するロジック、バックフィル、健全性チェックあり）。
  - kabusys.data.pipeline / etl
    - ETLResult データクラスを公開（ETL の取得数／保存数／品質問題／エラー概要を保持）。
    - pipeline モジュールに基づく ETL 設計（差分取得、品質チェック、idempotent 保存、backfill の扱い等）。
    - ETLResult.to_dict() で品質問題をシリアライズ可能に。

- テスト向け・実装配慮
  - OpenAI 呼び出し箇所を patch 可能にしユニットテストで差し替えられる設計。
  - DuckDB 互換性のため executemany の空リスト回避などの細かな実装（DuckDB 0.10 対応）。
  - ルックアヘッドバイアス対策として datetime.today()/date.today() を直接参照しない設計方針が複数モジュールで徹底。

### 変更 (Changed)
- 該当なし（初回リリースのため）。

### 修正 (Fixed)
- 該当なし（初回リリースのため）。

### 削除 (Removed)
- 該当なし（初回リリースのため）。

### 非推奨 (Deprecated)
- 該当なし。

### セキュリティ (Security)
- 該当なし。

---

注記:
- 上記はソースコードから推測して記載した変更点です。実際のリリースノートやユーザ向けドキュメントでは、API の安定度、互換性、既知の制限事項（OpenAI モデル依存、DuckDB バージョン依存など）を明確に追記することを推奨します。