# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはまだ初回リリース（0.1.0）です。

全般的な注意:
- 日付はパッケージの __version__ に基づくリリース日を記載しています。
- 実装・設計方針の多くはソースコード内のドキュメントストリング（docstring）に明記されているため、
  ここではユーザーに影響する主要な追加・改善点と運用上の注意を抜粋して記載します。

Unreleased
- （次回リリースに向けた未確定の変更項目をここに記載）

[0.1.0] - 2026-04-04
Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ入口: kabusys.__init__ を公開（submodule: data, strategy, execution, monitoring）
- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの自動設定読み込み機能を提供
  - 自動ロード順序: OS環境変数 > .env.local > .env（プロジェクトルートを .git または pyproject.toml から検出）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサ実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなし時のインラインコメント判定（直前がスペース/タブの場合のみ）
    - ファイル読み込み失敗時は警告発行
  - Settings クラスを公開（jquants, kabu API, LINE, DBパス, 監視設定, 環境/ログレベル検証など）
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL のバリデーション
    - 各種パス（duckdb, sqlite, pid_file 等）は環境変数から Path として返却
- AI（自然言語処理）モジュール (kabusys.ai)
  - ニュースセンチメント集約 (kabusys.ai.news_nlp)
    - raw_news / news_symbols を元に銘柄ごとにニュースを集約して OpenAI の JSON mode へバッチ送信
    - チャンク処理（1 API コールあたり最大 20 銘柄）、1銘柄あたりの最大記事数と最大文字数制限によるトークン制御
    - 再試行ロジック（429, ネットワーク断, タイムアウト, 5xx に対して指数バックオフ）
    - レスポンスの堅牢なバリデーション（JSON 抽出、results リスト、コードマッチング、数値チェック）
    - スコアは ±1.0 にクリップし、ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）
    - テスト容易性: OpenAI 呼び出し箇所を patch できるよう分離実装
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF (1321) の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して
      日次で市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ冪等書き込み
    - OpenAI 呼び出しは gpt-4o-mini を想定、API 呼び出し・リトライ・フォールバック（API 失敗時は macro_sentiment=0）を実装
    - ルックアヘッドバイアス対策: datetime.today()/date.today() を直接参照せず、prices_daily クエリも target_date 未満のデータのみ使用
    - テスト容易性: API 呼び出しを差し替え可能
- データプラットフォーム（kabusys.data）
  - ETL パイプラインインターフェースと結果型
    - pipeline.ETLResult を公開（kabusys.data.etl 経由で再エクスポート）
    - ETLResult は品質チェック結果やエラー情報を含み、to_dict によるサマリ出力をサポート
  - ETL 実装ガイドラインを具現化した pipeline モジュール
    - 差分取得、バックフィルによる後出し修正吸収、品質チェック（quality モジュール連携）等を想定
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを用いた営業日判定ロジックを提供
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
    - DB データがない場合は曜日（平日＝営業日）でフォールバック
    - next/prev の探索上限（最大探索日数）を導入して無限ループを防止
    - calendar_update_job: J-Quants API（jquants_client）から差分取得して market_calendar を冪等更新
      - バックフィル（日数）を入れて直近訂正を取り込む
      - 健全性チェック（将来日付の異常検出）を実装
- 研究（research）モジュール (kabusys.research)
  - factor_research: モメンタム／ボラティリティ／バリュー等のファクター計算を提供
    - calc_momentum: 1M/3M/6M リターンおよび MA200 乖離（データ不足時は None）
    - calc_volatility: 20日 ATR、ATR比率、20日平均売買代金、出来高比率等
    - calc_value: EPS から PER、ROE を raw_financials と prices_daily から計算
    - 全関数は DuckDB と prices_daily/raw_financials のみ参照（発注等の副作用なし）
  - feature_exploration: 将来リターン、IC（Spearman ρ）、統計サマリー、ランク付けユーティリティを実装
    - calc_forward_returns: 複数ホライズンの将来リターンを1クエリで取得（ホライズン上限・検証あり）
    - calc_ic: ランク相関（Spearman）の実装（有効レコードが 3 未満なら None を返す）
    - factor_summary: count/mean/std/min/max/median を計算
    - rank: 同順位は平均ランクを返す（丸めて tie の判定を安定化）
- テスト性・堅牢性に関する設計
  - OpenAI 呼び出し関数は各モジュールで分離しており、テスト時に mock/patch で差し替え可能
  - DB 書き込みは明示的にトランザクション（BEGIN/DELETE/INSERT/COMMIT）と ROLLBACK ハンドリングを行う
  - API 呼び出し失敗は基本的にフェイルセーフ（例: スコア 0.0、または該当銘柄をスキップ）でサービス継続を優先

Changed
- 初期リリースのため該当なし

Fixed
- 初期リリースのため該当なし

Deprecated
- 初期リリースのため該当なし

Removed
- 初期リリースのため該当なし

Security
- OpenAI API キーの扱い:
  - 各関数は引数 api_key でキーを注入可能。未指定時は環境変数 OPENAI_API_KEY を参照する。
  - コード中に API キーをハードコードしない設計。

運用上の注意（重要）
- .env 自動ロードはプロジェクトルートの検出に依存するため、パッケージ配布後の挙動に注意:
  - CWD に依存しない探索を行うが、配布形態によってはプロジェクトルートが見つからない場合がある（その場合自動ロードはスキップされる）。
- DuckDB executemany の互換性: 一部空リストを渡せないバージョンに配慮した実装があるため、DuckDB のバージョン互換性に注意。
- ルックアヘッドバイアス対策として、各関数は外部の「現在時刻」参照を避け、呼び出し側が target_date を渡す設計です。運用時は target_date の扱いに注意してください。

ライセンス・連携
- J-Quants / kabu API / OpenAI など外部 API に依存しています。実運用では各 API の利用規約・レート制限・コスト管理を行ってください。

以上。今後のリリースでは以下を検討しています（未確定）:
- strategy / execution / monitoring の具現化とテスト済みワークフロー
- ai モジュールの多言語/モデル選択対応、ローカル推論バックエンドの追加
- ETL の並列化・部分失敗回復の強化