# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-28
初回リリース。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を定義（src/kabusys/__init__.py）。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ に設定。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび OS 環境変数から設定を自動ロードする機能を実装。
  - プロジェクトルートを .git または pyproject.toml を基準に探索するため、CWD に依存しない自動読み込みを実現。
  - .env パーサの強化:
    - コメント行・空行無視、`export KEY=val` 形式サポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - クォートなし値のインラインコメント処理（直前に空白/タブがある `#` をコメントと認識）。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - Settings クラスでアプリケーション設定をプロパティとして提供（必須キーは未設定時に ValueError）。
  - 設定検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）とユーティリティプロパティ（is_live / is_paper / is_dev）。
  - デフォルトの DB パス（DuckDB / SQLite）を設定。

- AI（自然言語処理） (src/kabusys/ai/)
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信して銘柄ごとのセンチメント ai_score を算出。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチサイズ、記事数・文字数トリム、リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）、レスポンスの厳密なバリデーション、スコアの ±1.0 クリップ。
    - DuckDB への冪等書き込み（DELETE→INSERT）を行い、部分失敗時に既存スコアを保護。
    - テスト用に OpenAI 呼び出しを差し替え可能（_call_openai_api を patch 可能）。
  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - MA 計算はルックアヘッドバイアス防止のため target_date 未満のデータのみを使用。
    - マクロ記事がある場合にのみ OpenAI を呼び出し、API エラー時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
    - レジーム結果を market_regime テーブルへ冪等保存（BEGIN / DELETE / INSERT / COMMIT）し、失敗時は ROLLBACK を試行して例外を上位に伝播。
    - API 呼び出しのリトライ・バックオフ・エラーハンドリングを実装。

- Research（因子・特徴量解析） (src/kabusys/research/)
  - factor_research モジュール
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離率を calc_momentum で計算（データ不足時は None）。
    - Volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率を calc_volatility で計算（データ不足は None）。
    - Value: raw_financials を用いた PER / ROE を calc_value で計算。
    - DuckDB を用いた SQL ベースの実装で外部 API 呼び出し無し、結果を (date, code) ベースで返す。
  - feature_exploration モジュール
    - 将来リターン calc_forward_returns（任意ホライズン: デフォルト [1,5,21]、入力検証あり）。
    - IC（Spearman の ρ）計算 calc_ic（コードマッチング・None 除外・最小サンプルチェック）。
    - ランク変換 rank（同順位は平均ランクを使用、丸めで ties の検出誤差を防止）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median を計算）。
  - research パッケージの __all__ に必要関数をエクスポート。

- Data（ETL / カレンダー） (src/kabusys/data/)
  - calendar_management モジュール
    - market_calendar テーブルに基づく営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にデータがない場合は曜日ベース（日曜・土曜は非営業日）でフォールバック。
    - JPX カレンダーを J-Quants API から差分取得して保存する夜間バッチ calendar_update_job を実装（バックフィル・健全性チェック・Idempotent 保存）。
  - pipeline モジュール（ETL）
    - ETLResult dataclass を導入して ETL 処理の集計と品質チェック結果、エラーの収集を可能に。
    - 差分取得、バックフィル、品質チェックを考慮した設計方針に基づくユーティリティ関数を提供（テーブル存在チェック・最大日付取得など）。
  - etl エントリポイントで ETLResult を再エクスポート。

### Changed
- 設計方針の明示
  - LLM/データ取得に関するフォールバック、ルックアヘッドバイアス回避、DuckDB の互換性配慮（executemany の空リスト回避等）をコード内の docstring とログで明確化。
  - OpenAI 呼び出しはモジュール間でプライベート関数を共有せず、各モジュールでテスト用差し替えポイントを提供。

### Fixed
- DB トランザクションの安全化
  - market_regime / ai_scores などへの書き込みで BEGIN/COMMIT/ROLLBACK の扱いを実装し、ROLLBACK 失敗時に警告ログを出すことで失敗時の痕跡把握を容易に。

### Security
- 環境変数保護
  - .env 読み込み時に OS 環境変数を protected セットとして扱い、override フラグの有無により上書き制御。

---

脚注:
- 多くのモジュールで「datetime.today()/date.today() を参照しない」設計が採られており、データ処理でのルックアヘッドバイアスを避けることを旨としています。  
- OpenAI への実際の API 呼び出しは gpt-4o-mini モデルと JSON Mode を想定しており、レスポンス検証・エラーハンドリング・リトライの実装が組み込まれています。  
- この CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のリリースノート作成時は実行環境・テストの結果・リリース日・著者情報などを合わせて更新してください。