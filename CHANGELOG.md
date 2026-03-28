# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
リリース日はコードベースの現在日時（自動推測）に基づき記載しています。

## [0.1.0] - 2026-03-28 (初回リリース)

### Added
- 基本パッケージ初期実装
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py にて定義）。
  - 公開サブパッケージ: data, research, ai, monitoring, strategy, execution（__all__ による概念的公開）。

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local / OS 環境変数からの設定自動読み込み機能。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を基準に探索（CWD 非依存）。
  - .env パーサ: コメント、export 句、シングル／ダブルクォート、バックスラッシュエスケープ、行内コメントへの対応。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 設定ラッパー Settings を提供（プロパティ経由で必須変数チェックや既定値・検証を実施）。
    - 必須環境変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パス設定: DUCKDB_PATH, SQLITE_PATH（既定値: data/kabusys.duckdb, data/monitoring.db）
    - 環境種別検証: KABUSYS_ENV ∈ {development, paper_trading, live}
    - ログレベル検証: LOG_LEVEL ∈ {DEBUG, INFO, WARNING, ERROR, CRITICAL}

- AI 関連（src/kabusys/ai）
  - ニュースNLP: score_news 関数（src/kabusys/ai/news_nlp.py）
    - raw_news + news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode で一括センチメント評価。
    - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄あたりの最大記事数・文字数制限（トリム）。
    - 再試行ロジック（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）。
    - レスポンス検証: JSON 抽出、results 配列・型チェック、未知コードの無視、スコアは ±1.0 にクリップ。
    - 書き込みは部分的冪等（取得成功コードのみ DELETE→INSERT）で DB への部分失敗から既存スコアを保護。
    - テスト用に OpenAI 呼び出し部分を差し替え可能（_call_openai_api を patch 可能）。
    - 時間ウィンドウ計算 util: calc_news_window（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して半開区間扱い）。
    - 失敗時フェイルセーフ: API キー未設定では ValueError、API 呼び出し失敗はスキップ（例外を破壊的に投げない設計）。

  - 市場レジーム判定: score_regime 関数（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせ、日次でレジーム判定（bull / neutral / bear）。
    - MA 計算は target_date 未満のデータのみを使用しルックアヘッドバイアスを防止。
    - マクロニュース取得は news_nlp のウィンドウ計算を再利用（calc_news_window）。
    - OpenAI 呼び出しのリトライ/フェイルセーフ実装（API 失敗時は macro_sentiment=0.0）。
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT、ROLLBACK のハンドリング）。
    - テスト性のため OpenAI 呼び出し箇所を差し替え可能。

- Research（src/kabusys/research）
  - factor_research モジュール（calc_momentum, calc_value, calc_volatility）
    - モメンタム: 約1ヶ月/3ヶ月/6ヶ月リターン、200 日移動平均乖離（ma200_dev）。
    - バリュー: PER・ROE（raw_financials から最新財務データを取得して算出）。
    - ボラティリティ/流動性: 20 日 ATR（true range の扱いに注意）、20 日平均売買代金、出来高比率。
    - DuckDB を用いた SQL ベースの実装。結果は (date, code) をキーとする dict リストで返す。
  - feature_exploration モジュール（calc_forward_returns, calc_ic, rank, factor_summary）
    - 将来リターン計算（horizons のバリデーション、単一クエリで複数ホライズンを取得）。
    - IC（Spearman の ρ）計算（ランク相関）。
    - ランク関数（同順位は平均ランク、丸めによる ties 対処）。
    - ファクターの統計サマリ（count/mean/std/min/max/median）。
  - research パッケージ __init__ で zscore_normalize を data.stats から再エクスポート。

- Data プラットフォーム（src/kabusys/data）
  - calendar_management モジュール
    - JPX カレンダーの管理（market_calendar テーブルの夜間バッチ更新、差分取得、ON CONFLICT での上書き）。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータがない/未登録日のフォールバックは曜日ベース（週末を非営業日と扱う）。
    - バックフィル・健全性チェック（バックフィル日数、将来日付が過度に大きい場合はスキップ）。
    - calendar_update_job: J-Quants からの差分取得→保存のラッパー（例外・ログ管理）。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラス（取得数 / 保存数 / 品質チェック問題 / エラーの集約、to_dict によるシリアライズ）。
    - 差分取得、バックフィル、品質チェックの設計方針を反映した骨組み。
    - data.etl で ETLResult を再エクスポート。

- 共通点 / 実装方針（横断的）
  - DuckDB を主要なローカル分析 DB として使用（関数は DuckDB の接続オブジェクトを引数に取る）。
  - 外部 API 呼び出し（OpenAI / J-Quants）に対して再試行・フォールバック・ログを徹底している（サービス停止時の安全性を重視）。
  - ルックアヘッドバイアス対策: datetime.today() / date.today() の直接参照を避け、target_date を明示する設計。
  - DB 操作は冪等性・トランザクション（BEGIN/COMMIT/ROLLBACK）を意識して実装。
  - テスト容易性: OpenAI 呼び出しや内部ユーティリティをモック差替えできる箇所を用意。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーおよび各種シークレットは環境変数経由で扱うことを想定（Settings で必須チェック）。
- .env ファイル読み込みはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

### Important notes / 要点
- 必要な DB テーブル（想定）
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar などが各モジュールで参照されるため、スキーマ準備が必要です（実装はコードコメント・ドキュメント参照）。
- OpenAI の利用
  - gpt-4o-mini を JSON Mode（response_format={"type": "json_object"}）で使用する想定。
  - API 呼び出しはリトライ・タイムアウト・レスポンス検証を行い、失敗時は安全なデフォルト（0.0 やスキップ）にフォールバックする設計。
- ETL・カレンダー更新
  - calendar_update_job は J-Quants クライアント（data.jquants_client）に依存。API のレスポンス／保存関数は例外を投げる可能性があるため呼び出し側でログ・戻り値で確認してください。
- テスト支援
  - AI 呼び出し（_call_openai_api）や time.sleep の差し替えが想定されており、ユニットテストでモック可能。

---

将来的なリリースでは、モジュールの追加、パフォーマンスチューニング、より詳細な品質チェックルールの実装、監視／アラート機能強化などを予定しています。必要であれば上記各機能についてより細かい変更履歴（関数ごとの変更点や DB スキーマ要件）を追記します。