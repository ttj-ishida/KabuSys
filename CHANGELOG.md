CHANGELOG
=========

この変更履歴は「Keep a Changelog」フォーマットに準拠しています。  
（コードベースから推測して作成した初期リリースの変更点を記載しています）

Unreleased
----------

- なし

[0.1.0] - 2026-04-04
--------------------

Added
- 基本パッケージ
  - kabusys パッケージ初期リリース。パッケージバージョン: 0.1.0。
  - 公開モジュール: data, strategy, execution, monitoring（__all__ に登録）。

- 環境・設定管理
  - 環境変数自動ロード機能を追加（プロジェクトルートの .env / .env.local を読み込み）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - プロジェクトルートの検出は __file__ を基準に .git または pyproject.toml を探索。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメント処理）。
  - .env 読み込みの上書きポリシー実装:
    - .env は既存 OS 環境変数を上書きしない（override=False）。
    - .env.local は上書きする（override=True）ただし OS 環境変数は protected として保護。
  - Settings クラスを提供（settings インスタンスで取得）。
    - J-Quants / kabu API / LINE / DB パス / 監視設定 / システム設定（KABUSYS_ENV, LOG_LEVEL）などのプロパティを定義。
    - KABUSYS_ENV のバリデーション（development, paper_trading, live）。
    - ログレベルのバリデーション（DEBUG..CRITICAL）。
    - 各種しきい値（CPU/Memory/Disk）や PID / kill フラグのパスなどデフォルト値を提供。

- AI（自然言語処理）
  - ニュースNLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して OpenAI にバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込むワークフローを実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチ処理、トークン肥大化対策（1銘柄あたり最大記事数／最大文字数）、チャンクサイズ、JSON mode 利用、レスポンス検証、スコアクリップを実装。
    - 再試行戦略（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）を導入。
    - DuckDB の executemany の制約（空リスト不可）に配慮した DB 書き込み（部分置換ロジック: DELETE → INSERT）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算、マクロキーワードで raw_news をフィルタ、OpenAI（gpt-4o-mini）を使ったマクロセンチメント評価、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API キーは引数または環境変数 OPENAI_API_KEY で提供。未設定時は ValueError を送出。
    - API エラー時のフォールバック（macro_sentiment=0.0）やリトライ処理を実装。

- データ処理（data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーを扱うユーティリティ群を提供: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - market_calendar がない場合の曜日ベースフォールバック（週末を非営業日扱い）。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等に更新する夜間バッチ実装（バックフィル・健全性チェック含む）。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（ETL 実行結果の集約）。
    - 差分取得、保存（jquants_client の save_* を利用して冪等保存）、品質チェック（quality モジュール想定）を行う設計を反映。
    - 最小データ日 (_MIN_DATA_DATE)、バックフィル日数、カレンダー先読み等のデフォルトを定義。
    - DuckDB テーブル存在チェックや最大日付取得ユーティリティを実装（ETL 内部で使用）。

- Research（kabusys.research）
  - ファクター計算と特徴量探索機能を提供:
    - factor_research: calc_momentum / calc_value / calc_volatility（モメンタム、バリュー、ボラティリティ／流動性ファクター）。
    - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank（将来リターン、IC 計算、統計サマリー等）。
  - 実装方針として DuckDB の SQL ウィンドウ関数を多用し、外部 API や pandas 等の依存を避ける。

Changed
- 初期リリースのため「Changed」はなし。

Fixed
- .env 読み込みにおける堅牢性を確保:
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、コメントの取り扱いを改善。
  - .env ファイル読み込み失敗時に警告を出して処理継続（warnings.warn）。
- DB 書き込みで障害発生時にトランザクションを ROLLBACK して例外を伝播するように実装（冪等・安全性向上）。
- OpenAI API 呼び出しにおけるエラー処理強化（RateLimit, Timeout, APIError の扱い・リトライロジックの導入）。

Security
- OpenAI API キーは必須（api_key 引数または OPENAI_API_KEY 環境変数）。未設定時は ValueError を送出することで誤操作を防止。
- .env 読み込みで OS 環境変数は protected として優先（.env / .env.local による意図しない上書きを防止）。

Known limitations / Notes
- DuckDB を前提とした実装であり、prices_daily / raw_news / ai_scores / market_regime / market_calendar / raw_financials 等のテーブルスキーマ依存がある。
- OpenAI 呼び出しは gpt-4o-mini（JSON mode）を想定している。SDK の将来の変更により挙動が変わる可能性あり（コード内で一部互換性配慮あり）。
- レスポンスのパースに関してはフォールバック（文字列内の最外 {} 抽出など）を入れているが、LLM の不正な出力は完全には防げない。
- ai/news の処理は部分失敗を許容する設計（成功した銘柄のみ上書き）であるため、部分的にデータが欠ける可能性がある。
- execution / strategy / monitoring モジュールはパッケージ公開対象に含まれているが、このリリースでの詳細実装（発注ロジック等）はコードベースの範囲に依存します。

Acknowledgements
- 初期設計では「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ」を重視して実装されています。