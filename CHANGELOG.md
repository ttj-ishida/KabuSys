# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-03-28
初回リリース。本リポジトリは日本株向け自動売買 / データプラットフォームの基盤モジュール群を提供します。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0
  - __all__ として data, strategy, execution, monitoring をエクスポート（戦略・実行・監視のプレースホルダを含む）。

- 環境設定管理 (src/kabusys/config.py)
  - .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を起点に探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサ実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - クォート無し値のインラインコメント処理（'#' の前が空白/タブの場合をコメントとして扱う）
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境種別（development|paper_trading|live）等の取得・検証を行う。
  - 必須項目未設定時は ValueError を送出する _require を実装。

- ニュースNLP（AI） (src/kabusys/ai/news_nlp.py)
  - score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント（-1.0〜1.0）を取得、ai_scores テーブルへ idempotent に書き込む。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して比較）を対象。calc_news_window を提供。
    - バッチ処理: 1 API 呼び出しで最大 20 銘柄、1 銘柄あたり最大 10 記事／3000 文字でトリム。
    - OpenAI への呼び出しは JSON Mode を利用し、レスポンスのバリデーション・パース復元（前後余計テキストから {} を抽出）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx サーバーエラーに対して指数バックオフのリトライ実装。
    - 失敗時は当該チャンクをスキップして他チャンクの処理を継続する（フェイルセーフ）。
    - テスト容易性: _call_openai_api をパッチ差し替え可能に設計。
    - スコアは ±1.0 にクリップして保存。

- 市場レジーム判定（AI + 指標合成） (src/kabusys/ai/regime_detector.py)
  - score_regime(conn, target_date, api_key=None)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull / neutral / bear）を判定し、market_regime テーブルへ冪等書き込みを行う。
    - マクロキーワードで raw_news をフィルタし、最大 20 件を LLM に送信。
    - OpenAI 呼び出しは gpt-4o-mini（JSON Mode）を利用、エラー時のリトライとフェイルセーフ（macro_sentiment=0.0）を実装。
    - レジームスコア合成式、閾値、ログ出力により監査可能。
    - テスト容易性: _call_openai_api を差し替え可能。

- リサーチ / ファクター計算 (src/kabusys/research/)
  - factor_research.py
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility(conn, target_date): 20 日 ATR（atr_20）、相対 ATR (atr_pct)、20 日平均売買代金 (avg_turnover)、出来高比(volume_ratio) を計算。
    - calc_value(conn, target_date): raw_financials から最新の財務データを取得して PER, ROE を計算（EPS=0/欠損時は None）。
    - 全関数は DuckDB の prices_daily / raw_financials のみを参照し、外部 API へはアクセスしない設計。
    - 出力は (date, code) を含む dict のリスト。
  - feature_exploration.py
    - calc_forward_returns(conn, target_date, horizons): 将来リターン（例: 1,5,21 日）を計算。ホライズン検証・同一クエリでの LEAD 利用により効率化。
    - calc_ic(factor_records, forward_records, factor_col, return_col): Spearman ランク相関（IC）を実装（欠損・定数分布に対応）。
    - rank(values): 同順位は平均ランクを返す実装（丸めことで浮動小数の ties を安定化）。
    - factor_summary(records, columns): count/mean/std/min/max/median を算出するユーティリティ。
  - research パッケージは zscore_normalize を kabusys.data.stats から再エクスポート。

- データプラットフォーム（DuckDB ベース） (src/kabusys/data/)
  - calendar_management.py
    - JPX カレンダー管理用ユーティリティ:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
      - market_calendar テーブルが存在しない場合は曜日ベースのフォールバック（週末を非営業日扱い）。
      - DB の登録値を優先し、未登録日は曜日フォールバックで一貫した挙動を保証。
      - calendar_update_job(conn, lookahead_days=90) により J-Quants API から差分取得して market_calendar を冪等保存。バックフィル・健全性チェックを実装。
  - pipeline.py / etl.py
    - ETLResult データクラスを定義（取得件数、保存件数、品質チェック結果、エラー一覧を含む）。
    - 差分取得・backfill・品質チェック・idempotent 保存（jquants_client の save_*）のための設計方針を実装。
    - 内部ユーティリティ: テーブル存在確認、最大日付取得など。
    - etl.py で ETLResult を公開再エクスポート。
  - jquants_client / quality との連携を想定（実装はクライアントモジュール側に依存）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーは関数引数で注入可能かつ、環境変数 OPENAI_API_KEY から取得する仕組みとし、明示的に未設定時は ValueError を出して誤動作を防止。

### 既知の設計上のポイント / 注意点
- AI モジュール（news_nlp / regime_detector）はルックアヘッドバイアスを避けるため、datetime.today() / date.today() を直接参照しない設計。すべて target_date ベースで計算する。
- OpenAI 呼び出しは JSON mode を期待するが、実際のレスポンスが前後に余計なテキストを含むケースを考慮してパース回復ロジックを実装している。
- API 呼び出し失敗時は局所的にフェイルセーフ（0.0 やスキップ）して全体処理を継続する設計。部分失敗時の DB 一貫性を保つため書き込みは対象コードを限定して置換（DELETE → INSERT）する。
- DuckDB 0.10 周りの挙動（executemany に空リスト不可等）を考慮した実装がされている。
- テスト容易性のために外部 API 呼び出し点（_call_openai_api 等）はパッチ差し替え可能に実装している。

---

今後の予定（案）
- strategy / execution / monitoring の具体実装（売買ロジック・発注ラッパ・監視アラート）
- jquants_client の具体的実装と CI 用のモック
- ドキュメント（StrategyModel.md、DataPlatform.md 等）の整備と例示スクリプト追加

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートとして使用する際は適宜補正してください。）