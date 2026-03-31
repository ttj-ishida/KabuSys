# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注意: 本ファイルはリポジトリ内のコードから実装内容を推測して作成した初期のリリースノートです。

## [Unreleased]

## [0.1.0] - 2026-03-31
初回公開リリース。以下の主要機能・実装を含みます。

### Added
- パッケージ基盤
  - kabusys パッケージの初期実装（バージョン 0.1.0 を package 内に定義）。
  - パッケージの public API として data, strategy, execution, monitoring をエクスポート。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート判定は .git または pyproject.toml を起点に探索（CWD に依存しない）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
  - .env のパース機能を実装（export 構文、引用符・バックスラッシュのエスケープ、行内コメント処理に対応）。
  - settings オブジェクト（Settings クラス）を提供し、J-Quants / kabuステーション / Slack / DBパス / 監視閾値 / 環境種別・ログレベル検証等のプロパティを公開。
    - 必須環境変数未設定時は ValueError を送出。
    - KABUSYS_ENV と LOG_LEVEL の妥当性チェックを実装。

- AI（自然言語処理）機能 (kabusys.ai)
  - news_nlp.score_news
    - raw_news と news_symbols を集約して銘柄ごとのニュースをまとめ、OpenAI（gpt-4o-mini）を用いて銘柄別センチメントを算出して ai_scores テーブルへ書き込み。
    - 処理は記事ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を正確に算出（UTC 換算）して対象記事を選定。
    - チャンク処理（デフォルト最大 20 銘柄/回）、1銘柄あたり記事数上限および文字数トリムの仕組みを実装。
    - JSON モードでのレスポンス検証、スコア ±1.0 のクリップ、レスポンスパース失敗や API エラー時のフェイルセーフ（失敗チャンクはスキップ）を実装。
    - テスト容易性のため _call_openai_api を差し替え可能。
    - DuckDB 0.10 の executemany に関する空リスト回避ロジック（空 params を avoid）を実装。
  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、market_regime テーブルへ日次で冪等書き込み。
    - マクロニュース抽出（マクロキーワードリスト）→ OpenAI での JSON スコア取得 → スコア合成アルゴリズム実装。
    - LLM コールのリトライ（指数バックオフ）と API 障害時のフォールバック（macro_sentiment=0.0）。
    - ルックアヘッドバイアス回避のため datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計。

- データ基盤 (kabusys.data)
  - calendar_management
    - JPX カレンダー管理ロジックを実装（market_calendar テーブルに依存）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等、営業日判定・探索ユーティリティを提供。
    - DB にカレンダー情報がない場合は曜日ベース（平日）でフォールバックする一貫した挙動。
    - calendar_update_job: J-Quants API から差分取得し冪等的に market_calendar を更新する夜間バッチ処理を実装（バックフィル・健全性チェックあり）。
  - pipeline (ETL)
    - ETLResult データクラスを実装（ETL 実行結果の構造化）。
    - 差分更新、バックフィル、品質チェックを想定した ETL 設計（jquants_client 連携、quality モジュール利用）。
    - _table_exists / _get_max_date 等の内部ユーティリティを実装。
  - etl モジュールで ETLResult を再エクスポート。

- リサーチ（ファクター・特徴量解析） (kabusys.research)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離の計算を実装。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER, ROE を算出（EPS=0/欠損時は None）。
    - DuckDB のウィンドウ関数を用いた効率的な SQL 実装。
  - feature_exploration
    - calc_forward_returns: 任意のホライズン（デフォルト [1,5,21]）で将来リターンを計算（horizons の入力検証あり）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコードが 3 未満で None を返す）。
    - rank / factor_summary: ランク変換（同順位は平均ランク）および基本統計量（count/mean/std/min/max/median）を計算。
    - 外部ライブラリに依存せず標準ライブラリ + duckdb で実装。

### Changed
- （初回リリースのためなし）

### Fixed
- （初回リリースのためなし）

### Removed
- （初回リリースのためなし）

### Security
- OpenAI API キーの取り扱いは api_key 引数または環境変数 OPENAI_API_KEY を優先し、未設定時は ValueError を発生させることで明示的なエラーを出す実装。

### Notes / Implementation Details
- ルックアヘッドバイアス対策
  - AI モジュール（news_nlp / regime_detector）およびリサーチ系関数は内部で date.today() を参照せず、すべて target_date を明示的に受け取る設計になっています。
- OpenAI 呼び出し
  - gpt-4o-mini を利用する想定で JSON モードを使い、レスポンス検証・パース耐性（前後余計テキストの復元など）を実装。
  - API エラー（RateLimit, Connection, Timeout, 5xx）に対して指数バックオフでリトライし、最終的にフェイルセーフとして部分スコアをスキップまたは 0.0 を返す方針。
  - テスト用に _call_openai_api を patch して差し替え可能。
- DuckDB 依存性と互換性
  - DuckDB 上の SQL を多用。DuckDB 0.10 における executemany の空リスト問題に対応するため、空 params の場合は実行をスキップするガードを入れている。
- フェイルセーフ設計
  - API 失敗時・データ不足時にプロセス全体が停止しないよう、個別チャンクのスキップやデフォルト値（中立 0.0 / ma200_ratio=1.0 等）を用いる実装を採用。
- ロギング
  - 各処理に詳細な logger メッセージを追加し、失敗箇所や理由が追跡しやすいようにしている。
- 既知の前提・制約
  - 各モジュールは DuckDB 内の特定テーブル（prices_daily, raw_news, raw_financials, market_calendar, ai_scores, news_symbols など）の存在を前提とする。
  - OpenAI API の利用には別途 API キーが必要。

---

もし CHANGELOG に追記したい項目（バグ修正、追加機能、リリース日付の変更等）があれば、その内容を教えてください。必要に応じて Unreleased セクションや過去バージョンの追記も作成します。