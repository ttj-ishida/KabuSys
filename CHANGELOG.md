CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは "Keep a Changelog" の諸原則に準拠しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

(なし)

0.1.0 - 2026-04-02
------------------

Added
- パッケージ初期リリース (バージョン 0.1.0)
  - 基本情報
    - パッケージ名: kabusys
    - __version__ = "0.1.0"
    - パッケージ公開インターフェースに data, strategy, execution, monitoring を含める設定。

- 設定 / 環境変数管理 (kabusys.config)
  - プロジェクトルート自動検出: .git または pyproject.toml を基準にルートを探索する実装を追加。
  - .env 自動読み込み:
    - 読み込み順: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env 読み込みは既存 OS 環境変数を保護する protected 機能を実装。
  - .env パーサー強化:
    - export KEY=val 形式のサポート。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ対応。
    - クォートなしの行でのインラインコメント判定対応（直前が空白/タブの場合）。
  - Settings クラスを提供:
    - J-Quants / kabuステーション / Slack / データベース / 監視 / システム関連のプロパティを環境変数から取得。
    - 必須キー未設定時は ValueError を投げる _require 実装。
    - env, log_level に対する値検証（有効値セットを定義）。
    - デフォルト値（例: DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等）を Path 型で返す。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - タイムウィンドウ計算: target_date に対するニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で実装。
    - raw_news と news_symbols から銘柄ごとに記事を集約する _fetch_articles を実装（1銘柄あたり最新記事数制限・文字数トリム対応）。
    - OpenAI (gpt-4o-mini) を用いたバッチ評価:
      - 1 API 呼び出しで最大 20 銘柄を処理するチャンク方式。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
      - レスポンス検証 (_validate_and_extract): JSON 抽出・構造検証（results 配列・code/score 検査）・数値チェック・スコア ±1.0 クリップ。
      - 部分成功を許容する DB 書き込み（取得した銘柄のみ DELETE → INSERT）で既存データ保護。
      - DuckDB executemany の互換性対策（空パラメータを避けるチェック）。
    - score_news: 全体ワークフロー（APIキー解決、ウィンドウ計算、記事集約、チャンク評価、DB 書込）を提供。
    - テスト容易性のため _call_openai_api を内部で定義しモック差し替え可能。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（_MA_WINDOW=200）とマクロニュース LLM センチメントを重み合成して日次レジーム判定（'bull' / 'neutral' / 'bear'）。
    - 設計:
      - ma200_ratio の計算においてルックアヘッドを防止（date < target_date）。
      - マクロ記事の抽出は news_nlp.calc_news_window を利用。
      - OpenAI 呼び出し（gpt-4o-mini）で JSON レスポンスをパースし macro_sentiment を取得。API 失敗時はフェイルセーフで 0.0 を採用。
      - 合成スコア: 70% (MA) / 30% (macro)、スコアを -1.0〜1.0 にクリップ。閾値でラベル決定。
      - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- Research / ファクター計算 (kabusys.research)
  - calc_momentum:
    - mom_1m / mom_3m / mom_6m・ma200_dev を prices_daily から計算。データ不足時は None。
  - calc_volatility:
    - 20日 ATR、相対 ATR (atr_pct)、20日平均売買代金、出来高比率を計算。true_range の NULL 傳播を明示的に扱う実装。
  - calc_value:
    - raw_financials から直近の財務データを取得し PER / ROE を計算（EPS が 0/欠損時は None）。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを単一クエリで算出。horizons の検証あり。
    - calc_ic: Spearman ランク相関（Information Coefficient）計算。サンプルが少ない場合は None を返す。
    - rank: 同順位は平均ランクを返すランク関数（丸めで ties 対応）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー実装。
  - 実装方針:
    - DuckDB 接続を受け取り SQL + Python で完結。外部ライブラリに依存しない。

- Data プラットフォーム (kabusys.data)
  - calendar_management:
    - market_calendar を扱う一連のユーティリティを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録がある場合は DB 値優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - 最大探索日数 (_MAX_SEARCH_DAYS) による無限ループ防止。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存（バックフィル機構・健全性チェックあり）。jquants_client を通じた fetch/save を使用。
  - ETL / pipeline:
    - ETLResult dataclass を公開（target_date, fetched/saved counts, quality_issues, errors 等を含む）。
    - pipeline モジュールの基本ユーティリティ（テーブル存在チェック、最大日付取得等）を実装。
    - ETL の設計方針: 差分更新、バックフィル、品質チェックを行い部分失敗許容の保存戦略を採用。
  - 実装上の互換性対策や安全策:
    - DuckDB の型・空リスト executemany の制約や日付型の取り扱いに配慮した実装。
    - DB 書き込みは明示的なトランザクションで冪等性・ロールバック対応。

Changed
- （初回リリースのためなし）

Fixed
- （初回リリースのためなし）

Deprecated
- （初回リリースのためなし）

Removed
- （初回リリースのためなし）

Security
- 環境変数に機密情報（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）を使用。
  - Settings._require により必須未設定時は明示的にエラーを出す。環境変数管理に注意してください。

Notes / 設計上の注意点
- 全てのモデル（AI）関連処理は日次バッチ的に設計され、ルックアヘッドバイアスを避けるため datetime.today()/date.today() を直接参照しない実装ポリシーを採用しています。
- OpenAI 呼び出しは JSON モード (response_format={"type": "json_object"}) を使用しますが、稀に余分なテキストが混ざるケースを想定してパースの復元処理を行っています。
- API 呼び出し失敗時はフェイルセーフ（スコア 0.0 やスキップ）で処理を継続する設計です（部分失敗を許容して他データを保護します）。
- DuckDB 互換性・安全性（executemany 空リスト回避、日付の型変換、トランザクション管理）に配慮した実装です。

今後の予定（参考）
- strategy / execution / monitoring モジュールの詳細実装（本リリースではパッケージ公開名の宣言のみ）。
- テストカバレッジ拡充（特に OpenAI 呼び出し周りの HTTP エラーや JSON 辞書検証）。
- jquants_client の実装・統合テストと ETL バッチの定期実行化。

お問い合わせ
- 実装の詳細や設計意図についてはソースコード内の docstring に説明があります。コードベースを参照してください。