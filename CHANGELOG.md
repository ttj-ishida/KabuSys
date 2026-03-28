Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。
このファイルは "Keep a Changelog" のフォーマットに準拠します。

[Unreleased]
------------

（現在の差分はありません）

[0.1.0] - 2026-03-28
-------------------

Added
- 初回リリース。パッケージ "kabusys" を提供。
  - パッケージ公開情報:
    - __version__ = "0.1.0"
    - エクスポート: data, strategy, execution, monitoring（__all__）
- 環境設定/設定管理モジュール (kabusys.config)
  - .env / .env.local 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能
  - .env パースの強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメントの扱い（クォート無しの場合は '#' の直前が空白/tab のときコメント判定）
  - OS 環境変数を保護する protected オプション（.env.local で OS 環境を上書きしない）
  - Settings クラスを提供（プロパティ経由で必須トークンやパス、環境/ログレベルのバリデーションを実施）
    - 必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - デフォルト値や Path 型返却（DUCKDB_PATH / SQLITE_PATH 等）
    - KABUSYS_ENV / LOG_LEVEL の許容値検証
- AI モジュール (kabusys.ai)
  - news_nlp.score_news:
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）を用いた銘柄別センチメント評価を行い ai_scores テーブルへ書き込み
    - タイムウィンドウ計算 (前日 15:00 JST ～ 当日 08:30 JST)（calc_news_window 提供）
    - 1銘柄あたりの記事数・文字数上限（トークン肥大化対策）
    - バッチ処理（最大 20 銘柄 / API 呼び出し）
    - 再試行（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）
    - レスポンス検証とスコアクリッピング（±1.0）
    - DuckDB の制約に合わせた安全な置換ロジック（DELETE → INSERT、executemany 空リスト回避）
    - テスト用フック: _call_openai_api を unittest.mock.patch で差し替え可能
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込み
    - マクロ記事の抽出（マクロキーワード一覧）→ OpenAI によるセンチメント評価（gpt-4o-mini）
    - API 失敗時は macro_sentiment=0.0 をフォールバック（フェイルセーフ）
    - ルックアヘッドバイアス対策（datetime.today()/date.today() を使用しない、DB クエリに date < target_date の排他条件を使用）
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック時のログ
    - テスト用フック: _call_openai_api を差し替え可能
- Research モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev の計算（prices_daily を使用）
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio の計算（ATR の NULL 伝播を明示的に制御）
    - calc_value: per / roe の算出（raw_financials と prices_daily 組合せ、最新財務レコード取得ロジック）
    - DuckDB 上で完結する設計（外部 API 呼び出しなし）
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD で一括取得
    - calc_ic: スピアマンランク相関（Information Coefficient）計算、必要件数不足時は None を返す
    - rank: ランク付け（同順位は平均ランク、丸めで ties 対応）
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー
    - 外部ライブラリ不使用（標準ライブラリのみ）
- Data モジュール (kabusys.data)
  - calendar_management:
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days の実装
    - market_calendar がない場合は曜日ベースのフォールバック（週末を非営業日とする）
    - DB 登録値を優先し、未登録日は曜日フォールバックで一貫した判定
    - calendar_update_job: J-Quants API から差分取得して market_calendar テーブルを更新（バックフィル・健全性チェック有）
  - pipeline / etl:
    - ETLResult データクラスの公開（kabusys.data.etl は pipeline.ETLResult を再エクスポート）
    - ETL パイプライン用のユーティリティと DuckDB との互換性考慮のユーティリティ関数（_get_max_date 等）
    - 設計上の備考として差分更新、バックフィル、品質チェック（quality モジュールとの連携）を想定

Changed
- （初回リリースにつき該当なし）

Fixed
- （初回リリースにつき該当なし）

Security
- OpenAI API キーや各種トークンは Settings/properties で必須扱いとし、未設定時は明確なエラーを発生させる設計
- .env 自動読み込み時に OS 環境変数を保護するロジックを追加（.env.local で既存の OS 環境を不用意に上書きしない）

Notes / 設計方針（重要な挙動）
- ルックアヘッドバイアス対策: LLM による評価・ファクター計算・ETL の各所で datetime.today()/date.today() を直接参照しない設計。すべて外部から与えた target_date を基準に処理する。
- フェイルセーフ: 外部 API（OpenAI/J-Quants）障害時は例外を投げずにフォールバック（0.0 やスキップ）する箇所があるため、データ欠損時にも処理継続を優先。
- テスト容易性: OpenAI 呼び出し部分に差し替え可能な内部関数を用意（unittest.mock.patch によるモック可）。
- DuckDB 互換性: executemany に空リストを渡せない環境に対するガードや、list 型バインディングの互換性回避（個別 DELETE を利用）などの実装上の配慮あり。
- ロギング: 各モジュールで詳細な debug/info/warning ログを出力するよう実装。

Acknowledgements / 未実装（今後の候補）
- 一部外部クライアント実装は kabusys.data.jquants_client に依存（本差分では詳細未提示）
- Strategy・execution・monitoring パッケージの具体実装はこのリリース内では含まれていない想定（パッケージトップで __all__ として公開）
- PBR・配当利回りなどの一部バリューファクターは未実装（calc_value に注記あり）

References
- 本 CHANGELOG はコードベースの内容から機能・設計方針を推測して作成しています。実際のコミット履歴やリリースノートがある場合はそれに合わせて更新してください。