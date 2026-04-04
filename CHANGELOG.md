# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

注: この CHANGELOG はリポジトリ内のソースコードから機能・設計方針を推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-04
初回リリース。

### Added
- パッケージ初期化
  - kabusys パッケージを公開。バージョンは 0.1.0。
  - __all__ に data, strategy, execution, monitoring を設定。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート検出はパッケージファイル位置を起点に .git または pyproject.toml を探索して実施（CWD 非依存）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env パーサ実装:
    - 空行・コメント行（#）のスキップ、`export KEY=val` 形式のサポート。
    - クォートあり（シングル/ダブル）の値のエスケープ処理、クォートなし値のインラインコメント処理などに対応。
    - ファイル読み込み失敗時は警告を出力して無視。
    - override と protected（OS 環境変数保護）オプションをサポートするロード関数を提供。
  - Settings クラスを提供（settings インスタンスをエクスポート）:
    - J-Quants / kabuステーション / LINE / DB パス / 監視設定 / システム設定などのプロパティを環境変数から取得。
    - 必須値未設定時は ValueError を投げる _require ヘルパー。
    - KABUSYS_ENV と LOG_LEVEL のバリデーション（許容値セットを定義）。
    - is_live / is_paper / is_dev のブールヘルパー。

- AI モジュール（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）でセンチメントをバッチ評価。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST の UTC 変換）を提供（calc_news_window）。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたりの最大記事数・文字数制限を実装。
    - OpenAI 呼び出しは JSON mode（厳密な JSON 出力）を期待し、レスポンスのバリデーションとスコアの ±1.0 クリップを行う。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフでのリトライを実装。その他のエラー時は当該チャンクをスキップするフェイルセーフ設計。
    - DuckDB へ書き込む際は部分失敗時に既存スコアを守るため、対象コードのみ DELETE → INSERT を行う冪等処理。
    - テスト容易性のため OpenAI 呼び出し点は _call_openai_api を通す設計（モックで差し替え可能）。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
  - regime_detector:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは raw_news からマクロキーワード（日本・米国等）でフィルタしてタイトルを抽出。
    - OpenAI（gpt-4o-mini）へ渡して -1.0〜1.0 の macro_sentiment を算出。API エラー時は macro_sentiment=0.0 にフォールバック。
    - レジームスコアは clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1) で算出し閾値によりラベル付け。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX カレンダー（market_calendar）を扱うユーティリティ群を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定 API を提供。
    - market_calendar が未取得の場合は曜日ベース（週末除外）でフォールバック。
    - DB に一部のみカレンダーがある場合でも DB 値を優先し、未登録日は曜日フォールバックで一貫性を保つ設計。
    - 夜間バッチ calendar_update_job を実装。J-Quants から差分取得 → jquants_client 経由で保存（バックフィル・健全性チェックを含む）。
  - pipeline / etl:
    - ETLResult dataclass を公開（kabusys.data.etl から再エクスポート）。
    - ETL パイプライン設計方針と結果を表す構造体を実装（取得件数・保存件数・品質問題・エラー一覧など）。
    - 差分更新・backfill・品質チェック（quality モジュールと連携）の方針を実装（実装は pipeline モジュール内で行う）。
    - DuckDB のテーブル確認ユーティリティ等を提供。

- リサーチ（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性指標（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials を参照して計算する関数を実装。
    - 関数は全て (date, code) 単位の辞書リストを返す仕様。
    - 例: calc_momentum, calc_volatility, calc_value。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（営業日ベース）に対するリターンを一度のクエリで取得する実装。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関を計算。データ不足時は None を返す。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を返す汎用ユーティリティ。
    - rank 関数: same-rank averaging（同順位は平均ランク）を実装。

### Changed
- 設計上の重要な方針明記（コード内ドキュメント）
  - 主要モジュールで「ルックアヘッドバイアス防止」のため datetime.today()/date.today() を直接参照しないことを徹底。すべての関数は target_date を引数で受け取る設計。
  - OpenAI 呼び出しの失敗はフェイルセーフ（スコア 0.0 のフォールバック、もしくは該当チャンクスキップ）とし、ETL やバッチ処理が止まらないように配慮。
  - DuckDB の executemany のバージョン差分対応（空リストバインド回避）等、エンジン互換性に配慮した実装。

### Fixed
- N/A（初回リリースのため既存バグ修正は該当なし、実装上の回復処理や各種エラー時の安全動作を多数実装）。

### Security
- OpenAI API キーや機密情報は環境変数経由で取得。未設定時は明示的に ValueError を投げる設計で安全性を確保。
- .env の読み込みは OS 環境変数を protected として上書きを防ぐオプションを提供。

### Notes / Limitations
- OpenAI（gpt-4o-mini）を利用する機能は API キーが必須。API 呼び出しに関するテスト容易性のため、内部の _call_openai_api をモックする設計になっている。
- ETL / calendar_update_job / AI スコアリングは DuckDB に保存されたテーブル（prices_daily, raw_news, news_symbols, raw_financials, market_regime, ai_scores 等）を前提とする。
- README や実行方法、実際の jquants_client の実装・API トークン取得手順は別途必要。

---

（この CHANGELOG はコード中の docstring やコメント、実装の挙動から推測して作成しました。差分や今後のリリースでは実際の変更に合わせて更新してください。）