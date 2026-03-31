# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠します。

フォーマット:
- 変更はカテゴリ（Added / Changed / Fixed / Security / Removed）ごとに分類しています。
- 各項目はコードベースから推測できる実装内容・設計方針・ユーザーに影響する注意点を含みます。

## [Unreleased]

（現時点で未リリースの変更はありません。）

## [0.1.0] - 2026-03-31

初期リリース。日本株自動売買プラットフォーム（kabusys）のコア機能をまとめた最初のバージョン。

### Added
- パッケージ基礎
  - パッケージ初期化: kabusys パッケージのエントリポイントを追加（バージョン: 0.1.0）。
  - __all__ に data, strategy, execution, monitoring を公開。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定値を安全に読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
    - プロジェクトルート検出は __file__ の親ディレクトリから .git もしくは pyproject.toml を探索して行う（CWD 非依存）。
  - .env パーサ実装: export 形式、クォート、エスケープ、コメント処理をサポート。
  - 環境変数保護: .env の読み込み時に OS 環境変数を保護する仕組み（protected）。
  - Settings クラスを提供し、アプリ設定をプロパティ経由で取得可能。
    - 必須変数取得時は未設定なら ValueError を送出する _require を実装。
    - 提供される設定例:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN（必須）
      - SLACK_CHANNEL_ID（必須）
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV（development / paper_trading / live の検証）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - 環境（is_live, is_paper, is_dev）を判定するユーティリティプロパティを実装。

- AI サブシステム（kabusys.ai）
  - ニュースセンチメント（news_nlp）
    - raw_news / news_symbols を集約して銘柄別に記事をまとめ、OpenAI（gpt-4o-mini）を用いてセンチメントを評価。
    - バッチ処理: 最大 20 銘柄 / リクエスト、1 銘柄あたり最大記事数・文字数でトリム。
    - 再試行戦略: 429/ネットワーク/タイムアウト/5xx に対する指数バックオフ（最大リトライ回数を定義）。
    - レスポンス検証: JSON の抽出・バリデーション実装（results 配列、code/score の検査、スコアの ±1.0 クリップ）。
    - DB 書き込みは冪等（対象コードのみ DELETE → INSERT）で部分失敗時に他銘柄の既存スコアを保護。
    - タイムウィンドウ: JST 前日 15:00 ～ 当日 08:30（内部は UTC naive で計算）を calc_news_window で提供。
    - API キー未設定時は ValueError を送出。
  - 市場レジーム判定（regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは news_nlp の calc_news_window を利用して同じ時間ウィンドウで取得。
    - LLM 呼び出しは専用関数を利用し、news_nlp と内部実装を分離（モジュール結合を避ける）。
    - API 呼び出し失敗時のフェイルセーフ: macro_sentiment=0.0 として処理継続。
    - 計算結果は market_regime テーブルへ冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - OpenAI の利用モデルは gpt-4o-mini（JSON mode）に対応。

- Data / ETL（kabusys.data）
  - ETL 結果オブジェクト ETLResult を追加（pipeline モジュールを介して再エクスポート）。
    - 取得数・保存数、品質チェック結果、エラーリストなどを保持し、to_dict で辞書化可能。
  - pipeline モジュール（ETL ロジック骨子）
    - 差分取得、バックフィル、品質チェックのためのユーティリティを実装。
    - DuckDB の最大日付取得等のユーティリティを提供。
    - デフォルトのバックフィル日数やカレンダー先読みなどの定数を定義。
  - マーケットカレンダー管理（calendar_management）
    - market_calendar テーブルを元に営業日判定ユーティリティを提供:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB に登録がない場合は曜日ベース（平日のみ営業日）でフォールバックする一貫した設計。
    - calendar_update_job により J-Quants API から差分取得して market_calendar を冪等保存（バックフィル・健全性チェックを実装）。
    - 最大探索日数による無限ループガードや、将来日付が異常に先の場合のスキップロジックを実装。

- Research（kabusys.research）
  - ファクター計算と特徴量探索ツールを追加:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取り、PER/ROE を計算（EPS 欠損で PER は None）。
    - calc_forward_returns: 将来リターン（任意ホライズン）を取得する汎用関数。
    - calc_ic: ランク相関（Spearman）に基づく IC 計算。
    - factor_summary / rank: 統計サマリーとランク関数。
  - 実装方針:
    - DuckDB の SQL + 最小限の Python を組み合わせて実装。
    - 外部依存（pandas 等）を使わずに標準ライブラリのみで集計・統計を実装。
    - すべての関数は lookahead バイアスを避ける設計（date 引数に基づく）。

### Changed
- （初期リリースのため変更履歴なし）

### Fixed
- （初期リリースのため修正履歴なし）

### Security
- 環境変数の自動読み込みで OS 環境変数を上書きしないデフォルト挙動により、意図しない上書きを防止。
- API キー未設定の際には明確なエラー（ValueError）を返す実装で、秘密情報の欠落を早期に検知可能。

### Notes / Implementation details / ユーザー向け注意点
- OpenAI API
  - モデル: gpt-4o-mini を想定しており JSON mode（response_format）を利用しているため、OpenAI SDK の互換性に依存します。
  - API 呼び出しはリトライとエラーハンドリングの実装があるものの、API キーは必須（関数引数で注入可能）。
  - テスト容易性のため、内部の _call_openai_api 関数を unittest.mock.patch などで差し替え可能。

- データベース（DuckDB）
  - DuckDB 0.10 系の制約（executemany に空リストを渡せない等）に配慮した実装を行っています（空チェックを明示的に実施）。
  - DB 書き込みは基本的に冪等を心がけ（DELETE → INSERT のパターンなど）。

- 時刻・日付
  - ルックアヘッドバイアス防止のため、内部で datetime.today() / date.today() を安易に参照せず、明示的に target_date を受け取る設計。
  - ニュースやレジーム判定のウィンドウは JST ベースで設計し、DB 内値は UTC として扱う前提の通信ロジックを組み込んでいます。

- 環境変数名（参考）
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 任意/デフォルトあり: KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH, KABUSYS_DISABLE_AUTO_ENV_LOAD
  - OpenAI API キーは関数引数で渡すか、環境変数 OPENAI_API_KEY を利用。

### Known limitations / TODO（推測）
- order execution / strategy / monitoring の具体実装は本リリースで公開されたインターフェースに基づくが、実運用前の追加テスト・監査が推奨されます。
- ニュース API のプロンプト・結果フォーマット依存があるため、LLM の振る舞い変化への監視が必要です。
- raw_financials のデータカバレッジや欠損時の扱いにより一部指標（PER 等）が欠損する可能性があるため、上位レイヤーでの補完方針が必要です。

---

This project follows semantic versioning. 今後のリリースでは機能追加、修正、互換性の破壊についてこの CHANGELOG にて明示的に記録します。