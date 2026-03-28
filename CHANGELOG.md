# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買システム「KabuSys」の基盤的機能を実装。

### Added
- パッケージ初期化
  - パッケージバージョンを __version__ = "0.1.0" として公開。
  - パッケージ外部公開モジュール: data, strategy, execution, monitoring を __all__ に定義。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定読み込みを実装。
  - プロジェクトルート自動探索: .git または pyproject.toml を起点に .env/.env.local を検索し自動ロード（CWD 非依存）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーの改善:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応。
    - クォート無し値に対するインラインコメント解釈（# の直前が空白・タブの場合のみコメント扱い）。
  - .env と .env.local の読み込み順: OS 環境 > .env.local（上書き）> .env（未設定のみ）。
  - 環境変数保護: 既存 OS 環境変数を保護する protected 機能（override 時の上書き除外）。
  - Settings クラスを提供（settings インスタンス）:
    - J-Quants / kabuステーション / Slack / DB パス等の必須／デフォルト値取得。
    - env 値（development / paper_trading / live）および LOG_LEVEL のバリデーション。
    - is_live/is_paper/is_dev のユーティリティプロパティ。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコアリングを実装。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して処理（ルックアヘッドバイアス防止）。
    - バッチ処理: 1コールあたり最大 20 銘柄、各銘柄は最大 10 記事・3000 文字にトリム。
    - JSON Mode を利用しレスポンスを厳密に検証。冗長テキストが混入しても {} 範囲抽出を試行して解析。
    - リトライ / バックオフ: 429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフで再試行。
    - スコアのバリデーションと ±1.0 にクリップ。
    - 書き込みは冪等（DELETE -> INSERT）で部分失敗時に既存データを保護。DuckDB の executemany 空配列制約に対処。
    - テスト容易性: _call_openai_api をパッチ差し替え可能。
    - 公開関数: score_news(conn, target_date, api_key=None) -> 書き込んだ銘柄数 を返す。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワード一覧を用いて raw_news タイトルを抽出し、OpenAI（gpt-4o-mini）で macro_sentiment を JSON で取得。
    - マクロAPI失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - レジームスコアの計算式と閾値を設定し、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - ルックアヘッドバイアス防止: DB クエリは target_date 未満のデータのみ参照、datetime.today()/date.today() を直接参照しない。
    - 公開関数: score_regime(conn, target_date, api_key=None) -> 1（成功）を返す。

- Research（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン・200日MA乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比）、バリュー（PER・ROE）等のファクター計算を実装。
    - DuckDB 上の prices_daily / raw_financials のみを参照し、外部 API へアクセスしない安全設計。
    - 関数: calc_momentum, calc_volatility, calc_value（いずれも conn, target_date を引数にリストを返す）。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）を提供。
    - calc_forward_returns は任意ホライズンの検証（バリデーション）と1クエリ実行での効率的取得を実装。
    - calc_ic はスピアマンのランク相関を厳密に計算（同順位の平均ランク処理含む）。
  - 研究用ユーティリティを __all__ で公開（zscore_normalize は data.stats から再エクスポート）。

- Data プラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）
    - JPX カレンダーを扱う market_calendar の読み書き・判定ヘルパーを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB 登録値を優先し、未登録日は曜日ベースのフォールバックで一貫性を保つ設計。
    - calendar_update_job: J-Quants API 経由で差分取得・バックフィル（直近数日）・健全性チェック（将来日付が異常に遠い場合はスキップ）を実装。
  - ETL パイプライン（pipeline）
    - ETLResult dataclass を実装し、ETL の取得数・保存数・品質問題・エラーを記録する構造を提供。
    - _get_max_date などのヘルパーで差分更新ロジックの基盤を実装。
    - jquants_client と quality モジュールの連携を想定した設計（差分取得・保存・品質チェックのフロー）。
  - etl.py は pipeline.ETLResult を公開インターフェースとして再エクスポート。

### Changed
- 設計方針の明示化
  - AI / リサーチ / データ処理いずれもルックアヘッドバイアス防止のため日時参照を直接行わない設計を明示。
  - API 呼び出しの失敗は基本的に例外を破壊的に伝播させず、フェイルセーフ（可能な部分は処理継続）とする方針を採用。
  - DuckDB の互換性（executemany の空配列制約など）に配慮した実装に変更。

### Fixed
- ロバスト性向上
  - .env 読み込みでのファイル読み取り失敗時に警告を出して続行するように対応。
  - OpenAI レスポンスの JSON パース失敗や API エラー時に適切にログを残してフォールバックする処理を追加（news_nlp / regime_detector）。
  - DB 書き込み時のトランザクションエラーハンドリング強化（ROLLBACK の失敗もログ記録）。

### Security
- 機密情報の扱い
  - 環境変数から API キー等を取得する設計。API キーが未設定の場合は明示的に ValueError を発生させることで誤動作を防止。
  - .env の自動読み込みは環境変数フラグで無効化可能（テスト等の用途）。

### Documentation / Tests
- コード中に詳細な docstring と設計ノートを追加（各関数・モジュールで振る舞い・制約・設計方針を明示）。
- テストしやすさを考慮して、OpenAI 呼び出し部分をパッチ差し替え可能な構造にしている（ユニットテストでのモック化を想定）。

---

今後の予定（例）
- strategy / execution / monitoring の実装（注文実行ロジック、バックテスト、モニタリング・アラート）。
- jquants_client の具象実装・API エラーハンドリングの進化。
- 追加のファクター・ポートフォリオ生成ロジック・モデル評価ツールの実装。

もし CHANGELOG に反映して欲しい追加の項目（実際のコミット差分・リリースノート等）があれば、その情報をいただければ更新します。