# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは Keep a Changelog の形式に準拠しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-31
初回リリース。日本株自動売買システム "KabuSys" のコアライブラリを公開します。主な追加点は以下の通りです。

### Added
- パッケージ基礎
  - src/kabusys/__init__.py
    - パッケージのメタ情報と公開モジュール一覧（data, strategy, execution, monitoring）。
    - バージョン: 0.1.0

- 設定管理
  - src/kabusys/config.py
    - .env ファイルと環境変数から設定を読み込む自動ローダーを実装。
      - 読み込み優先度: OS 環境変数 > .env.local > .env
      - プロジェクトルート判定は __file__ を基点に .git / pyproject.toml を探索（CWD に依存しない）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
    - .env パーサーは以下をサポート:
      - export KEY=val 形式
      - シングル/ダブルクォート、バックスラッシュによるエスケープ
      - インラインコメントの扱い（クォート有無に応じた厳密な処理）
      - OS 環境変数を保護する protected セット（.env.local の上書き制御）
    - Settings クラスを公開（settings インスタンス）
      - 各種必須値取得メソッド（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）
      - パス類は Path オブジェクトで返却（duckdb/sqlite のデフォルトパス設定）
      - KABUSYS_ENV / LOG_LEVEL のバリデーション・ユーティリティ（is_live / is_paper / is_dev）

- AI（ニュース NLP / レジーム検出）
  - src/kabusys/ai/news_nlp.py
    - ニュース記事テキストを銘柄単位で集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを評価して ai_scores テーブルへ書き込む。
    - 特徴:
      - JST 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供（UTC naive datetime を返す）。
      - 1銘柄あたりのトークン肥大対策（記事数上限／文字数上限 _MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
      - 最大バッチサイズ 20 銘柄単位で API コール。
      - 429, ネットワーク断, タイムアウト, 5xx に対する指数バックオフリトライ実装。
      - レスポンス検証（JSON 抽出、results フォーマット検証、未知銘柄の無視、スコア数値化と ±1.0 のクリップ）。
      - 部分失敗に備え、書き込みは取得済みコードのみ DELETE → INSERT（冪等性・他銘柄保護）。
      - テスト容易性: _call_openai_api を patch して差し替え可能。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と
      マクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む。
    - 特徴:
      - prices_daily を用いた MA200 比率算出（ルックアヘッド防止: date < target_date を適用）。
      - マクロニュース抽出（マクロキーワードによるタイトルフィルタ、最大 20 記事）。
      - OpenAI 呼び出し（gpt-4o-mini, JSON mode）による macro_sentiment 評価、失敗時は 0.0 にフォールバック。
      - API 呼び出しに対する再試行とバックオフ、エラーのログ出力。
      - 計算結果は冪等的に market_regime テーブルへ書き込み（BEGIN / DELETE / INSERT / COMMIT、例外時は ROLLBACK）。

- データ処理 / ETL / カレンダー
  - src/kabusys/data/pipeline.py
    - ETLResult dataclass による ETL 実行結果の構造化（品質問題やエラーの収集）。
    - 差分更新、バックフィル、品質チェックのためのユーティリティ（テーブル存在確認、最大日付取得、トレーディングデイ調整等）。
    - J-Quants クライアント（jquants_client）と品質チェックモジュール（quality）を組み合わせる設計。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult を外部公開。
  - src/kabusys/data/calendar_management.py
    - JPX カレンダーの夜間更新ジョブ calendar_update_job を実装（J-Quants から差分取得して market_calendar を冪等更新）。
    - 営業日判定ユーティリティ:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - 設計上の注意:
      - market_calendar が未取得の場合は曜日ベースのフォールバック（週末を非営業日扱い）。
      - DB に一部データがある場合は DB 値を優先し、未登録日は曜日フォールバックで埋めることで一貫性を保つ。
      - カレンダージョブはバックフィル（直近数日を再取得）と健全性チェック（将来過剰日数の検出）を行う。

- リサーチ（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - 定量ファクター計算（Momentum / Volatility / Value / Liquidity の一部）を提供:
      - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（データ不足時は None）。
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（ウィンドウ内データ不足時は None）。
      - calc_value: per, roe（raw_financials の最新レコードを target_date 以前から取得）。
    - DuckDB を活用した SQL ベースの実装（外部 API 非依存、発注 API にはアクセスしない）。
  - src/kabusys/research/feature_exploration.py
    - 研究用途ユーティリティ:
      - calc_forward_returns: 任意ホライズンの将来リターン（デフォルト [1,5,21]）。
      - calc_ic: Spearman ランク相関（IC）計算（レコード不足時は None）。
      - rank: ランク付け（同順位は平均ランク、丸め処理あり）。
      - factor_summary: count/mean/std/min/max/median のサマリー統計量。
    - 外部ライブラリに依存せず標準ライブラリ + DuckDB で実装。

- パッケージ公開 API の整理
  - src/kabusys/ai/__init__.py: score_news を公開
  - src/kabusys/research/__init__.py: 主要関数（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）を再エクスポート

### Changed
- 設計方針 (コード内ドキュメント)
  - 多くのモジュールで「ルックアヘッドバイアス防止」の方針を明確に記述（datetime.today()/date.today() を直接参照しない）。
  - OpenAI 呼び出し部のテスト容易性を考慮し、内部呼び出し関数を patch で差し替え可能にした（ユニットテストしやすい設計）。
  - DuckDB のバージョン差異（executemany の空リスト扱い等）に対応するワークアラウンドを導入。

### Fixed / Robustness
- フォールバックとフェイルセーフの実装強化
  - AI モジュール: API ネットワークエラー／JSON パースエラー／5xx 等のケースで例外を投げず安全にフォールバック（macro_sentiment=0.0、あるいはスコア取得スキップ）する実装。
  - データ不足時の明確な振る舞い（ma200_ratio が計算できない場合は中立値 1.0 を使用、ファクターは None を返す等）。
  - DB 書き込みは冪等性を意識（DELETE → INSERT、トランザクション COMMIT/ROLLBACK の確実な扱い）。
  - calendar_update_job: 取得失敗や異常検知時に 0 を返し安全に終了する。

### Security
- 環境変数/シークレットの取り扱い:
  - Settings は必須のシークレット未設定時に明示的な ValueError を発生させる（誤動作を早期に検出）。
  - .env 読み込みで OS 環境変数を保護する仕組み（protected set）を導入。

### Notes / Known limitations
- OpenAI 依存部分は API キー（api_key 引数 or OPENAI_API_KEY 環境変数）を必要とする。
- JSON モードの応答整形に依存しているため、将来的な OpenAI SDK の仕様変更に注意が必要。
- DuckDB の SQL 方言・バインドの挙動はバージョン差により影響を受ける箇所があるため、運用時は動作確認を推奨。

---

（以降のリリースはここに追記します）