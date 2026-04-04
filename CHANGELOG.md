CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは "Keep a Changelog" に準拠しています。
SemVer を使用します。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-04
--------------------

Added
- パッケージ初期リリース。
  - src/kabusys/__init__.py にてバージョンを "0.1.0" として公開。
  - 公開サブパッケージ（__all__）に data, strategy, execution, monitoring を含む（利用者向け公開面を意識）。
- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を起点）から自動読み込みする仕組みを実装。
  - 読み込み順序: OS 環境変数 > .env.local > .env。既存の OS 環境変数は保護（protected）される。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - export KEY=val 形式、クォート内のバックスラッシュエスケープ、行末コメントなど多様な .env 記法に対応するパーサーを実装。
  - Settings クラスを提供し、J-Quants / kabu / LINE / DB パス / 監視閾値 等の設定プロパティを環境変数経由で取得可能。必須項目は _require で明示的に検証。
  - 環境値の検証: KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL の妥当性チェックを実装。
- AI（ニュース NLP / レジーム判定）（src/kabusys/ai）
  - news_nlp.score_news: raw_news と news_symbols を用いて銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）に JSON Mode で問い合わせて銘柄ごとのセンチメント（ai_scores テーブル）を算出・書き込みする機能を実装。
    - チャンク処理（最大20銘柄/コール）、1銘柄当たりの記事数・文字長制限、JSON レスポンスのバリデーション、スコアのクリップ（±1.0）等をサポート。
    - API 呼び出しのリトライ（429/ネットワーク断/タイムアウト/5xx）を実装し、失敗時は部分的スキップでフェイルセーフに継続する設計。
    - 時間ウィンドウは JST 前日15:00〜当日08:30（UTC に変換）を採用、ルックアヘッドバイアスを避けるため date.today() を直接参照しない設計。
  - regime_detector.score_regime: ETF 1321 の 200日移動平均乖離（重み70%）とニュースマクロセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し、market_regime テーブルへ冪等書き込みを行う機能を実装。
    - ma200 計算は target_date 未満のデータのみ使用してルックアヘッドを避ける。データ不足時は中立（1.0）扱いで警告ログを出力。
    - OpenAI 呼び出しは再試行・バックオフ・5xx判定・パース失敗時のフォールバックを実装（API全失敗時は macro_sentiment=0.0）。
    - OpenAI クライアント注入は環境変数 OPENAI_API_KEY か引数 api_key から解決し、未設定時は ValueError を送出。
- Data（ETL / カレンダー / Pipeline）（src/kabusys/data）
  - pipeline.ETLResult を定義して ETL 実行結果を構造化して返却・ログ用に辞書化するユーティリティを実装。
    - 取得/保存件数、品質問題（quality.QualityIssue）やエラー一覧などを保持。品質エラー判定や has_errors プロパティを提供。
  - calendar_management:
    - JPX カレンダー管理ロジックを実装（market_calendar テーブル利用）。is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等のAPIを提供。
    - DB 優先で未登録日は曜日ベースにフォールバックする設計。最大探索日数やバックフィル、健全性チェックを実装。
    - calendar_update_job: J-Quants API から差分取得し冪等で market_calendar を更新する夜間バッチロジックを実装（バックフィルと取得失敗時の例外ハンドリングあり）。
  - ETL パイプライン設計をドキュメント化（差分更新、保存（idempotent）、品質チェックの集約的扱い、テストしやすい id_token 注入など）。
- Research（ファクター計算・特徴量探索）（src/kabusys/research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離等のモメンタム指標を DuckDB / prices_daily に対して計算する関数を実装。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（true range の取り扱いに注意）、相対 ATR、20日平均売買代金、出来高比などのボラティリティ/流動性指標を実装。必要件数未満は None を返す。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算する関数を実装。EPS がゼロ/欠損時は PER を None とする。
  - feature_exploration:
    - calc_forward_returns: target_date の終値から各ホライズン（デフォルト: 1,5,21 営業日）先までのリターンを計算する機能を実装。horizons の入力バリデーションあり。
    - calc_ic: factor_records と forward_records を code で結合してスピアマンランク相関（IC）を計算。有効レコードが3件未満の場合は None を返す。
    - rank: 同順位は平均ランクとするランク化関数を実装（丸め対策あり）。
    - factor_summary: 指定カラムの count/mean/std/min/max/median を算出する統計サマリー機能を提供。
- パッケージ内部の設計方針・品質配慮
  - ルックアヘッドバイアス防止（date.today()/datetime.today() を直接参照しない）を明確に徹底。
  - DuckDB を前提とした SQL 実行と Python 側のロジック分離。DB 書き込みは冪等に配慮（DELETE→INSERT 等、トランザクション管理）。
  - OpenAI 呼び出しは JSON モードの取り扱いやレスポンスパースのロバスト化（前後余分テキストの復元等）を実装。
  - API 呼び出しでのリトライ/バックオフ戦略や失敗時のフェイルセーフ（部分書き込みやスキップ）を多数の箇所で実装。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / 注意事項
- 必要な環境変数:
  - JQUANTS_REFRESH_TOKEN（必須、Settings.jquants_refresh_token）
  - KABU_API_PASSWORD（必須、Settings.kabu_api_password）
  - OPENAI_API_KEY（AI 機能を使用する場合必須。api_key 引数での注入も可能）
  - その他: KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, DUCKDB_PATH, SQLITE_PATH 等は Settings で既定値あり
- DuckDB を使用するテーブル（主な参照先）:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など
- OpenAI API 呼び出しは gpt-4o-mini を想定。レスポンスフォーマットや API 仕様の変更により動作が変わる可能性があるため、テスト時は該当内部関数をモック可能（ユニットテスト用フックあり）。
- .env 自動読み込みはプロジェクトルートの検出に依存するため、パッケージ配布後に動作させる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を適切に設定するか、環境変数を直接セットしてください。

Contributors
- 初期コード（本リリース）の作成者による実装。

今後の予定（提案）
- strategy / execution / monitoring モジュールの具体実装と統合テストの追加
- テストカバレッジ拡張（特に OpenAI 呼び出し周りの挙動）
- ドキュメント（Usage, Migration, デプロイ手順）の充実化

---