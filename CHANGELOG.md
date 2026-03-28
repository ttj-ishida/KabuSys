# CHANGELOG

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog (https://keepachangelog.com/ja/1.0.0/).  
リリース日付はコミット時点の想定日（2026-03-28）で記載しています。

## [0.1.0] - 2026-03-28

### 追加 (Added)
- パッケージ初期リリース
  - パッケージメタ情報: kabusys/__init__.py にてバージョン 0.1.0、および公開サブパッケージのエクスポートを定義（data, strategy, execution, monitoring）。

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local または OS 環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を起点に探索）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - .env 読み込みの優先度: OS 環境変数 > .env.local > .env。OS 環境変数は保護（protected）され、.env.local の override を制御。
  - .env パーサを独自実装（export プレフィックス対応、シングル/ダブルクォート・バックスラッシュエスケープ、行末コメントの扱いの考慮）。
  - Settings クラスを提供:
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティを環境変数から取得（必須項目は未設定時に ValueError を送出）。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許可値チェック）、および is_live / is_paper / is_dev の便利プロパティ。
    - デフォルト DuckDB/SQLite パスを提供。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成し、OpenAI (gpt-4o-mini) を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST の UTC 換算）を calc_news_window で提供。
    - チャンクバッチ処理（デフォルト 20 銘柄/チャンク）、1銘柄あたりの最大記事数・最大文字数制限（トークン肥大化対策）。
    - JSON Mode の応答を検証・復元（前後余分テキストの切出し含む）、スコアは ±1.0 にクリップ。
    - API エラー（429・ネットワーク断・タイムアウト・5xx）に対する指数バックオフリトライ、失敗時は個別チャンクをスキップするフェイルセーフ設計。
    - テスト容易性: OpenAI 呼び出しをラップした _call_openai_api を patch 可能に実装。
    - DB 書き込みは冪等性を保つ（該当 date/code の DELETE → INSERT、DuckDB executemany の空リスト回避処理あり）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ保存。
    - マクロニュース抽出はニュースタイトルのキーワードマッチベース（複数マクロキーワードを定義）。
    - OpenAI 呼び出しは JSON レスポンスを期待し、リトライ/バックオフ・5xx の取り扱い・パース失敗時は macro_sentiment=0.0 とするフェイルセーフ設計。
    - レジームスコア合成処理および閾値判定、結果はトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等に保存。
    - テスト容易性: _call_openai_api の差し替えや _score_macro の _sleep_fn 注入により高速テストが可能。
    - API キーは引数 api_key または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError。

- Research モジュール (src/kabusys/research)
  - factor_research.py
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性指標（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB の SQL ウィンドウ関数で計算する関数群を提供。
    - データ不足時の None 処理を明確にし、結果は (date, code) キーの dict リストで返却。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）：任意のホライズン（デフォルト 1,5,21 営業日）を一つのクエリで取得。horizons の検証（正の整数かつ <=252）。
    - IC 計算（calc_ic）：Spearman ランク相関（ランクは平均ランク、ties を考慮）を計算。データ不足時は None を返す。
    - rank, factor_summary: ランク化ユーティリティと列ごとの基本統計量（count/mean/std/min/max/median）を提供。
  - research パッケージは data.stats の zscore_normalize を再利用するエクスポートを含む。

- Data モジュール (src/kabusys/data)
  - calendar_management.py
    - market_calendar テーブルを利用した営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。
    - DB にカレンダーがない場合は曜日ベース（土日を休日）でフォールバックする一貫した挙動。
    - 最大探索範囲および健全性チェック（最大未来日数）を導入し無限ループや誤データに対処。
    - calendar_update_job: J-Quants クライアント（jquants_client.fetch_market_calendar / save_market_calendar）を用いて差分取得・バックフィル（デフォルト直近 7 日を再取得）し、冪等的に保存。API エラー時はログ出力して 0 を返す。
  - pipeline.py / etl.py
    - ETLResult データクラスを追加（ETL の集約結果・品質問題・エラーメッセージを格納、to_dict によるシリアライズをサポート）。
    - ETL パイプライン設計に関するユーティリティ（差分更新、backfill、品質チェックの扱い）を実装する基礎を提供。
    - 内部ユーティリティ: テーブル存在チェック、テーブル最大日付取得等。
    - data.etl で ETLResult を再エクスポート。

### 変更 (Changed)
- 初回公開のため該当なし。

### 修正 (Fixed)
- 初回公開のため該当なし。

### 削除 (Removed)
- 初回公開のため該当なし。

### 非推奨 (Deprecated)
- 初回公開のため該当なし。

### セキュリティ (Security)
- 初回公開のため該当なし。

---

注記（設計上の重要ポイント）
- ルックアヘッドバイアス対策:
  - AI スコアリング / レジーム判定 / ファクター計算は内部で datetime.today()/date.today() を直接参照せず、呼び出し側が target_date を与える設計。DB クエリでも target_date 未満・未満等でルックアヘッドを防止。
- フェイルセーフ:
  - 外部 API（OpenAI, J-Quants 等）失敗時は例外で即中断せずフォールバック（スコア=0.0、チャンクスキップ、0件返却 等）してパイプラインの一部だけが失敗しても全体を破壊しないように設計。
- テスト容易性:
  - OpenAI 呼び出しラッパーや sleep 関数、API キー注入、関数単位の責務分割によりユニットテスト／モックが容易。
- DB 書き込み:
  - 可能な限り冪等操作（DELETE → INSERT、ON CONFLICT 方式等）およびトランザクション（BEGIN/COMMIT/ROLLBACK）での保護を行っている。

もし追加でリリースノートに含めたい詳細（例えば各関数の戻り値のサンプル、API スキーマや期待される DB スキーマの抜粋、あるいは「既知の制限事項」など）があれば教えてください。必要に応じてセクションを拡張して反映します。