# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このファイルは初回リリース相当の状態（version 0.1.0）をコードベースから推測して要約したものです。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-04
初期リリース（コードベース解析に基づく要約）

### Added
- パッケージ基盤
  - kabusys パッケージを追加。パッケージバージョンは `__version__ = "0.1.0"`。
  - パッケージの公開モジュール: data, strategy, execution, monitoring を __all__ で定義。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイル（.env および .env.local）と OS 環境変数から設定値を自動ロードする仕組みを実装。
  - プロジェクトルートの自動検出: 現在のモジュールファイルを起点に `.git` または `pyproject.toml` を探索してプロジェクトルートを判断。
  - .env のパース機能を強化:
    - 空行・コメント（行頭 `#`）を無視。
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォートとバックスラッシュエスケープ対応の値解析。
    - クォートなし値のインラインコメント認識（`#` の前が空白/タブの場合）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - 環境変数を保護するため、既存 OS 環境変数を踏まえた上で .env/.env.local をロード（.env.local は上書き、但し OS のキーは protected）。
  - Settings クラスを導入し、アプリケーション設定をプロパティ経由で取得できるようにした（J-Quants/LINE/kabu API 等の設定、DBパス、監視パラメータ、環境/ログレベル検証など）。
  - 環境値の検証:
    - KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかのみ許容。
    - LOG_LEVEL は "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL" のみ許容。
  - 必須設定未定義時は明示的に ValueError を送出する `_require` を提供。

- AI ニュース処理（kabusys.ai.news_nlp）
  - raw_news / news_symbols テーブルからニュースを集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントスコアを計算して ai_scores テーブルへ保存する `score_news` を実装。
  - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ `calc_news_window` を提供。
  - バッチ処理: 最大 20 銘柄単位で API 呼び出しを行う（_BATCH_SIZE）。
  - 1 銘柄あたりの記事数 / 文字数制限（トークン肥大化対策）を実装（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
  - OpenAI 呼び出しは JSON mode（response_format={"type":"json_object"}）を利用し、厳密な JSON 応答を期待。
  - レートリミット（429）、接続断、タイムアウト、5xx サーバーエラーに対する指数バックオフのリトライ実装。
  - 応答の堅牢なバリデーション実装:
    - JSON パース、"results" リスト検査、要素の "code" / "score" チェック、未知コードの無視、スコアの数値変換と有限性チェック、±1.0 でクリップ。
    - JSON 以外の余計な前後テキストが混在する場合に最外側の {..} を抽出して復元するフォールバック。
  - DuckDB の制約（executemany に空リスト不可）への対応（書き込み前に空チェック）。
  - テスト容易性のため、内部の OpenAI 呼び出し関数はパッチ差替え可能（unittest.mock.patch 用のフック）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定する `score_regime` を実装。
  - MA 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを排除。
  - マクロニュースは news_nlp と同様に OpenAI（gpt-4o-mini）を用いて JSON レスポンスからスコアを抽出。記事がない場合は LLM 呼び出しをスキップ（macro_sentiment=0.0）。
  - API エラーやパース失敗時はフェイルセーフにより macro_sentiment=0.0 を使用。
  - 併せて market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
  - OpenAI 呼び出しは news_nlp と意図的に別実装とし、モジュール結合を避ける設計。

- データプラットフォーム（kabusys.data）
  - カレンダー管理モジュール（calendar_management）を実装:
    - JPX カレンダーの夜間バッチ更新 job（calendar_update_job）を実装し、J-Quants クライアント経由で差分取得・冪等保存を行う（バックフィル・健全性チェックを含む）。
    - 営業日判定ユーティリティを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar がない場合の曜日ベースのフォールバック（週末は非営業日）や、DB に登録がある場合は DB 値優先の一貫した挙動。
    - 最大探索日数やバッファ等の安全対策を実装（_MAX_SEARCH_DAYS 等）。
  - ETL パイプライン（pipeline）を実装・公開:
    - 差分取得・保存・品質チェックを行う設計を備えた ETLResult データクラスを追加（ETL 実行結果の集約）。
    - ETLResult は品質問題（quality.QualityIssue）を集約し、has_errors / has_quality_errors プロパティや辞書化メソッドを提供。
    - ETL の設計方針として差分更新、バックフィル、品質チェックの非 Fail-Fast 動作を明記。

- 研究用モジュール（kabusys.research）
  - ファクター計算（factor_research）を実装:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均出来高・出来高比率）、バリュー（PER, ROE）を DuckDB 上の prices_daily / raw_financials を参照して計算するユーティリティを提供（calc_momentum, calc_volatility, calc_value）。
    - データ不足時は None を返す設計とし、DuckDB のウィンドウ関数を活用。
  - 特徴量探索（feature_exploration）を実装:
    - 将来リターン計算（calc_forward_returns）、IC（情報係数）計算（calc_ic）、ランク関数（rank）、統計サマリー（factor_summary）を提供。
    - 外部ライブラリに依存せず標準ライブラリ + DuckDB の SQL で実装。
  - data.stats の zscore_normalize を再エクスポートして利用可能化。

### Changed
- （初期リリースにつき該当なし）コードの設計上の重要な方針をドキュメント化:
  - 全ての時間計算で datetime.today()/date.today() の直接参照を避け、ルックアヘッドバイアスを防止する方針を採用。
  - DB 書き込みは可能な限り冪等操作（DELETE→INSERT や ON CONFLICT）で行う。
  - 外部 API の失敗を厳密に扱い、致命的エラーを極力防ぐ（フェイルセーフ）設計。

### Fixed
- （初期リリースにつき該当なし）実装時に考慮された互換性・安定化対応:
  - DuckDB の executemany に関する既知の制約（空リスト不可）への対応を実装。
  - OpenAI SDK のエラーオブジェクトの差異（status_code 存在の有無）に対する堅牢な処理。

### Security
- OpenAI API キーの取り扱い:
  - API キーは関数引数で注入可能（テスト/制御のため）、引数が None の場合は環境変数 OPENAI_API_KEY を参照。
  - API キー未設定時は ValueError を送出して明示的に失敗させる仕様。

### Notes / Implementation details（重要設計メモ）
- テスト容易性:
  - OpenAI 呼び出し関数はモジュール内部で定義されており、単体テスト時に patch して差し替えられるようになっている（news_nlp._call_openai_api / regime_detector._call_openai_api）。
- ログと監視:
  - 各処理で適切なログ（info/warning/debug/exception）を出力し、失敗時の解析を容易にする設計。
- フォールバックと保護:
  - 外部データ（market_calendar, raw_news, prices_daily）が不足する場合でも安全に処理を継続するフェイルセーフを多用している。

---

（この CHANGELOG はコードベースの内容を解析して推測した初期リリースの要約です。実際のリリースノート作成時はコミット履歴やリリース担当の確認情報を反映してください。）