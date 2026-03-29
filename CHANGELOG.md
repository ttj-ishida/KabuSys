# Changelog

すべての重要な変更をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に従います。  

- リリース日の日付はコード内容の取得日（この CHANGELOG 作成日）を使用しています。
- 記載内容はソースコードから推測した機能・設計意図・エラー処理挙動等に基づきまとめています。

## [Unreleased]

## [0.1.0] - 2026-03-29
最初の公開リリース。日本株自動売買／リサーチ用のコアライブラリを追加。

### Added
- パッケージ初期化
  - kabusys パッケージのエントリポイントを追加（src/kabusys/__init__.py）。
  - パブリック API として data, strategy, execution, monitoring をエクスポートする設定。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
    - 自動読み込みの優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化対応（テスト用）。
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
  - .env のパース機能に対応:
    - export KEY=val 形式、シングル／ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱い等に対応。
  - 上書き挙動:
    - override フラグと protected（OS 環境変数保護）をサポート。
  - Settings クラスを提供（型付きプロパティ）:
    - J-Quants / kabu ステーション / Slack / DB パス等の必須／既定値取得。
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の入力バリデーション。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI：ニュース NLP と市場レジーム判定（src/kabusys/ai/*）
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成。
    - OpenAI（gpt-4o-mini）を用いたバッチセンチメント評価（JSON Mode）。
    - バッチサイズや最大記事文字数、リトライ（429/ネットワーク/5xx）や指数バックオフ等を実装。
    - レスポンスのバリデーション（JSON 抽出・results 構造検証・スコア数値化・クリッピング）。
    - DuckDB への冪等書き込み（該当 date/code の DELETE → INSERT）。部分失敗時に既存スコアを保護する設計。
    - テスト容易性のため _call_openai_api の差し替えを想定。
    - news_nlp.score_news API を公開（書き込み銘柄数を返す）。
  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出。
    - prices_daily, raw_news, market_regime を参照し、計算結果を冪等に market_regime テーブルへ書き込み。
    - OpenAI 呼び出しは専用の内部実装を持ち、リトライ（RateLimit/接続/タイムアウト/5xx）や指数バックオフを実装。
    - API 失敗時は macro_sentiment=0.0 のフェイルセーフを採用（例外を伝搬させず継続）。
    - テスト用に _call_openai_api を差し替え可能。
    - regime_detector.score_regime API を公開（成功時に 1 を返す）。

  - 共通設計方針（AI）
    - モデル gpt-4o-mini を使用、JSON モードで厳密な JSON 応答を期待。
    - レスポンスパース失敗や API エラーは警告記録し安全側のデフォルトを使う設計（フェイルセーフ）。
    - ルックアヘッドバイアス回避のため datetime.today()/date.today() を直接参照しない実装（target_date を必須引数として受ける）。

- リサーチ（src/kabusys/research/*）
  - factor_research モジュール（calc_momentum / calc_volatility / calc_value）
    - Momentum: 1M/3M/6M リターンと 200 日 MA 乖離（ma200_dev）を計算。
    - Volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。
    - Value: raw_financials から最新の EPS/ROE を取り出し PER/ROE を計算（EPS が 0 や欠損の場合は None）。
    - DuckDB を用いた SQL ベース実装で、欠損やデータ不足時は None を返す設計。
  - feature_exploration モジュール（calc_forward_returns / calc_ic / rank / factor_summary）
    - 将来リターン（翌日・翌週・翌月等）を LEAD を使って一括取得。
    - IC（Spearman ρ）をランク相関で計算（最小有効レコード数 3）。
    - rank は同順位の平均ランク計算を実装（浮動小数誤差対策で round を使用）。
    - factor_summary は count/mean/std/min/max/median を計算。
    - pandas 等外部依存無し、標準ライブラリ + duckdb で実装。

- データ管理（src/kabusys/data/*）
  - calendar_management モジュール
    - market_calendar テーブルを基に営業日判定・次/前営業日取得・期間内営業日列挙・SQ日判定等のユーティリティを提供。
    - DB にデータが無いときは曜日ベース（土日除外）でフォールバックする堅牢な設計。
    - calendar_update_job により J-Quants API から差分取得→冪等保存（先読み・バックフィル・健全性チェックあり）。
    - 最大探索範囲の制限（_MAX_SEARCH_DAYS）やバックフィル期間（_BACKFILL_DAYS）、将来日異常検出（_SANITY_MAX_FUTURE_DAYS）を実装。
  - pipeline モジュール / ETL インターフェース（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult dataclass を公開（取得・保存件数、品質チェック結果、発生したエラーを集約）。
    - 差分取得・バックフィル・品質チェック・冪等保存の方針に従った ETL 実装の基盤を用意。
    - テーブルの最大日付取得や存在チェックなどのユーティリティを実装。

- その他
  - 複数モジュールで DuckDB を操作する設計（DuckDBPyConnection を引数に取る関数群）。
  - ロギング（logger）を各モジュールに導入し、警告・情報を適切に出力するよう実装。
  - テストしやすい設計（OpenAI 呼び出しの差し替え等のフックを用意）。

### Changed
- N/A（初回リリースのため該当なし）

### Fixed
- N/A（初回リリースのため該当なし）

### Security
- 外部 API キー（OpenAI、J-Quants 等）は Settings で環境変数から取得する設計。  
  - 必須設定がない場合は ValueError を発生させて明示的に要求する実装。

### Notes / 設計上の重要なポイント（実装上の注意）
- ルックアヘッドバイアス回避:
  - AI スコア・レジーム判定・ファクター計算などすべて target_date ベースで実行し、内部で現在時刻を参照しない方針。
- 冪等性:
  - DB への書き込みは基本的に冪等（DELETE → INSERT、ON CONFLICT 等）を意識した実装。
- フェイルセーフ:
  - 外部 API の失敗時には処理を続行できるデフォルト（例: macro_sentiment=0.0、スコアチャンクのスキップ）を採用。
- テスト支援:
  - OpenAI 呼び出しをモック可能にしてユニットテスト容易化を考慮。
- DuckDB 互換性:
  - executemany への空リストバインド回避、list 型バインドの回避等、DuckDB バージョン差分に配慮した実装。

## 未記載の既知制約 / TODO（推測）
- strategy / execution / monitoring モジュールの具体的な実装は本差分では未提示（パッケージ内で公開はしているが実体は省略されている可能性）。
- 一部外部クライアント（jquants_client 等）はこの差分に含まれていないため、実稼働前に該当クライアントの実装・設定が必要。
- 単体テスト・統合テストの有無はソースからは不明。API 呼び出しのモックは想定されているが、テスト実装は別途必要。

---

以上。必要であれば各モジュールごとの変更（関数一覧、引数、例外挙動、SQL スキーマ想定等）をさらに詳述したバージョンの CHANGELOG を作成します。どのレベルの詳細が必要か教えてください。