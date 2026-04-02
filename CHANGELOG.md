CHANGELOG
=========
すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。
リリースはセマンティックバージョニングに従います。

[Unreleased]
------------

[0.1.0] - 2026-04-02
--------------------
初回公開リリース。

Added
- パッケージ基盤
  - kabusys パッケージ初期化 (src/kabusys/__init__.py)。
    - __version__ = "0.1.0" を設定。
    - パブリックモジュールとして data, strategy, execution, monitoring をエクスポート。

- 設定・環境変数管理
  - kabusys.config (src/kabusys/config.py)
    - .env ファイルまたは OS 環境変数から設定を自動読み込み（プロジェクトルートを .git/pyproject.toml で検出）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - .env のパースは以下をサポート:
      - コメント行 / export KEY=val 形式 / シングル・ダブルクォート、バックスラッシュエスケープ / インラインコメントの扱い。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / データベース / 監視 / ログ設定等をプロパティで取得可能。
    - 必須設定未定義時は _require() が ValueError を送出。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実装（許容値はコード内定義）。

- AI（ニュース・レジーム判定）
  - kabusys.ai.news_nlp (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - タイムウィンドウ（日次、JST基準で前日15:00～当日08:30）を calc_news_window で計算。
    - バッチ処理: 最大 20 銘柄/回、1銘柄あたり最大 10 記事・3000 文字にトリム。
    - JSON Mode を使った堅牢なレスポンスパースとバリデーションを実装（results 配列の検証、スコアの数値チェック、±1.0 でクリップ）。
    - リトライ戦略: 429、ネットワーク断、タイムアウト、5xx に対し指数バックオフで再試行。その他はスキップして継続（フェイルセーフ）。
    - 成果は ai_scores テーブルへ（部分的失敗に備え、対象コードのみ DELETE → INSERT を行うことで冪等化）。
    - パブリック API: score_news(conn, target_date, api_key=None) -> 書き込んだ銘柄数。
    - テスト容易性: _call_openai_api の差し替え（mock）を想定。

  - kabusys.ai.regime_detector (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - マクロニュースの抽出は news_nlp.calc_news_window を利用し、raw_news からマクロキーワードでフィルタ。
    - OpenAI 呼び出しは独立実装で、API エラー時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - レジームスコアはクリップされ、判定結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - パブリック API: score_regime(conn, target_date, api_key=None) -> 1（成功）／例外。

- データ基盤（Data Platform）
  - kabusys.data.calendar_management (src/kabusys/data/calendar_management.py)
    - JPX カレンダー管理ロジック（market_calendar テーブルを参照）。
    - 営業日判定ユーティリティ: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - DB にデータがない場合は「曜日ベース（平日のみ営業日）」でフォールバックする設計。
    - calendar_update_job(conn, lookahead_days=90) を実装し、J-Quants クライアント経由で差分取得 → 保存（バックフィル・健全性チェック含む）。

  - kabusys.data.pipeline / kabusys.data.etl (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETL パイプラインの基礎（差分取得、保存、品質チェック）を実装するためのインターフェースと ETLResult データクラスを提供。
    - ETLResult は取得・保存件数、品質問題、エラー一覧などを格納し、to_dict() でシリアライズ可能。
    - pipeline モジュールの ETLResult を etl モジュールで再エクスポート。

  - DB ユーティリティ
    - テーブル存在チェックや最大日付取得など、DuckDB を使ったユーティリティ関数を実装（内部使用）。

- 研究用モジュール（Research）
  - kabusys.research パッケージの初期公開 (src/kabusys/research/__init__.py)
    - zscore_normalize を data.stats から再利用。
    - factor_research と feature_exploration の主要関数をエクスポート:
      - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank

  - kabusys.research.factor_research (src/kabusys/research/factor_research.py)
    - Momentum / Volatility / Value / Liquidity 等の定量ファクターを DuckDB 上で計算する関数を実装:
      - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m、ma200_dev（データ不足時は None）
      - calc_volatility(conn, target_date): atr_20, atr_pct, avg_turnover, volume_ratio（データ不足時は None）
      - calc_value(conn, target_date): per, roe（raw_financials から最新財務を取得）
    - 全て prices_daily / raw_financials のみ参照し、本番取引 API 等にはアクセスしない設計。

  - kabusys.research.feature_exploration (src/kabusys/research/feature_exploration.py)
    - 将来リターン calc_forward_returns(conn, target_date, horizons=None)（デフォルト [1,5,21]）を実装。
    - IC（Information Coefficient）計算 calc_ic とランク化 rank、統計サマリー factor_summary を実装。
    - pandas 等に依存せず、標準ライブラリのみで完結する実装。

Security / Behavior notes
- 環境変数の自動ロードはプロジェクトルート検出に依存（.git または pyproject.toml）。検出できない場合は自動ロードをスキップ。
- .env 読み込み時、既存 OS 環境変数は保護される（protected set）。.env.local は .env を上書き可能。
- OpenAI API 呼び出しを伴う処理（score_news, score_regime）は api_key 引数を受け取り、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出。
- AI 系機能は応答パース失敗や API エラー時に個別スコアを 0.0 にフォールバックまたは該当チャンクをスキップするため、処理全体の停止を避けるフェイルセーフ設計。
- DB 書き込みは可能な限り冪等に実装（DELETE → INSERT、BEGIN/COMMIT/ROLLBACK の使用等）。

Notes / Known limitations
- PBR・配当利回りなどの一部バリュー指標は未実装（calc_value に明記）。
- DuckDB バインドの互換性問題（executemany に空リストを渡せない等）を考慮した実装になっている。
- news_nlp / regime_detector は gpt-4o-mini を想定した JSON Mode を使用する設計だが、プロバイダ側仕様変更に対する保守が必要。

Acknowledgements
- J-Quants / kabuステーション / OpenAI（gpt-4o-mini）との連携を想定した設計。

---
将来のリリースではバグ修正、テスト、ドキュメント追加、Strategy/Execution/Monitoring の各モジュールの実装拡充を予定しています。