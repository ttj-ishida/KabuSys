# CHANGELOG

すべての重要な変更は Keep a Changelog のフォーマットに従って記載しています。  
このファイルはリポジトリのコードベースから推測して作成した初回リリース向けの変更点要約です。

なお、本リリースのバージョンはパッケージメタデータ (kabusys.__version__) に合わせて 0.1.0 としています。

## [Unreleased]

## [0.1.0] - 2026-04-09

### 追加 (Added)
- パッケージ初期公開: 日本株自動売買支援ライブラリ "KabuSys"（バージョン 0.1.0）。
- 基本モジュール構成を追加:
  - kabusys.config: 環境変数 / .env 読み込み・管理（自動ロード機能、OS 環境変数保護）。
    - .env ファイルのパースロジックを実装（クォート・エスケープ・コメント処理、export プレフィックス対応）。
    - 自動ロード順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
    - Settings クラスを提供し、J-Quants / kabu API / LINE / DB /監視・システム設定などのプロパティを型付で取得可能。
    - 設定値の検証を実装（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL などの許容値チェック）。
  - kabusys.ai: ニュースNLP と市場レジーム判定モジュールを提供。
    - news_nlp.score_news:
      - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON Mode へバッチ送信してセンチメント（ai_score）を算出。
      - JST ベースのニュースウィンドウ（前日15:00〜当日08:30 JST → UTC 変換）計算ユーティリティ calc_news_window を提供。
      - バッチサイズや記事/文字数トリム、リトライ（429/ネットワーク/5xx）やレスポンス検証ロジックを実装。
      - DuckDB 互換性のため executemany に対する空リスト回避（部分書き換え戦略）を採用。
    - regime_detector.score_regime:
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成し、日次で market_regime テーブルへ冪等書き込み。
      - OpenAI 呼び出しは独立実装、API 失敗時は macro_sentiment=0.0 のフェイルセーフ。
  - kabusys.data:
    - calendar_management: JPX カレンダー管理（market_calendar テーブル）、営業日判定、next/prev/get_trading_days、SQ 日判定を提供。DB 未登録時は曜日ベースでフォールバック。
    - pipeline / etl: ETLResult データクラスと ETL パイプラインの公開インターフェース（差分取得、保存、品質チェックを想定）。
    - etl モジュールの結果データ構造（ETLResult）を定義（品質問題一覧・エラー集約・to_dict）。
  - kabusys.research:
    - factor_research: Momentum / Volatility / Value などの定量ファクター計算関数を提供（calc_momentum, calc_volatility, calc_value）。
      - DuckDB を用いた SQL ベース実装。営業日を考慮したウィンドウ設計とデータ不足時の None 戻り値設計。
    - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク付けユーティリティ、統計サマリー（factor_summary）を提供。
  - kabusys.data.jquants_client を想定した外部クライアント連携部位（calendar_update_job 等）を実装。

### 変更 (Changed)
- ー（初回リリースのため既存変更は無し）

### 修正 (Fixed)
- ー（初回リリースのため修正履歴無し）

### セキュリティ (Security)
- OpenAI API キーは引数で注入可能（テスト容易性）かつ環境変数 OPENAI_API_KEY を参照する設計。キー未設定時は明示的な ValueError を発生させることで誤操作を防止。

### 設計上の注意点 / 実装上の重要事項
- DuckDB との互換性対応:
  - executemany に空リストを渡すと失敗するバージョン対策として、空チェックを行ってから実行する実装を採用。
  - 日付は date 型で扱い、DB からの値を安全に変換するユーティリティ（_to_date）を提供。
- LLM / 外部 API 呼び出し:
  - gpt-4o-mini を JSON Mode で利用する前提。API 呼び出しはリトライ（指数バックオフ）ロジックを実装。リトライ対象は主に 429 / ネットワーク断 / タイムアウト / 5xx。
  - レスポンスパースやバリデーションに失敗した場合は該当チャンクをスキップし、他の処理は継続する「フェイルセーフ」設計。
  - 単体テストしやすいように _call_openai_api を patch で差し替え可能にしている。
- 冪等性:
  - market_regime / ai_scores 等の DB 書き込みは冪等化（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK）を意識した実装になっている。
- ルックアヘッドバイアス防止:
  - 各 AI/研究モジュールは date.today()/datetime.today() を参照しない設計（target_date を明示的に受け取る）。
- 環境変数パース:
  - .env のクォート・エスケープ・行コメント等の細かいケースに対応したパーサを実装。
  - .env.local を優先して上書き可能（override）にする挙動を採用。OS 環境変数は protected として上書きされない。

### 既知の制約 / 将来的に注意すべき点
- news_nlp/regime_detector は外部 OpenAI API に依存するため、API 利用制限やコストに留意が必要。
- calendar_update_job は jquants_client.fetch_market_calendar / save_market_calendar に依存するため、実装/レスポンスに変更があった場合は調整が必要。
- 一部の設計（例: sentiment と ai_score が同値で扱われる点、PBR/配当の未実装など）は今後拡張予定。

---

（備考）この CHANGELOG はリポジトリ内のソースコードのコメント、関数名、処理フロー記述等から機能や設計意図を推測して作成したものです。実際のリリースノートとして公開する際は、実際のコミット履歴やリリース日、差分に基づいて適宜調整してください。