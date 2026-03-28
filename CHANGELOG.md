# Changelog

すべての注目すべき変更点をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

現在のリリース方針:
- 日付はリリース日（YYYY-MM-DD）で記載しています。
- 各エントリは Added / Changed / Fixed / Deprecated / Removed / Security のカテゴリで整理しています。

## [Unreleased]

## [0.1.0] - 2026-03-28
### Added
- パッケージ初期リリース "KabuSys"。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）。
  - 主なサブパッケージ: data, research, ai, execution, strategy, monitoring（__all__ による公開）。

- 環境設定 / 自動 .env 読み込み機能（src/kabusys/config.py）。
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能（テスト用）。
  - export KEY=val 形式やシングル/ダブルクォート、エスケープ、インラインコメントなどに対応する堅牢なパーサ実装。
  - OS 環境変数を保護する protected キー群による上書き制御。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境（development/paper_trading/live） / ログレベル等の取得を容易に。
  - 未設定の必須環境変数は ValueError を投げる（_require）。

- AI モジュール（src/kabusys/ai/*）。
  - ニュースセンチメントスコアリング: score_news（news_nlp.py）。
    - gpt-4o-mini を JSON Mode で呼び出し、銘柄ごとの -1.0〜1.0 のスコアを ai_scores テーブルへ書込み。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
    - バッチ処理（最大20銘柄 / チャンク）、1銘柄あたり記事数/文字数制限、レスポンス検証、スコアクリップ、DuckDB への冪等書込み（DELETE → INSERT）。
    - リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフを実装。
    - テスト用に _call_openai_api をパッチ可能にして差し替えを容易に。
  - 市場レジーム判定: score_regime（regime_detector.py）。
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書込み。
    - マクロキーワードによるフィルタ、LLM 呼び出し（gpt-4o-mini）、リトライ/フェイルセーフ（API失敗時 macro_sentiment=0.0）。
    - _calc_ma200_ratio/_fetch_macro_news/_score_macro 等の内部関数を公開せず実装。

- Data モジュール（src/kabusys/data/*）。
  - カレンダー管理（calendar_management.py）。
    - JPX カレンダー取得・夜間バッチ更新用 calendar_update_job 実装（J-Quants クライアント経由で差分取得→保存）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定ユーティリティを提供。
    - market_calendar が未取得の場合は曜日ベース（土日除外）でフォールバックする堅牢な設計。
    - 最大探索日数・バックフィル方針・健全性チェックを実装して異常ケースを防止。
  - ETL パイプライン（pipeline.py / etl.py）。
    - ETLResult データクラスを公開（etl.py から再エクスポート）。
    - 差分更新、バックフィル、品質チェック（quality モジュール経由）、idempotent な保存（jquants_client.save_* を想定）等の設計に基づくユーティリティ。
    - DuckDB の存在確認や最大日付取得などの内部ユーティリティを実装。

- Research モジュール（src/kabusys/research/*）。
  - factor_research.py:
    - Momentum（1M/3M/6M リターン）、200 日 MA 乖離、Volatility（20 日 ATR）、
      Liquidity（20 日平均売買代金、出来高比率）、Value（PER, ROE）を計算する関数を提供（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上の SQL とウィンドウ関数を活用した実装。データ不足時の None 取り扱いとログ出力。
    - 原データのみ参照し、実際の取引や外部 API へはアクセスしない設計。
  - feature_exploration.py:
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応）。
    - IC（Spearman の ρ）計算（calc_ic）、ランク変換ユーティリティ（rank）。
    - ファクター統計サマリー（factor_summary）。
    - 外部依存を持たず標準ライブラリと DuckDB のみで実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数の読み込みで OS 環境変数を保護する protected 機能を実装（.env の上書きを制御）。
- OpenAI API キーは引数から注入可能で、未設定時は ValueError を返すなど誤配置を検出しやすくしている。

### Notes / Implementation details
- ルックアヘッドバイアス対策: 日付参照に datetime.today()/date.today() を直接使わず、target_date を明示的に受け取る設計を多くの関数で採用。
- DuckDB を主なデータバックエンドとして想定し、SQL と Python の組合せで計算・集約処理を実装。
- OpenAI 呼び出し箇所は JSON Mode を使い厳密な JSON 出力を前提に実装。レスポンスパースやバリデーションに堅牢性を持たせている。
- API リトライやフェイルセーフ（API失敗時は無害なデフォルト値を使用、例: macro_sentiment=0.0）を各所で採用。
- テスト容易性のため、OpenAI 呼び出しを差し替え可能な内部関数（_call_openai_api）を用意。
- DuckDB executemany に関する互換性対策（空リスト不可）に対応した実装を行っている。
- 各モジュールは「DB のみ参照する」「本番発注等の副作用を持たない」方針を明記。

## Deprecated
- （初回リリースのため該当なし）

## Removed
- （初回リリースのため該当なし）

(注) 本 CHANGELOG はコードベースから推測して作成したリリースノートです。実際のリリース履歴や日付はリポジトリ運用ポリシーに合わせて調整してください。