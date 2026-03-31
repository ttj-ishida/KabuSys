# CHANGELOG

すべての注記は Keep a Changelog の慣例に従います。  
本ドキュメントはコードベース（src/kabusys 以下）の内容から機能・修正点を推測して作成した変更履歴です。

## [Unreleased]
- （現時点の HEAD に未リリースの変更はありません）

## [0.1.0] - 2026-03-31
初回リリース。日本株自動売買システムのコアライブラリ（データ取得・ETL・研究用ファクター計算・AI ニュース解析・市場レジーム判定・カレンダー管理・設定管理など）を実装。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョンを `0.1.0` として公開。主要サブパッケージを __all__ でエクスポート（data, strategy, execution, monitoring）。

- 環境設定モジュール（kabusys.config）
  - .env ファイル（および .env.local）の自動読み込み機能をプロジェクトルート（.git または pyproject.toml）から探索して実装。
  - .env の行パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート内のエスケープ対応、インラインコメント判定など）。
  - .env 読み込み時の上書き制御（override）とプロテクトセット（既存 OS 環境変数を保護）をサポート。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / 監視閾値 / 実行環境 等の設定プロパティを安全に取得（必須値チェックを含む）。KABUSYS_ENV と LOG_LEVEL の検証を実施。
  - パスは expanduser して扱う。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信して銘柄別センチメント（ai_score）を計算する機能を実装。
  - 1銘柄当たりの最大記事数や文字数トリム、バッチサイズ（最大20銘柄）などトークン肥大化対策を実装。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライロジックを実装。致命的エラー以外はフェイルセーフでスキップ。
  - レスポンスのバリデーションを実装（JSON 抽出、results 配列、code/score の検証、数値チェック、±1.0 でクリップ）。
  - ai_scores テーブルへの冪等的書き込み（対象コードのみ DELETE → INSERT）を実装。
  - 公開 API: score_news(conn, target_date, api_key=None)

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を日次判定する機能を実装。
  - prices_daily からの MA 計算（target_date 未満の排他条件でルックアヘッド防止）、raw_news からマクロキーワード抽出、OpenAI 呼び出し（gpt-4o-mini）による macro_sentiment 評価、スコア合成、market_regime テーブルへの冪等書き込みを実装。
  - OpenAI API 呼び出しに対するリトライ/フォールバック（失敗時は macro_sentiment=0.0）を実装。
  - 公開 API: score_regime(conn, target_date, api_key=None)

- データ ETL（kabusys.data.pipeline / kabusys.data.etl）
  - ETL パイプラインの骨格を実装（差分更新、保存、品質チェックの呼び出し等を想定）。
  - ETL 実行結果を格納する ETLResult データクラスを提供（取得数/保存数/品質問題/エラー情報等を含む）。has_errors / has_quality_errors / to_dict を実装。

- マーケットカレンダー（kabusys.data.calendar_management）
  - market_calendar テーブルを利用した営業日判定ユーティリティ群を実装:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
  - DB 記録がまばらな場合でも曜日ベースのフォールバックを行い、一貫性のある探索を実現。
  - calendar_update_job を実装し、J-Quants クライアントを介して差分取得 → market_calendar へ冪等保存（バックフィル/先読み/健全性チェック含む）する夜間バッチ処理を提供。

- 研究用モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日 MA 乖離）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（atr_20）/ 相対 ATR（atr_pct）/ 20日平均売買代金 / 出来高比率 を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（EPS が 0 / NULL の場合は None）。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - calc_forward_returns: target_date から指定ホライズン（デフォルト [1,5,21]）先の将来リターンを一括 SQL で取得。
    - calc_ic: ランク相関（Spearman ランク相関）により IC を計算。データ不足時は None。
    - rank: 同順位は平均ランクとするランク付けユーティリティ。
    - factor_summary: 各ファクターの count/mean/std/min/max/median を計算。
  - zscore_normalize を含むデータ統計ユーティリティとの連携（kabusys.data.stats から再利用）。

### Changed
- 設計方針（全体）
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() をスコア算出や集計ロジックの内部参照に用いない実装方針を明示的に採用（target_date を明示的引数として受ける関数設計）。
  - 外部依存を最小化（研究モジュールは pandas 等に依存せず標準ライブラリ + DuckDB で完結）。
  - DuckDB を主要データストアとして想定（SQL を駆使してウィンドウ集計や窓関数を活用）。

### Fixed
- なし（初回リリースのためバグ修正履歴なし）

### Security
- 環境変数の必須キー取得時は未設定なら ValueError を送出して明示的に失敗させる（API キー漏れ等の早期検出を容易にする実装）。

---

注:
- 本 CHANGELOG はソースコードの実装内容から機能群・設計思想・API を推測して作成しています。実際のコミット履歴がある場合はそちらに基づく差分記載に置き換えてください。