# Changelog

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

- 既知の安定性・互換性方針:
  - 初期リリースでは後方互換性を意識して設計されていますが、内部APIは将来変更される可能性があります。
  - DuckDB および OpenAI SDK（gpt-4o-mini を想定）に依存します。

## [0.1.0] - 2026-04-03

初回リリース。日本株自動売買システム「KabuSys」のコアライブラリを追加しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージバージョンを設定 (kabusys.__version__ = "0.1.0")。
  - パッケージ公開インターフェースに data, strategy, execution, monitoring 等を想定。

- 設定・環境管理 (kabusys.config)
  - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml ベース）を採用し、CWD に依存しない読み込みを実現。
  - .env パーサーの強化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ処理、行内コメントの取り扱い、無効行スキップ等の堅牢なパース。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - Settings クラスを提供し、アプリケーションで利用する設定値をプロパティ経由で取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD などの必須トークン取得（未設定時は ValueError を送出）。
    - KABU_API_BASE_URL のデフォルト、LINE API 関連設定、データベースパス（DUCKDB_PATH, SQLITE_PATH）、
      監視用ファイルパス（PID_FILE_PATH, KILL_FLAG_PATH）、リソース閾値 (CPU/MEM/DISK) など。
    - KABUSYS_ENV の列挙バリデーション（development / paper_trading / live）および log_level の検証。
    - ヘルパープロパティ: is_live / is_paper / is_dev。

- AI ニュース NLP（センチメント） (kabusys.ai.news_nlp)
  - raw_news / news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）の JSON mode で一括評価して ai_scores テーブルへ書き込み。
  - 時間ウィンドウ計算（JST 基準の前日 15:00 〜 当日 08:30 を UTC に変換）を提供（calc_news_window）。
  - バッチ処理（最大 20 銘柄 / リクエスト）、1銘柄あたり記事数・文字数のトリム制御（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
  - 再試行ポリシー実装（429, ネットワーク断, タイムアウト, 5xx を対象に指数バックオフ）。
  - レスポンスの堅牢なバリデーション（JSON 抽出、results フォーマット検査、未知コード無視、スコアを ±1 でクリップ）。
  - 部分失敗を許容する idempotent な DB 書き込み（対象コードのみ DELETE → INSERT）により既存スコアの保護。
  - フェイルセーフ: API キー未設定時に ValueError、API/パース失敗時は該当チャンクをスキップして継続。

- 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
  - マクロキーワードで raw_news をフィルタし、OpenAI による -1.0〜1.0 の JSON スコアを利用。
  - LLM 呼び出しに対するリトライ、API 失敗時のマクロスコアフォールバック（0.0）、およびロールバック対応の DB トランザクション（BEGIN / DELETE / INSERT / COMMIT）。
  - ルックアヘッドバイアス防止（target_date 未満のみを参照、datetime.today()/date.today() を直接参照しない設計）。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高変化率）、バリュー（PER, ROE）を DuckDB 上で計算する関数を提供（calc_momentum, calc_volatility, calc_value）。
    - データ不足時は None を返す、安全な計算ロジック。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（Spearman ランク相関: calc_ic）、ランク関数、ファクター統計サマリ（factor_summary）を提供。
    - 外部ライブラリ非依存での実装、営業日ベースホライズンの扱い、入力検証を含む。
  - 共通ユーティリティ: zscore_normalize の再エクスポート（kabusys.data.stats から）。

- データプラットフォーム (kabusys.data)
  - カレンダー管理（calendar_management）:
    - market_calendar テーブルの存在チェック、営業日判定、next/prev_trading_day、get_trading_days、is_sq_day などのユーティリティ。
    - DB にカレンダー登録がない場合は曜日ベースでフォールバック（週末を非営業日扱い）。DB 登録ありの場合は DB 値を優先し未登録日はフォールバックで補完。
    - 夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得・保存（バックフィル・健全性チェック付き）。
  - ETL パイプライン（pipeline, etl）:
    - ETLResult データクラス（取得数・保存数・品質問題・エラーを含む）を公開。
    - 差分取得、idempotent 保存（jquants_client の save_* を利用）、品質チェック（quality モジュール）を想定した設計。
    - バックフィル日数・カレンダー先読み・品質チェックの重大度扱いなどの制御。
  - jquants_client への参照（外部 API クライアントモジュールを想定）。

- 共通
  - DuckDB を主要なデータストアとして利用する設計を明記。
  - ロギング（logger.debug/info/warning/exception）を広く利用して操作ログと問題の可観測性を確保。
  - API キー注入可能な設計（関数引数で api_key を受け取れる点はテスト容易性に寄与）。

### Security
- 設定値（トークン等）は環境変数 / .env 経由で管理することを想定。コード内にハードコーディングされた機密情報は含まれていません。

### Notes / Behavior
- すべての日付処理でルックアヘッドバイアス防止を意識した設計（target_date 未満 / 指定範囲のみ参照）。
- OpenAI 呼び出しは JSON mode（厳密な JSON 出力期待）を前提とし、レスポンスパースの堅牢化（余分テキストの切り出し等）を行っています。
- DB 書き込みは可能な限り冪等性を保証する（DELETE→INSERT など）ため、部分失敗時のデータ保護を行います。
- DuckDB のバージョン互換性（executemany の空リスト扱いなど）を考慮したガードを実装。

### Removed
- なし（初回リリース）。

### Fixed
- なし（初回リリース）。

---

今後のリリースでは、strategy / execution / monitoring による実際の発注ロジック・モニタリング・運用ジョブ等の実装、テストカバレッジの追加、外部クライアント（J-Quants / kabu-station / LINE）周りの統合処理強化を予定しています。