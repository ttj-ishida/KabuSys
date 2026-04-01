# Changelog

すべての変更は Keep a Changelog に準拠しています。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-01

### Added
- パッケージ初期リリース。
- 基本情報
  - パッケージバージョンを src/kabusys/__init__.py にて "0.1.0" として定義。
- 設定・環境変数管理（kabusys.config）
  - .env / .env.local ファイル自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml から検出）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装：コメント行、export プレフィックス、クォート（シングル/ダブル）とバックスラッシュエスケープ対応、インラインコメントの扱い。
  - .env 読み込み時に OS 環境変数を保護する protected 機構を実装し、.env.local での上書きを許可。
  - Settings クラスを公開（J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境・ログレベル判定などのプロパティを提供）。
  - KABUSYS_ENV と LOG_LEVEL のバリデーション（許容値チェック）。
- AI ニュース解析（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成。
  - OpenAI（gpt-4o-mini、JSON Mode）を用いた銘柄ごとのセンチメントスコアリング機能 score_news を提供。
  - API バッチ処理（1回あたり最大 20 銘柄）、1銘柄あたりの最大記事数／最大文字数によるトリム。
  - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）をエクスポネンシャルバックオフで実装。
  - レスポンス検証ロジック（JSON 抽出、results 配列・code/score 確認、スコアの数値変換、未知コードの無視、±1.0 クリップ）。
  - ai_scores テーブルへの冪等的な置換（対象コードを絞って DELETE → INSERT）。
  - calc_news_window ユーティリティ（JST 基準のニュースウィンドウを UTC naive datetime で返す）。
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム判定 score_regime を実装。
  - prices_daily / raw_news を用いて ma200_ratio を計算、マクロニュースはニュースタイトルをマクロキーワードでフィルタして取得。
  - OpenAI（gpt-4o-mini）呼び出しを独立した内部実装で行い、API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフ設計。
  - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
- 研究用ファクター計算（kabusys.research）
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials から最新の財務データを取得して PER / ROE を計算。
    - 各関数は DuckDB を用いた SQL ベース実装で、(date, code) キーの dict リストを返す。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコード 3 件未満は None）。
    - rank: 同順位は平均ランクで扱うランク関数（丸め誤差対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー関数。
  - 研究用 API を __all__ で再エクスポート。
- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX カレンダーの管理（market_calendar テーブルを利用）。
    - 営業日判定 is_trading_day、次/前営業日 next_trading_day/prev_trading_day、期間内営業日取得 get_trading_days、SQ 判定 is_sq_day の提供。
    - DB 登録なしは曜日ベースでフォールバック（週末を非営業日）。
    - calendar_update_job: J-Quants API から差分取得し冪等的に保存（バックフィル・健全性チェックあり）。
  - ETL パイプライン（pipeline）:
    - ETLResult dataclass を公開（取得件数・保存件数・品質問題・エラーの集約）。
    - 差分更新・バックフィル・品質チェックの方針を実装（jquants_client と quality モジュールを利用する設計）。
  - ETL 用公開インターフェース kabusys.data.etl に ETLResult を再エクスポート。
- research と data 間の依存関係整理と公開用 __all__ の整備。
- OpenAI 呼び出し部でのテスト置換ポイント（_call_openai_api の箇所）を各モジュールで用意。

### Changed
- 初期実装だが、設計として以下を明確化。
  - ルックアヘッドバイアス対策: datetime.today()/date.today() をスコア計算内部で参照しない設計（target_date に依存）。
  - API 不可用時のフェイルセーフ: LLM 呼び出しエラーやパース失敗は例外で停止せず、ゼロスコアまたは該当コードスキップで継続して堅牢性を優先。
  - DuckDB の互換性考慮: executemany に空リストを渡せない点を回避するガードを追加。
  - レスポンスパースのロバスト化: JSON Mode でも前後に余計なテキストが混在するケースを考慮して最外側の {} を抽出して復元を試みる処理を追加。
  - OpenAI API エラー分類: RateLimit / Connection / Timeout / 5xx をリトライ対象とし、非 5xx は即座にフェイル（スキップ）する挙動に分離。

### Fixed
- API レスポンスパース失敗や不正スコアで処理が全停止する問題を回避（ログ出力して該当チャンク/記事をスキップ）。
- market_regime / ai_scores への書き込みでの部分失敗による他銘柄データ消失リスクを回避（対象コードを限定した DELETE → INSERT の冪等パターンを採用）。
- .env 読み込み時のファイル読み取り失敗でのクラッシュを警告に置き換え（読み込み失敗時は処理継続）。

### Security
- 環境変数の扱いにおいて、OS 環境変数を保護（.env による意図せぬ上書きを防止）する仕組みを導入。

---

注記:
- 本 CHANGELOG はソースコードの内容から機能・設計・フェイルセーフ挙動を推測して作成しています。実際の機能要件や仕様書と差異がある可能性があります。詳細は各モジュールの docstring と実装を参照してください。