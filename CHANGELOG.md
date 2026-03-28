# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog のフォーマットに従い、セマンティックバージョニングを採用します。

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-28
初回リリース

### Added
- パッケージ基盤
  - kabusys パッケージの公開（__version__ = 0.1.0）。
  - モジュール分割: data, research, ai, config, etc.

- 環境設定 / 設定管理（kabusys.config）
  - .env / .env.local ファイルと OS 環境変数の統合読み込み機能を実装。
  - プロジェクトルート判定ロジックを導入（.git または pyproject.toml を基準に探索）。これによりカレントワーキングディレクトリに依存しない自動ロードが可能。
  - .env のパース機能を強化。export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、行末コメント処理をサポート。
  - 自動読み込みの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを導入し、J-Quants / kabuステーション / Slack / DB パス / 実行環境等の設定をプロパティ経由で取得可能。
  - 環境値の妥当性チェック（KABUSYS_ENV、LOG_LEVEL 等）を実装。
  - OS 環境変数を保護する protected オプションによる .env 上書き制御。

- データ基盤（kabusys.data）
  - calendar_management: JPX カレンダー管理と営業日判定ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB（market_calendar）データがない場合は曜日ベースのフォールバックを行う。
    - 夜間バッチジョブ calendar_update_job により J-Quants から差分取得して冪等的に保存。
    - 健全性チェック、バックフィル、最大探索日数の制約による安全設計。
  - pipeline / ETL: ETLResult データクラスと ETL パイプラインの基礎（差分取得、保存、品質チェック設計）。
    - ETL 結果・品質問題の集約（quality モジュールとの連携を想定）。
    - DuckDB と組み合わせた最終取得日の判定等ユーティリティ実装。
  - etl モジュールの公開インターフェース（ETLResult の再エクスポート）。

- AI（kabusys.ai）
  - news_nlp: ニュース記事を銘柄ごとに集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄別センチメント(ai_score) を ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST、UTC へ変換）を提供（calc_news_window）。
    - バッチサイズ、1銘柄あたりの最大記事数／最大文字数制限、JSON Mode レスポンスのバリデーション、スコアのクリップ処理を実装。
    - レート制限(429)、ネットワーク断、タイムアウト、5xx に対する指数バックオフによるリトライ実装。
    - レスポンスパース失敗や不正なスコアはスキップ（フェイルセーフ）。部分成功時に既存スコアを保護するため、取得済みコードのみを DELETE→INSERT で置換。
    - テスト容易性のため _call_openai_api を patch して差し替え可能に設計。
  - regime_detector: 市場レジーム判定ロジックを実装。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次で 'bull'/'neutral'/'bear' を判定し market_regime テーブルへ冪等書き込み。
    - マクロ記事抽出（マクロキーワード一覧）、OpenAI 呼び出し（gpt-4o-mini）による JSON レスポンスの取り扱い、リトライ／フェイルセーフ設計を実装。
    - ルックアヘッドバイアス防止の設計（date 引数ベース、DB クエリに date < target_date 等）。

- 研究（kabusys.research）
  - factor_research: モメンタム・ボラティリティ・バリュー等のファクター計算を実装。
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離など。
    - calc_volatility: 20 日 ATR、ATR 比率、20日平均売買代金、出来高比率など。
    - calc_value: PER / ROE（raw_financials からの最新財務データ結合）。
    - 全関数とも DuckDB の prices_daily / raw_financials のみを参照し、本番発注等には影響しない設計。
  - feature_exploration: 将来リターンや IC 計算・統計サマリー用ユーティリティを実装。
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得する効率的クエリ。
    - calc_ic: スピアマンランク相関（Information Coefficient）の計算。必要レコード数が不足する場合は None を返す。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を計算。

- DuckDB 統合
  - 各モジュールで DuckDB 接続（DuckDBPyConnection）を受け取り SQL と Python を組み合わせた実装を採用。

- ロギングと堅牢性
  - 各所で詳細なログ出力を追加（info/debug/warning/exception）。
  - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT を用いた冪等操作。例外時は ROLLBACK を試行しログ出力。
  - 外部 API 失敗時のフォールバック（例: macro_sentiment=0.0、空スコアスキップ）により処理継続性を確保。

### Changed
- 新規初回リリースのため該当なし。

### Fixed
- 新規初回リリースのため該当なし。ただし以下の点を設計として明記:
  - .env 読み込み時、既存 OS 環境変数を保護するため protected 機構を導入。
  - OpenAI API のエラー処理で status_code の有無に依存しない安全な取り扱いを実装。

### Deprecated
- なし

### Removed
- なし

### Security
- なし（ただし API キー未設定時は明示的に ValueError を投げることで、安全な失敗を促す設計になっています）

---

注記:
- 本 CHANGELOG は提供されたコードから設計・挙動を推測して作成しています。実際のリリースノート作成時はコミット履歴・リリース目的に応じて調整してください。