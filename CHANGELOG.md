CHANGELOG
=========

すべての重要な変更をここに記録します。本ファイルは "Keep a Changelog" の慣習に準拠します。

バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

0.1.0 - 2026-04-03
------------------

初回リリース。

追加
- パッケージ基盤
  - パッケージ初期化: src/kabusys/__init__.py（__version__ = "0.1.0"、公開サブパッケージの __all__ を定義）。
- 環境設定 / 設定管理
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env パーサを独自実装（export 形式、クォート内のエスケープ、インラインコメントの取り扱いに対応）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - OS 環境変数を保護する仕組み（読み込み時の protected set）。
    - Settings クラスを提供し、アプリケーション設定をプロパティで取得可能：
      - J-Quants / kabuステーション / LINE API / DB パス（DuckDB/SQLite）/監視関連設定（pid, kill flag, CPU/MEM/DISK 閾値）など。
      - KABUSYS_ENV と LOG_LEVEL の入力検証（有効な値集合をチェック）。
      - is_live / is_paper / is_dev のヘルパー。
    - 必須環境変数未設定時は明確な ValueError を送出する _require 実装。
- AI（自然言語処理）モジュール
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON mode を使って銘柄別センチメントを算出して ai_scores テーブルへ保存する機能。
    - タイムウィンドウ計算（calc_news_window）: JST ベースのウィンドウ（前日15:00〜当日08:30）を UTC naive datetime で返す。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたりの記事数・文字数トリム（デフォルト制限あり）を実装。
    - API 呼び出し時の耐障害性: レート制限/ネットワーク/タイムアウト/5xx に対する指数バックオフとリトライ、レスポンスの厳格なバリデーション、JSON パースの頑健化（前後余計テキストの除去）など。
    - スコアは ±1.0 にクリップ。部分失敗時にも既存スコアを保護するために、対象コードに限定して DELETE → INSERT を行う冪等性を担保した DB 書き込み。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し、market_regime テーブルへ保存する機能。
    - prices_daily からの ma200_ratio 計算（ルックアヘッド防止: target_date 未満のデータのみ使用、データ不足時は中立扱い）。
    - マクロキーワードで raw_news をフィルタし、最大件数まで LLM に渡してマクロセンチメントを取得（API 失敗時は macro_sentiment = 0.0 にフォールバック）。
    - OpenAI 呼び出しは独立実装で、リトライとエラー種別ごとの挙動を設計。
    - 計算結果はトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等書き込み。
- Data（データ基盤）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録データを優先し、未登録日は曜日ベースのフォールバック（週末を非営業日）で一貫した挙動を提供。
    - 夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants クライアントから差分取得し保存、バックフィル・健全性チェックを含む）。
  - src/kabusys/data/pipeline.py
    - ETL パイプラインの枠組みと ETLResult データクラスを実装:
      - 差分取得、保存、品質チェック（quality モジュール連携）の設計を反映。
      - ETLResult に品質問題とエラー一覧を格納し、has_errors / has_quality_errors / to_dict を提供。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得ユーティリティ等を実装。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult の公開再エクスポート。
  - jquants_client など外部データ取得用クライアントを参照する実装（詳細実装ファイルは別途）。
- Research（リサーチ支援）
  - src/kabusys/research/__init__.py に主要関数を公開（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）といった定量ファクターの SQL ベース計算を実装。
    - DuckDB を用いた SQL ウィンドウ関数中心の実装で、外部 API には依存しない設計。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部依存を持たない純標準ライブラリ実装。入力検証（horizons の制約など）あり。
- 研究用・ユーティリティ
  - src/kabusys/ai/__init__.py, src/kabusys/research/__init__.py を通じたクリーンな API エクスポート。

設計上の注意点（リスク・既知の動作）
- DuckDB テーブル前提
  - 多くの関数は DuckDB 上の特定テーブル（prices_daily, raw_news, news_symbols, ai_scores, raw_financials, market_calendar 等）を前提として実装されています。テーブルが存在しない・スキーマが異なる場合はエラーになります。
- OpenAI API 要件
  - score_news / score_regime は OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）を必要とします。キー未指定時は ValueError を発生させます。
  - API 呼び出しはレート制限やネットワーク障害を考慮したリトライ・フォールバック実装を備えていますが、外部 API の長期的な停止や仕様変更には注意が必要です。
- ルックアヘッドバイアス対策
  - 全ての分析処理は内部で datetime.today() / date.today() に依存しない設計になっています（target_date を明示的に与えて実行する設計）。
- 冪等性 / トランザクション
  - market_regime や ai_scores への書き込みは、既存データを対象日に対して削除 → INSERT することで冪等性を確保。トランザクションを使用し、失敗時は ROLLBACK を試みます。
- 部分的失敗の保護
  - score_news の書き込みは、スコアを取得したコードだけを置換する設計とし、部分失敗時に既存スコアを消さないようにしています。
- テスト容易性
  - OpenAI 呼び出し部は内部関数（_call_openai_api）に切り出されており、unittest.mock.patch による差し替えが可能です。

既知の制約 / TODO（今後の改善候補）
- エラー分類やリトライ戦略は現在の実装で一般的なケースをカバーしていますが、より詳細なメトリクス/監視や通知（LINE 連携等）との統合が望まれます。
- research の出力は現状リスト/辞書ベースです。大量データ処理のために DataFrame 等の選択肢や並列化の検討余地があります。
- jquants_client の実装や外部クライアントのエラーハンドリング、単体テスト・統合テストの整備が引き続き必要です。

破壊的変更
- なし（初回リリース）。

注記
- この CHANGELOG は、提供されたコードベースの内容から機能・設計方針を推測して作成した初版リリースノートです。実際のリリース日や細部の実装差異に応じて適宜更新してください。