Keep a Changelog
=================

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」仕様に準拠します。

フォーマット
-----------
- 変更はセクション (Added, Changed, Fixed, Security, etc.) に分類します。
- 日付は YYYY-MM-DD 形式。
- バージョン番号はパッケージの __version__（現状 0.1.0）に合わせています。

Unreleased
----------
（現在未リリースの変更はここに記載）

[0.1.0] - 2026-04-04
--------------------
初回公開リリース。以下の主要機能および設計上の注意点を実装しています。

Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - サブパッケージエクスポート: data, strategy, execution, monitoring。

- 設定 / 環境変数読み込み（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルートの自動検出ロジック（.git または pyproject.toml を探索）により CWD に依存しない読み込みを実現。
  - .env と .env.local の優先順位・上書きルールを実装（OS 環境変数は保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプション。
  - Settings クラスを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境種別 / ログレベル等のプロパティ）。

- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp.score_news:
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）でセンチメントを評価。
    - チャンク処理（最大 20 銘柄/回）、トークン肥大化対策（記事数・文字数制限）。
    - レスポンスの堅牢なバリデーション（JSON 抽出、型チェック、スコアクリップ）。
    - DuckDB へ idempotent に ai_scores を書き込み（DELETE→INSERT の方針で部分失敗耐性を確保）。
    - API エラー（429/タイムアウト/ネットワーク/5xx）に対する指数バックオフリトライ実装。
    - ルックアヘッドバイアス対策: datetime.today() を直接参照しない設計（target_date ベース）。

  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で market_regime を算出・保存。
    - マクロキーワードで raw_news をフィルタ、OpenAI を呼び出して macro_sentiment を算出（記事なし時は呼ばない）。
    - API 呼び出しのリトライ / フェイルセーフ（失敗時は macro_sentiment=0.0）を実装。
    - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。

- リサーチ（kabusys.research）
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を算出。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を算出。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を算出（EPS が 0/欠損 の場合は None）。
    - 設計上、DuckDB の SQL ウィンドウ関数を活用して効率的に計算。外部 API にはアクセスしない。

  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: Spearman（ランク相関）で IC を計算（結合・除外処理を行う）。
    - rank / factor_summary: ランク付け、基本統計量（count/mean/std/min/max/median）を算出。
    - 外部依存を用いず純粋 Python + DuckDB で実装。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar に基づく営業日判定、next/prev/get_trading_days、is_sq_day を提供。
    - DB 登録がない場合でも曜日ベースのフォールバックを実装。
    - calendar_update_job: J-Quants API からの差分取得・バックフィル・健全性チェック・冪等保存を実装（jquants_client を利用）。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL の実行結果、品質問題の収集、エラーリスト等）。
    - ETL パイプライン設計に基づく差分取得・品質チェック・保存処理の基盤を準備。
    - DuckDB テーブル存在チェック、最大日付取得等のユーティリティを用意。

Changed
- （初版のため該当なし）

Fixed
- レスポンスパース等での堅牢化:
  - OpenAI の JSON mode で前後余計なテキストが混ざる場合に備えた復元ロジックを実装（最外部の {} を抽出してパースを試行）。
  - news_nlp におけるスコアの数値チェックと有限性検査（NaN/Inf を除外）。
  - DuckDB に対する executemany の空パラメータ問題への対策（空時には実行しないガード）。
  - calendar_management / data 側で NULL や欠損データに対するフォールバックおよび警告ログ出力を追加。

Security
- 環境変数読み込み時に OS 環境変数を保護する設計（.env による上書きを制御）。
- OPENAI_API_KEY や各種トークンは Settings 経由で明示的に取得するよう設計。未設定時には ValueError を送出して安全に失敗。

Notes / Behavior / Migration
- OpenAI 関連:
  - API キーは引数 api_key または環境変数 OPENAI_API_KEY から取得。
  - API 呼び出しは gpt-4o-mini を想定し JSON Mode を利用する設計。
  - API 失敗時は多くの箇所で例外を投げずにログ警告とデフォルト値（0.0 等）で継続するフェイルセーフ戦略を採用。

- 必要な DuckDB テーブル（想定）
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等（各モジュールが参照/更新）。

- ローカル実行・テスト:
  - 自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - OpenAI 呼び出しはユニットテスト用に _call_openai_api を patch することで差し替え可能な設計。

- ルックアヘッドバイアス対策:
  - 全ての日付操作は target_date に依存する設計で、datetime.today()/date.today() を直接参照しない箇所が多く、バッチ再現性を重視。

Acknowledgements / Limitations
- 初期バージョンのため以下は未実装または将来的な拡張候補:
  - Strategy / Execution / Monitoring の具体的な発注ロジックや監視エージェントの詳細（公開インターフェースは存在するが実装状況に応じた追加が必要）。
  - PBR・配当利回り等の追加ファクターは未実装（calc_value に注記あり）。
  - J-Quants / kabu ステーションとの具体的な認証フロー・API クライアント実装（jquants_client は参照済みだが、実装の詳細に依存）。

お問い合わせ
- 本 CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノート作成時は、リリース管理・コミット履歴・リリースコメントに基づいた追記・修正を推奨します。