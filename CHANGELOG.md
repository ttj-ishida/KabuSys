# CHANGELOG

このプロジェクトは Keep a Changelog の慣例に従って変更履歴を管理します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

- すべての変更はセマンティックバージョニングに従います。
- 日付はリリース日を示します。

## [Unreleased]

## [0.1.0] - 2026-04-03
初回リリース。本バージョンでは日本株自動売買フレームワークの基礎機能を提供します。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージ公開インターフェースに data / research / ai / ... モジュールを含める設定。

- 設定管理
  - 環境変数・設定読み込み機能（kabusys.config.Settings）。
  - .env / .env.local の自動ロード機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env 解析の堅牢化（export 形式、クォート中のエスケープ、インラインコメント処理）。
  - 必須環境変数取得時のエラーチェック（_require）と環境値の検証（KABUSYS_ENV, LOG_LEVEL）。
  - パス系設定は Path 型で返却（duckdb/sqlite/pid/kill flag 等）。

- データプラットフォーム / ETL
  - ETL の公開インターフェース（ETLResult の定義、kabusys.data.pipeline）。
  - 差分取得・保存・品質チェックを想定した ETLResult（品質問題の収集、エラー集約、辞書化ユーティリティ）。
  - DuckDB を想定したテーブル存在チェックや最大日付取得ユーティリティ（pipeline 内部ユーティリティ）。

- カレンダー管理
  - market_calendar を用いた営業日判定ロジック（kabusys.data.calendar_management）。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
    - DB 登録データ優先、未登録日は曜日ベースのフォールバック。
    - 最大探索日数制限および健全性チェックの実装。
  - 夜間バッチジョブ calendar_update_job（J-Quants からの差分取得・保存・バックフィルロジック）。
  - J-Quants クライアント（jquants_client）との連携を想定。

- AI（ニュース NLP / レジーム判定）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp.score_news）
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ投入してスコアを取得。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST の記事を対象（UTC に変換して DB 比較）。
    - バッチ処理: 最大 20 銘柄/コール、記事数/文字数のトリム制御（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - レスポンス検証: JSON 抽出、results 配列の構造検証、コード一致・数値検証、±1.0 でクリップ。
    - 冪等書き込み: ai_scores テーブルに対して対象コードのみ DELETE → INSERT（部分失敗時に既存データを保護）。
    - エラー耐性: 429/ネットワーク断/タイムアウト/5xx は指数バックオフでリトライ、その他エラーはスキップ（フェイルセーフ）。
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
    - ETF 1321（日経225連動）200日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成し、日次で regime_score/regime_label を market_regime テーブルへ保存。
    - マクロニュース抽出はキーワードベース（複数キーワード）でタイトルを取得して LLM に渡す。
    - OpenAI 呼び出しは専用の呼出し関数（テスト時に差し替え可能）を用意。
    - API 失敗時は macro_sentiment=0.0 にフォールバックし処理継続（フェイルセーフ）。
    - DB 書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等実装、失敗時は ROLLBACK。

- リサーチ / ファクター
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離率を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials と株価を組み合わせて PER/ROE を算出（最新財務データを target_date 以前から取得）。
    - 実装は DuckDB SQL を用いたウィンドウ関数中心。データ不足時は None を返す設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンのスピアマン（ランク相関）IC を計算。サンプル不足（<3）時は None。
    - factor_summary: count/mean/std/min/max/median を計算。
    - rank: 同順位の平均ランク処理（float の丸めで ties 検出の安定化）。

- 汎用性 / 実装上の配慮
  - すべての「日付」を引数で受け取り内部で datetime.today()/date.today() を参照しない実装によりルックアヘッドバイアスを防止。
  - OpenAI API 呼び出し部分に明示的なタイムアウトと JSON Mode レスポンス処理を使用。
  - DuckDB との互換性を考慮した executemany の扱い（空リストを渡さないガード）や日付型変換ユーティリティを実装。
  - ロギングを多用し、フェイルセーフ時に WARNING/INFO を記録。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし（実装内で部分的に堅牢化を実施。例: API エラー時のフォールバック動作、JSON パース回復処理など）。

### セキュリティ (Security)
- 初回リリースのため該当なし。

---

注記:
- 本 CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートやリポジトリの履歴が存在する場合は、そちらに合わせて修正してください。