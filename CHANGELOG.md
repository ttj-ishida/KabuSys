CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
この CHANGELOG は提示されたコードベースの内容から推測して作成したもので、実際のコミット履歴ではありません。

[Unreleased]
------------

- ドキュメント / その他
  - 初期開発中の機能追加・修正が継続中。API 抑止やテストフック（環境変数による自動 .env ロード抑止等）が設計に組み込まれています。

[0.1.0] - 2026-04-03
-------------------

Added
- パッケージ基盤
  - kabusys パッケージを初期実装。__version__ を "0.1.0" に設定し、主要サブパッケージ（data, research, ai, execution, monitoring, strategy 等）を公開。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）により CWD に依存しない動作を実現。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のキー/値パースは export 形式、シングル/ダブルクォート、エスケープ、インラインコメントなどに対応。
    - 読み込み時は既存 OS 環境変数を protected として上書きを回避する仕組みあり。
  - Settings クラスを提供し、J-Quants、kabu API、LINE、データベースパス、監視設定、閾値、実行環境（development/paper_trading/live）やログレベルのバリデーションを行うプロパティを実装。
    - 必須環境変数未設定時は明示的なエラーを発生させる (_require)。
    - KABUSYS_ENV や LOG_LEVEL に対する有効値チェックを実装。
    - データベースパス・PID/kill flag パス・閾値などのデフォルトを設定。

- AI 関連 (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news / news_symbols テーブルからニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信して銘柄ごとのセンチメント ai_score を ai_scores テーブルへ保存する処理を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で計算。UTC naive datetime を返す。
    - 1銘柄当たり最大記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 一度に最大 20 銘柄を処理するチャンクング（_BATCH_SIZE）と、429/ネットワーク/タイムアウト/5xx に対する指数バックオフによるリトライを実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出・results リスト・code/score 型チェック・スコアの有限性確認）を行い、スコアは ±1.0 にクリップして保存。
    - DuckDB の executemany の制約に配慮して、書き込みは DELETE（各 code 毎）→ INSERT の手順で冪等性を確保（部分失敗時に既存データを保護）。
    - API 呼び出し箇所はテスト用に差し替え可能（_call_openai_api を patch 可能）。

  - 市場レジーム判定 (ai.regime_detector.score_regime)
    - ETF 1321（日経225連動型）の直近 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込み。
    - MA の計算は target_date 未満のデータのみ使用し、ルックアヘッドバイアスを防止。
    - マクロニュースは raw_news からマクロキーワードでフィルタ（_MACRO_KEYWORDS）し最大件数を制限。記事が無ければ LLM 呼び出しをスキップして macro_sentiment を 0 とするフェイルセーフ。
    - OpenAI API 呼び出しは専用実装でリトライ・エラー処理を行い、API 失敗やパース失敗時は macro_sentiment=0.0 へフォールバック。
    - レジームスコア合成と閾値判定（_BULL_THRESHOLD, _BEAR_THRESHOLD）を実装。

- データ基盤 (kabusys.data)
  - マーケットカレンダー管理 (data.calendar_management)
    - market_calendar テーブルに基づく営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 優先、未登録日は曜日ベースでフォールバックする一貫した挙動を実現。
    - カレンダー夜間バッチ更新 job (calendar_update_job) を実装。J-Quants から差分取得して保存、バックフィル（日数）や健全性チェック（将来日付の異常検知）を組み込み。
    - 最大探索範囲による無限ループ防止や NULL 値検出時の警告ログ出力。

  - ETL パイプライン (data.pipeline / data.etl)
    - ETLResult データクラスを公開。取得/保存件数、品質チェック結果、エラー一覧を格納し、has_errors / has_quality_errors プロパティや to_dict を提供。
    - 差分更新、バックフィル、品質チェックの設計方針を実装（jquants_client を利用した idempotent な保存、品質チェックは致命的エラーでも収集継続）。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを実装。

- 研究用ユーティリティ (kabusys.research)
  - ファクター計算 (research.factor_research)
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）の計算関数を提供（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上の SQL とウィンドウ関数を駆使して実装。データ不足時は None を返す設計。
  - 特徴量探索 (research.feature_exploration)
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク化ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。ties は平均ランクで扱うなど数値安定性に配慮。

Changed
- 実装方針・設計
  - すべての AI / 研究 / データ処理関数は datetime.today() / date.today() を内部参照せず、明示的な target_date を受け取ってルックアヘッドバイアスを避ける設計を採用。
  - DuckDB の互換性や制約（executemany の空リスト禁止など）に配慮した実装に変更（部分書換えの手法を採用）。
  - OpenAI 呼び出し箇所は JSON Mode を想定しつつ、応答に余計なテキストが混入するケースに対して最外の JSON を抽出する復元ロジックを追加。
  - API エラー時は例外を投げるのではなくフェイルセーフ（スコア 0、チャンクスキップ、警告ログ）で継続するポリシーを採用。

Fixed
- 安全性 / ロバストネス
  - .env パーサーのクォート・エスケープ処理やインラインコメントの扱いを強化し不正なパースを防止。
  - OpenAI API 呼び出しでの 5xx やネットワークエラーに対するリトライ戦略を実装し、一部エラーを適切に分類して再試行/スキップするよう修正。
  - DB 書き込み時のトランザクション処理（BEGIN / DELETE / INSERT / COMMIT / ROLLBACK）を厳格化し、ROLLBACK 失敗時は警告ログを出すようにして障害時のログ可観測性を向上。

Notes / Known limitations
- OpenAI の利用
  - score_news / score_regime は OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）が必須。未設定時は ValueError を送出する。
- DuckDB
  - 実装は DuckDB を前提としている (DuckDBPyConnection)。バインドや executemany の挙動が DuckDB のバージョンに依存する箇所があるため、運用環境の DuckDB バージョンとの互換性確認が必要。
- 部分失敗時の挙動
  - AI API の部分失敗は他の銘柄データの上書きを防ぐために「取得できたコードのみ」置換する戦略を採用している（完全成功を前提としないフォールバック方針）。

今後の予定（推測）
- strategy / execution / monitoring モジュールの具体的な注文ロジック、発注・監視の統合実装。
- テストカバレッジ強化、CI 連携、リリース版の整備（バージョンアップ、Breaking changes の明文化）。
- パフォーマンス改善（大規模データでの ETL 最適化）や OpenAI 呼び出しの費用対策（プロンプト最適化、キャッシュなど）。

ライセンスや開発フローに関するメタ情報はソースからは推測できなかったため省略しています。必要であれば実際のコミットログやプロジェクト方針に合わせて調整してください。