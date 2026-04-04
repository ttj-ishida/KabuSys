# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトの初期リリース（0.1.0）に含まれる主要機能・設計方針・重要な挙動を記載します。

全般の備考
- 日付の基準: ルックアヘッドバイアス防止のため、多くの処理は datetime.today()/date.today() を参照しない設計になっています（呼び出し側から target_date を受け取る）。
- DB: DuckDB を主要なローカルデータストアとして使用します。SQL 実行は duckdb.PyConnection を前提としています。
- OpenAI 連携: gpt-4o-mini を想定した JSON Mode（response_format）での呼び出し実装。API エラー・タイムアウト等に対するリトライ・フォールバックが組み込まれています。
- フェイルセーフ: 外部 API の失敗やデータ不足時は極力例外を投げずにログ出力して中立な値（0.0/1.0/None 等）で処理を継続する方針です。
- テスト性: OpenAI 呼び出し部分や環境変数自動ロードは外から差し替え可能／無効化可能にしてテストしやすくしています。

## [0.1.0] - 2026-04-04

### Added
- パッケージ基盤
  - kabusys パッケージ開始。__version__ = 0.1.0 を定義。
  - 公開サブパッケージ: data, strategy, execution, monitoring（__all__ にてエクスポート）。

- 環境設定（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメント等に対応。
  - Settings クラスを実装し、J-Quants や kabu ステーション、LINE、DB パス、監視閾値、環境（development/paper_trading/live）等の設定プロパティを提供。
  - 必須環境変数未設定時は _require() が ValueError を送出。

- AI 関連（kabusys.ai）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols からターゲットウィンドウの記事を銘柄ごとに集約し、OpenAI にバッチ送信して銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書き込む。
    - バッチサイズ、文字数・記事数制限、JSON レスポンスのバリデーション、スコアの ±1.0 クリップ、429/ネット断/5xx に対する指数バックオフリトライなどを実装。
    - 部分成功時にも既存データを保護する（対象コードのみ DELETE→INSERT）。
    - API 呼び出し部はテストで差し替え可能（unittest.mock.patch）に実装。
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ日次で書き込み。
    - prices_daily から ma200_ratio を計算する内部ロジック、raw_news からマクロキーワード抽出、OpenAI 呼び出し・リトライ・フォールバック（記事無し／API失敗時は macro_sentiment=0.0）を実装。
    - 出力は regime_score（-1〜1）と regime_label（bull/neutral/bear）を保存。DB 書き込みは冪等（BEGIN/DELETE/INSERT/COMMIT）で行う。

- データ処理（kabusys.data）
  - calendar_management モジュール
    - JPX カレンダー管理ロジックを実装。is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の API を提供。
    - market_calendar が存在しない場合は曜日（平日）でフォールバックする仕組み。
    - calendar_update_job により J-Quants API からの差分取得・バックフィル・健全性チェックを実装（jquants_client 依存）。
  - pipeline モジュール
    - ETLResult データクラスを実装（ETL 実行結果の集約、品質問題・エラー一覧の保持、to_dict メソッド等）。
    - ETL の差分取得・バックフィル・品質チェックを想定したインターフェース設計（jquants_client / quality モジュールとの連携設計）。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- 研究・ファクター分析（kabusys.research）
  - factor_research モジュール
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。
    - calc_volatility(conn, target_date): 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等を計算。
    - calc_value(conn, target_date): raw_financials からの EPS/ROE を用いた PER・ROE を計算（EPS が 0/欠損時は None）。
    - 全関数は prices_daily / raw_financials のみ参照し、結果は (date, code) ベースの dict リストを返す。
  - feature_exploration モジュール
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（デフォルト [1,5,21]）を計算。horizons のバリデーションあり。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を実装。有効レコードが 3 件未満なら None を返す。
    - rank(values): 同順位は平均ランクにするランク関数（丸め処理で ties 対策）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算し返す。
  - research パッケージは上記主要関数群を再エクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは明示的に渡すか環境変数 OPENAI_API_KEY を設定する必要がある。未設定の場合は ValueError を送出して明示的に失敗します。
- 環境変数の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テストや CI 用）。

### Notes / Implementation details / 互換性
- DuckDB の executemany に関する互換性問題（空リスト不可）に配慮して、INSERT/DELETE の実行前にパラメータの空チェックを行っています（特に ai_scores 書き込み処理）。
- OpenAI の API エラー処理では、429/ネットワーク断/タイムアウト/5xx をリトライ対象とし、それ以外はログ出力してフォールバックします。news_nlp と regime_detector でそれぞれ独立した _call_openai_api 実装を持ち、モジュール間の内部関数共有を避けています（テスト時の差し替えが容易）。
- 多くの箇所でデータ不足時は None や中立値（1.0 / 0.0）を返すため、呼び出し側はこれらを扱う責務があります。
- calendar_update_job は jquants_client の fetch/save 実装に依存します。API 呼び出し失敗時は 0 を返しログを残します。

---

今後のリリースで想定される追加事項（例）
- strategy / execution / monitoring の実装詳細（本リリースではパッケージ名のみ準備）。
- ai モデルやプロンプトのチューニング、JSON スキーマの厳密化。
- ETL の具体的な差分計算・品質チェックルールの拡充。
- 単体テスト・統合テストおよび CI の導入。