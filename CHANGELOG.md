# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

※ バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-29

Added
- パッケージ初期リリース。基本アーキテクチャを実装。
  - パッケージメタ情報:
    - バージョン: 0.1.0
    - エクスポート: data, strategy, execution, monitoring（src/kabusys/__init__.py）
- 環境設定管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env パーサーで以下をサポート・堅牢化:
    - 空行・コメント（#）の扱い
    - export KEY=val 形式への対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなし値のインラインコメント判定（直前が空白またはタブの場合のみ）
  - .env 読み込み時の上書き制御（override）と OS 環境変数保護（protected set）を実装。
  - 環境変数取得ユーティリティ _require と Settings クラスを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として取得
    - KABUSYS_ENV の検証（development / paper_trading / live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - データベースパスのデフォルト（DuckDB / SQLite）
    - is_live / is_paper / is_dev の便利プロパティ
  - 自動ロード無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD

- データ基盤関連 (kabusys.data)
  - calendar_management:
    - JPX（マーケット）カレンダー管理のロジックを実装
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供
    - market_calendar が未取得時の曜日ベースフォールバック（週末を非営業日扱い）
    - 最大探索日数やバックフィル、健全性チェックを実装して無限ループや未来日付異常を防止
    - calendar_update_job: J-Quants からの差分取得 → 保存（fetch / save 呼び出しのラップ）
  - ETL パイプライン基盤:
    - ETLResult をデータクラスとして公開（kabusys.data.pipeline、kabusys.data.etl で再エクスポート）
    - 差分取得ロジック、バックフィル、品質チェックとの連携を設計（quality モジュールとの連携想定）
    - DuckDB テーブル存在チェック、最大日付取得ユーティリティ等を実装
    - DuckDB の互換性考慮（executemany に空リストを渡さない等のワークアラウンド）

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）
    - Volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比）
    - Value（PER、ROE の算出、raw_financials の最新レコード参照）
    - DuckDB を用いる SQL ベースの実装。欠損やデータ不足時の None 処理を明確化
  - feature_exploration:
    - calc_forward_returns（任意ホライズン対応、入力検証あり）
    - calc_ic（Spearman ランク相関の実装、データ不足時は None を返す）
    - rank（同順位は平均ランクで処理、丸めにより ties 検出漏れを低減）
    - factor_summary（count/mean/std/min/max/median の算出）
  - reexports:
    - zscore_normalize を kabusys.data.stats から取り込み
    - 主要関数群をパッケージ API としてエクスポート

- AI 関連 (kabusys.ai)
  - news_nlp:
    - raw_news と news_symbols を基に、銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini）の JSON mode でセンチメントを算出
    - タイムウィンドウ定義（前日 15:00 JST 〜 当日 08:30 JST に対応。UTC 変換で DB と比較）
    - バッチ処理（最大 20 銘柄 / コール）、1 銘柄あたりの記事件数・文字数上限、トリム実装
    - エラー処理: 429・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライ、その他はスキップ（フェイルセーフ）
    - レスポンスバリデーション（JSON 抽出、results 配列、コード整合、スコア数値化、±1.0 クリップ）
    - DuckDB 書き込みは部分置換（該当コードのみ DELETE → INSERT）で部分失敗から既存データを保護
    - テスト容易性: _call_openai_api を patch 可能
  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定
    - マクロニュースは news_nlp.calc_news_window を利用して取得
    - OpenAI 呼び出しは独立実装、リトライ・エラーハンドリング・フォールバック（API 失敗時 macro_sentiment=0.0）
    - レジームスコアはクリップし閾値判定、DuckDB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を行う
    - テスト容易性: _call_openai_api を patch 可能

- その他設計上の注意点（ドキュメントに明示）
  - すべてのモジュールで datetime.today() / date.today() の直接参照を避ける（ルックアヘッドバイアス防止）。target_date を明示的に受け取る設計。
  - OpenAI 呼び出しの堅牢化（JSON パースの回復処理、数値変換、クリップ、リトライ戦略）
  - DB トランザクションでの ROLLBACK の試行とログ出力（失敗時の追加警告）
  - DuckDB のバージョン差異に対応する実装上の注意点（executemany 空リスト回避、リスト型バインド回避等）

Changed
- 初期リリースのため該当なし

Fixed
- 初期リリースのため該当なし

Security
- 初期リリースのため該当なし

Notes / Known limitations
- monitoring, strategy, execution 等のパッケージ名は __all__ に含まれるが（パッケージ API の一部として予約）実装ファイルが今回のリリースに含まれていない可能性があるため、利用時は import エラーに注意してください。
- OpenAI API キーが未設定の場合、news_nlp.score_news / regime_detector.score_regime は ValueError を投げる。運用時は環境変数 OPENAI_API_KEY または api_key 引数を渡してください。
- DuckDB による書き込みは現時点で単純な DELETE→INSERT を使用。大規模データや競合が頻発する運用では最適化やロック戦略の検討が必要です。
- J-Quants クライアントの具体実装（kabusys.data.jquants_client）は呼び出し箇所を想定して設計していますが、外部 API の挙動変更には注意が必要です。

[0.1.0]: https://example.com/kabusys/releases/tag/0.1.0