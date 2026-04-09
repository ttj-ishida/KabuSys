# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
安定版リリース番号はパッケージ内の __version__ に合わせて記載しています。

## [0.1.0] - 2026-04-09

初回公開リリース。

### 追加
- パッケージの基本構成を追加
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring（src/kabusys/__init__.py）

- 設定管理（src/kabusys/config.py）
  - .env ファイルおよびOS環境変数から設定を読み込む自動ロード機能を実装。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に探索。CWDに依存しない実装。
  - .env のパース機能を実装（コメント、export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープに対応）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DBパス / Paper Trading 等の設定をプロパティで取得可能に。
  - 値の検証を実装（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL など）。未設定の必須環境変数取得時はエラーを送出。

- AI モジュール（src/kabusys/ai/*）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント（ai_score）を算出。
    - チャンク処理（最大 20 銘柄／コール）、1銘柄あたりの記事数・文字数制限、JSON Mode を用いた厳密なレスポンス検証を実装。
    - 再試行（429/ネットワーク/タイムアウト/5xx）を指数バックオフで行い、エラー時はフェイルセーフでスキップ。
    - レスポンスのバリデーションと ±1.0 のクリップ、DuckDB 互換性（executemany の空リスト回避）に配慮。
    - 公開 API: score_news(conn, target_date, api_key=None)
    - テストフック: _call_openai_api を patch してモック可能。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動）200日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロセンチメントは OpenAI（gpt-4o-mini）にタイトルを与えて JSON で取得。記事が無い場合は LLM 呼び出しを行わず 0.0 を使用。
    - API 呼び出しに対するリトライ／フォールバックロジックを実装。API失敗時は macro_sentiment=0.0 として継続。
    - データベースへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み。
    - 公開 API: score_regime(conn, target_date, api_key=None)
    - テストフック: _call_openai_api を patch してモック可能。

- Data モジュール（src/kabusys/data/*）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を基に営業日判定／次営業日・前営業日・期間内営業日取得・SQ判定等のユーティリティを実装。
    - DB にデータがない/未登録日の場合は曜日ベース（週末判定）のフォールバックロジックを提供。最大探索範囲で無限ループ回避。
    - 夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants から差分取得して保存、バックフィル、健全性チェック含む）。
    - DuckDB と互換性のある日付変換・存在確認処理を実装。

  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - 差分取得 → 保存（idempotent）→ 品質チェック（quality モジュール）という ETL フローのためのユーティリティ。
    - ETL 実行結果を表す ETLResult データクラスを実装（ターゲット日、取得/保存件数、品質問題、エラー等）。
    - デフォルトのバックフィル日数やカレンダー先読み等の定義を含む。
    - ETLResult.to_dict() で品質問題をシリアライズ可能に。

  - ETLResult の再エクスポート（src/kabusys/data/etl.py）により外部からの参照を簡素化。

- Research モジュール（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M、MA200乖離）、Volatility（20日ATR、相対ATR）、Liquidity（20日平均売買代金、出来高比率）、Value（PER, ROE）を DuckDB の prices_daily / raw_financials から計算。
    - データ不足時の扱い（None）やスキャン範囲のバッファ処理を実装。
    - 関数: calc_momentum, calc_volatility, calc_value。

  - 特徴量探索・統計ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）：任意ホライズン（デフォルト [1,5,21]）に対応、入力検証あり。
    - IC（Information Coefficient）計算（calc_ic）：Spearman ランク相関による評価（有効レコードが少ない場合は None）。
    - ランク変換ユーティリティ（rank）：同順位は平均ランクで処理。
    - ファクター統計サマリー（factor_summary）：count/mean/std/min/max/median を算出。
    - research パッケージで便利関数を再エクスポート（zscore_normalize 等）。

### 設計方針・品質面の考慮
- ルックアヘッドバイアス防止
  - 各モジュール（news_nlp, regime_detector, research など）は datetime.today()/date.today() を直接参照せず、必ず target_date を引数として受け取る設計。
  - DB クエリでは target_date 未満（排他）や適切なウィンドウ指定を行い将来データを参照しないようにしている。

- フェイルセーフ性
  - OpenAI API の失敗時はスコアを 0.0 にフォールバックするなど、例外で全処理を止めない実装。
  - DB 書き込み時はトランザクション（BEGIN/COMMIT/ROLLBACK）を用い、ROLLBACK失敗をログに記録。

- テスト容易性
  - OpenAI 呼び出しを行う内部関数（_call_openai_api）に対して patch できるようにしており、ユニットテストで外部依存を差し替え可能。

- DuckDB 互換性配慮
  - executemany に空リストを渡せない（DuckDB 0.10 等）点を考慮して条件分岐で回避。
  - 日付型の取り扱いを安全に行うユーティリティを提供。

### 変更（既知の実装上の注意点）
- .env 自動ロードはプロジェクトルートが特定できない場合はスキップされる（パッケージ配布後の挙動に配慮）。
- OpenAI のレスポンスは JSON Mode を前提とするが、余計な前後テキストが混入する場合に備え最外の {} を抽出してパースを試みる復元処理を実装。
- market_calendar のデータが不完全（NULL 含む）場合はログを出して曜日ベースのフォールバックを使用する。

### 破壊的変更
- なし（初回リリース）

### セキュリティ
- 特になし

---

今後のリリースで予定している改善（例）
- strategy / execution / monitoring の具体実装（現在はパッケージのエントリのみ登録済み）
- OpenAI レスポンスのより厳密なスキーマ検証や、モデル切り替え設定の外部化
- ETL/pipeline のより詳細な品質チェックルール拡張およびモニタリング連携

（必要なら、各モジュールごとの細かなログ出力例や API 仕様の抜粋を CHANGELOG に追加します。ご希望があれば追記します。）