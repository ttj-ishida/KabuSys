Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記載します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠します。  

フォーマット: YYYY-MM-DD

[Unreleased]
------------

- （今後の変更をここに記載）

0.1.0 - 2026-03-28
-----------------

### 追加 (Added)

- パッケージ初期実装を追加。
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エクスポート: top-level __all__ により "data", "strategy", "execution", "monitoring" を公開。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイル（.env / .env.local）または OS 環境変数から設定値を読み込む自動読み込み機能を実装。
  - プロジェクトルート探索ロジック: __file__ を起点に .git または pyproject.toml を探索してプロジェクトルートを特定（CWD 非依存）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能（テスト用）。
  - .env パーサ: export PREFIX、シングル/ダブルクォート、エスケープ、インラインコメント処理、空行・コメント行スキップなどに対応。
  - 環境変数保護: OS 環境変数を protected として .env.local の上書きを制御。
  - Settings クラス: J-Quants / kabuステーション / Slack / DB パス / env 判定・ログレベル等のプロパティを提供。入力値検証（KABUSYS_ENV, LOG_LEVEL）を実装。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news と news_symbols を元に、指定ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）で記事を収集。
    - 銘柄ごとに最新記事を最大件数・最大文字数でトリムして結合し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信。
    - バッチ処理: 1回のAPI呼び出しで最大 20 銘柄(_BATCH_SIZE)を処理。
    - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。
    - レスポンス検証: JSON パース、"results" リスト、code の照合、スコア数値性検証、スコア ±1 にクリップ。
    - DB 書き込み: 成功した銘柄コードのみを対象に DELETE → INSERT を実行（部分失敗時の既存データ保護）。DuckDB executemany の空パラメータ問題に対する防御あり。
    - テスト補助: _call_openai_api の差し替え（patch）を想定した設計。

  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日経225連動型）について 200 日移動平均乖離を計算（重み 70%）。
    - news_nlp.calc_news_window を使ってマクロニュースを抽出し、LLM でマクロセンチメント（重み 30%）を評価。
    - レジームスコア合成: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1,1)。
    - 閾値により 'bull' / 'neutral' / 'bear' を判定。
    - DB 書き込みは冪等（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）を採用。例外時は ROLLBACK を実施して上位に例外を伝播。
    - API 呼び出し失敗時は macro_sentiment=0.0 のフォールバック（フェイルセーフ）。
    - LLM 呼び出しは専用実装（news_nlp とプライベート関数を共有しない）。

  - 共通設計方針（AI モジュール共通）
    - datetime.today() / date.today() を直接参照せず、外部から target_date を受け取ることでルックアヘッドバイアスを排除。
    - OpenAI クライアント生成は api_key 引数または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を送出。

- データモジュール (kabusys.data)
  - カレンダー管理 (calendar_management)
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day の営業日判定 API を実装。
    - market_calendar テーブルが存在しない/未取得の場合は曜日ベース（土日非営業）でフォールバック。
    - DB 登録値を優先し、未登録日は曜日フォールバックで一貫した挙動を実現。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に更新（バックフィルや健全性チェックを含む）。J-Quants クライアント呼び出しをラップしてエラー処理を追加。

  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）。
    - 差分取得、保存、品質チェック（quality モジュール）を想定した設計。バックフィルや最小データ日等の定数を定義。
    - DuckDB 用のユーティリティ: テーブル存在チェック、最大日付取得などを実装。

- リサーチモジュール (kabusys.research)
  - ファクター計算 (factor_research)
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev を計算。必要データ不足時は None を返す。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算（ATR の NULL 伝播を慎重に制御）。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算。
    - すべて DuckDB 上の prices_daily / raw_financials を参照し、外部 API へは接続しない設計。

  - 特徴量探索 (feature_exploration)
    - calc_forward_returns: 指定ホライズンに対する将来リターンを効率的に取得（ホライズン検証あり）。
    - calc_ic: スピアマンのランク相関（IC）を実装（最小レコード閾値あり）。
    - rank: 同順位は平均ランクを返すランク関数（丸めで ties を安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。

### 変更 (Changed)

- 初期リリースのため特になし（他プロジェクトやバージョンからの変更はなし）。

### 修正 (Fixed)

- 初期リリースのため特になし。

### セキュリティ (Security)

- 初期リリースのため特になし。

補足 / 設計上の注記
------------------

- DuckDB を主なストレージとして想定。executemany の空リストバインドに対するガードを実装している（DuckDB 0.10 の挙動への対応）。
- 日付/時刻の取り扱いは UTC naive datetime と JST の変換（ニュースウィンドウ等）を明確にし、タイムゾーン混入を防止。
- 重要箇所で冪等性（idempotency）やフェイルセーフ（API失敗時のフォールバック）を重視して実装。
- テストしやすさを配慮し、外部 API 呼び出し点（OpenAI クライアント呼び出し等）を差し替え可能にしている。

今後の予定（例）
----------------

- strategy / execution / monitoring の実装拡充・テストカバレッジ追加。
- ドキュメント（API リファレンス、運用手順、ETL の監査ログ仕様）整備。
- パフォーマンス改善（大口データ処理時の最適化）、および DuckDB スキーマ・インデックス最適化。

---