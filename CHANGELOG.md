# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」準拠です。  
リリース日付はコードベースから推定した作成日を使用しています（必要に応じて調整してください）。

## [Unreleased]

（現時点で未リリースの変更はありません）

---

## [0.1.0] - 2026-04-04

初回公開リリース。

### 追加 (Added)
- パッケージの追加
  - kabusys パッケージ全体を提供。
  - パッケージバージョン: 0.1.0

- 設定・環境変数サポート（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を検索）から自動ロードする仕組みを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パースの堅牢化:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの取り扱い（クォート有無での違いを考慮）
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB パス / 監視設定 / ログレベル等をプロパティで取得可能。
  - 必須環境変数未設定時は明示的に ValueError を発生させる _require を実装。
  - 有効な環境値の検証（KABUSYS_ENV, LOG_LEVEL 等）。

- AI 関連モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いて銘柄毎のニュースを集約し、OpenAI（gpt-4o-mini、JSON mode）でセンチメントを評価。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大対策（記事数・文字数制限）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - レスポンスの厳密なバリデーションとスコアの ±1.0 クリッピング。
    - スコアは ai_scores テーブルへ冪等的に（DELETE → INSERT）書き込み。部分失敗時に既存の他銘柄スコアを保持する設計。
    - テスト用に _call_openai_api を patch して差し替え可能。
    - calc_news_window(target_date) を提供（JST基準のニュースウィンドウを UTC naive datetime で返す）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - OpenAI 呼び出しは JSON パース・リトライ・フェイルセーフ（API失敗時 macro_sentiment=0.0）を備える。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - テストのため _call_openai_api を差し替え可能。

- データプラットフォーム関連（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルの存在チェック、DB優先での営業日判定、DBがない場合の曜日ベースフォールバックを実装。
    - next_trading_day / prev_trading_day / get_trading_days / is_trading_day / is_sq_day を提供。
    - calendar_update_job により J-Quants からの差分取得と冪等的保存を行う仕組み（バックフィル、健全性チェックを含む）。
    - 最大探索日数を設定し無限ループを防止。

  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラー等を集約）。
    - 差分更新、バックフィル方針、品質チェックとの連携（quality モジュールを利用）を念頭に設計。

- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）
    - Value（PER、ROE、raw_financials からの最新値使用）
    - Volatility / Liquidity（20日 ATR、平均売買代金、出来高比率）
    - DuckDB を用いた SQL 主導の実装。データ不足時は None を返す設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（複数ホライズン対応、horizons 引数で制御）
    - IC（Spearmanランク相関）計算 util
    - ファクター統計サマリー（count/mean/std/min/max/median）
    - 自前実装で pandas 等に依存しない設計。

- その他
  - モジュール間の結合を避ける設計（例：regime_detector は news_nlp の内部 _call_openai_api を参照しない）。
  - DuckDB に対するトランザクション処理と ROLLBACK のフォールバックログ出力を実装（DB 書き込み失敗時の安全確保）。
  - 多くの関数でルックアヘッドバイアス対策（date.today()/datetime.today() を直接参照しない、target_date に基づく処理）を採用。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。
- 実装上のフェイルセーフ・ログ出力を充実させ、API失敗やDB問題時にアプリ全体が致命的に停止しない設計を採用。

### 非推奨 (Deprecated)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY で供給する必要あり。未設定時は ValueError を発生させるため、キーの管理に注意してください。
- .env 自動読み込みは環境変数で明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

## マイグレーション / 利用上の注意
- 必須テーブル（DuckDB）:
  - prices_daily, raw_news, ai_scores, market_regime, market_calendar, news_symbols, raw_financials などの存在を前提とする機能が多くあります。ETL を実行し DB を初期化してから各機能を利用してください。
- OpenAI 連携:
  - gpt-4o-mini を想定した JSON Mode を使用しています。API レスポンスの形式や rate-limit 挙動に依存するため、運用時は API キーと割当に注意してください。
- テスト・モック:
  - OpenAI 呼び出し箇所は module 内の _call_openai_api を unittest.mock.patch で差し替えてテスト可能です。
- 環境変数:
  - .env の自動ロード動作はプロジェクトルート検出に依存します。パッケージ配布後の利用やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使うか明示的に環境変数を設定してください。

---

貢献・バグ報告・改善提案は issue/PR を通じて歓迎します。