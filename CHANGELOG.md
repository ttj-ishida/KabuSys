# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

現在のバージョン: 0.1.0

## [Unreleased]


## [0.1.0] - 2026-04-02

### Added
- 初期公開リリース（kabusys v0.1.0）。
- パッケージ構成を追加・公開
  - kabusys パッケージルート（__version__ = 0.1.0, __all__）。
  - サブパッケージ（data, research, ai, research, 等の主要モジュール群）。
- 環境設定管理モジュール（kabusys.config）
  - .env / .env.local の自動読み込み機構（プロジェクトルートを .git / pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサの強化:
    - export プレフィックス対応（export KEY=val）。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - コメント処理（クォート外の # を適切に無視）。
  - 環境変数取得ユーティリティ（Settings クラス）を実装。
    - J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / ログレベル等のプロパティを用意。
    - 値検証（LOG_LEVEL, KABUSYS_ENV の許容値チェック）とヘルプメッセージ。
- AI モジュール
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を銘柄別に集約し、OpenAI（gpt-4o-mini）へ JSON Mode でバッチ送信。
    - バッチサイズ・文字数制限（1銘柄あたり最大記事数・最大文字数）を実装。
    - 再試行（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実装。
    - レスポンスの厳格なバリデーションとスコアクリップ（±1.0）。
    - ai_scores テーブルへ冪等的に書き込み（部分書き込み戦略: 対象コードのみ DELETE → INSERT）。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書込銘柄数を返す。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して
      市場レジーム（bull/neutral/bear）を日次判定。
    - DuckDB からのデータ取得（prices_daily, raw_news）と market_regime への冪等書き込みを実装。
    - OpenAI 呼び出しは失敗時フォールバック（macro_sentiment=0.0）やリトライを実装。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 1（成功）を返す。
- リサーチ（定量）モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離の計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率。
    - calc_value: PER（EPS が無効な場合は None）、ROE（raw_financials から取得）。
    - DuckDB ベースの SQL 実装。結果は (date, code) を含む dict のリストで返却。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン（複数ホライズン対応、入力検証あり）。
    - calc_ic: ランク相関（Spearman）の計算（欠損/非有限値は除外、最小レコード数チェック）。
    - rank: 同順位は平均ランクで処理（丸め対策あり）。
    - factor_summary: count/mean/std/min/max/median の統計サマリー。
  - research パッケージは利用しやすい再エクスポートを提供（主要関数を __all__ に公開）。
- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar を参照した営業日判定、前後営業日の取得、期間内営業日リスト取得、SQ 日判定を提供。
    - DB にカレンダーがない場合は曜日ベースでフォールバック（設計上一貫性あり）。
    - calendar_update_job: J-Quants から差分取得して market_calendar を更新（バックフィル、健全性チェック、冪等保存）。
  - pipeline / ETL:
    - ETLResult データクラスを公開（pipeline.ETLResult を kabusys.data.etl 経由で再エクスポート）。
    - ETLResult は取得件数・保存件数・品質問題・エラー概要を保持し、辞書化ユーティリティを提供。
    - ETL 実装方針・ユーティリティ（テーブル存在チェック、最終日取得など）を準備。
  - DuckDB との互換性や実行時の注意（executemany の空リスト回避等）を考慮した実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数で注入可能（テスト容易性）かつ環境変数 OPENAI_API_KEY を利用。キーのログ出力や誤流出を避ける実装方針。
- .env 読み込みで OS 環境変数を保護する機能（protected set）を実装。  

### Notes / 注意事項
- 必要とする DB テーブル（例）:
  - prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials, news_symbols 等。
- OpenAI 呼び出しは gpt-4o-mini を想定し、JSON Mode を利用する設計。API レスポンスの形式が変わるとパース/バリデーションに影響します。
- .env の自動読み込みはプロジェクトルート探索に依存するため、パッケージ配布後や実行環境によっては KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自前で設定を行ってください。
- 既知の設計方針:
  - ルックアヘッドバイアス対策として datetime.today()/date.today() を直接参照しない関数設計。
  - API 失敗時はフェイルセーフ（スコア 0.0 / スキップ）して処理継続する方針。
  - DuckDB のバージョン差異（executemany の空配列制約など）を考慮して実装。

もし詳細な変更差分（コミット単位）やリリースノート向けの要約（短い文言）が必要であれば、用途に合わせて別途出力します。