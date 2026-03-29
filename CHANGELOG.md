# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

- リリース日付はコミット時の推定日を使用しています（2026-03-29）。

## [0.1.0] - 2026-03-29

初回公開リリース。日本株自動売買システムのコアコンポーネントの最初の実装を含みます。主に以下の機能群を実装しています。

### 追加 (Added)
- パッケージ初期化
  - src/kabusys/__init__.py
    - パッケージバージョン __version__ = "0.1.0"
    - 公開サブパッケージ: data, strategy, execution, monitoring（strategy, execution, monitoring の実体は別途実装想定）

- 環境変数・設定管理
  - src/kabusys/config.py
    - .env 自動読み込み機能（優先順位: OS 環境 > .env.local > .env）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化可能。
    - .env パーサ実装（export フォーマット、シングル/ダブルクォート、エスケープ、インラインコメント判別など対応）。
    - プロジェクトルートの自動探索（.git または pyproject.toml を基準）。
    - Settings クラスを公開（J-Quants / kabu / Slack / DB パス / 環境モード / ログレベルなどの取得）。
    - 必須環境変数未設定時は ValueError を発生させる _require() を提供。
    - KABUSYS_ENV に対する許容値検証（development, paper_trading, live）と LOG_LEVEL の検証。

- AI（自然言語処理）モジュール
  - src/kabusys/ai/news_nlp.py
    - ニュース記事をバッチで OpenAI（gpt-4o-mini）へ送りセンチメントスコアを算出し ai_scores テーブルへ書き込む処理。
    - 対象ウィンドウは前日15:00 JST ～ 当日08:30 JST（UTC に変換した半開区間）。
    - 1銘柄あたり最大記事数・最大文字数でトリムする保護 (_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK)。
    - バッチサイズ、エクスポネンシャルバックオフによる再試行、JSON レスポンスの堅牢なバリデーションとパースを実装。
    - API キー注入対応（api_key 引数または環境変数 OPENAI_API_KEY）。
    - フェイルセーフ設計: API エラー時は該当チャンクをスキップし、処理継続。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - マクロキーワードで raw_news をフィルタ、最大記事数を取得して OpenAI に問い合わせる。
    - API 呼び出しのリトライ、5xx の取り扱い、パースエラー時のフォールバック（macro_sentiment=0.0）を実装。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を使用。
    - ルックアヘッドバイアス対策: datetime.today()/date.today() を参照せず、prices_daily は target_date 未満のデータのみを使用。

- データプラットフォーム（Data）モジュール
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理・営業日判定ロジック。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - market_calendar が未登録場合は曜日ベースのフォールバック（土日を非営業日扱い）。
    - カレンダー更新バッチ calendar_update_job 実装（J-Quants API から差分取得 → 保存の流れ、バックフィル、健全性チェックを含む）。
    - DB に一部しか登録がない場合でも一貫した判定を行う設計。

  - src/kabusys/data/pipeline.py
    - ETL パイプラインの基盤実装（差分取得、保存、品質チェックの呼び出し設計）。
    - ETLResult データクラス（target_date, fetched/saved 件数, quality_issues, errors）を実装。
    - テーブル存在チェックや最大日付取得ユーティリティを提供。
    - バックフィル日数や J-Quants の開始日などの定数を定義。

  - src/kabusys/data/etl.py
    - pipeline.ETLResult の再エクスポート。

  - その他
    - src/kabusys/data/__init__.py（パッケージ化用）

- リサーチ（研究）モジュール
  - src/kabusys/research/factor_research.py
    - モメンタム、ボラティリティ、バリューなどのファクター計算機能を実装。
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時は None を返す）。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から直近財務データを取得して PER/ROE を計算。
    - DuckDB を使った SQL 中心の実装で、外部 API には依存しない。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク付け（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
    - Spearman 型のランク相関計算や欠損値・非有限値の扱いに注意した実装。

  - src/kabusys/research/__init__.py
    - 主要関数の再エクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）

### 修正 (Fixed)
- （初回リリースのため既知のバグ修正履歴はなし）

### 破壊的変更 (Breaking Changes)
- なし（初回リリース）

### セキュリティ (Security)
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を使用。キーはログに出力しない設計を想定。
- 環境変数読み込み時、OS 環境変数は保護され .env ファイルで上書きされない（protected set を利用）。

### 注意事項 / マイグレーション
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings クラスから取得するプロパティで必須とされる（未設定で ValueError）。
  - OPENAI_API_KEY は AI 関数（score_news, score_regime）実行時に必要。
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で上書き可能）
  - SQLite（監視用）: data/monitoring.db（環境変数 SQLITE_PATH で上書き可能）
- 自動 .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で利用）。
- DuckDB 互換性:
  - executemany に空リストを渡すとエラーになる点を回避するため、空チェックを行ってから executemany を実行する実装になっています。

今後の予定（未実装・予定機能・改善案）
- strategy / execution / monitoring の具象実装（現状はパッケージ・名前空間のみ）。
- jquants_client の具体実装・外部 API との統合部分の拡充。
- 単体テスト・統合テストと CI 設定の追加。
- ドキュメント（API リファレンス、運用手順、データモデル）の整備。

もし追加で、特定ファイルごとの詳細な変更点やリリースノートの文言修正、日付の変更などが必要であればお知らせください。