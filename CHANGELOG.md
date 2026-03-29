# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはまだ初期リリースの段階です。主な追加機能・設計方針・注意点を日本語でまとめています。

現在日付: 2026-03-29

## [Unreleased]
- なし

## [0.1.0] - 2026-03-29
初回公開リリース。

Added
- パッケージの初期バージョンを設定
  - kabusys.__version__ = "0.1.0"
  - top-level の公開モジュールを __all__ で定義（data, strategy, execution, monitoring）

- 環境変数／設定管理（kabusys.config）
  - .env ファイル（.env / .env.local）および OS 環境変数からの自動読み込みを実装
    - プロジェクトルートの自動検出: .git または pyproject.toml を基準に探索（CWD 非依存）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能
    - .env ファイルのパースは export KEY=val、引用符（シングル/ダブル）・エスケープ・コメント処理に対応
    - .env.local は .env を上書き（ただし OS 環境変数は保護）
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得
    - J-Quants / kabu ステーション / Slack / DB パス等の設定プロパティ
    - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の検証ロジックを実装
    - デフォルトのデータベースパス（DUCKDB_PATH, SQLITE_PATH）を設定

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON モードでバッチ評価して ai_scores テーブルへ書込み
  - 特徴
    - JST ベースのニュース収集ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST → UTC に変換）
    - 銘柄あたり最大記事数／最大文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）
    - 1 API コールで最大 20 銘柄を処理するチャンク処理
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ
    - レスポンスの厳格バリデーション（JSON モードの余分なテキスト対策も含む）
    - スコアを ±1.0 にクリップ
    - 部分失敗に備え、書込みは対象コードのみを DELETE→INSERT する冪等処理（トランザクション）
  - テスト容易性のため、OpenAI 呼び出しをモック差替え可能（内部 _call_openai_api）

- AI 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定
  - 特徴
    - ma200_ratio の計算は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを回避
    - マクロニュースはキーワードフィルタ（日本およびグローバルなマクロ用キーワード群）で抽出
    - OpenAI（gpt-4o-mini）への JSON モード呼び出しとリトライ/バックオフを実装
    - API 失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ
    - 最終的なスコアはクリップされ閾値に応じてラベル化
    - market_regime テーブルへの冪等書込み（BEGIN / DELETE / INSERT / COMMIT）
    - テスト用に _call_openai_api を差し替え可能

- 研究用ファクター群（kabusys.research）
  - factor_research: モメンタム / ボラティリティ / バリュー等の計算関数を提供
    - calc_momentum: mom_1m/3m/6m、200日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す設計
    - calc_volatility: 20日 ATR、ATR 相対値、平均売買代金、出来高比率等を計算（部分窓でも可能）
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算
  - feature_exploration: 将来リターン・IC計算・統計サマリー等
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターン計算（horizon の妥当性検証あり）
    - calc_ic: Spearman のランク相関による IC 計算（有効データが 3 件未満なら None）
    - rank: 同順位は平均ランクで扱うランク化ユーティリティ（丸めにより ties 検出の安定化）
    - factor_summary: 各ファクター列に対する count/mean/std/min/max/median を計算
  - すべて DuckDB 接続を受け取り prices_daily / raw_financials 等のみを参照（外部 API には接続しない設計）

- データプラットフォーム（kabusys.data）
  - calendar_management: 市場カレンダー管理と営業日ロジック
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装
    - market_calendar がない場合は曜日（平日）ベースのフォールバック
    - DB に登録済み値を優先し、未登録日は曜日フォールバックで一貫性を保つ
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存（バックフィル・健全性チェックを実装）
  - pipeline / ETL: ETLResult データクラスと ETL パイプライン基盤
    - ETLResult による実行結果の構造化（取得数・保存数・品質問題・エラー等）
    - 差分取得・backfill・品質チェック（quality モジュール）を想定した設計
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを提供
  - etl モジュールは pipeline.ETLResult を再エクスポート

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数読み込み時に OS 環境変数を保護する仕組みを導入（.env による上書きを制限）

Notes / Design decisions / Caveats
- ルックアヘッドバイアス防止:
  - 多くのモジュール（news_nlp, regime_detector, research 等）は datetime.today() / date.today() を直接参照せず、target_date 引数を用いる設計としています。
- テスト性:
  - OpenAI 呼び出し箇所（_call_openai_api）は unittest.mock.patch 等で差し替え可能にしてあり、API 呼び出しを伴うユニットテストが書きやすい設計。
- トランザクションと部分失敗保護:
  - ai_scores や market_regime への書き込みは DELETE→INSERT の形で部分失敗時に既存データを不必要に消さないよう配慮しています（DuckDB の executemany の空リスト扱いへの対処を含む）。
- 環境変数バリデーション:
  - 必須設定が未定義の場合は明確な ValueError を投げる（例: OPENAI_API_KEY / SLACK_* / JQUANTS_REFRESH_TOKEN 等）。
- 依存:
  - DuckDB と OpenAI SDK（OpenAI クライアント）が必要。外部 API 呼び出しは失敗時フォールバックやリトライが組み込まれていますが、API キーやネットワークの設定は利用者側で準備してください。

Breaking Changes
- なし（初回リリース）

お問い合わせ・貢献
- バグ報告・改善提案・Pull Request はリポジトリの Issue / PR 機能をご利用ください。README やドキュメント（StrategyModel.md / DataPlatform.md 等）参照の上での貢献を歓迎します。