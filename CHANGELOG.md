# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
このファイルはコードベース（kabusys パッケージ）の現状ソースから推測して作成した変更履歴です。

## [Unreleased]
（無し）

## [0.1.0] - 2026-04-03
初回リリース。主要機能・モジュールを追加。

### 追加 (Added)
- パッケージ基礎
  - パッケージのエントリポイントを追加（src/kabusys/__init__.py）。バージョン情報 __version__ = "0.1.0" を定義。主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。

- 設定管理（src/kabusys/config.py）
  - .env ファイルあるいは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）で CWD に依存しない自動ロードを実現。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env パーサーは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いに対応。
  - override と protected オプションにより OS 環境変数を保護しつつ .env.local による上書きを許可。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB パス / 監視設定 / システム設定等のプロパティを公開。
    - 必須環境変数は _require() で検証（未設定時に ValueError を送出）。
    - KABUSYS_ENV の検証（development/paper_trading/live）や LOG_LEVEL の検証を行う。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を元に銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを算出。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたりの記事数・文字数上限（デフォルト: 10 件 / 3000 文字）を実装。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実施。API 失敗はログ出力してフェイルセーフにより継続。
    - レスポンスのバリデーション機構を実装（JSON 抽出、"results" 構造チェック、コード照合、数値チェック）。
    - スコアは ±1.0 にクリップ。成功分のみ ai_scores テーブルへ冪等的に置換（DELETE → INSERT）。
    - calc_news_window(target_date) を提供（JST ウィンドウを UTC naive datetime へ変換するユーティリティ）。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ書き込む。
    - マクロキーワードによる記事抽出、OpenAI 呼び出し（gpt-4o-mini, JSON mode）、リトライ/バックオフ、API エラー時は macro_sentiment=0.0 にフォールバック。
    - レジームスコア合成はクリップ済みで閾値によりラベリング（デフォルトの閾値を設定）。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）としている。公開 API: score_regime(conn, target_date, api_key=None)。

- リサーチ / ファクター群（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum(conn, target_date): mom_1m / mom_3m / mom_6m / ma200_dev を計算。200 日 MA のデータ不足時は None を返す。
    - calc_volatility(conn, target_date): 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率などを計算。必要行数不足時は None を返す。
    - calc_value(conn, target_date): raw_financials の最新財務データを利用して PER / ROE を計算（EPS が 0 または NULL の場合は None）。
    - DuckDB を用いた SQL ベースの実装で、外部 API へは接続しない設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns(conn, target_date, horizons=None): 指定ホライズン先の将来リターンを計算（デフォルト [1,5,21]）。入力の検証あり。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（Information Coefficient）を計算。十分サンプルがない場合は None。
    - rank(values): 同順位は平均ランクとするランク変換ユーティリティ（浮動小数の丸め対策あり）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計サマリー。
  - research パッケージの __init__ で主要関数をエクスポート（calc_momentum, calc_value, calc_volatility 等）。

- データプラットフォーム（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー（market_calendar）を扱うユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。DB にデータがない場合は曜日ベースのフォールバック（週末を非営業日）を採用。
    - calendar_update_job(conn, lookahead_days=90): J-Quants API から差分取得して market_calendar を更新。バックフィル（直近数日）や健全性チェックを含む。
    - 最大探索範囲 _MAX_SEARCH_DAYS を設定して無限ループを回避。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETLResult dataclass を追加（取得件数・保存件数・品質問題・エラー一覧を保持）。to_dict() により品質問題を dict に変換して出力。
    - 差分取得・バックフィル・品質チェック方針の実装に向けたユーティリティを準備。DuckDB のテーブル existence / max_date 取得ヘルパーを用意。
  - ETL の公開インターフェース（src/kabusys/data/etl.py）で ETLResult を再エクスポート。
  - data パッケージの __init__ および jquants_client / quality 等のクライアント連携を想定した設計。

- パッケージエクスポート
  - ai、research、data の __init__ で主要関数を明示的にエクスポート（__all__ を利用）。

### 変更 (Changed)
- （初版のため過去変更は無し）

### 修正 (Fixed)
- （初版のため過去修正は無し）

### 既知の設計上の注意 / 方針
- ルックアヘッドバイアス対策: score_news / score_regime 等は内部で datetime.today() や date.today() を直接参照しない設計になっている（target_date を明示的に受け取る）。
- フェイルセーフ設計: OpenAI や外部 API の失敗時は稼働継続を優先し、該当部分をスキップまたは中立値で埋める（例: macro_sentiment=0.0、スコア未取得コードは書き込みを行わない）。
- DuckDB をストレージ層として想定。実装は SQL を多用し、可能な限り冪等性（DELETE→INSERT や ON CONFLICT 想定）を担保している。
- OpenAI 呼び出しは JSON Mode を利用し、レスポンスパースのための頑健な処理（前後余計なテキストの抽出等）を実装。

### セキュリティ (Security)
- API キー等の取得は Settings 経由または score_* 関数の api_key 引数で注入する設計。env の自動読み込みは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

今後の追加/改善候補（参考）
- strategy / execution / monitoring モジュールの具体的実装（現状はパッケージ名がエクスポートされているが、ソース内に実装が存在しない想定）。
- 単体テスト・統合テストの追加（特に OpenAI 呼び出しや DuckDB 操作のモックを含む）。
- J-Quants / kabu API クライアントの詳細実装と認可フローの例示。
- メトリクス収集・監視周り（PID ファイル管理、kill flag 処理など）のランタイム検証。

（この CHANGELOG はソースコードの内容から推測して作成したものであり、実際のリリースノートとして利用する場合は必要に応じて加筆・修正してください。）