Keep a Changelog
=================

すべての注目すべき変更を記録します。This project adheres to "Keep a Changelog" として、
セマンティック バージョニングを採用します。

[Unreleased]

[0.1.0] - 2026-04-01
-------------------

初回リリース。日本株自動売買・データプラットフォームのコアライブラリを提供します。
主要な追加点、設計方針、既知の問題を以下にまとめます。

Added
- パッケージ基礎
  - kabusys パッケージ初期バージョンを追加。__version__ は 0.1.0。
  - パッケージ公開 API の __all__ に data/strategy/execution/monitoring を設定。

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を起点）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト用）。
  - .env 解析の堅牢化
    - export KEY=val 形式対応、シングル/ダブルクォートとバックスラッシュエスケープの扱い、インラインコメント処理の実装。
  - Settings クラスでアプリ設定を型付きプロパティとして提供（J-Quants, kabuAPI, Slack, DBパス, 監視閾値, 環境/ログレベル判定等）。
  - 環境値の検査（KABUSYS_ENV, LOG_LEVEL の許容値検証）と便利プロパティ（is_live, is_paper, is_dev）。

- AI: ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約して銘柄別に記事をまとめ、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメント（ai_score）を算出。
  - タイムウィンドウ計算（JST ベース: 前日 15:00 ～ 当日 08:30 を UTC に変換）を calc_news_window で提供。
  - リトライ・バックオフ機構（429 / ネットワーク断 / タイムアウト / 5xx を対象）を実装。最大バッチサイズ、記事/文字数上限でトークン肥大を制御。
  - レスポンス検証ロジック（JSON 抽出、"results" フォーマット検証、未知コード無視、数値検査、±1.0 でクリッピング）。
  - DB への冪等書き込み（該当 date/code の DELETE → INSERT）により部分失敗から既存データを保護。
  - テスト容易性: OpenAI 呼び出し部分を内部関数で切り出し、テスト時にモック可能。

- AI: 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム ('bull'/'neutral'/'bear') を判定。
  - prices_daily / raw_news / market_regime を参照し、ma200_ratio 計算、マクロ記事抽出、OpenAI によるマクロセンチメント評価、スコア合成を実装。
  - API 呼び出しのリトライ・バックオフ、API 失敗時のフェイルセーフ（macro_sentiment=0.0）。
  - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
  - モジュール間結合を避けるため、OpenAI 呼び出しは news_nlp と別実装に。

- Research（kabusys.research）
  - ファクター計算モジュール（factor_research）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離 (ma200_dev) を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials より EPS/ROE を取得し PER/ROE を算出（EPS=0/欠損時は None）。
  - 特徴量探索（feature_exploration）
    - calc_forward_returns: 指定ホライズンの将来リターン（LEAD ベース、一括クエリで取得）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - rank / factor_summary: ランキング変換（同順位は平均ランク）と統計サマリーを提供。
  - 全関数は DuckDB 接続を受け取り、prices_daily/raw_financials のみ参照する設計（実トレード実行ロジックへは影響しない）。

- Data プラットフォーム（kabusys.data）
  - calendar_management: JPX カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）と夜間バッチ更新 job（calendar_update_job）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバック。最大探索日数制限で無限ループ対策。
    - J-Quants クライアント経由の差分取得と冪等保存（fetch/save を呼ぶ）。
  - pipeline / etl: ETLResult dataclass とパイプライン骨組み
    - ETLResult に品質チェック結果（quality.QualityIssue）とエラーメッセージを保持し、has_errors / has_quality_errors / to_dict を提供。
    - ETL の差分取得・バックフィル設計方針をコメントとして明示。
  - etl モジュールから ETLResult を再エクスポート。

Changed / Design decisions
- ルックアヘッドバイアス防止:
  - AI 及び研究系の全処理（score_news, score_regime, 各種 calc_*）は内部で datetime.today()/date.today() を参照しない。外部から target_date を与える設計。
  - DB クエリでは target_date 未満 / 以前 といった排他条件・過去データ限定のクエリを採用。
- フェイルセーフ:
  - OpenAI/API 失敗時は例外を投げて処理全体を止めず、既定値（例: macro_sentiment=0.0）やスキップを行うことで処理継続を優先。
- テスト性:
  - OpenAI 呼び出し部分は内部 _call_openai_api を通す実装で、ユニットテスト時は patch により差し替え可能。
- DuckDB 互換性配慮:
  - executemany に空リストを渡さないガード（DuckDB 0.10 の制約）や、list バインドの回避（個別 DELETE を executemany で行う）等を実装。

Fixed
- 初回リリースに伴う主要機能の実装（上記 Added の通り）。

Known issues / TODOs
- pipeline._get_max_date の末尾でソースが途中で途切れており（return date.fro のような不完全な行）、このままでは実行時に SyntaxError / NameError が発生します。CI/リリース前に修正が必要です（意図は DuckDB の最大日付を date に変換して返すロジックと思われます）。
- 一部外部クライアント実装（kabusys.data.jquants_client）の具象化は本リリースに含まれている想定だが、外部依存が未提供の場合は calendar_update_job 等で例外が発生する可能性あり。jquants_client の実装・モックを用意して運用してください。
- OpenAI API 使用には OPENAI_API_KEY が必須（各関数で引数 api_key を受け付けるが、未指定時は環境変数 OPENAI_API_KEY を参照）。API コストとレート制限に注意。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）が事前に作成され、必要なカラムが揃っていることを前提としています。運用前にスキーマ定義と初期ロードを確認してください。

Security
- 本バージョンでは機密情報（APIキー等）を環境変数で扱う設計。 .env の読み込み・取り扱いに注意し、プロダクション環境では適切なシークレット管理（Vault 等）の利用を推奨します。

Migration notes
- 初回リリースのためマイグレーション不要。ただし既存のスキーマ・データ準備、環境変数の設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY 等）が必要です。

Development notes
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動読み込みを無効化できます。
- OpenAI 呼び出し箇所は _call_openai_api をモックし、レスポンス検証ロジックやリトライ挙動をユニットテスト可能です。

---

（必要に応じて各機能の詳細な変更ログやチケット参照を追記してください。）