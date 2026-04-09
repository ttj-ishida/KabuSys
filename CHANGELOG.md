Keep a Changelog 準拠の CHANGELOG.md

すべての変更はセマンティックバージョニングに従います。
このファイルはコードベースから推測して作成した初期リリースの変更履歴です。

Unreleased
----------
（現時点の未リリースの変更はありません）

[0.1.0] - 2026-04-09
-------------------

Added
- 初期リリース: kabusys パッケージ v0.1.0 を公開。
  - パッケージの公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする仕組みを導入。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
  - .env のパーサを実装（コメント行、export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント取り扱いなどに対応）。
  - 環境変数保護（読み込み時に既存 OS 環境変数を protected として扱う）と override オプションをサポート。
  - Settings クラスを追加し、アプリケーション設定をプロパティで提供:
    - J-Quants / kabu station API / LINE Messaging API の設定（必須トークンは取得時に未設定で ValueError を送出）。
    - データベースパス（DuckDB / SQLite）や Paper Trading 用 DB パスのデフォルトと上書き機能。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject のみ許容）。
    - 監視関連設定（PID ファイル、kill フラグ、リソース閾値）とログ環境（KABUSYS_ENV, LOG_LEVEL）に対する検証。
    - ヘルパー is_live/is_paper/is_dev を提供。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news + news_symbols を集約して銘柄ごとにニュースを統合し、OpenAI（gpt-4o-mini）でセンチメント（-1.0〜1.0）を評価して ai_scores テーブルへ書き込む score_news を実装。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST に対応する UTC 範囲）を提供（calc_news_window）。
  - バッチ処理（1 API コールあたり最大 20 銘柄）、記事/文字数トリム（1銘柄あたり最大記事数/最大文字数）を実装し、トークン肥大化への対処を行う設計。
  - OpenAI 呼び出しは JSON モードで行い、429/ネットワーク断/タイムアウト/5xx に対する指数バックオフとリトライを実装。
  - レスポンス検証ロジックを実装（JSON 抽出、"results" の存在、code/score の型チェック、未知コード無視、スコアクリップ）。
  - DB 書き込みは冪等性を考慮（部分失敗時に既存スコアを保護するため、書き込み対象コードのみ DELETE → INSERT）し、DuckDB executemany の空パラメータ制約に配慮。
  - テスト容易性として _call_openai_api をパッチ差し替え可能に設計。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ書き込む score_regime を実装。
  - マクロ記事抽出（マクロキーワードリストによるタイトル検索）、OpenAI（gpt-4o-mini）によるマクロセンチメント評価、API エラー時のフェイルセーフ（macro_sentiment=0.0）、および再試行/バックオフを実装。
  - MA 計算・ニュース抽出ともにルックアヘッドバイアス防止（target_date 未満のみを参照）を徹底。
  - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等動作を実現。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）:
    - JPX カレンダーを管理する market_calendar を前提に、is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar 未取得時は曜日ベースのフォールバック（週末を非営業日）を採用。
    - 夜間バッチ更新 calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック、保存は jquants_client を通じて冪等保存）。
    - 探索の最大範囲制限やバックフィル日数、未来日チェックなどの安全策を導入。

  - ETL パイプライン（pipeline、etl の公開インターフェース経由で ETLResult を再エクスポート）:
    - 差分更新・保存・品質チェックの設計に基づく ETLResult データクラスを提供（取得件数、保存件数、品質問題リスト、エラーリスト、ヘルパー has_errors / has_quality_errors / to_dict）。
    - ETL 設計方針（営業日単位差分、バックフィル、品質チェックは収集継続する方針、id_token 注入可能）を反映。

- Research ユーティリティ（kabusys.research）
  - ファクター計算（factor_research）:
    - calc_momentum（1M/3M/6M リターン、200日 MA 乖離）。
    - calc_volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）。
    - calc_value（PER, ROE の計算、raw_financials から最新財務データを取得）。
    - DuckDB の SQL とウィンドウ関数を活用し、データ不足時は None を返す堅牢な実装。
  - 特徴量探索（feature_exploration）:
    - calc_forward_returns（任意ホライズンの将来リターン、ホライズン入力検証）。
    - calc_ic（スピアマンランク相関による IC 計算、データ不足時は None）。
    - rank（同順位は平均ランクで扱うランク化ユーティリティ）。
    - factor_summary（各ファクター列に対する count/mean/std/min/max/median を算出）。
  - data.stats の zscore_normalize を再エクスポート。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Notes
- 全体的設計方針:
  - ルックアヘッドバイアス防止のため、内部処理で datetime.today() / date.today() を参照しない設計が徹底されている（すべて target_date を明示的に受け取る）。
  - OpenAI 呼び出しは JSON Mode（response_format に json_object 指定）を用い、レスポンスの厳密な検証を行うことで LLM 出力の不整合に耐性を持たせている。
  - DuckDB を主要なデータストアとして利用し、SQL と Python の組合せで高性能にデータ処理を行う設計。
  - テスト容易性を考慮し、OpenAI 呼び出しや一部内部関数をパッチ差し替え可能に実装している。
  - DB 書き込みは冪等性（DELETE→INSERT 等）・トランザクション・部分失敗時の既存データ保護を重視。

Acknowledgements
- 本 CHANGELOG は与えられたコードベースの内容から推測して作成したものであり、実際のリリースノートと差異がある場合があります。