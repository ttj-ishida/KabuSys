# Changelog

すべての変更は Keep a Changelog の形式に従い、重要な、利用者向けの変更点を記載します。  
フォーマット: https://keepachangelog.com/ja/

最新更新日: 2026-04-01

## [Unreleased]

（現在のブランチにリリース前の変更がある場合に使用してください。特に未リリースの差分はありません。）

---

## [0.1.0] - 2026-04-01

初期リリース。日本株自動売買プラットフォーム「KabuSys」のコア機能群を実装しています。
主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - kabusys パッケージの初期化ファイルを追加。バージョン情報（0.1.0）と主要サブパッケージの公開 API を定義（data, strategy, execution, monitoring）。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
  - .env パーサを実装（export プレフィックス対応、シングル／ダブルクォートのエスケープ処理、行内コメントの扱い等）。
  - 環境変数必須チェック（_require）と Settings クラスを追加。J-Quants、kabu API、Slack、DB パス、監視しきい値、実行環境やログレベルのバリデーションを提供。
  - KABUSYS_ENV、LOG_LEVEL の検証と is_live/is_paper/is_dev ユーティリティ。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を元に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）にバッチ送信して銘柄別センチメント（ai_score）を計算・ai_scores テーブルへ書き込み。
    - チャンク処理（デフォルト 20 銘柄/回）、1 銘柄あたりの記事数上限と文字数トリム、JSON Mode のレスポンス検証、スコアの ±1.0 クリップ。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、失敗時のフェイルセーフ（スキップして継続）。
    - DB 書き込みは部分的失敗に備えて対象コードのみ DELETE → INSERT の冪等更新を実装。DuckDB 互換性のため executemany の空パラメータ回避など考慮。
    - calc_news_window ユーティリティを提供（JST ベースのニュースウィンドウを UTC naive datetime で返す）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次 market_regime を判定・保存する score_regime を追加。
    - OpenAI 呼び出しのリトライ／バックオフ、API 失敗時の macro_sentiment=0.0 フェイルセーフ、JSON パース失敗時のフォールバック。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。
    - 外部依存（news_nlp）の内部結合を避け、必要箇所で独立した呼び出し実装を採用。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを追加。取得件数・保存件数・品質チェック結果・エラー概要を格納。to_dict により品質問題を辞書化。
    - 差分更新、バックフィル、品質チェック、jquants_client 経由の idempotent 保存（設計方針とインターフェース）を実装（内部ロジックの土台）。
  - ETL 公開インターフェース（kabusys.data.etl）に ETLResult を再エクスポート。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルの管理と JPX カレンダー差分取得ジョブ（calendar_update_job）を追加。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを提供。DB データ優先、未登録日は曜日ベースでフォールバックする一貫性のあるロジック。
    - カレンダー更新はバックフィル（日数調整）と健全性チェック（極端な将来日付の検出）を保持。
    - DuckDB の日付型・NULL 値扱いに配慮した実装。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20 日 ATR、ATR 比率）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER、ROE）を計算する関数を追加（calc_momentum, calc_volatility, calc_value）。
    - DuckDB のウィンドウ関数と SQL 組合せで実装。データ不足時は None を返す設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク付けユーティリティ（rank）、ファクター統計サマリー（factor_summary）を提供。
    - Spearman（ランク相関）を内部実装し、ties の処理や最小サンプル制約を考慮。
  - research パッケージは主要ユーティリティを __all__ で公開（zscore_normalize を data.stats から再利用）。

### Changed
- なし（初回リリースのため「変更」は無し）

### Fixed
- なし（初回リリース）

### Notes / 設計上の重要点
- ルックアヘッドバイアス回避
  - AI モジュールやリサーチ機能では datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を与える設計を採用。DB クエリも target_date より前のみ参照するなど、バックテスト/合成評価でのルックアヘッドを防止。
- API 呼び出しの堅牢性
  - OpenAI（gpt-4o-mini）呼び出しは JSON mode を利用、429/ネットワーク/タイムアウト/5xx に対して指数バックオフを実装。重大な失敗はログ出力して個別処理をスキップするフェイルセーフ設計。
- DB 書き込みの冪等性
  - market_regime / ai_scores 等への書き込みは DELETE → INSERT または ON CONFLICT の冪等操作を想定。DuckDB の制約（executemany の空リスト不可等）に配慮した実装。
- DuckDB 互換性
  - 日付データの取り扱い、情報スキーマ参照、executemany の扱いなど DuckDB バージョン差分を考慮した実装がなされています。
- 環境変数の自動読み込み
  - .env の自動読み込みはプロジェクトルート探索に依存するため、パッケージ配布後も CWD に依存せず動作するよう設計。ただし CI/テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

---

開発・利用にあたっての補足
- OpenAI API を利用する機能（news_nlp, regime_detector, その他将来の AI 機能）は OPENAI_API_KEY の設定が必須（Settings 参照）。api_key 引数で明示的に注入も可能。
- J-Quants / kabu API / Slack 連携の設定は Settings の環境変数名を参照。.env.example 等に従い設定してください。
- DuckDB によるローカルデータ管理（デフォルト path は data/kabusys.duckdb）を想定しています。監視用 SQLite（デフォルト data/monitoring.db）も利用可能。

もしリリースノートの粒度（モジュール別の個別項目、既知の制限や将来予定の変更点等）を細かくしたい場合は、望むフォーマットや追加で注記したい観点（セキュリティ、互換性、移行手順等）を教えてください。