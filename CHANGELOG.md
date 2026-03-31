# Changelog

すべての変更は Keep a Changelog 準拠で記載します。  
リリース日付はパッケージのバージョン情報および現行のコミット状況に基づいています。

全般的な記載方針:
- 日付は YYYY-MM-DD 形式で記載しています。
- 各項目では実装された主要機能、設計上の注意点、互換性の有無を簡潔に示します。

## [Unreleased]
（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-31

### Added
- 初回公開リリース。以下の主要サブパッケージ・機能を実装。
  - パッケージのエントリポイント
    - kabusys.__init__: パッケージ名とバージョンを定義（__version__ = "0.1.0"）。
  - 設定・環境変数管理（kabusys.config）
    - .env ファイルおよび OS 環境変数から設定を自動読み込みする機能を提供。
    - プロジェクトルートの判定は __file__ を起点に .git または pyproject.toml を探索するため、CWD に依存しない挙動。
    - .env パーサーは export プレフィックス、クォート（シングル/ダブル）内のエスケープ、インラインコメントの処理をサポート。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - Settings クラスでアプリケーション設定（J-Quants / kabuステーション / Slack / DB パス / 監視しきい値 / 環境判定等）をプロパティとして提供。バリデーション（enum 的な値・ログレベル検証）を実装。
  - AI（自然言語処理 / レジーム判定）
    - kabusys.ai.news_nlp
      - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメント（ai_score）を算出して ai_scores テーブルへ書き込む。
      - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTC に変換してクエリ）を対象にする calc_news_window を提供。
      - バッチ処理（1 API 呼び出しで最大 20 銘柄）・記事数/文字数のトリム（1銘柄あたり最大記事数/最大文字数）を実装。
      - API 失敗（429/ネットワーク断/タイムアウト/5xx）は指数バックオフでリトライし、最大回数超過時は当該チャンクをスキップして継続するフェイルセーフ設計。
      - レスポンスの厳密なバリデーションを行い、score を ±1.0 にクリップして保存。部分成功時は対象コードのみ置換して既存スコアを保護（DELETE→INSERT）。
      - テストを容易にするため、OpenAI 呼び出し部分は内部関数（_call_openai_api）を patch できる設計。
    - kabusys.ai.regime_detector
      - ETF 1321（日経225連動ETF）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースからの LLM センチメント（重み 30%）を合成して日次マーケットレジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする score_regime を実装。
      - マクロニュース抽出はニュースタイトルのマクロキーワード照合で行い、該当記事がある場合にのみ OpenAI を呼び出す（記事なし時は macro_sentiment=0.0）。
      - OpenAI 呼び出しはリトライ・エラーハンドリング・JSON パース保護を備え、障害時はマクロスコアを 0.0 にフォールバックして処理継続する設計。
      - ルックアヘッドバイアス回避のため、日付比較は厳密（target_date 未満のデータのみ）で datetime.today()/date.today() を直接参照しない実装。
  - Data（ETL / カレンダー等）
    - kabusys.data.pipeline
      - ETLResult データクラスを導入。ETL の実行結果（取得数/保存数/品質問題/エラー）を構造化して返却・監査用に to_dict を提供。
      - 差分更新・バックフィル・品質チェックを想定した ETL の設計方針を実装（実際の ETL 呼び出しロジック・jquants_client 連携はモジュール参照）。
    - kabusys.data.etl
      - pipeline.ETLResult を再エクスポート。
    - kabusys.data.calendar_management
      - JPX カレンダー管理機能を実装: market_calendar テーブルの参照・更新ロジック、営業日判定（is_trading_day）、前後営業日取得（next_trading_day / prev_trading_day）、期間内営業日取得（get_trading_days）、SQ 日判定（is_sq_day）、および夜間バッチ更新 job（calendar_update_job）を提供。
      - DB にカレンダーがない場合は曜日ベース（土日除外）でフォールバックする堅牢な挙動。
      - バックフィル、ルックアヘッド、健全性チェック（過度に未来の last_date に対する警告）を実装。
      - jquants_client 経由での差分取得と保存処理を想定（fetch/save の呼び出しは try/except で安全に扱う）。
  - Research（ファクター計算 / 特徴量探索）
    - kabusys.research.factor_research
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
      - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率などを計算。入力ウィンドウにおける NULL の取り扱いに注意。
      - calc_value: raw_financials から最新の財務データを取得し PER（EPS が 0/NULL の場合は None）・ROE を計算。
      - 全関数は DuckDB 接続を受け取り SQL を主体に処理（外部 API 呼び出しなし）。
    - kabusys.research.feature_exploration
      - calc_forward_returns: 指定基準日から各ホライズン（デフォルト [1,5,21]）の将来終値リターンを計算（ホライズンが存在しない場合は None）。
      - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。サンプル数不足時は None。
      - rank: 同順位は平均ランクで処理するランク化ユーティリティを実装（丸めによる tie 判定対策あり）。
      - factor_summary: count/mean/std/min/max/median を計算する統計サマリー機能を提供。
  - その他
    - internal logger 呼び出しや duckdb クエリの実装により、DB 側での冪等性・互換性（DuckDB のバージョン差分を考慮）を考慮した実装。
    - テスト容易性: OpenAI 呼び出しや時間ベース処理の注入/モックポイントを設けている（例: _call_openai_api を patch 可能）。

### Changed
- 新規リリースにつき該当なし。

### Fixed
- 新規リリースにつき該当なし。

### Deprecated
- 該当なし。

### Removed
- 該当なし。

### Security
- 複数の機能で外部機密情報（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を環境変数として利用。
  - Settings にて必須項目は _require() によって未設定時に ValueError を投げることで、起動時の明示的なエラーとして通知する設計。
  - .env の自動読み込みは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

### 注意事項 / 既知の制限
- strategy / execution / monitoring パッケージは __all__ に名を挙げているが（kabusys.__all__）、このリリースに含まれるコードスニペットではそれらの具体的実装が含まれていない（将来リリースで追加予定の可能性あり）。
- OpenAI との連携は gpt-4o-mini を想定した実装になっているが、API仕様や SDK のバージョン変更により status_code 等の属性が変わる可能性があるため、エラーハンドリングは慎重に行っている（getattr を多用）。
- DuckDB のバージョン差（例: executemany に対する空リストの挙動、配列バインド）に配慮した実装を行っているが、利用環境の DuckDB バージョンによっては追加の互換対応が必要になる場合がある。
- ルックアヘッドバイアス防止のため、全てのアルゴリズムは日付比較において target_date 未満/未満等を厳密に扱う設計となっており、date の取り扱いは timezone 混入を避けるため全て date / UTC-naive datetime を利用している点に留意してください。
- エラー時はサービス継続性を優先する（多くのケースでフェイルセーフとしてスコアを 0.0 にする、または当該チャンクをスキップする）設計のため、部分的な失敗が発生しても処理全体は継続されます。必要に応じて呼び出し元で再試行やアラートを行ってください。

---

今後のリリースでは以下を予定しています（例）:
- strategy / execution / monitoring の具象実装と、実際の発注ロジックとの連携
- 単体テスト・CI 設定の追加、型チェックの強化
- J-Quants クライアント（jquants_client）と quality モジュールの具体実装と公開

もし CHANGELOG に追記してほしい項目（実際のコミットや対応チケットに基づく詳細な変更点等）があれば、該当情報を提供してください。追加・修正して更新します。