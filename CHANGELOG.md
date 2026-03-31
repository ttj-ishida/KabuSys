# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このプロジェクトの初期リリースを示します。

全般的な方針：
- DuckDB を主要データストアとして利用
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント／レジーム判定を実装
- ルックアヘッドバイアスを避ける設計（関数内で date.today()/datetime.today() を参照しない等）
- DB 書き込みは冪等性を重視（DELETE → INSERT / ON CONFLICT 等）
- エラー時はフェイルセーフで続行する設計（API 失敗時のフォールバックやログ記録）

## [0.1.0] - 2026-03-31

### Added
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として公開。
  - パッケージ公開 API に data, strategy, execution, monitoring を設定。

- 環境設定管理 (`kabusys.config`)
  - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動ローダーを実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化用フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パーサを実装（export プレフィックス、クォート内のバックスラッシュエスケープ、コメントの扱い等に対応）。
  - Settings クラスを提供し、主要設定値をプロパティ経由で取得可能:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development|paper_trading|live、検証あり）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、検証あり）
  - 未設定の必須環境変数は ValueError を送出。

- AI モジュール (`kabusys.ai`)
  - ニュース NLP スコアリング (`news_nlp.score_news`)
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成。
    - OpenAI（gpt-4o-mini）の JSON mode を用いてバッチでスコアリング（チャンク単位、デフォルト 20 銘柄/チャンク）。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して比較）。
    - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ。
    - レスポンス検証（JSON パース、results リスト、コード整合性、数値検証）。不正レスポンスはスキップ。
    - スコアは ±1.0 にクリップ。
    - DuckDB 0.10 の executemany 空リスト制約に対応した安全な INSERT/DELETE ロジック。
    - テスト容易性: 内部の OpenAI 呼び出し関数を patch 可能（unittest.mock で差し替え）。
    - 返り値: 書き込んだ銘柄数。

  - 市場レジーム判定 (`regime_detector.score_regime`)
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で 'bull'/'neutral'/'bear' を算出。
    - LLM を用いる場合はマクロキーワードで raw_news をフィルタ（最大 20 件）。
    - OpenAI 呼び出しは独立実装で、失敗時は macro_sentiment = 0.0 として継続。
    - レジームスコアは -1.0〜1.0 にクリップし、閾値でラベル化。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - 返り値: 成功時 1。

- Research（ファクター・特徴量） (`kabusys.research`)
  - ファクター計算 (`factor_research`)
    - calc_momentum: 約1/3/6ヶ月のリターン、200 日 MA 乖離を計算。データ不足時は None。
    - calc_volatility: 20 日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算。データ不足時は None。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS が無効なら None）。
    - すべて DuckDB の prices_daily / raw_financials のみ参照。外部発注 API 等アクセスなし。

  - 特徴量探索 (`feature_exploration`)
    - calc_forward_returns: 各ホライズン（デフォルト [1,5,21] 営業日）での将来リターンを計算。horizons の検証あり。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算。十分なデータがない場合は None。
    - rank: 同順位を平均ランクで扱うランク変換ユーティリティ（丸めによる ties 回避）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。

- Data モジュール (`kabusys.data`)
  - カレンダー管理 (`calendar_management`)
    - JPX カレンダーの夜間バッチ更新 job（calendar_update_job）を実装：J-Quants から差分取得・冪等保存。
    - 営業日判定・検索ユーティリティ:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - カレンダーデータがない／未登録日には曜日（平日）ベースのフォールバックを実装。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) により無限ループを防止。
    - バックフィル、健全性チェックを実装（極端に未来の日付がある場合はスキップ）。

  - ETL パイプライン (`pipeline.ETLResult` と etl 再エクスポート)
    - ETLResult データクラスを公開（取得件数、保存件数、品質問題、エラーの集約）。
    - ETL 処理方針に基づく定数（バックフィル日数等）と内部ユーティリティを実装。

### Changed
- 初回リリースのため特段の「変更」は無し（初期導入）。

### Fixed
- 初回リリースのため特段の「修正」は無し。

### Notes / 設計上の重要な挙動
- ルックアヘッドバイアス回避:
  - score_news, score_regime, 各 research 関数は内部で現在時刻を参照せず、必ず引数として与えられた target_date を基準に処理します。
- フェイルセーフ:
  - OpenAI 呼び出しの失敗やパースエラーは基本的に例外を上位に伝播させず、適切なデフォルト（0.0 や空辞書、スキップ）で継続しログに記録します。ただし、DB 書き込み時の例外は ROLLBACK 後に伝播します。
- DuckDB 互換性対応:
  - executemany に空リストを渡すと失敗するバージョン（例: DuckDB 0.10）を考慮し、空チェックを行ってから executemany を実行します。
- テストのしやすさ:
  - OpenAI 呼び出し部分はモジュール内の私的関数を patch することで簡単にモック可能（例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")）。

### Migration / Upgrade notes
- 本リリースは初期バージョンのため、既存の API からの互換性問題は想定していません。
- 使用にあたっては下記の環境変数を適切に設定してください（不足すると ValueError を発生します）:
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
  - OPENAI_API_KEY (news_nlp / regime_detector 使用時に必要。関数呼び出しで api_key を明示的に渡すことも可能)
- デフォルトの DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- 自動で .env を読み込む振る舞いはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。CI やテストで自動ロードを抑止するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

今後のリリースで検討している事項（例）:
- strategy / execution / monitoring の実装拡張（現在はパッケージ公開のみ）
- J-Quants クライアントの詳細実装と統合テスト
- より詳細な品質チェックルールの追加（quality モジュール拡張）
- ロギング設定・構成の柔軟化（JSON ログ、外部ロガーへの転送等）