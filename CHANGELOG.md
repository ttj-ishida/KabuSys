# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。  

## [Unreleased]
- 今後の変更をここに記載します。

## [0.1.0] - 2026-03-31
初期リリース。日本株自動売買 / データ基盤・リサーチ・AI スコアリングのコア機能を実装。

### Added
- パッケージのメタ情報
  - kabusys パッケージを追加。バージョン: 0.1.0。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイル／環境変数から設定を自動ロードする仕組みを実装。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - プロジェクトルートは .git または pyproject.toml を起点に探索（CWD に依存しない実装）。
  - .env パーサ実装（export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメントの扱いに対応）。
  - Settings クラスを提供（J-Quants / kabuステーション / Slack / DB パス / 環境モード / ログレベル などのプロパティ）。
    - 必須の環境変数未設定時は明確な ValueError を送出。
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）のバリデーション（許容値チェック）。
    - デフォルトの DB パス（duckdb: data/kabusys.duckdb、sqlite: data/monitoring.db）を提供。

- AI 関連（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - score_news(conn, target_date, api_key=None)
      - 前日 15:00 JST 〜 当日 08:30 JST（UTC に変換）の時間窓で raw_news を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）でセンチメントを取得。
      - バッチ送信（最大 20 銘柄 / リクエスト）、1 銘柄あたりの記事数と文字数に上限を設定（max articles / max chars）。
      - 429 / ネットワーク切断 / タイムアウト / 5xx に対する指数バックオフ・リトライを実装。
      - レスポンス検証（JSON 抽出、results フィールド、code と score の検証）とスコアの ±1.0 クリップ。
      - 成功した銘柄のみ ai_scores テーブルに置換的（DELETE → INSERT）書き込みを実行（部分失敗時に既存データ保護）。
    - calc_news_window(target_date) ユーティリティでニュースウィンドウを計算。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull / neutral / bear）を判定。
      - calc_ma200_ratio によるデータ存在・日数不足時のフォールバック（中立 1.0）。
      - マクロ記事抽出はキーワードマッチ（複数キーワード）で最大記事数を制限。
      - OpenAI 呼び出しはリトライ・フェイルセーフ（失敗時 macro_sentiment=0.0）。
      - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー更新ジョブ calendar_update_job(conn, lookahead_days=...)
      - J-Quants API から差分取得して market_calendar に冪等保存。バックフィルと健全性チェックを実装。
    - 営業日判定ユーティリティ:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
      - market_calendar データがある場合は DB 値優先、未登録日は曜日ベースのフォールバック（週末除外）で一貫した挙動を保持。
      - 最大探索日数制限（_MAX_SEARCH_DAYS）により無限ループ回避。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（取得数・保存数・品質チェック・エラー概要を保持）。
    - 差分更新・バックフィル・品質チェック方針をコード化（J-Quants から差分取得、保存は idempotent、品質問題は収集して返却）。
    - 内部ユーティリティ：テーブル存在チェック、最大日付取得等を実装。
  - jquants_client のラッパーを使ったデータ取得・保存機能（モジュール分離）。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得し PER, ROE を計算（EPS が 0/欠損の場合は None）。
    - DuckDB 上の SQL ウィンドウ関数を活用し効率的に集計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定日から各ホライズン（デフォルト 1,5,21 営業日）までの将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンランク相関（IC）を計算。有効レコードが 3 件未満なら None を返す。
    - rank: 同順位は平均ランクを返す実装（丸めによる ties の検出対策あり）。
    - factor_summary: 各ファクター列の基本統計（count/mean/std/min/max/median）を返す。
  - zscore_normalize は kabusys.data.stats から再エクスポート。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーの取り扱い
  - api_key を明示的に引数で渡せる設計。未指定時は環境変数 OPENAI_API_KEY を参照し、未設定の場合は ValueError を投げることで誤使用の早期検出を図る。

### Notes / 実装上の重要な設計判断
- ルックアヘッドバイアス対策
  - 全ての日時ロジック（ニュースウィンドウ、MA 計算、ETL 等）は target_date を明示して計算し、datetime.today() / date.today() を直接参照しないよう設計（再現性・テスト容易性向上）。
- フェイルセーフ設計
  - 外部 API（OpenAI / J-Quants）失敗時は例外で即終了するのではなくログを残しフォールバック値（例: macro_sentiment=0.0）やスキップで継続する箇所を用意。DB 書き込み時の失敗はトランザクションでロールバックして上位へ伝播。
- テスト容易性
  - OpenAI 呼び出しを隠蔽する内部関数（_call_openai_api）を用意し、unit test でパッチできるようにしている。
- DuckDB 互換性
  - executemany に空リストを渡さない等、DuckDB 特有の制約に配慮した実装。

---

開発チームへ:
- この CHANGELOG はコードベースから推測して作成しています。リリースノートに追記したい利用上の注意や既知の問題があれば追記してください。