# CHANGELOG

すべての変更は Keep a Changelog の形式に基づいて記載しています。  
このファイルはリポジトリ内のソースコードから推測して自動生成しています。実際の公開履歴やリリースノート作成時は必要に応じて編集してください。

## [0.1.0] - 2026-03-28

### Added
- 基本パッケージ初期リリース。パッケージ名: kabusys、バージョン: 0.1.0。
- パブリック API / モジュール群を追加:
  - kabusys.config: 環境変数・設定管理（Settings オブジェクト）を提供。.env 自動ロード、必須キー取得ヘルパーを含む。
  - kabusys.ai: ニュース NLP と市場レジーム判定機能を追加。
    - news_nlp.score_news(conn, target_date, api_key=None): raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを計算して ai_scores テーブルへ保存。
    - regime_detector.score_regime(conn, target_date, api_key=None): ETF(1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して market_regime テーブルへ保存。
  - kabusys.research: ファクター計算・特徴量探索ツール群を追加。
    - calc_momentum / calc_value / calc_volatility: prices_daily / raw_financials を参照して各種ファクターを計算。
    - calc_forward_returns / calc_ic / rank / factor_summary: 将来リターンの算出、IC（Spearman）の計算、統計サマリーなどを提供。
  - kabusys.data: データ基盤ユーティリティを追加。
    - calendar_management: JPX カレンダーの管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）と夜間バッチ更新 calendar_update_job を実装。
    - pipeline / etl: ETL パイプラインの骨組みと ETLResult データクラスを追加。差分取得・保存・品質チェックを想定。
    - etl, pipeline の公開用ラッパー（ETLResult の再エクスポート）。
  - kabusys.data.jquants_client との連携ポイント（fetch/save を呼ぶ設計）。
- 環境変数自動読み込み機構:
  - プロジェクトルート探索（.git または pyproject.toml を基準）により .env/.env.local を自動読み込み。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーは export KEY=... 形式、クォートのエスケープ、インラインコメントなどに対応。.env.local は .env を上書きする（ただし OS 環境変数は protected）。
- OpenAI 呼び出しの JSON mode 利用と堅牢化:
  - gpt-4o-mini を使用。response_format に JSON を指定した呼び出し実装を含む。
  - 429/ネットワーク断/タイムアウト/5xx などを対象とした指数バックオフリトライ（最大回数設定）を実装。
  - レスポンスの JSON パースやスキーマ検証処理を実装（news_nlp._validate_and_extract など）。
- DuckDB を用いた DB 操作を前提にした冪等保存ロジック:
  - score_news / score_regime / calendar_update_job などは BEGIN / DELETE / INSERT / COMMIT を用い、例外時に ROLLBACK を試行するよう設計。
  - DuckDB の executemany の制約（空リスト不可）を考慮した分岐処理を実装。
- ルックアヘッドバイアス対策（時刻取得を外部化・不使用）:
  - 全てのバッチ処理・スコア計算関数は内部で datetime.today() / date.today() を直接参照せず、target_date を引数にして deterministic に計算する設計を採用（テスト容易性とデータリーク防止）。
- 各種デフォルト・閾値・定数を明示的に設定（例: ニュースウィンドウ、MA 期間、重み、最大記事数、バッチサイズ等）。

### Changed
- （初回公開のため差分履歴はなし）ただし設計方針・実装上の重要な選択を明記:
  - news_nlp と regime_detector は内部で OpenAI 呼び出し関数を別実装にしてモジュール結合を避ける（テスト時に個別で差し替え可能）。
  - カレンダー関連は DB 登録値を優先し、未登録日は曜日ベースでフォールバックする一貫したロジックを適用。
  - get_trading_days / next_trading_day / prev_trading_day は探索上限（_MAX_SEARCH_DAYS）を設け、無限ループを防止。
  - ETL の品質チェックは Fail-Fast ではなく問題を収集して呼び出し元に委ねる設計。

### Fixed
- N/A（初回リリース相当のため既存不具合修正履歴はなし）。ただし以下の堅牢化を実装:
  - .env 読み込み失敗時は警告を出して処理継続（例外を投げずフェイルソフト）。
  - OpenAI レスポンスのパースに失敗した場合は該当スコアを 0.0 やスキップにフォールバックして全体処理を継続。
  - DB 書き込み失敗時の ROLLBACK を試行し、ROLLBACK 自体の失敗も警告ログで記録。

### Security
- 機密情報の取り扱い:
  - Settings から JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID を必須取得（_require で未設定時は ValueError を送出）。
  - .env 読み込み時に OS 環境変数を保護する protected キーセットを導入（.env による上書きを抑止）。

### Notes / Implementation details（重要な設計・挙動）
- news_nlp:
  - ニュースの時間ウィンドウは JST 前日 15:00 〜 当日 08:30（内部では UTC naive datetime に変換して扱う）。
  - 1 銘柄あたりの最大記事数・最大文字数を制限してトークン肥大化を抑制。
  - チャンク単位（デフォルト 20）で OpenAI に送信し、部分失敗時に他銘柄の既存スコアを消さないよう対象コードだけを DELETE → INSERT。
  - レスポンス検証で未知コードや非数値スコアは無視。
- regime_detector:
  - ETF 1321 の 200 日 MA 乖離（重み 70%）と LLM マクロセンチメント（重み 30%）を合成。スコアは -1〜1 にクリップ。
  - API 呼び出し失敗時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。
  - レジーム閾値を設定し、'bull'/'neutral'/'bear' を決定して market_regime に冪等書き込み。
- research:
  - ファクター計算は DuckDB SQL を多用し、営業日ベースのラグ（LAG / LEAD / WINDOW）で算出。
  - calc_forward_returns の horizons は安全性チェック（1〜252 の整数）を実施。
  - calc_ic はスピアマンのランク相関を直接実装（同順位は平均ランク）。
- data.calendar_management:
  - calendar_update_job は J-Quants から差分取得 → jq.save_market_calendar に保存。バックフィル・健全性チェックを実装。
  - market_calendar が未取得であれば曜日ベースのフォールバックを行う。
- ETL pipeline:
  - ETLResult に品質問題とエラー収集用フィールドを持たせ、to_dict でシリアライズ可能。

---

注: 実際のリリースノート作成時は、ここに記載した設計意図・未実装機能・依存（OpenAI / J-Quants / DuckDB）を踏まえて、テスト手順・既知の制限・マイグレーション手順等を追記してください。