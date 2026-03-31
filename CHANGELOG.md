# Changelog

すべての注記は Keep a Changelog 準拠で記載しています。  
このファイルはコードベースから推測可能な実装内容・設計方針に基づいて作成しています。

全般:
- バージョンはパッケージ定義（kabusys.__version__ = "0.1.0"）に合わせています。
- 日付は本CHANGELOG作成日（2026-03-31）を使用しています。

## [Unreleased]
- 今後の変更点はここに記載します。

## [0.1.0] - 2026-03-31

Added
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__init__）。__version__ = "0.1.0"、主要サブパッケージ名を __all__ に定義 (data, strategy, execution, monitoring)。
- 環境設定管理 (kabusys.config)
  - .env ファイル自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml に基づく）。
  - .env/.env.local の読み込み順・上書きルールを実装（OS 環境変数保護、.env.local は上書き）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - 高度な .env 行パーサー実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のエスケープ処理
    - インラインコメントの正確な無視（条件付き）
  - Settings クラスを導入し、アプリ設定をプロパティ経由で取得可能に:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト値あり）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（デフォルトパスあり）
    - KABUSYS_ENV の検証（development/paper_trading/live のみ許容）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ヘルパー: is_live / is_paper / is_dev
- AI モジュール (kabusys.ai)
  - ニュース NLU/スコアリング (news_nlp)
    - ニュース収集ウィンドウ計算 (calc_news_window)（JST 基準を UTC naive datetime に変換）
    - raw_news と news_symbols を結合して銘柄ごとに記事集約 (_fetch_articles)
    - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント評価機能 (score_news)
      - バッチ処理（最大20銘柄/チャンク）、トークン肥大化対策（記事数／文字数制限）
      - JSON Mode を期待したレスポンスパースと冗長部分の復元ロジック
      - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ再試行
      - レスポンス検証（results キー・型・コード整合性・数値チェック）、スコア ±1.0 にクリップ
      - DuckDB の互換性考慮（executemany 空リスト回避、部分書き換えによる冪等性確保）
      - テスト容易性のため _call_openai_api を切り替え可能（unittest.mock.patch を想定）
  - 市場レジーム判定 (regime_detector)
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio）算出 (_calc_ma200_ratio)
      - ルックアヘッド防止: target_date 未満のデータのみ使用、データ不足時は中立(1.0)にフォールバック
    - raw_news からマクロキーワードでフィルタしタイトル取得 (_fetch_macro_news)
    - OpenAI を用いたマクロセンチメント評価 (_score_macro)（失敗時のフォールバック macro_sentiment=0.0）
      - 再試行ロジック、APIError の status_code による挙動分岐、JSON パース例外対策
    - ma200 と macro_sentiment を重み付け合成してレジームスコア判定（bull/neutral/bear）
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装
- 研究 (research) パッケージ
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等
    - calc_value: raw_financials を用いた PER/ROE の算出（target_date 以前の最新財務レコードを使用）
    - DuckDB を使った SQL ベース実装、営業日ベースのウィンドウ設計
  - feature_exploration モジュール:
    - calc_forward_returns: 将来リターンの一括取得（複数ホライズン対応、horizons の検証）
    - calc_ic: スピアマンランク相関（IC）計算（ランク計算を含む、最小レコード数チェック）
    - factor_summary: 各ファクターの count/mean/std/min/max/median を計算
    - rank: 同順位は平均ランクを返す実装（丸めで ties を安定検出）
  - research.__init__ で主要関数群をエクスポート
- データ基盤 (data) パッケージ
  - calendar_management:
    - market_calendar テーブルの有無に応じた営業日判定 is_trading_day / is_sq_day
    - next_trading_day / prev_trading_day / get_trading_days 実装（DB 登録値優先、未登録は曜日フォールバック）
    - calendar_update_job: J-Quants からの差分取得 → market_calendar へ冪等更新、バックフィル・健全性チェック実装
    - テーブル存在確認等ユーティリティ (_table_exists / _has_calendar_data / _fetch_is_trading / _to_date)
  - pipeline / etl:
    - ETLResult dataclass 追加（ETL の各種件数、品質問題、エラー概要を保持）
    - ETL ユーティリティ（データ最終日取得 _get_max_date、公称の差分/バックフィル方針等）
    - data.etl で ETLResult を再エクスポート
  - jquants_client との連携ポイント（fetch/save を呼ぶ想定）を組み込み（実装は別モジュール）
- ロギング / 設計方針
  - ルックアヘッドバイアス防止設計: 各処理は datetime.today()/date.today() を内部参照しない（引数で target_date を受ける）
  - フェイルセーフ姿勢: OpenAI/API 失敗やデータ不足時は例外を全体に投げずフォールバックやスキップを行う（必要に応じて警告ログ）
  - DuckDB の互換性（executemany 空リスト等）を考慮した実装

Changed
- 初回リリースのため過去変更はなし。

Fixed
- 初期実装で以下の堅牢化を行い問題を未然に防止:
  - .env パーサーでのクォート内エスケープとインラインコメント処理を改善
  - OpenAI API 呼び出し時のエラー分類（RateLimit/接続/タイムアウト/5xx）に基づいた再試行ロジックを追加
  - JSON Mode でも前後余剰テキストが混ざるケースへの耐性（最外の {} を抽出してパース）
  - DuckDB への書き込みで executemany に空リストを渡さない安全処理を追加（DuckDB 0.10 互換性）

Security
- セキュリティ関連の変更はなし。ただし API キー等は環境変数経由で取得し、Settings._require により必須チェックを行う設計。

Notes / 既知の制約
- OpenAI クライアントとして openai.OpenAI を利用する実装だが、実行環境での API キー設定が必須（api_key 引数または OPENAI_API_KEY 環境変数）。
- news_nlp / regime_detector は外部 API（OpenAI）に依存するため、API エラー時は一部スコアが生成されない可能性がある（フォールバックは実装済み）。
- 明示的に strategy / execution / monitoring の実装は今回のコードスニペット内に含まれていない（パッケージ公開名として用意）。

参考
- 各モジュール内の docstring に設計方針・処理フロー・フェイルセーフの振る舞いが詳細に記載されています。必要に応じて該当モジュールの docstring を参照してください。