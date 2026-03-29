Keep a Changelog
=================

すべての注目すべき変更点を記録します。  
このファイルは "Keep a Changelog" のフォーマットに準拠しています。  

[0.1.0] - 2026-03-29
--------------------

Added
- パッケージ初期リリース。主要サブモジュールを追加。
  - kabusys.config
    - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供（settings インスタンスを公開）。
    - プロジェクトルート自動検出ロジックを実装（.git / pyproject.toml を基準）。配布後も CWD に依存しない設計。
    - .env パーサを実装。export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメントを考慮。読み込み時に既存 OS 環境変数を保護する protected オプションをサポート。
    - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
    - 各種必須設定（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID など）をプロパティで提供。環境値検証（KABUSYS_ENV・LOG_LEVEL など）を実装。
  - kabusys.ai
    - news_nlp モジュール（score_news）を追加
      - raw_news / news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）の JSON Mode へバッチ送信してセンチメント（ai_score）を算出。
      - バッチサイズ、1銘柄当たりの最大記事数・文字数トリム、最大リトライや指数バックオフなどを実装。
      - レスポンスの堅牢なバリデーション（JSON 抽出・results キー検証・コード照合・数値検査）とスコアの ±1.0 クリップ。部分失敗時に既存スコアを保護する DB 書き込み（DELETE → INSERT）を採用。
      - ルックアヘッドバイアス対策として datetime.today()/date.today() を参照しない設計、UTC 変換を明示。
      - API キー注入可能（api_key 引数または OPENAI_API_KEY 環境変数）。
    - regime_detector モジュール（score_regime）を追加
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定し market_regime テーブルへ冪等書き込み。
      - マクロキーワードによる raw_news フィルタリング、OpenAI 呼び出し（gpt-4o-mini）で JSON レスポンスをパース、API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
      - 再試行制御（リトライ回数・指数バックオフ）および 5xx 系の扱いを実装。
      - ルックアヘッドバイアス防止のため prices_daily 取得条件に target_date 未満を採用。
  - kabusys.data
    - calendar_management モジュールを追加
      - JPX カレンダー管理、market_calendar テーブルを使った営業日判定・next/prev/get_trading_days/is_sq_day などのユーティリティを提供。
      - DB にデータが無い場合は曜日ベースでフォールバック（週末は非営業日）。DB 登録値を優先する一貫した挙動を実装。
      - calendar_update_job: J-Quants API から差分取得して冪等保存、バックフィル（日数指定）と健全性チェックを実装。
    - pipeline / etl モジュールを追加
      - ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）。
      - 差分更新ロジック、バックフィル処理、品質チェック（quality モジュールとの連携）を実装するための基盤を追加。品質問題は収集して呼び出し元に伝播できる設計（Fail-Fast しない）。
      - DuckDB との互換性考慮（テーブル存在チェック、最大日付取得ユーティリティ）。
  - kabusys.research
    - factor_research モジュールを追加
      - Momentum（1M/3M/6M、MA200乖離）、Volatility（20日 ATR、ATR比）、Value（PER/ROE）などの定量ファクター計算を実装。すべて DuckDB 上の prices_daily / raw_financials を参照し外部 API に依存しない。
      - 計算結果は (date, code) をキーとする dict のリストで返却。
    - feature_exploration モジュールを追加
      - 将来リターン計算（複数 horizon 対応）、IC（Spearman ρ）計算、ランク変換、ファクター統計サマリーを実装。pandas 等に依存せず標準ライブラリのみで実装。
  - パッケージ公開インターフェース
    - kabusys.__init__.py で主要サブパッケージ（data, strategy, execution, monitoring）を __all__ に追加（将来的な拡張を示唆）。

Changed
- 初期リリースのため該当なし（新規機能群の同梱）。

Fixed
- 初期リリースのため該当なし。

Notes / Implementation details（重要な設計・挙動）
- OpenAI 呼び出しは各モジュールで独立実装（内部の _call_openai_api をテスト時に差し替え可能）。モジュール間でプライベート関数を共有しないことで結合度を低減。
- API レベルの失敗（429・タイムアウト・ネットワーク断・5xx）は再試行の対象。致命的でないエラーはフェイルセーフでスコアを 0.0 にフォールバック、またはそのチャンクをスキップ。
- DuckDB への書き込みは冪等性に配慮（DELETE→INSERT のパターン、BEGIN/COMMIT/ROLLBACK によるトランザクション管理）。DuckDB 0.10 の executemany の仕様（空リスト不可）に対するワークアラウンドを実装。
- すべての「日付」処理は lookahead バイアスを避けるために target_date ベースで明示的に計算。datetime.today()/date.today() に依存しない実装方針を徹底。
- ニュース取得ウィンドウは JST を基準に UTC へ変換して比較（明示的な境界設定）。
- .env パーサは実運用でよくあるケース（export プレフィックス、クォート内エスケープ、インラインコメント）に対応して安全に環境変数を設定。

今後の予定（短期）
- strategy / execution / monitoring モジュールの実装（パッケージインターフェースに存在するため今後拡張予定）。
- 品質チェック（quality モジュール）や J-Quants クライアントの統合テスト、ETL の運用テストを強化。
- モデル・プロンプトのチューニングや、LLM 呼び出しのメトリクス収集・監視機能追加。

References
- リポジトリ内の doc（DataPlatform.md, StrategyModel.md 等）に基づく設計記述に従って実装されています（実ファイルの存在を仮定）。