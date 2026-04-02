Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。

0.1.0 - 2026-04-02
------------------

Added
- 初回リリース。パッケージ名: kabusys, バージョン 0.1.0 を src/kabusys/__init__.py に定義。
- 環境設定管理モジュール (kabusys.config)
  - .env/.env.local ファイルまたは環境変数から設定を自動読み込みする機能を提供。
  - プロジェクトルートの探索は __file__ を起点に .git または pyproject.toml を探す実装で、CWD に依存しない。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサは export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの解釈ルールを実装。
  - protected パラメータにより OS 環境変数の上書きを防止する仕組みを実装。
  - Settings クラスを公開 (settings)：J-Quants / kabu API / Slack / DB パス / 監視閾値 / 実行環境などのプロパティを提供。
  - 必須キーが未設定の場合は _require が ValueError を投げる。

- AI モジュール (kabusys.ai)
  - news_nlp.score_news
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI (gpt-4o-mini) にバッチ送信してセンチメントを算出。
    - タイムウィンドウは JST ベース（前日 15:00 ～ 当日 08:30）を UTC に変換して比較。
    - バッチサイズ上限 20 銘柄、1 銘柄あたりの記事数/文字数制限を実装（トリム処理）。
    - JSON Mode を使い厳密な JSON を要求。レスポンスのバリデーションを実装し、不正応答はスキップ。
    - 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフで再試行。
    - ai_scores テーブルへは部分書き込み保護（対象コードのみ DELETE → INSERT）を行い、部分失敗時に既存データを保護。
    - DuckDB 0.10 の executemany の制約を回避するため、空パラメータでの実行を避けるチェックを実装。
    - API キーは引数 api_key または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を投げる。
    - テスト容易性のため _call_openai_api を patch して差し替え可能。

  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離 (ma200_ratio) と、news_nlp ベースのマクロセンチメントを重み合成して市場レジーム（'bull' / 'neutral' / 'bear'）を判定。
    - ma200_weight=0.7, macro_weight=0.3、スケーリング等の定数と閾値を実装。
    - マクロニュースはマクロキーワードでフィルタして最大 20 件を LLM に渡す。
    - OpenAI 呼び出しは JSON mode を使いリトライ制御を実装。API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - 結果は market_regime テーブルへ冪等に保存（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込みエラー時は ROLLBACK を試み上位に例外を伝播。

- Research モジュール (kabusys.research)
  - factor_research: calc_momentum, calc_volatility, calc_value を実装。
    - Momentum: mom_1m/mom_3m/mom_6m, ma200_dev（データ不足時は None を返す）。
    - Volatility/Liquidity: 20 日 ATR（atr_20）、atr_pct、avg_turnover、volume_ratio（必要行数未満は None）。
    - Value: raw_financials から直近財務を取得して PER / ROE を計算（EPS 0/欠損は None）。
    - 全関数は DuckDB の prices_daily / raw_financials のみ参照。結果は (date, code) を含む dict のリストで返す。
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank を実装。
    - calc_forward_returns は複数ホライズン（デフォルト [1,5,21]）に対応、horizons のバリデーションを行う。
    - calc_ic は Spearman ランク相関を実装（同率順位は平均ランク）、対象レコードが 3 未満なら None。
    - factor_summary は count/mean/std/min/max/median を算出。
    - rank は小数丸め (round(v, 12)) を用いた同順位処理を行う。
  - 一部ユーティリティを kabusys.data.stats から再エクスポート。

- Data モジュール (kabusys.data)
  - calendar_management
    - JPX カレンダー管理。is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった営業日判定 API を提供。
    - market_calendar テーブルが無い場合は曜日ベース（週末除外）でフォールバックする一貫した挙動を設計。
    - calendar_update_job により J-Quants API から差分取得・バックフィル（直近 _BACKFILL_DAYS）して market_calendar を冪等保存する処理を実装。健全性チェックあり。
    - jquants_client (jq) に依存して fetch/save を行う。
  - pipeline / etl
    - ETLResult dataclass を定義して ETL 実行結果（取得数・保存数・品質問題・エラー）を表現。to_dict で品質問題を簡易辞書化可能。
    - pipeline モジュールで差分更新戦略、backfill、品質チェック（quality）連携の土台を実装。
    - 内部ユーティリティとしてテーブル存在チェックや最大日取得ユーティリティなどを追加。
  - etl の公開インターフェースに ETLResult を再エクスポート。

Changed
- 設計上の重要方針や安全策を明文化・実装
  - すべての AI/リサーチ/データ処理関数で datetime.today()/date.today() の直接参照を避け、引数 target_date を使うことでルックアヘッドバイアスを防止。
  - OpenAI API 呼び出しはレスポンスの頑健なバリデーションとリトライロジック（指数バックオフ、5xx 判定）を適用。
  - DB 書き込みは冪等性を優先（DELETE → INSERT 等）し、部分失敗時に他コードの既存データを維持する実装（ai_scores など）。
  - テスト・モックを容易にするため、OpenAI 呼び出し部分は内部関数化して差し替え可能にした（unittest.mock.patch を想定）。

Fixed
- エッジケース耐性の強化
  - .env パーサで引用符内のバックスラッシュエスケープとインラインコメントの扱いを明確化。
  - DuckDB executemany の空リストエラー回避（空の params を渡さないガード）。
  - API レスポンスの JSON パース失敗時に前後の不要テキストを含むケースから最外の {} を抽出して復元するロジックを追加（news_nlp）。

Notes / Migration
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings クラスのプロパティで必須とされ ValueError を発生させる。
- 環境変数・設定の主なキー
  - KABUSYS_ENV (development|paper_trading|live)
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
  - DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - OPENAI_API_KEY を env に置くか、score_news/score_regime の api_key 引数で渡す。
  - 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- DB テーブル
  - 本リリースでは以下の DuckDB テーブルを想定している: prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials。各モジュールの docstring を参照してスキーマ要件に合わせてください。
- OpenAI
  - デフォルトモデルは gpt-4o-mini。レスポンスは JSON モードを利用し厳密な JSON を期待する。
  - API 呼び出しは自動リトライ・エラーハンドリング付きだが、API キー未設定時は ValueError が発生するため注意。

Acknowledgements / Testing tips
- テスト時には kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api を unittest.mock.patch して Chat API 呼び出しを差し替えることで外部 API 依存を排除できます。
- DuckDB 関連のソースは executemany の空リスト制約や日付型の取り扱いに配慮した実装になっています。

今後の予定（例）
- ファクターの追加（PBR・配当利回り等）
- ETL の品質チェックレポート強化 / 自動アラート化
- モデルやプロンプトの改善、温度・システムプロンプトの柔軟化

---
このリリースはソースコードから推測して記載しています。追加の変更点や修正がある場合は教えてください。