# Changelog

すべての非互換な変更は最初に記載してください。  
このファイルは "Keep a Changelog" の形式に準拠しています。  

## [Unreleased]

## [0.1.0] - 2026-04-09
初回リリース。日本株自動売買 / データ基盤 / 研究用ユーティリティ群を含む基本機能を提供します。

### Added
- パッケージ基盤
  - kabusys パッケージの初期バージョンを追加。バージョンは 0.1.0。
  - パッケージ公開インターフェースに data, strategy, execution, monitoring を定義。

- 設定 / 環境変数管理 (`kabusys.config`)
  - .env および環境変数から設定を読み込む自動ロード機能を実装（優先順位: OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）を追加し、CWD に依存しない読み込みを実現。
  - .env のパースを堅牢化（export 形式、クォート内のエスケープ、インラインコメントの取り扱いなど）。
  - Settings クラスを提供し、J-Quants / kabuAPI / LINE / DB / 監視閾値 / システム設定等のプロパティを環境変数から取得する API を追加。
  - 環境変数値の検証（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL など）を実装。
  - 必須変数未設定時に ValueError を投げる _require() を提供。

- AI ニュース NLP (`kabusys.ai.news_nlp`)
  - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメント（ai_score）を算出する score_news を実装。
  - 処理の特徴:
    - 前日 15:00 JST ～ 当日 08:30 JST を対象とするタイムウィンドウ計算（calc_news_window）。
    - 銘柄ごとに記事を最大 N 件・最大文字数でトリムし、最大 20 銘柄ずつバッチで API 呼び出し。
    - JSON Mode を利用し、レスポンスのバリデーションとスコアの ±1.0 クリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ。
    - 部分失敗時に既存スコアを保護するため、書き込みは該当コードのみ DELETE → INSERT（トランザクション）で実施。
  - テスト容易性のため _call_openai_api を patch 可能に実装。
  - ログ出力で処理状況（対象記事数・チャンク数・書込み件数等）を記録。

- 市場レジーム判定 (`kabusys.ai.regime_detector`)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
  - 処理の特徴:
    - DuckDB 上の prices_daily / raw_news を参照して ma200_ratio とニュースタイトルを取得。
    - マクロキーワードリストに基づく記事抽出（最大 20 件）。
    - OpenAI を用いた JSON レスポンスからマクロセンチメントを取得（失敗時は 0.0 にフォールバック）。
    - スコア合成後、market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - API エラーのリトライや 5xx の取り扱い、レスポンスパース失敗時のフェイルセーフ動作を実装。
  - テスト容易性のため _call_openai_api を別実装で提供（news_nlp とは別実装でモジュール結合を避ける）。

- データ基盤 / ETL (`kabusys.data.*`)
  - ETL 結果を表す ETLResult データクラスを追加（pipeline.ETLResult を再エクスポートする etl モジュールを用意）。
  - ETL パイプライン設計（kabusys.data.pipeline）:
    - 差分更新・バックフィル機構、J-Quants クライアントを用いた冪等保存（ON CONFLICT に相当の処理）と品質チェック連携を実装する方針・骨組みを用意。
    - 品質チェックの結果を ETLResult に格納し、has_errors / has_quality_errors プロパティで状態判定可能。
  - マーケットカレンダー管理（kabusys.data.calendar_management）:
    - market_calendar テーブルを用いた営業日判定 API（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - DB 登録値優先、未登録日は曜日ベースのフォールバックを行い、全機能で一貫した挙動を保証。
    - calendar_update_job で J-Quants からの差分フェッチと冪等保存（バックフィル・健全性チェック含む）を実装。
    - テーブル存在チェックや NULL 値に対する警告ログなど堅牢化を実施。
  - jquants_client / quality 等のクライアントモジュールと連携する設計。

- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離率を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials からの EPS/ROE を用いた PER/ROE 計算（最新財務データを target_date 以前から取得）。
    - いずれも DuckDB 上の prices_daily / raw_financials のみ参照し、ルックアヘッドバイアス防止に配慮。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - calc_forward_returns: 将来リターン（指定ホライズン）を一括 SQL で計算（ホライズンの妥当性検査あり）。
    - calc_ic: スピアマンのランク相関（IC）を計算するユーティリティ（必要サンプル数チェックあり）。
    - rank: 平均ランク（同順位は平均ランク）を計算する実装（丸めで ties 対応）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。

- 共通実装上の設計・品質配慮
  - ルックアヘッドバイアス対策として、各モジュールで datetime.today() / date.today() の直接参照を避け、target_date ベースで処理する実装方針を徹底。
  - OpenAI 呼び出しについてはリトライ・バックオフ・パース検証・フェイルセーフ（失敗時はスキップまたは既定値）を組み込み、外部 API の不安定性に耐える設計。
  - DuckDB のバージョン差異（executemany の空リスト扱い等）に配慮した実装（空パラメータは回避）。
  - ロギングで詳細な処理情報（警告・情報）を出力することで運用観察を容易に。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

---

注: 実装は各モジュールの Docstring / ログメッセージ / 関数シグネチャに従って推測して記載しています。実際の運用時は README やドキュメントと合わせて確認してください。