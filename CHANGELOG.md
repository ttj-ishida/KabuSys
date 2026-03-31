# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従っています。  

## [0.1.0] - 2026-03-31
初回リリース。以下の主要機能と設計方針を実装しました。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの公開バージョンを "0.1.0" として定義。
  - パッケージ公開モジュール: data, strategy, execution, monitoring を __all__ でエクスポート。

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - 自動 .env ロードの実装（優先順位: OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサは以下をサポート:
    - コメント行、空行のスキップ
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート中のバックスラッシュエスケープ処理
    - クォートなし値のインラインコメント処理（直前が空白/タブの場合）
  - 環境変数の上書き制御（override と protected（OS 環境の保護））。
  - 必須の環境変数未設定時に ValueError を送出する _require を提供。
  - 主要設定項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, CPU/MEMORY/DISK 閾値、KABUSYS_ENV（development/paper_trading/live 検証）、LOG_LEVEL 検証など。
  - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI (kabusys.ai)
  - news_nlp モジュール
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）を使って銘柄ごとのニュースセンチメントを算出し ai_scores テーブルへ書き込む score_news 関数を提供。
    - ニュースウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive datetime で扱う）。
    - バッチ処理（最大 20 銘柄 / コール）、記事数・文字数のトリミング（最大記事数/最大文字数）。
    - OpenAI へのリトライ（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）と JSON レスポンスの厳密バリデーション。
    - レスポンス検証で不正な項目はスキップし、スコアを ±1.0 にクリップ。
    - DuckDB への書き込みは部分失敗耐性を考慮し、該当コードのみ DELETE → INSERT を行う（冪等性確保）。
    - テスト容易性のため _call_openai_api をモック差し替え可能。
  - regime_detector モジュール
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定する score_regime 関数を提供。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
    - マクロニュース用キーワードセットを使って raw_news からタイトルを抽出し、OpenAI を呼んで macro_sentiment を算出。
    - API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
    - レジームスコアのクリップ、ラベル付けし market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI 呼び出しは独立実装でモジュール間の結合を避ける設計。

- データ (kabusys.data)
  - calendar_management モジュール
    - JPX カレンダーの夜間バッチ更新（calendar_update_job）と営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - market_calendar テーブルが未存在/未取得の場合は曜日ベース（土日休）でフォールバック。
    - バックフィル、先読み、健全性チェック（過度な将来日付は警告してスキップ）。
    - DB 値優先、未登録日は曜日フォールバックで一貫性を保つロジック。
  - pipeline / etl
    - ETLResult データクラスで ETL 実行結果を構造化（取得数・保存数・品質検査結果・エラーメッセージ等）。
    - 差分取得・保存・品質チェックのパターンを想定した ETL パイプライン骨格。
    - jquants_client と quality モジュールを用いた差分取得・保存・品質チェックの設計方針を反映。
    - デフォルトのバックフィル日数や最小データ日付などの定数を定義。
    - DuckDB に対するテーブル存在チェック、最大日付の取得ユーティリティ（内部実装の一部）。

- 研究（kabusys.research）
  - factor_research
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials を参照して各種ファクター（モメンタム、MA200乖離、ATR、平均売買代金、PER、ROE など）を計算。
    - SQL ウィンドウ関数を利用して DuckDB 内で一貫して計算。
    - データ不足時は None を返す方針。
  - feature_exploration
    - calc_forward_returns（将来リターン計算）、calc_ic（Spearman ランク相関 IC 計算）、rank（平均ランク処理）、factor_summary（基本統計量）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB で完結する設計。

### 変更 (Changed)
- 設計方針・安全策（全体、ドキュメント的に実装）
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() をスコア計算内部で直接参照しない実装方針を徹底（外から target_date を渡す設計）。
  - DuckDB への書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護。ROLLBACK 実行に失敗した場合は警告ログを出力。
  - DuckDB 0.10 の仕様（executemany に空リストを渡せない）に配慮した空チェックを実装。
  - OpenAI API 呼び出しに対する堅牢なリトライ/フォールバック戦略（429・ネットワーク断・タイムアウト・5xx 対応）を導入。

### 修正 (Fixed)
- 初期実装のため既知のバグフィックス項目は特になし（初回公開）。

### セキュリティ (Security)
- API キーの取り扱いは環境変数経由を想定。OpenAI API キー未設定時には明示的に ValueError を発生させ処理を停止する箇所を用意（誤った空文字取り扱い防止）。
- .env 読み込み時に OS 環境変数を上書きしないデフォルト動作や protected セットにより、テスト/デプロイ時の上書きリスクを低減。

---

注:
- 本 CHANGELOG はソースコードから推測して作成した要約です。実際のリリースノートでは API 仕様の違いや追加のマイナー変更、破壊的変更の有無を確認のうえ追記してください。