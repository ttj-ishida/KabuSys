CHANGELOG
=========

すべての重要な変更点はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に準拠します。  

0.1.0 - 2026-04-01
------------------

Added
- パッケージ初期リリース。
  - パッケージ名: kabusys、__version__ = "0.1.0"。
  - パブリック API を __all__ で公開（data, strategy, execution, monitoring）。

- 環境設定・読み込み機能（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み。  
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env と .env.local の読み込み順序と .env.local の上書き動作（OS 環境変数は保護）。
  - .env 行パーサ実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、コメント処理）。  
  - ファイル読み込み失敗時は警告発行して継続。
  - Settings クラスを導入し、J-Quants / kabuステーション / Slack / DB パス /監視閾値 / システム設定（env, log_level）等をプロパティで安全に取得。  
    - 必須設定未設定時は ValueError を送出するヘルパー _require を提供。
    - KABUSYS_ENV、LOG_LEVEL に対する値検証を実装（許容値チェック）。
    - パス値は Path 型で返却（expanduser 対応）。

- ニュース NLP / LLM ベースの分析（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約して銘柄別にニュースを合成し、OpenAI（gpt-4o-mini）により -1.0〜1.0 のセンチメントを算出して ai_scores テーブルへ書き込み。
  - タイムウィンドウ計算 util calc_news_window（JST ベース前日 15:00 ～ 当日 08:30 を UTC へ変換）を実装。
  - バッチ処理（最大 _BATCH_SIZE=20 銘柄）、1 銘柄あたり記事数・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）によるトリム。
  - JSON Mode を用いた厳密な JSON レスポンス想定。応答のバリデーション（results リスト、code/score 検証、スコアの数値化・有限性確認）。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ実装（_MAX_RETRIES, _RETRY_BASE_SECONDS）。
  - スコアは ±1.0 にクリップ。部分失敗時に既存スコアを保護するため、書き込みは対象コードに限定した DELETE → INSERT の冪等処理。
  - テスト容易性: _call_openai_api を patch して置換可能。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（N225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム判定（'bull' / 'neutral' / 'bear'）。
  - MA 比率計算（_calc_ma200_ratio）では target_date 未満のデータのみ使用し、データ不足時は中立（1.0）でフォールバック。
  - マクロニュース抽出（_fetch_macro_news）ではキーワードによる ILIKE フィルタ（最大件数制限）。
  - OpenAI 呼び出し（_score_macro）にはリトライと 5xx の区別、JSON パース失敗時は macro_sentiment=0.0 でフェイルセーフ。
  - レジームスコア合成ロジック（スケール・重み付け・クリップ）と閾値判定、結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
  - LLM 呼び出しは専用の内部実装で news_nlp と結合しない設計（モジュール結合を避ける）。

- データプラットフォーム（kabusys.data）
  - ETL 用の ETLResult データクラスを pipeline モジュールで導入・再エクスポート（kabusys.data.etl）。
    - ETL 実行結果（取得数・保存数・品質問題・エラー）を集約、辞書変換ユーティリティを提供。
  - pipeline モジュールで差分取得・保存・品質チェックの設計を用意（J-Quants クライアント経由）。
  - calendar_management: JPX カレンダー管理機能を実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。  
    - market_calendar が未登録のときは曜日ベース（土日除外）でフォールバックして一貫性維持。
    - calendar_update_job による夜間差分取得と保存（バックフィル、健全性チェック、J-Quants へのフェールセーフ）を実装。
    - 最大探索日数やバックフィル日数等の安全パラメータを設定して無限ループや過剰取得を回避。

- 研究用モジュール（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER、ROE）を DuckDB ベースの SQL で計算。
    - データ不足時の None ハンドリングを実装。
  - feature_exploration:
    - 将来リターン計算 calc_forward_returns（horizons に対応）、IC（Spearman ρ）計算 calc_ic、ランク変換、ファクター統計サマリーを提供。
    - 外部依存を避け標準ライブラリのみで実装。

Changed
- 設計原則として全ての AI / 研究関数で datetime.today() / date.today() を直接参照しない方式を採用（ターゲット日引数ベース）。これによりルックアヘッドバイアスを避ける設計を明示。

Fixed / Robustness
- DB 書き込み時のトランザクション安全性を考慮し、例外時は ROLLBACK を試み失敗時に警告ログを出すなどのフォールトハンドリングを強化。
- DuckDB の executemany に空リストを渡せない制約に合わせて条件付き実行を実装（空の params を回避）。

Known limitations / Notes
- OpenAI API の利用には OPENAI_API_KEY の環境変数設定、もしくは各関数の api_key 引数による注入が必要。未設定時は ValueError を送出する。
- DuckDB 接続（duckdb.DuckDBPyConnection）を引数として受け取る関数群が多く、呼び出し側で DB コネクション管理が必要。
- 現段階では一部ファクター（PBR・配当利回り等）は未実装。
- JSON Mode を期待するため、LLM 側のフォーマットが変わるとパースロジックの調整が必要となる可能性あり。

Security
- 現時点で公開されたセキュリティフィックスはありません。環境変数の取り扱いや API キーの管理は利用者側で慎重に行ってください。

今後の予定（参考）
- ファクター群の拡張（PBR・配当利回り等）、研究用ユーティリティの追加。
- API クライアント周りの抽象化とテストカバレッジ強化。
- 監視・実行部分（execution / monitoring）や strategy モジュールの実装・公開。

----- 

注: 上記は現行コードベースからの推測に基づく CHANGELOG です。必要に応じてリリース日や記述をプロジェクト実際の運用に合わせて調整してください。