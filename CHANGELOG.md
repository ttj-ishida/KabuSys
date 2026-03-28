# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
現在のバージョン: 0.1.0 — 2026-03-28

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買システム「KabuSys」の基本モジュール群を実装しました。主な追加項目と挙動は以下のとおりです。

### 追加
- パッケージ全体
  - パッケージ初期化 (src/kabusys/__init__.py)：バージョン番号を設定し、公開サブパッケージを定義（data, research, ai, ...）。
- 設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を自動ロードする機能を追加。
      - プロジェクトルート検出は __file__ を起点に `.git` または `pyproject.toml` を探索（CWD 非依存）。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
      - .env パーサは `export KEY=val`、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント（クォートなしの `#` 前にスペースがある場合）等に対応。
      - 既存 OS 環境変数は protected として上書きから保護（override 引数で挙動制御）。
    - Settings クラスを提供し、主要設定をプロパティ経由で取得可能:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須環境変数として検証）
      - KABU_API_BASE_URL, DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV（development / paper_trading / live の検証）および LOG_LEVEL（DEBUG/INFO/... の検証）
      - is_live / is_paper / is_dev の便利プロパティ
- AI（NLP）関連
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を銘柄毎に集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメント（-1.0～1.0）を算出し ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - 銘柄バッチ処理（デフォルト最大 20 銘柄／回）、記事トリム（最大記事数・文字数制限）を実装。
    - 再試行ロジック（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）を実装。
    - レスポンスのバリデーション（JSON 抽出・構造検証・コード照合・数値チェック）、スコアの ±1.0 クリッピング、部分成功時に既存スコアを保護するための部分置換（DELETE→INSERT）を実装。
    - テスト容易性のため、OpenAI 呼び出し関数をパッチ可能に設計（_call_openai_api の差し替え等）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする機能を実装。
    - マクロニュース抽出（マクロキーワードリスト）→ OpenAI（gpt-4o-mini）で JSON パース→ 再試行・フォールバック（API 失敗時 macro_sentiment=0.0）を備える。
    - レジーム算出ロジック、閾値定義、DuckDB トランザクション（BEGIN/DELETE/INSERT/COMMIT）とエラーハンドリング（ROLLBACK ログ）を実装。
    - ルックアヘッドバイアス対策として date 比較は target_date 未満や calc_news_window を用いる等、日付参照の取り扱いに注意。
- データプラットフォーム（DuckDB ベース）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar）と、営業日判定ユーティリティを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
      - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存（バックフィル・健全性チェックを実装）
    - DB にカレンダーがない/未登録の日は曜日ベース（平日=営業日）でフォールバックする一貫したロジックを採用。
    - 探索上限（_MAX_SEARCH_DAYS）など無限ループ防止。
  - src/kabusys/data/pipeline.py
    - ETL パイプラインの基本ユーティリティを実装。ETLResult データクラスを導入して取得件数、保存件数、品質チェック結果、エラー概要を集約できるようにした。
    - データ取得の差分判定、バックフィル、品質チェック（quality モジュール連携）に対応する設計方針を注記。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポート（公開 API）。
  - jquants_client 関連（参照／利用）
    - calendar_update_job 等で外部クライアント（jquants_client）を利用してデータ取得・保存を行う設計。
- リサーチ（ファクター算出・特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタム calc_momentum、ボラティリティ・流動性 calc_volatility、バリュー calc_value を実装。
    - DuckDB の SQL を活用し、ATR・移動平均・リターン・PER/ROE などを効率的に算出。データ不足時の None 扱いなどを明確化。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン calc_forward_returns（任意ホライズン対応）、IC（Spearman）計算 calc_ic、ランク化ユーティリティ rank、統計サマリー factor_summary を実装。
    - pandas 等に依存せず標準ライブラリ＋DuckDBで実装。
  - src/kabusys/research/__init__.py
    - 主要関数の再エクスポートを設定（研究用途に使いやすく公開）。
- ロギング／堅牢性
  - 各所で詳細なログ出力（info/warning/debug）を実装。異常時の例外捕捉とフェイルセーフ（スキップやデフォルト値使用）を意識して設計。
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() の直接参照回避を明記している箇所あり（関数引数で基準日を渡す設計）。

### 変更
- 初回リリースのため該当なし。

### 修正
- 初回リリースのため該当なし。

### 非推奨
- 初回リリースのため該当なし。

### 削除
- 初回リリースのため該当なし。

### セキュリティ
- OpenAI/外部 API キー等の取り扱いに関する注意:
  - OPENAI_API_KEY は関数引数で注入可能（api_key パラメータ）か環境変数で設定する必要あり。未設定時は ValueError を送出する箇所あり。
  - .env 自動ロードはプロジェクトルート検出に依存するため、配布後に挙動を管理する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

### 備考 / 開発者向けメモ
- テスト性: OpenAI 呼び出し部分は内部関数をパッチしてモック可能（ユニットテストを容易にする設計）。
- DB 書き込みは冪等（DELETE→INSERT 等）を意識して実装しており、部分失敗があっても既存データを不要に消さない設計になっています。
- DuckDB のバージョン差異（executemany の空リスト不可、配列バインドの挙動など）を考慮した実装上の注意点をコード中にコメントとして反映しています。
- 今後のリリースで想定される追加:
  - 監視（monitoring）・実行（execution）・strategy モジュールの実装拡張
  - テストカバレッジ拡充、各種例外・エラー処理の細分化
  - ドキュメント（API 使用例・運用ガイド）の追加

---

このファイルはコードベースの現在実装内容に基づき推測して作成しています。必要であれば、より詳細なリリースノート（関数ごとの変更点、既知の制限、使用例、必須環境変数一覧など）を追記します。どのレベルの詳細が必要か指示してください。