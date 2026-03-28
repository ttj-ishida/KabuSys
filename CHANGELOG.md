# CHANGELOG

すべての重要な変更はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠します。

## [0.1.0] - 2026-03-28

### Added
- 基本パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報: __version__ = "0.1.0"、パッケージ外部公開モジュールとして data/strategy/execution/monitoring を列挙。
- 環境設定管理モジュール (kabusys.config)
  - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
  - .env パーサの実装: コメント、export 形式、シングル/ダブルクォート、バックスラッシュのエスケープ処理などに対応。
  - 自動ロードの優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
  - Settings クラスを提供し、アプリケーションで使用する設定プロパティを公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development/paper_trading/live のバリデーション）、LOG_LEVEL（DEBUG/INFO/... のバリデーション）および is_live / is_paper / is_dev ヘルパー
  - 必須環境変数未設定時は ValueError を送出する _require 実装。
- AI モジュール (kabusys.ai)
  - news_nlp モジュール:
    - raw_news / news_symbols を集約して OpenAI (gpt-4o-mini) にバッチ送信し、銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書き込む機能。
    - バッチサイズ、記事数・文字数トリム、JSON Mode 利用、レスポンス検証、スコアの ±1.0 クリップ、実行結果の部分書き換え（DELETE → INSERT）に対応。
    - 再試行（429/ネットワーク断/タイムアウト/5xx）に対する指数バックオフ実装。
    - calc_news_window(target_date) 関数により日本時間のニュースウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を算出。
    - public API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返却。api_key 未指定時は OPENAI_API_KEY を参照し未設定なら ValueError を送出。
  - regime_detector モジュール:
    - ETF 1321（日経225連動型）の直近200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・保存。
    - マクロニュース抽出はキーワードベースで raw_news からタイトルを取得（最大 20 件）。
    - OpenAI 呼び出しは JSON Mode で実施。API エラー時はマクロセンチメントを 0.0 にフォールバックするフェイルセーフ実装。
    - レジーム結果を market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT）。
    - public API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返却。api_key 未指定時は OPENAI_API_KEY を参照し未設定なら ValueError を送出。
- Research モジュール (kabusys.research)
  - factor_research:
    - モメンタム（約1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER/ROE）等の定量ファクター計算関数を実装。
    - 関数: calc_momentum(conn, target_date), calc_volatility(conn, target_date), calc_value(conn, target_date)
    - DuckDB の SQL + Python ロジックにより、prices_daily / raw_financials のみを参照して結果を (date, code) ベースの dict リストで返却。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク関数（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリおよび DuckDB で完結する実装。
  - research パッケージの __all__ を整備し主要 API を再エクスポート（zscore_normalize は kabusys.data.stats から）。
- Data モジュール (kabusys.data)
  - calendar_management:
    - market_calendar テーブルを用いた営業日判定ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB 登録値を優先し、未登録日は曜日ベースのフォールバック（週末は非営業日）で一貫して扱う設計。
    - calendar_update_job(conn, lookahead_days=90) を実装し J-Quants API から差分取得 → 保存（バックフィル・健全性チェック含む）。
  - ETL / pipeline:
    - ETLResult データクラスを導入し、ETL 実行結果（取得件数・保存件数・品質問題・エラー）を構造化して返却可能に。
    - パイプライン内での差分取得、バックフィル、品質チェック（kabusys.data.quality）との連携方針を実装。
    - データ存在チェックや最大日付取得などのユーティリティを実装。
  - jquants_client との連携を前提とした保存/取得フローを想定（fetch/save 関数を使用）。
- テスティング/拡張性に配慮した実装
  - OpenAI 呼び出し部分は内部でラップしており、テスト時に patch で差し替え可能（各モジュールで独立実装）。
  - DuckDB との相互作用は接続オブジェクトを引数として受け取ることで副作用を限定。
  - ルックアヘッドバイアス防止のため各処理で datetime.today()/date.today() を直接参照しない設計（target_date を明示）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- 環境変数のロードにおいて OS 環境変数を保護する機構を導入（.env ファイルによる上書きを制御）。
- 必須トークン（OpenAI / Slack / J-Quants / kabu API）に関して未設定時は明示的にエラーを出すため、秘密情報の漏れに付随する誤動作を抑止。

### Notes / 実装上の注意点
- DuckDB バージョン依存性に関する互換性考慮:
  - executemany に空リストを渡せないバージョン（例: DuckDB 0.10）を考慮して空チェックを行っている箇所がある。
- OpenAI API 呼び出しは JSON Mode を使用して厳密な JSON レスポンスを期待するが、実運用で余剰テキストが混入するケースに対しては復元ロジックを実装している（最外側の { } を抽出してパース）。
- API 呼び出し失敗時は多くの箇所でフェイルセーフ（スコア 0.0 / スキップ）とし、処理全体を止めない設計。
- 一部関数は外部 API（jquants_client や OpenAI）との連携を前提としており、実行には対応する API キー・接続および DB スキーマ（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials 等）が必要。

---

（初回リリース — 今後のリリースでは [Unreleased] セクションを用いて変更を記録してください。）