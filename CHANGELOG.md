# Changelog

すべての重要な変更はこのファイルに記載します。  
このプロジェクトはセマンティックバージョニングに従います。詳細は Keep a Changelog (https://keepachangelog.com/ja) を参照してください。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回公開リリース。本リリースでは日本株のデータパイプライン／研究用ユーティリティ／ニュースNLP・市場レジーム判定を中心とした基盤機能を実装しています。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__version__ = "0.1.0"）。公開モジュール: data, strategy, execution, monitoring。
- 環境設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダ実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env パーサの実装: コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - .env 読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数保護（protected set）を実装。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト用）。
  - Settings クラスを公開（settings オブジェクト）: J-Quants / kabuAPI / Slack / DB パス / 環境（development/paper_trading/live）/ログレベルなどの取得とバリデーションを提供。必須変数未設定時は ValueError を送出。
  - デフォルト DB パス: DuckDB `data/kabusys.duckdb`、SQLite `data/monitoring.db` を設定。

- AI 関連 (`kabusys.ai`)
  - ニュースNLP スコアリング (`news_nlp.score_news`)
    - 指定日の前日 15:00 JST ～ 当日 08:30 JST を対象ウィンドウとして記事を集約し、OpenAI（gpt-4o-mini + JSON Mode）にバッチ送信して銘柄別センチメント（-1.0〜1.0）を算出・ai_scores テーブルへ書込。
    - バッチ処理（最大 _BATCH_SIZE＝20 銘柄/コール）、1銘柄あたり最大記事数・文字数制限、レスポンスのバリデーション、スコアの ±1 クリップを実装。
    - リトライロジック（429、接続断、タイムアウト、5xx に対する指数バックオフ）とフェイルセーフ（失敗時は該当チャンクをスキップ）。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（unittest.mock.patch を想定）。
  - 市場レジーム判定 (`regime_detector.score_regime`)
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定・market_regime テーブルへ冪等的に保存。
    - マクロキーワードによる raw_news フィルタ、OpenAI 呼び出し（gpt-4o-mini）、API失敗時は macro_sentiment=0.0 のフォールバック、リトライとログ出力を実装。
    - ルックアヘッドバイアス回避の設計（target_date 未満のデータのみ参照、date.today() を直接参照しない）を採用。
  - AI モジュールは api_key 引数を受け取り、未指定時は環境変数 OPENAI_API_KEY を参照（未設定なら ValueError）。

- データ処理・ETL (`kabusys.data`)
  - ETL 結果の共通データクラス `ETLResult` を実装・公開（kabusys.data.ETLResult）。
  - パイプラインユーティリティ (`pipeline.py`)：差分取得・保存・品質チェック方針の基盤実装（DuckDB接続前提、バックフィル、品質問題の集約など）。
  - カレンダー管理 (`calendar_management.py`)
    - JPX 市場カレンダー管理ロジック（market_calendar の存在確認、DB優先の営業日判定、曜日フォールバック、next/prev/get_trading_days、is_sq_day、夜間バッチ更新 job）。
    - calendar_update_job: J-Quants API からの差分取得・保存フロー、バックフィル日数、健全性チェック（未来日付が大きすぎる場合のスキップ）を実装。
    - DB にデータがまばらな場合でも一貫した判定ができる設計。

- 研究用ユーティリティ (`kabusys.research`)
  - ファクター計算 (`factor_research`)
    - Momentum：1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）等の計算（DuckDB SQL ベース）。
    - Volatility：20日 ATR、相対 ATR、20日平均売買代金、出来高比率の計算。
    - Value：最新の raw_financials を用いて PER, ROE を計算（EPS が 0/欠損 の場合は None）。
    - いずれも prices_daily / raw_financials のみ参照し、実取引 API にはアクセスしない。
  - 特徴量探索 (`feature_exploration`)
    - 将来リターン calc_forward_returns（任意ホライズン）、IC（Spearman の ρ）計算 calc_ic、ランク化ユーティリティ rank、統計サマリー factor_summary を実装。
    - pandas 等に依存しない純標準ライブラリ実装。

- その他
  - news_nlp / regime_detector / score_news 等で OpenAI 呼び出し結果の JSON Mode を厳密にパースするための復元ロジックを実装（前後雑多なテキスト混入時に最外の {} を抽出する等）。
  - DuckDB を前提とした SQL 実装と互換性考慮（executemany の制約回避、list 型バインド回避、date 変換ユーティリティなど）。
  - ロギングと詳細な WARN/INFO メッセージを多数追加（データ不足、API失敗、ROLLBACK 失敗等）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

### 注意事項 / 設計上の重要点
- 全体を通して「ルックアヘッドバイアス防止」を重視：内部実装では datetime.today()/date.today() を直接参照する処理を避け、score やウィンドウは caller が指定する target_date に基づく設計になっています。
- OpenAI API 呼び出しは外部サービス依存のため、失敗時は安全側のフォールバック（スコア 0.0 など）を採用し、プロセスの全体停止を避ける実装になっています。ただし API キー未設定時は明示的に ValueError を発生させます。
- DB 書き込みは冪等性を意識（DELETE→INSERT または ON CONFLICT 相当の保存）しており、部分失敗時に既存の他銘柄データを不用意に消さないよう配慮しています。
- テスト容易性のため、OpenAI 呼び出し部はモック差し替えを想定した実装になっています（内部関数 _call_openai_api をパッチ可能）。

---

開発や利用時に発見された問題や改善提案は CHANGELOG に追記します。