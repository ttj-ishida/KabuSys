Keep a Changelog
=================

すべての変更は https://keepachangelog.com/ja/ の慣例に従って記載しています。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- セキュリティ (Security)

Unreleased
---------

（現在未リリースの変更はここに記載してください）

[0.1.0] - 2026-04-04
-------------------

初期リリース。以下の主要機能・モジュールを追加しました。

Added
- パッケージ全体
  - 基本パッケージ kabusys の初期実装を追加。バージョンは 0.1.0。
  - エクスポート: data, strategy, execution, monitoring をパッケージ外部公開。

- 設定 / 環境変数管理 (kabusys.config)
  - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込みする機能を実装。CWD に依存せずパッケージ配布後も動作。
  - 読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数を保護するため protected セットで上書き制御。
  - .env パーサは以下をサポート:
    - コメント行・空行、`export KEY=val` 形式
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなし値に対するインラインコメント判定（直前がスペース/タブ の場合）
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、アプリ設定をプロパティ経由で取得:
    - J-Quants / kabuステーション / LINE / DB パス（デフォルト: data/kabusys.duckdb, data/monitoring.db）等
    - 監視関連パス（PID ファイル、kill flag）や閾値（CPU/MEM/DISK）
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL のバリデーション
    - is_live / is_paper / is_dev のヘルパー

- AI モジュール (kabusys.ai)
  - news_nlp.score_news
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - チャンク単位（最大 20 銘柄）で API コール、1 銘柄あたり最大記事数・文字数（既定: 10 件 / 3000 文字）でトリム。
    - JSON Mode を用いた応答バリデーションを実装（レスポンスのパース復元処理含む）。不正応答はログを出力してスキップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ、その他はスキップ。
    - 成功した銘柄のみ ai_scores テーブルへ置換（DELETE → INSERT）して部分失敗時に既存データを保護。
    - テストしやすいように _call_openai_api を patch 可能に設計。
    - calc_news_window: JST ベースのニュース集計ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算するユーティリティを提供。
  - regime_detector.score_regime
    - ETF 1321（先物連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出・保存。
    - OpenAI（gpt-4o-mini）呼出しはリトライとフェイルセーフ（失敗時 macro_sentiment=0.0）を実装。
    - レジームスコアはクリッピング、閾値に基づきラベル付与。
    - market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT / ROLLBACK ハンドリング）。
    - ルックアヘッドバイアスを避けるため datetime.today()/date.today() を参照しない設計（target_date を明示的に受け取る）。

- データプラットフォーム (kabusys.data)
  - calendar_management
    - JPX カレンダーの管理、営業日判定ロジックを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（土日を休場）を使用。
    - calendar_update_job: J-Quants クライアントから差分取得し保存。バックフィルと健全性チェックを実装。
  - pipeline / etl
    - ETL パイプラインの結果を表す ETLResult データクラスを実装（品質チェック結果・エラー集約）。
    - 差分更新・バックフィル・保存（jquants_client の save_* を利用）・品質チェックを行う設計方針を実装（詳細は pipeline モジュールに準備）。
  - etl モジュールは ETLResult を再エクスポート。

- リサーチ / ファクター (kabusys.research)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から最新の EPS/ROE を参照し PER/ROE を算出（EPS が 0/欠損の場合は None）。PBR/配当利回りは未実装。
    - DuckDB を用いた SQL ベースの実装で、外部 API にはアクセスしない。
  - feature_exploration
    - calc_forward_returns: 指定基準日から各ホライズン後の将来リターンを計算（デフォルト [1,5,21]）。
    - calc_ic: Spearman ランク相関（IC）を計算（3 件未満は None を返す）。
    - rank: 同順位は平均ランクで処理するランク付けユーティリティ（丸め誤差対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ機能。
  - research パッケージは主要関数を __all__ で公開。

- 共通設計上の注意点
  - ルックアヘッドバイアス回避のため、内部処理は target_date を受け取り datetime.today()/date.today() を直接参照しない。
  - OpenAI 呼び出しに対してリトライと指数バックオフを実装し、API 失敗時はフェイルセーフ（0.0 やスキップ）で継続する方針。
  - DuckDB の特性（executemany の空リスト不可等）を考慮した実装。
  - 各 DB 書き込みはなるべく冪等に（DELETE → INSERT 等）行い、ROLLBACK の取り扱いを明確化。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- （初期リリースのため該当なし）

注記（既知の制限 / 今後の予定）
- calc_value では現時点で PBR・配当利回りを未実装。
- AI モジュールは OpenAI API キー（OPENAI_API_KEY）または api_key 引数を必要とする。キー未設定時は ValueError を送出。
- news_nlp / regime_detector は gpt-4o-mini を想定しているが、モデル/レスポンス形式の変更に対してはパースロジックの更新が必要。
- strategy / execution / monitoring パッケージの公開はあるが、本リリースでの実装範囲は上記モジュール群に主に集中。

--- 
開発者向け: 変更履歴の書式に従って今後のリリースでは Unreleased セクションに作業中の項目を記載し、リリース時にバージョンと日付を追記してください。