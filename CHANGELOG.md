# Changelog

すべての変更は https://keepachangelog.com/ja/ に準拠して記載しています。

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買システムのコアライブラリを実装しました。主要な機能・モジュール、設計上の安全策やフェイルセーフ、外部依存とのインターフェースを含みます。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py
    - バージョン `0.1.0` を定義。
    - パブリック API として ["data", "strategy", "execution", "monitoring"] を公開する意図を示すエクスポートを追加。

- 環境設定・読み込みユーティリティ
  - src/kabusys/config.py
    - .env ファイルまたは環境変数からの設定読み込み機能を実装。
    - プロジェクトルート自動検出: .git または pyproject.toml を基準に検索（パッケージ配布後も CWD に依存しない）。
    - .env パーサ実装（export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などに対応）。
    - 自動ロード優先順: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - 環境変数保護: OS の既存環境変数を protected として上書きを防止。
    - Settings クラスを公開（各種必須トークン取得、デフォルト値、バリデーションを提供）。
      - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID を必須化（未設定時に ValueError）。
      - KABUSYS_ENV の許容値検証（development / paper_trading / live）。
      - LOG_LEVEL の許容値検証。
      - データベースパスのデフォルト（DuckDB / SQLite）の設定。

- AI 関連機能（OpenAI 統合）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約して銘柄単位にニュースをまとめ、OpenAI（gpt-4o-mini）でセンチメントを評価し ai_scores テーブルへ書き込むフローを実装。
    - タイムウィンドウ定義（JST ベース: 前日 15:00 ～ 当日 08:30、内部は UTC naive で扱う calc_news_window を提供）。
    - チャンク処理（最大 _BATCH_SIZE=20 銘柄/回）、1銘柄あたりの記事数上限・文字数上限対応（トークン肥大化対策）。
    - OpenAI 呼び出しに対するリトライ（429 / ネットワーク断 / タイムアウト / 5xx を指数バックオフで再試行）とエラーフェイルセーフ（失敗時はそのチャンクをスキップ）。
    - レスポンスバリデーション（JSON 抽出、results リスト検査、コード照合、スコア数値検査）を実装。スコアは ±1.0 にクリップ。
    - DuckDB 互換性考慮: executemany に対する空リストチェック（DuckDB 0.10 の制約）と、書き込みは DELETE → INSERT の置換方式（部分失敗時に既存スコアを保護）。
    - テスト容易性: OpenAI 呼び出しを _call_openai_api でラップし、ユニットテストから差し替え可能。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を算出し market_regime テーブルへ冪等書き込みする機能を実装。
    - MA200 比率計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。データ不足時は中立（1.0）にフォールバックして警告ログを出力。
    - マクロニュース取得は news_nlp.calc_news_window と raw_news のキーワードフィルタを用いる。
    - OpenAI 呼び出し（gpt-4o-mini）に対するリトライ、API エラー・パース失敗時は macro_sentiment=0.0 にフォールバック。
    - 最終的なスコア合成と閾値判定、BEGIN / DELETE / INSERT / COMMIT による冪等的 DB 書き込みを実装。DB 書き込み失敗時は ROLLBACK を試行して例外を再送出。

  - src/kabusys/ai/__init__.py
    - news_nlp.score_news を公開。

- データプラットフォーム / ETL / カレンダー管理
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダー管理（market_calendar を利用した営業日判定、Next/Prev/Period の取得ロジック）を実装。
    - calendar_update_job により J-Quants API から差分取得 → 保存（jq.fetch_market_calendar / jq.save_market_calendar を想定）を行う。バックフィル、健全性チェック、保存件数のログを提供。
    - カレンダーデータがない場合は曜日ベース（日曜・土曜を非営業日）でフォールバックし、DB 登録がある場合は DB 値を優先する一貫性のある実装。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。最大探索日数制限で無限ループを防止。

  - src/kabusys/data/pipeline.py
    - ETL の高レベル設計に基づくユーティリティを実装。
    - ETLResult データクラスを導入（取得件数、保存件数、品質検査結果、エラー一覧などを保持）。has_errors / has_quality_errors / to_dict を提供。
    - 差分更新ロジック、バックフィル、品質チェック戦略（品質問題は収集して ETL を継続）などの方針をコードドキュメントで明示。

  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポート。

  - src/kabusys/data/__init__.py
    - データパッケージの初期化（空ファイル、サブモジュール公開の準備）。

- Research（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR、ATR 比率）、流動性（20日平均売買代金、出来高比率）、バリュー（PER、ROE）を DuckDB の prices_daily / raw_financials を用いて計算する関数を実装。
    - データ不足時の None 扱い、SQL ウィンドウ関数を活用した効率的実装、結果は (date, code) をキーとする dict のリストで返す。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（任意 horizon）をまとめて1クエリで取得する calc_forward_returns。
    - IC（Spearman の ρ）を計算する calc_ic（欠損・同一値ハンドリング、最小有効サンプル数チェック）。
    - ランク変換（同順位は平均ランク）を行う rank。
    - カラムごとの統計サマリーを返す factor_summary。
  - src/kabusys/research/__init__.py
    - 主要関数を再エクスポート（calc_momentum / calc_volatility / calc_value / zscore_normalize / calc_forward_returns / calc_ic / factor_summary / rank）。

### Changed
- （初版のため該当なし）設計文書に沿った実装を初回導入。

### Fixed
- （初版のため該当なし）

### Security
- 機密情報（API キー等）は Settings 経由で取得し、未設定時は明示的に ValueError を送出して安全性を確保。
- .env の自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テストや CI 用）。

### Notes / Implementation details・設計上の注意
- ルックアヘッドバイアス対策: AI モジュール・研究モジュールのすべてで datetime.today() / date.today() を内部で直接参照しない設計（呼び出し側が target_date を指定する）。
- OpenAI 呼び出しは各モジュールでラップし、テスト時に差し替え可能にしている。
- DuckDB 互換性のため executemany に対する空リスト回避や、DELETE→INSERT による部分置換方式を採用している。
- Log 出力、警告、フォールバック（中立スコアや 0.0 へのフォールバック）を多用して、外部 API 障害時にも過度に例外を投げずシステムを継続させる方針。
- 外部クライアント実装（jquants_client など）との連携ポイントは分離されており、モック可能な設計。

## 今後 / 未実装・確認事項
- strategy / execution / monitoring パッケージの具体実装（__all__ では公開予定）が未含まれるため、トレード実行フローや監視処理は今後追加予定。
- J-Quants クライアント（data.jquants_client）実装の存在を前提とした呼び出しがあるため、実際の API クライアント実装と接続しての動作確認が必要。
- 単体テスト・統合テストの整備（特に外部 API 呼び出しのモック、DuckDB のテスト用セットアップ）を推奨。

--- 

この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートとして利用する際は、リリース手順や変更履歴に合わせて必要に応じて補正してください。