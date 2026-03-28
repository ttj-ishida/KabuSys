# Changelog

すべての変更は「Keep a Changelog」形式に準拠しています。  
このプロジェクトはセマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン定義: `__version__ = "0.1.0"`。
  - パッケージ公開インターフェースに以下モジュールを含む: data, strategy, execution, monitoring。

- 環境設定 / 設定管理
  - 環境変数自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local をロード）。
  - .env パーサ実装（コメント、export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント取り扱い等に対応）。
  - 自動読み込みを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - Settings クラスを実装し、アプリケーション設定をプロパティ経由で取得可能に：
    - J-Quants、kabuステーション、Slack、DBパス（duckdb/sqlite）、実行環境（development / paper_trading / live）、ログレベルなど。
  - 必須環境変数未設定時は分かりやすいエラーメッセージを投げる `_require` 実装。
  - env / log_level の値検証（有効値チェック）を実装。

- AI（自然言語処理）機能
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメント分析を行い ai_scores テーブルへ書き込み。
    - 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算用ユーティリティ `calc_news_window` を提供。
    - バッチ処理（1 API コールで最大 20 銘柄）、記事数・文字数上限のトリム機能、JSON Mode を用いた堅牢な入出力を実装。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx 対応）と指数バックオフを実装。
    - レスポンスバリデーション（JSON 抽出、results 配列検査、score 数値検証、コード照合）とスコアの ±1.0 クリップを実装。
    - 部分失敗への影響を最小化するため、スコア取得済みコードのみを DELETE → INSERT で置換する冪等的書き込み。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で market_regime テーブルへ書き込み。
    - LLM 呼び出しは JSON Mode を想定、失敗時は macro_sentiment=0.0 でフォールバックするフェイルセーフ実装。
    - MA 計算は target_date 未満のデータのみを使うことでルックアヘッドバイアスを防止。
    - レジーム判定は閾値に基づき "bull"/"neutral"/"bear" を付与し、冪等性のある DB トランザクション（BEGIN / DELETE / INSERT / COMMIT）で保存。

  - テスト容易性の考慮
    - OpenAI 呼び出し部分（内部関数 `_call_openai_api`）はユニットテスト時に差し替え可能に設計（patch可能）。

- リサーチ（特徴量・ファクター）
  - ファクター計算モジュール（kabusys.research.factor_research）
    - Momentum: mom_1m / mom_3m / mom_6m（営業日ベース）、ma200_dev（200日MA乖離）。
    - Volatility / Liquidity: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）。
    - Value: PER、ROE（raw_financials から最新の報告を結合）。
    - DuckDB を用いた SQL ベースの実装。データ不足時は None を返す堅牢な設計。

  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）：任意ホライズン（デフォルト [1,5,21]）に対応。入力バリデーションあり。
    - IC（Information Coefficient）計算（calc_ic）：スピアマンのランク相関（ランクは同順位を平均ランクで処理）。
    - rank, factor_summary（count/mean/std/min/max/median）等の統計ユーティリティを実装。
    - pandas 等に依存せず標準ライブラリ＋DuckDBで完結する設計。

- データ基盤（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar テーブルを参照し営業日判定 API を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データがない場合は曜日ベースでフォールバック（週末を非営業日扱い）。
    - カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装し、J-Quants クライアント経由で差分取得 → 冪等的セーブを実行。
    - バックフィル、健全性チェック（極端な将来日付検出）を実装。

  - ETL パイプライン（pipeline / etl）
    - ETLResult を導入し、ETL 実行結果（取得・保存件数、品質チェック結果、エラーリストなど）を構造化して返却可能に。
    - 差分更新・バックフィル・品質チェックを想定した設計（外部 jquants_client / quality モジュールと連携するインターフェース）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / 設計上の重要点
- ルックアヘッドバイアス防止: 各スコアリング / 計算処理で datetime.today()/date.today() を直接参照せず、必ず target_date を引数で受ける設計。
- フェイルセーフ: LLM 呼び出しが失敗しても例外を上位に伝播させず、スコアを中立（0.0）にフォールバックする箇所がある（ニュース/レジーム判定）。
- DB 書き込みの冪等性を重視: 部分失敗時に既存データを不用意に消さないため、対象コードを限定した DELETE → INSERT を採用。
- テスト容易性: 内部の外部API呼び出し箇所はモック／パッチで差し替え可能に実装。

---

（将来的なリリースでは [Unreleased] セクションに変更点を記載し、リリース時にバージョンと日付を追加してください。）