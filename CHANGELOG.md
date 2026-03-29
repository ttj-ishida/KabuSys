Keep a Changelog に準拠した CHANGELOG.md（日本語）を作成しました。パッケージの __version__ が 0.1.0 のため、本リリースは 0.1.0 として記載しています。以下をプロジェクトルートの CHANGELOG.md としてご利用ください。

-------------------------------------------------------------------
CHANGELOG.md
-------------------------------------------------------------------

すべての変更はセマンティックバージョニングに従います。  
このファイルは Keep a Changelog のフォーマットに準拠しています。  

Unreleased
----------
（現在のブランチに未リリースの変更はありません。）

[0.1.0] - 2026-03-29
-------------------
Added
- パッケージ初期リリース: kabusys v0.1.0
  - 公開モジュール群:
    - kabusys.__init__ による公開名称: data, strategy, execution, monitoring
  - 環境設定管理:
    - kabusys.config
      - .env ファイルおよび環境変数の自動読み込み（優先順位: OS 環境 > .env.local > .env）。
      - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
      - プロジェクトルート検出ロジック（.git または pyproject.toml を起点に探索、CWD に依存しない）。
      - .env パーサ実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、ハッシュ記号によるコメント処理の取り扱い）。
      - 環境変数の保護（OS 環境変数を protected として上書き防止）。
      - Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 環境 / ログレベル等のプロパティ、入力値検証付き）。
  - AI/NLP 機能:
    - kabusys.ai.news_nlp
      - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（ai_score）を算出。
      - JST 時間ウィンドウ（前日 15:00 ～ 当日 08:30）を UTC に変換して DB クエリに使用。
      - 一銘柄あたりの最大記事数・文字数トリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
      - 最大バッチサイズ（_BATCH_SIZE）によるバッチ送信、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ。
      - レスポンスの堅牢なバリデーション（JSON 抽出・results リスト・code と score の検証、数値チェック）、スコアは ±1.0 にクリップ。
      - 部分成功対策として、書き込みは対象コードのみ DELETE → INSERT（DuckDB executemany の制約を考慮）。
      - API キー注入（api_key 引数または環境変数 OPENAI_API_KEY）。
      - エラー時は例外を直接波及させず、ログ出力してフォールバック（フェイルセーフ）を行う設計。
    - kabusys.ai.regime_detector
      - ETF 1321（日経225連動型）の 200 日移動平均乖離と、ニュース由来の LLM マクロセンチメントを組み合わせて日次の市場レジーム（bull/neutral/bear）を判定。
      - マクロキーワードによるニュース抽出、LLM（gpt-4o-mini）を用いたセンチメントスコア化、MA とマクロの重み付け合成。
      - LLM 呼び出しのリトライ/フォールバック（API 失敗時は macro_sentiment=0.0）。
      - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
  - Research（因子・特徴量探索）:
    - kabusys.research.factor_research
      - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。データ不足時は None を返す。
      - ボラティリティ/流動性: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率。
      - バリュー: raw_financials から最新財務（report_date <= target_date）を取得して PER/ROE を計算。
      - DuckDB を用いた SQL ベースの実装で外部 API を呼ばない。
    - kabusys.research.feature_exploration
      - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）のリターンを計算。
      - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関を実装し、必要なレコード数が足りない場合は None を返す。
      - ランク関数（rank）: 同順位は平均ランクで扱う（丸め処理で ties の検出を安定化）。
      - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。
    - re-export: kabusys.research.__init__ でデータユーティリティ（zscore_normalize）を含む主要関数を公開。
  - Data / ETL / カレンダー:
    - kabusys.data.calendar_management
      - market_calendar テーブルに基づく営業日判定（is_trading_day/is_sq_day）、前後営業日探索（next_trading_day/prev_trading_day）、期間内営業日列挙（get_trading_days）。
      - DB 登録が無い日については曜日ベースのフォールバック（週末は非営業日）。
      - カレンダー夜間更新ジョブ（calendar_update_job）: J-Quants API から差分取得して market_calendar を冪等に更新。バックフィル、健全性チェック、save の例外ハンドリングを実装。
    - kabusys.data.pipeline / etl
      - ETLResult データクラスを提供（target_date / fetched/saved counts / quality_issues / errors、シリアライズ用 to_dict）。
      - ETL の差分取得・バックフィル挙動・品質チェックの設計方針を実装。
    - jquants_client や quality などのクライアント/品質モジュールを想定した統合ポイントを提供。
  - テストしやすさの配慮:
    - OpenAI 呼び出し部分に対して _call_openai_api をテスト時にモック差替え可能（unittest.mock.patch を想定）。
    - API キーを引数で注入できる設計（テストで環境依存を排除）。

Changed
- （初期リリースにつき、変更履歴はありません）

Fixed
- （初期リリースにつき、修正履歴はありません）

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーは引数注入または環境変数（OPENAI_API_KEY）で解決。誤ってコードにハードコードしない運用を推奨。

Notes / Implementation details（重要な実装上の注意）
- ルックアヘッドバイアス防止:
  - news_nlp や regime_detector は内部で datetime.today()/date.today() を参照せず、必ず外部から渡された target_date に基づいてウィンドウ計算／クエリを行う設計。
- DuckDB 互換性:
  - executemany に空リストを渡さない等、DuckDB 特有の挙動を考慮して実装。
- フェイルセーフ:
  - LLM 呼び出し・外部 API の失敗は基本的に例外で中断せずフォールバックして継続する（ログ出力あり）。ただし DB 書き込み等で一貫性が必要な箇所は例外を伝播して呼び出し元で処理。
- 環境変数パース:
  - クォート内のエスケープ、export プレフィックス、インラインコメント処理など実用的な .env の特徴をサポート。

-------------------------------------------------------------------

今後の推奨
- リリース後は CHANGELOG に Unreleased セクションで次の変更を管理してください。
- セキュリティや認証情報（OpenAI / Slack / KABU API など）は環境変数管理シークレットストアの利用を推奨します。
- 大きな API 変更やデータスキーマ変更を行う場合は Breaking Changes を明示してください。

-------------------------------------------------------------------

必要であれば、各モジュール・関数ごとにより詳細な変更点（例えば SQL クエリやプロパティの厳密な振る舞い）を追記したバージョン別の細分化された履歴を作成します。どの程度の粒度が必要か教えてください。