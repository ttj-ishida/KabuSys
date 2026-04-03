CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠しています。
リリース日はパッケージ内の __version__ と現行のコードベースに基づいて推定しています。

[Unreleased]
------------

- なし（初期リリースのみ）

[0.1.0] - 2026-04-03
-------------------

Added
- パッケージ初期リリース "kabusys"（バージョン 0.1.0）。
  - メインパッケージ: src/kabusys/__init__.py にてバージョンと公開モジュールを定義。
- 環境変数・設定管理
  - src/kabusys/config.py
    - .env/.env.local 自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml）。
    - .env の行パーサを実装（export プレフィックス、クォート、エスケープ、インラインコメント処理に対応）。
    - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスを提供（J-Quants / kabu API / LINE / DBパス / 監視設定 / システム設定など）。
    - 環境値のバリデーション（KABUSYS_ENV の許容値: development/paper_trading/live、LOG_LEVEL の許容値等）。
    - デフォルト値やファイルパス（duckdb/sqlite/pid/kill flag 等）を設定。
- AI（NLP）関連
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）のJSON Modeで一括センチメント評価して ai_scores テーブルへ書き込む機能を実装。
    - バッチ処理（最大20銘柄/チャンク）、1銘柄当たりのトリム制御（記事数・文字数制限）を実装。
    - エラー耐性: 429／ネットワーク断／タイムアウト／5xx に対する指数バックオフリトライ。
    - レスポンスの堅牢なバリデーション（JSON抽出、resultsキー、コード整合性、数値チェック、スコアのクリップ）。
    - テスト容易性のため、内部の OpenAI 呼び出し関数は差し替え可能に実装。
    - 日付ウィンドウ計算（JST基準の前日15:00〜当日08:30相当）を calc_news_window で提供。
  - src/kabusys/ai/regime_detector.py
    - 日次で市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等書き込みする機能を実装。
    - 指標: ETF 1321 の 200日移動平均乖離（重み70%）とマクロセンチメント（重み30%）の合成。
    - マクロ記事抽出（マクロキーワードリスト）→ OpenAI による JSON 出力パース → スコア合成の流れを実装。
    - OpenAI 呼び出しは専用実装でテスト差し替え可能。API失敗時は macro_sentiment=0.0 として継続するフェイルセーフ動作。
    - DuckDB を用いたルックアヘッド防止（target_date 未満を参照）と冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）。
- データプラットフォーム関連
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダー管理（market_calendar テーブル読込/利用、営業日判定、next/prev/get_trading_days、SQ判定、夜間バッチ更新ジョブ）を実装。
    - DB 未取得時の曜日ベースフォールバック、最大探索幅制限、バックフィルや健全性チェック等を実装。
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL の結果を表す ETLResult データクラスを実装し公開（etl.py は pipeline.ETLResult を再エクスポート）。
    - 差分取得、保存（jquants_client の idempotent 保存想定）、品質チェックのフロー設計に対応する基盤コードと定数を実装。
    - ETLResult に品質問題リスト（quality.QualityIssue）とエラー収集を保持する仕組みを提供。
  - その他データユーティリティ
    - src/kabusys/data/__init__.py（パッケージ化）、jquants_client への参照を想定。
- リサーチ / ファクター
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20日ATR等）、バリュー（PER/ROE）を DuckDB の SQL とウィンドウ関数で計算する関数を実装。
    - データ不足時の None ハンドリング、ログ出力、返却形式を (date, code) を含む dict のリストで統一。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン（複数ホライズン）計算、IC（Spearman）計算、ランク変換、ファクター統計サマリーを実装。
    - pandas 等外部依存を用いず標準ライブラリと DuckDB で実装。
  - src/kabusys/research/__init__.py
    - 主要関数のエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize 等）を提供。

Changed
- 設計方針の明確化（コード内ドキュメントとして多数の設計方針・注意点を追加）
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を参照しない設計（target_date を明示して使用）。
  - DB 書き込みは可能な限り冪等に（DELETE→INSERT パターン、トランザクションでの COMMIT/ROLLBACK）。
  - OpenAI 呼び出しはモジュール間でプライベート実装を共有せず、各モジュールで差し替え可能に実装。
  - DuckDB の executemany における空リスト制約（バージョン依存）に配慮した実装。

Fixed
- エラーハンドリング／フォールバックを強化
  - OpenAI API の各種エラー（429, ネットワーク, タイムアウト, 5xx）に対するリトライや最終フォールバックを実装（警告ログ出力）。
  - JSON パース失敗やレスポンスの不整合時は例外を上位に投げず空スコアや 0.0 を返す等のフェイルセーフ挙動を導入。
  - DuckDB からの date 型取り扱いを統一するユーティリティ関数を追加（_to_date）。

Security
- 環境変数の扱いに注意
  - .env 自動ロード時に既存 OS 環境変数を保護する仕組みを実装（読み込み時に protected set を用いる）。
  - 必須の API キー未設定時は明確な ValueError を発生させる。

Known issues / Notes
- 実行に必要な外部依存:
  - OpenAI SDK（コードは OpenAI クライアントを直接利用する実装）。
  - DuckDB（DuckDB に依存する SQL クエリと executemany の挙動）。
  - jquants_client や quality モジュールは参照しており、実稼働ではそれらの実装が必要。
- DB スキーマ:
  - prices_daily / raw_news / news_symbols / ai_scores / market_regime / market_calendar / raw_financials 等のテーブルを前提としている（スキーマは実装側で準備が必要）。
- テスト支援:
  - _call_openai_api 等はテストで patch して差し替え可能。実APIに依存しないユニットテストが可能。
- まだ未実装／将来検討:
  - 一部指標（PBR・配当利回り等）は現バージョンでは未実装で将来拡張検討。

参考（主なファイル）
- src/kabusys/config.py
- src/kabusys/ai/news_nlp.py
- src/kabusys/ai/regime_detector.py
- src/kabusys/data/calendar_management.py
- src/kabusys/data/pipeline.py
- src/kabusys/data/etl.py
- src/kabusys/research/factor_research.py
- src/kabusys/research/feature_exploration.py

ライセンスや貢献方法はリポジトリの README 等を参照してください。