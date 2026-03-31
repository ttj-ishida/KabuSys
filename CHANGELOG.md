# Changelog

すべての非公開の変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従っており、セマンティック バージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-03-31
初回リリース。日本株自動売買プラットフォームのコアライブラリ群を実装しました。主な追加内容は以下の通りです。

### Added
- パッケージ初期化
  - kabusys パッケージの基本情報とバージョンを追加（__version__ = 0.1.0）。
  - public API の __all__ を定義（data, strategy, execution, monitoring）。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - ロード順: OS 環境変数 > .env.local > .env
    - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - プロジェクトルートの検出ロジックを実装（.git または pyproject.toml を探索）。
  - .env ファイルパーサ実装:
    - export KEY=val 形式に対応
    - シングル/ダブルクォートとバックスラッシュエスケープの扱いに対応
    - コメント扱いのルール（クォート内無視、非クォート時の # の扱い）を実装
    - ファイル読み込み失敗時に警告を出す安全な読み込み処理
    - 既存 OS 環境変数を保護する protected オプションを実装
  - Settings クラスを実装し、アプリケーション設定値（J-Quants / kabu API / Slack / DB パス / 監視しきい値 / env / log_level 等）をプロパティ経由で提供。
    - 必須環境変数未設定時は ValueError を送出する _require を実装
    - KABUSYS_ENV、LOG_LEVEL の検証（許容値チェック）
    - パスは Path オブジェクトで返却

- AI モジュール（kabusys.ai）
  - news_nlp モジュール（kabusys.ai.news_nlp）を追加
    - raw_news / news_symbols から記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄ごとのセンチメント（ai_score）を算出し ai_scores テーブルへ書き込む処理を実装
    - バッチ処理（1 API 呼び出しで最大 20 銘柄）・トリム（記事数・文字数上限）を実装
    - 再試行ポリシー（429/ネットワーク/タイムアウト/5xx の指数バックオフ）を実装
    - レスポンスバリデーション（JSON 抽出、results 構造、スコア数値検証、スコアのクリップ）を実装
    - 時刻ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST 相当の UTC 範囲）を提供する calc_news_window を実装
    - 外部依存を最小化し、失敗時はスキップして継続するフェイルセーフ方針を採用
  - regime_detector モジュール（kabusys.ai.regime_detector）を追加
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装
    - マクロニュース取得（raw_news）と LLM 呼び出し（gpt-4o-mini）によるセンチメント算出を実装
    - OpenAI 呼び出しは独立実装とし、API エラー時は macro_sentiment=0.0 にフォールバックする堅牢化を実装
    - レジーム書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で DB へ保存
    - ルックアヘッドバイアス防止の設計（target_date 未満のデータのみ参照）を反映

- データプラットフォーム関連（kabusys.data）
  - calendar_management モジュールを実装
    - market_calendar テーブルに基づく営業日判定 API を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
    - market_calendar が存在しない場合の曜日ベースのフォールバック
    - JPX カレンダーを J-Quants から差分取得して保存する夜間バッチ job（calendar_update_job）を実装（バックフィル・健全性チェックを含む）
  - pipeline / etl 周り
    - ETLResult データクラスを追加（ETL の集計結果・品質問題・エラーを保持）
    - ETL パイプライン用のユーティリティ（差分取得、backfill、品質チェックの考え方）を実装（pipeline モジュールに基づく）
    - data.etl で ETLResult を再エクスポート

- Research（kabusys.research）
  - factor_research を実装
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER/ROE）等のファクター計算関数（calc_momentum, calc_volatility, calc_value）を実装
    - DuckDB 上の SQL ウィンドウ関数を活用して効率的に計算
    - データ不足時の None 扱いやログ出力を実装
  - feature_exploration を実装
    - 将来リターン計算（calc_forward_returns）
    - IC（Information Coefficient）計算（calc_ic）とランク変換ユーティリティ（rank）
    - ファクター統計サマリー（factor_summary）
  - research.__init__ で主要関数を公開し、data.stats の zscore_normalize を再公開

### Changed
- （該当なし — 初回リリース）

### Fixed
- （該当なし — 初回リリース）

### Security
- OpenAI API キーを引数で明示的に渡せる実装を多くの関数でサポート（環境変数依存を緩和）。  
  - ただし API キーの扱いについては利用者側で安全に管理すること（コード中では環境変数 OPENAI_API_KEY を参照）。

Notes / 注意事項
- DuckDB を利用した SQL 処理が多いため、使用する DuckDB のバージョン互換性（executemany に空リスト不可等）に注意しました。コード中に互換性対策（空パラメータ回避、個別 DELETE）を入れています。
- 全体設計は「ルックアヘッドバイアスの防止」と「フェイルセーフ」を重視しています。時刻参照は target_date ベースで行い、API 呼び出し失敗時はスコアをゼロにするか処理をスキップして進行する実装が多く含まれます。
- OpenAI 呼び出し部分はユニットテスト容易性のためモック差し替えを想定した設計（モジュール内 private な呼び出し関数）になっています。

---

作成者: kabusys 開発チーム（コードベースから推測して作成）